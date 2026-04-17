"""
inbox_processor.py — 个人知识摄入处理器

扫描 inbox/ 目录，解析 .md/.txt 文件，写入 knowledge_entries.jsonl，
处理完后移动到 inbox/processed/。

用法：
    python3 tools/inbox_processor.py              # 处理所有新文件
    python3 tools/inbox_processor.py --dry-run    # 只预览，不写入
    python3 tools/inbox_processor.py --stats      # 查看知识库统计
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import yaml
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# 复用 memory_entry.py 的域推断和实体提取逻辑
DOMAIN_HINTS = {
    "JOB": ["面试", "offer", "岗位", "投递", "简历", "JD", "薪资", "招聘", "求职"],
    "LEARN": ["论文", "paper", "学习", "GRPO", "SFT", "RAG", "教程", "技能", "Agent", "LLM"],
    "ENGINEER": ["代码", "部署", "架构", "openclaw", "API", "Bug", "hook", "subagent"],
    "WORK": ["绩效", "OKR", "汇报", "职场", "晋升", "上级", "组织"],
    "MONEY": ["理财", "投资", "股票", "基金", "预算"],
    "LIFE": ["Tesla", "健康", "出行", "日程", "设备", "医疗"],
    "PARENT": ["孩子", "育儿", "教育", "亲子", "作息"],
}

ENTITY_PATTERNS = [
    r"(?:敦煌网|美团|字节|阿里|腾讯|百度|华为|京东|滴滴|快手|小红书|Shopee|longClaw|OpenClaw)",
    r"(?:GRPO|PPO|DPO|SFT|LoRA|RAG|GNN|GAT|LLM|Codex)",
    r"(?:Tesla|Mac\s*mini|MacBook)",
    r"[A-Z][a-z]+[A-Z]\w*",
    r"\d{4}-\d{2}-\d{2}",
]

IMPORTANCE_HIGH = ["决策", "结论", "重要", "关键", "P0", "核心", "必读", "关注"]
IMPORTANCE_LOW  = ["待更新", "TBD", "草稿", "draft"]

DEFAULT_INBOX   = Path("inbox")
DEFAULT_OUTPUT  = Path("tools/artifacts/knowledge_entries.jsonl")
DEFAULT_PROCESSED = Path("inbox/processed")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """解析 YAML frontmatter，返回 (meta, body)"""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            try:
                meta = yaml.safe_load(text[3:end]) or {}
                body = text[end + 4:].strip()
                return meta, body
            except Exception:
                pass
    return {}, text


def infer_domain(text: str, meta_domain: str = "") -> str:
    if meta_domain and meta_domain.upper() in DOMAIN_HINTS:
        return meta_domain.upper()
    lower = text.lower()
    best, best_n = "LEARN", 0  # 知识库默认域为 LEARN
    for domain, hints in DOMAIN_HINTS.items():
        n = sum(1 for h in hints if h.lower() in lower)
        if n > best_n:
            best, best_n = domain, n
    return best


def extract_entities(text: str) -> list[str]:
    entities: list[str] = []
    for p in ENTITY_PATTERNS:
        entities.extend(re.findall(p, text))
    return sorted(set(entities))


def estimate_importance(text: str, meta_importance: str = "") -> float:
    if meta_importance == "high":
        return 0.9
    if meta_importance == "low":
        return 0.3
    score = 0.5
    lower = text.lower()
    for kw in IMPORTANCE_HIGH:
        if kw.lower() in lower:
            score = min(score + 0.1, 1.0)
    for kw in IMPORTANCE_LOW:
        if kw.lower() in lower:
            score = max(score - 0.2, 0.1)
    return round(score, 2)


def make_id(source: str, idx: int, text: str) -> str:
    h = hashlib.md5(f"kb:{source}:{idx}:{text[:50]}".encode()).hexdigest()[:8]
    return f"kb_{h}"


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> list[str]:
    """按段落分块，尽量保持语义完整，超长段落按 chunk_size 切割"""
    paragraphs = re.split(r"\n{2,}", text.strip())
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para or len(para) < 20:
            continue
        # 段落本身超长，直接按字符切
        if len(para) > chunk_size * 2:
            for i in range(0, len(para), chunk_size - overlap):
                chunk = para[i:i + chunk_size]
                if len(chunk) >= 20:
                    chunks.append(chunk)
            continue
        # 累积到 chunk_size 再切
        if len(current) + len(para) > chunk_size and current:
            chunks.append(current.strip())
            # overlap：保留上一块末尾
            current = current[-overlap:] + "\n\n" + para if overlap else para
        else:
            current = (current + "\n\n" + para).strip() if current else para

    if current.strip():
        chunks.append(current.strip())
    return chunks


def process_file(path: Path, dry_run: bool = False) -> list[dict]:
    """解析单个文件，返回 entry 列表"""
    text = path.read_text(encoding="utf-8", errors="ignore")
    meta, body = parse_frontmatter(text)

    domain = infer_domain(body, meta.get("domain", ""))
    importance = estimate_importance(body, meta.get("importance", ""))
    tags = meta.get("tags", [])
    title = meta.get("title", path.stem)
    date_str = meta.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    # 从文件名提取日期（如 2026-04-17-xxx.md）
    m = re.match(r"(\d{4}-\d{2}-\d{2})", path.stem)
    if m:
        date_str = m.group(1)

    chunks = chunk_text(body)
    entries = []
    for i, chunk in enumerate(chunks):
        entry = {
            "id": make_id(str(path), i, chunk),
            "source": str(path),
            "source_type": "knowledge",
            "title": title,
            "domain": domain,
            "tags": tags,
            "created_at": date_str,
            "text": chunk,
            "entities": extract_entities(chunk),
            "importance": importance,
            "status": "active",
        }
        entries.append(entry)

    if not dry_run:
        print(f" [OK] {path.name} → {len(entries)} 块 | domain={domain} | importance={importance}")
    else:
        print(f" [DRY] {path.name} → {len(entries)} 块 | domain={domain}")

    return entries


def process_inbox(inbox: Path, output: Path, processed: Path,
                  dry_run: bool = False) -> int:
    """扫描 inbox/，处理所有 .md/.txt 文件"""
    if not inbox.exists():
        print(f"[WARN] inbox/ 目录不存在：{inbox}")
        return 0

    files = [f for f in inbox.glob("*") if f.suffix in (".md", ".txt") and f.name != "README.md"]
    if not files:
        print(f"[OK] inbox/ 无新文件")
        return 0

    print(f"[处理] 发现 {len(files)} 个新文件...")

    all_entries: list[dict] = []
    for f in sorted(files):
        try:
            entries = process_file(f, dry_run=dry_run)
            all_entries.extend(entries)
        except Exception as e:
            print(f" [ERROR] {f.name}: {e}")

    if not dry_run and all_entries:
        # 追加写入（不覆盖已有知识库）
        output.parent.mkdir(parents=True, exist_ok=True)
        existing_ids: set[str] = set()
        if output.exists():
            for line in output.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        existing_ids.add(json.loads(line)["id"])
                    except Exception:
                        pass

        new_entries = [e for e in all_entries if e["id"] not in existing_ids]
        with output.open("a", encoding="utf-8") as f:
            for e in new_entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        print(f" [OK] 新增 {len(new_entries)} 条写入 {output}")

        # 移动到 processed/
        processed.mkdir(parents=True, exist_ok=True)
        for f in files:
            dest = processed / f.name
            if dest.exists():
                dest = processed / f"{f.stem}_{datetime.now().strftime('%H%M%S')}{f.suffix}"
            shutil.move(str(f), str(dest))
            print(f" [移动] {f.name} → processed/")

    return len(all_entries)


def stats(output: Path) -> None:
    if not output.exists():
        print(f"[ERROR] {output} 不存在，请先运行 inbox_processor.py")
        return
    entries = [json.loads(l) for l in output.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"\n=== 知识库统计（共 {len(entries)} 条）===")
    print(f"\n按域：")
    for k, n in sorted(Counter(e["domain"] for e in entries).items(), key=lambda x: -x[1]):
        print(f"  {k:<15} {n}")
    print(f"\n按来源文件（Top 10）：")
    for k, n in sorted(Counter(Path(e["source"]).name for e in entries).items(), key=lambda x: -x[1])[:10]:
        print(f"  {k:<40} {n} 块")


def main() -> None:
    p = argparse.ArgumentParser(description="longClaw 个人知识摄入处理器")
    p.add_argument("--inbox",    type=Path, default=DEFAULT_INBOX)
    p.add_argument("--output",   type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--processed", type=Path, default=DEFAULT_PROCESSED)
    p.add_argument("--dry-run",  action="store_true", help="只预览，不写入不移动")
    p.add_argument("--stats",    action="store_true", help="查看知识库统计")
    args = p.parse_args()

    if args.stats:
        stats(args.output)
        return

    count = process_inbox(args.inbox, args.output, args.processed, dry_run=args.dry_run)
    if count:
        print(f"\n[完成] 共处理 {count} 个条目")
        if not args.dry_run:
            print(f"[提示] 运行 python3 tools/memory_entry.py --rebuild 可将知识库合并到检索索引")


if __name__ == "__main__":
    main()
