from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

# MEMORY.md 域块标记格式约束：
# - 必须单独成行，格式严格为 [DOMAIN] 或 (SYSTEM)
# - 不得加 # 前缀（如 ## [JOB] 会被解析器漏掉）
# - BRO 和 SIS 共用 [BRO/SIS] 块（路由注入时 BRO/SIS 均读此块）
DOMAIN_MARKERS = {
    "(SYSTEM)": "SYSTEM",
    "[JOB]": "JOB",
    "[WORK]": "WORK",
    "[LEARN]": "LEARN",
    "[MONEY]": "MONEY",
    "[LIFE]": "LIFE",
    "[PARENT]": "PARENT",
    "[ENGINEER]": "ENGINEER",
    "[BRO/SIS]": "BRO_SIS",
    "[META]": "META",
}

DOMAIN_HINTS = {
    "JOB": ["面试", "offer", "岗位", "投递", "简历", "JD", "薪资", "招聘"],
    "LEARN": ["论文", "paper", "学习", "GRPO", "SFT", "RAG", "教程", "技能"],
    "ENGINEER": ["代码", "部署", "架构", "openclaw", "substrate", "API", "Bug"],
    "WORK": ["绩效", "OKR", "汇报", "职场", "晋升", "上级", "组织"],
    "MONEY": ["理财", "投资", "股票", "基金", "预算"],
    "LIFE": ["Tesla", "健康", "出行", "日程", "设备", "医疗"],
    "PARENT": ["孩子", "育儿", "教育", "亲子", "作息"],
    "BRO_SIS": ["闲聊", "心情", "感情", "关系", "沟通"],
}

ENTITY_PATTERNS = [
    r"(?:敦煌网|美团|字节|阿里|腾讯|百度|华为|京东|滴滴|快手|小红书|Shopee|张宇|丁雪涛|邢轲)",
    r"(?:offer|Offer|OFFER)",
    r"(?:GRPO|PPO|DPO|SFT|LoRA|RAG|GNN|GAT|LLM)",
    r"(?:Tesla|Mac\s*mini|MacBook)",
    r"\d{4}-\d{2}-\d{2}",
]

WEEKDAY_MAP = {
    "周一": 0,
    "周二": 1,
    "周三": 2,
    "周四": 3,
    "周五": 4,
    "周六": 5,
    "周日": 6,
    "周天": 6,
}

EVENT_PATTERNS = {
    "interview": ["面试", "一面", "二面", "三面", "终面"],
    "chat": ["约聊", "初聊", "聊", "聊天", "initial chat"],
    "internal_mobility_chat": ["活水", "internal mobility chat"],
    "offer": ["offer", "发 offer", "口头 offer"],
}


def parse_explicit_domain(text: str) -> str | None:
    m = re.match(r"^\s*-?\s*\[(JOB|WORK|LEARN|MONEY|LIFE|PARENT|ENGINEER|META|BRO/SIS)\]", text)
    if not m:
        return None
    value = m.group(1)
    return "BRO_SIS" if value == "BRO/SIS" else value


def normalize_relative_dates(text: str, base_date_str: str) -> tuple[str, list[str]]:
    base = datetime.strptime(base_date_str, "%Y-%m-%d")
    week_start = base - timedelta(days=base.weekday())
    normalized: list[str] = []

    def add(dt: datetime, *labels: str) -> None:
        normalized.append(dt.strftime("%Y-%m-%d"))
        for label in labels:
            normalized.append(f"{label}={dt.strftime('%Y-%m-%d')}")

    if "今天" in text or "今晚" in text or "今天晚上" in text:
        labels = ["今天"]
        if "今晚" in text:
            labels.append("今晚")
        if "今天晚上" in text or ("今天" in text and "晚上" in text):
            labels.append("今天晚上")
        add(base, *labels)
    if "明天" in text:
        labels = ["明天"]
        if "明天晚上" in text or ("明天" in text and "晚上" in text):
            labels.append("明天晚上")
        add(base + timedelta(days=1), *labels)

    for token, weekday in WEEKDAY_MAP.items():
        if token not in text:
            continue
        target = None
        labels = [token]
        if f"下周{token[-1]}" in text:
            target = week_start + timedelta(days=7 + weekday)
            labels = [f"下周{token[-1]}", token]
        elif f"本周{token[-1]}" in text:
            target = week_start + timedelta(days=weekday)
            labels = [f"本周{token[-1]}", token]
        elif re.search(rf"(?<!下周)(?<!本周){token}", text):
            target = week_start + timedelta(days=weekday)
        if target is not None:
            if "晚上" in text:
                labels.append(f"{labels[0]}晚上")
            add(target, *labels)

    if not normalized:
        return text, []
    normalized = list(dict.fromkeys(normalized))
    return f"{text} [normalized_dates: {'; '.join(normalized)}]", normalized


def extract_entities(text: str) -> list[str]:
    entities: list[str] = []
    for p in ENTITY_PATTERNS:
        entities.extend(re.findall(p, text))
    return sorted(set(entities))


def extract_event_types(text: str) -> list[str]:
    text_lower = text.lower()
    hits: list[str] = []
    for event_type, patterns in EVENT_PATTERNS.items():
        if any(p.lower() in text_lower for p in patterns):
            hits.append(event_type)
    return sorted(set(hits))


def estimate_importance(text: str) -> float:
    high = ["决策", "结论", "P0", "重要", "关键", "offer", "面试", "上线", "已落地", "确认"]
    low = ["待更新", "（待更新）", "TBD"]
    score = 0.5
    lower = text.lower()
    for kw in high:
        if kw.lower() in lower:
            score = min(score + 0.1, 1.0)
    for kw in low:
        if kw.lower() in lower:
            score = max(score - 0.2, 0.1)
    return round(score, 2)


def make_id(source: str, idx: int, text: str) -> str:
    h = hashlib.md5(f"{source}:{idx}:{text[:50]}".encode()).hexdigest()[:8]
    return f"mem_{h}"


def infer_domain(text: str) -> str:
    best, best_n = "SYSTEM", 0
    lower = text.lower()
    for domain, hints in DOMAIN_HINTS.items():
        n = sum(1 for h in hints if h.lower() in lower)
        if n > best_n:
            best, best_n = domain, n
    return best


def parse_memory_md(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    entries: list[dict] = []
    current_domain = "SYSTEM"
    current_lines: list[str] = []

    def flush(domain: str, lines: list[str]) -> None:
        content = "\n".join(lines).strip()
        if not content or content in ("（待更新）", "TBD"):
            return
        for para in re.split(r"\n{2,}", content):
            para = para.strip()
            if len(para) < 10:
                continue
            entries.append(
                {
                    "id": make_id(str(path), len(entries), para),
                    "source": str(path),
                    "source_type": "long_term",
                    "domain": domain,
                    "session_type": "main",
                    "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "text": para,
                    "entities": extract_entities(para),
                    "event_types": extract_event_types(para),
                    "importance": estimate_importance(para),
                    "status": "active",
                }
            )

    for line in text.split("\n"):
        stripped = line.strip()
        matched = None
        for marker, name in DOMAIN_MARKERS.items():
            # 支持两种格式：单独成行的 [JOB] 或带 ## 前缀的 ## [JOB]
            if stripped == marker or stripped == f"## {marker}" or stripped == f"# {marker}":
                matched = name
                break
        if matched:
            flush(current_domain, current_lines)
            current_domain, current_lines = matched, []
        else:
            current_lines.append(line)
    flush(current_domain, current_lines)
    return entries


def parse_daily(path: Path) -> list[dict]:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    date_str = m.group(1) if m else datetime.now().strftime("%Y-%m-%d")
    text = path.read_text(encoding="utf-8", errors="ignore")
    entries: list[dict] = []

    lines = text.splitlines()
    bullets: list[str] = []
    current: list[str] = []
    for raw in lines:
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            if current:
                bullets.append("\n".join(current).strip())
                current = []
            continue
        if line.lstrip().startswith("- "):
            if current:
                bullets.append("\n".join(current).strip())
            current = [line.strip()]
        else:
            if current:
                current.append(line.strip())
            else:
                current = [line.strip()]
    if current:
        bullets.append("\n".join(current).strip())

    for i, para in enumerate(bullets):
        para = para.strip()
        if len(para) < 10:
            continue
        domain = parse_explicit_domain(para) or infer_domain(para)
        searchable_text, normalized_dates = normalize_relative_dates(para, date_str)
        entities = sorted(set(extract_entities(searchable_text) + normalized_dates))
        entries.append(
            {
                "id": make_id(str(path), i, para),
                "source": str(path),
                "source_type": "daily",
                "domain": domain,
                "session_type": "main",
                "created_at": date_str,
                "text": searchable_text,
                "entities": entities,
                "event_types": extract_event_types(searchable_text),
                "importance": estimate_importance(para),
                "status": "active",
            }
        )
    return entries


def build(workspace: Path, output: Path, rebuild: bool = False) -> list[dict]:
    if output.exists() and not rebuild:
        existing = [json.loads(l) for l in output.read_text(encoding="utf-8").splitlines() if l.strip()]
        print(f" [SKIP] 已存在 {len(existing)} 条，使用 --rebuild 强制重建")
        return existing

    all_entries: list[dict] = []
    mem_md = workspace / "MEMORY.md"
    if mem_md.exists():
        e = parse_memory_md(mem_md)
        all_entries.extend(e)
        print(f" [OK] MEMORY.md -> {len(e)} 条")

    mem_dir = workspace / "memory"
    if mem_dir.exists():
        files = sorted(mem_dir.glob("*.md"))
        daily_count = 0
        for f in files:
            e = parse_daily(f)
            all_entries.extend(e)
            daily_count += len(e)
        print(f" [OK] memory/*.md ({len(files)} 文件) -> {daily_count} 条")

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for e in all_entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f" [OK] 共 {len(all_entries)} 条写入 {output}")
    return all_entries


def stats(output: Path) -> None:
    if not output.exists():
        print(f"[ERROR] {output} 不存在，请先运行 memory_entry.py")
        return
    entries = [json.loads(l) for l in output.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"\n=== Memory Entries 统计（共 {len(entries)} 条）===")
    for label, key in (("按域", "domain"), ("按来源", "source_type")):
        print(f"\n{label}：")
        for k, n in sorted(Counter(e[key] for e in entries).items(), key=lambda x: -x[1]):
            print(f" {k:<15} {n}")

    # 老化检测：importance < 0.4 且超过 90 天未更新
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
    stale = [e for e in entries if float(e.get("importance", 0.5)) < 0.4 and e.get("created_at", "9999") < cutoff]
    if stale:
        print(f"\n[stale] 检测到 {len(stale)} 条可能过期条目（importance<0.4 且 >90天）：")
        for e in stale[:10]:
            print(f" [{e['domain']}] {e['created_at']} imp={e['importance']} | {e['text'][:80]}")


def check_stale(workspace: Path, output: Path) -> bool:
    """检查索引是否需要重建：memory/ 或 MEMORY.md 比索引文件更新则返回 True"""
    if not output.exists():
        print("[stale] 索引不存在，需要构建")
        return True

    index_mtime = output.stat().st_mtime

    # 检查 MEMORY.md
    mem_md = workspace / "MEMORY.md"
    if mem_md.exists() and mem_md.stat().st_mtime > index_mtime:
        print(f"[stale] MEMORY.md 比索引新（{datetime.fromtimestamp(mem_md.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}），需要重建")
        return True

    # 检查 memory/*.md
    mem_dir = workspace / "memory"
    if mem_dir.exists():
        for f in mem_dir.glob("*.md"):
            if f.stat().st_mtime > index_mtime:
                print(f"[stale] {f.name} 比索引新，需要重建")
                return True

    print(f"[fresh] 索引是最新的（{datetime.fromtimestamp(index_mtime).strftime('%Y-%m-%d %H:%M:%S')}）")
    return False


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", type=Path, default=Path("."))
    p.add_argument("--output", type=Path, default=Path("tools/artifacts/memory_entries.jsonl"))
    p.add_argument("--rebuild", action="store_true")
    p.add_argument("--stats", action="store_true")
    p.add_argument("--check-stale", action="store_true", help="检查索引是否过期，过期则自动重建")
    args = p.parse_args()

    if args.stats:
        stats(args.output)
        return

    if args.check_stale:
        if check_stale(args.workspace, args.output):
            print("[构建] 索引过期，自动重建...")
            build(args.workspace, args.output, rebuild=True)
        return

    print("[构建] Memory entries...")
    build(args.workspace, args.output, args.rebuild)


if __name__ == "__main__":
    main()
