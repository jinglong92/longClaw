from __future__ import annotations

import argparse
import json
import re
import subprocess
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

DEFAULT_ENTRIES = Path("tools/artifacts/memory_entries.jsonl")

DOMAIN_HINTS = {
    "JOB": ["job", "career", "offer", "interview", "岗位", "面试", "投递", "简历", "薪资"],
    "LEARN": ["learn", "paper", "study", "论文", "学习", "GRPO", "SFT", "RAG"],
    "ENGINEER": ["engineer", "code", "deploy", "架构", "代码", "openclaw", "substrate"],
    "WORK": ["work", "promotion", "职场", "绩效", "晋升", "汇报"],
    "MONEY": ["money", "finance", "invest", "理财", "投资", "股票"],
    "LIFE": ["life", "health", "travel", "生活", "健康", "Tesla"],
    "PARENT": ["parent", "child", "育儿", "孩子", "教育"],
    "BRO_SIS": ["chat", "mood", "闲聊", "心情", "感情"],
}


@dataclass
class Hit:
    id: str
    source: str
    domain: str
    date: str
    text: str
    entities: list[str]
    score: float
    level: int
    modes: list[str] = field(default_factory=list)

    @property
    def level_label(self) -> str:
        return {2: "同域近期", 3: "同域归档", 4: "跨域"}.get(self.level, "?")

    @property
    def mode_str(self) -> str:
        s = set(self.modes)
        return "hybrid" if len(s) > 1 else (next(iter(s), "fts"))


def load(path: Path = DEFAULT_ENTRIES) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def scope(entries: list[dict], domain: Optional[str], level: int) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    if level == 2 and domain:
        return [e for e in entries if e.get("domain") == domain and e.get("created_at", "") >= cutoff]
    if level == 3 and domain:
        return [e for e in entries if e.get("domain") == domain]
    return entries


ENTITY_PATTERNS = [
    r"(?:敦煌网|美团|字节|阿里|腾讯|百度|华为|京东|滴滴|快手|小红书|Shopee|longClaw|OpenClaw|openclaw)",
    r"(?:offer|Offer|OFFER)",
    r"(?:GRPO|PPO|DPO|SFT|LoRA|RAG|GNN|GAT|LLM|Codex|codex)",
    r"(?:Tesla|Mac\s*mini|MacBook)",
    r"[A-Z][a-z]+[A-Z]\w*",          # camelCase / PascalCase 混合词，如 longClaw
    r"[A-Z]{2,}(?:[A-Z][a-z]+)+",    # 全大写前缀词，如 SFT、GRPO
    r"\d{4}-\d{2}-\d{2}",
]


def extract_entities_from_query(query: str) -> list[str]:
    entities: list[str] = []
    for p in ENTITY_PATTERNS:
        entities.extend(re.findall(p, query))
    return sorted(set(entities))


def rewrite(query: str, domain: Optional[str]) -> list[str]:
    variants = [query]
    if domain and domain in DOMAIN_HINTS:
        variants.append(f"{query} {' '.join(DOMAIN_HINTS[domain][:3])}")
    entities = extract_entities_from_query(query)
    if entities:
        variants.append(" ".join(entities))
    return list(dict.fromkeys(variants))


def fts(query: str, entries: list[dict], top_k: int = 20) -> list[tuple[dict, float]]:
    tokens = set(re.findall(r"\w+", query.lower()))
    if not tokens:
        return []
    scored = []
    for e in entries:
        words = re.findall(r"\w+", e.get("text", "").lower())
        n = len(words) + 1
        tf = sum(words.count(t) / n for t in tokens)
        # 实体精确命中 bonus（精确实体命中比 importance 更重要）
        entity_hits = sum(1 for ent in e.get("entities", []) if ent.lower() in query.lower())
        eb = entity_hits * 0.4
        # importance 作为微调因子（缩小系数，不压过实体命中）
        ib = float(e.get("importance", 0.5)) * 0.05
        # daily 条目 bonus（事实性更强）
        sb = 0.05 if e.get("source_type") == "daily" else 0.0
        s = tf + eb + ib + sb
        if s > 0:
            scored.append((e, s))
    return sorted(scored, key=lambda x: -x[1])[:top_k]


def embed(text: str, model: str = "nomic-embed-text", debug: bool = False) -> Optional[list[float]]:
    # 新版优先：/api/embed + input
    try:
        payload = json.dumps({"model": model, "input": text[:512]}).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        vec = data.get("embedding")
        if not vec and "embeddings" in data and data["embeddings"]:
            vec = data["embeddings"][0]
        if vec:
            if debug:
                print(f" [embed] /api/embed ok len={len(vec)}")
            return vec
    except Exception as e:
        if debug:
            print(f" [embed] /api/embed failed: {e}")

    # 旧版兼容：/api/embeddings + prompt
    try:
        payload = json.dumps({"model": model, "prompt": text[:512]}).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        vec = data.get("embedding")
        if not vec and "embeddings" in data and data["embeddings"]:
            vec = data["embeddings"][0]
        if vec:
            if debug:
                print(f" [embed] /api/embeddings ok len={len(vec)}")
            return vec
    except Exception as e:
        if debug:
            print(f" [embed] /api/embeddings failed: {e}")

    return None


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def rrf(fts_list: list[dict], sem_list: list[dict], k: int = 60) -> list[tuple[dict, float, list[str]]]:
    scores: dict[str, dict] = {}
    for rank, e in enumerate(fts_list):
        eid = e["id"]
        scores.setdefault(eid, {"e": e, "s": 0.0, "m": []})
        scores[eid]["s"] += 1.0 / (k + rank + 1)
        scores[eid]["m"].append("fts")
    for rank, e in enumerate(sem_list):
        eid = e["id"]
        scores.setdefault(eid, {"e": e, "s": 0.0, "m": []})
        scores[eid]["s"] += 1.0 / (k + rank + 1)
        scores[eid]["m"].append("embedding")
    return sorted([(v["e"], v["s"], v["m"]) for v in scores.values()], key=lambda x: -x[1])


def search(query: str, domain: Optional[str] = None, top_k: int = 5, hybrid: bool = False,
           entries_path: Path = DEFAULT_ENTRIES, verbose: bool = False, debug_embed: bool = False) -> list[Hit]:
    all_entries = load(entries_path)
    if not all_entries:
        print(f"[WARN] {entries_path} 不存在或为空，请先运行: python3 tools/memory_entry.py")
        return []

    # 收集所有 level 的候选，最后统一按分数排序
    # level 作为 tiebreaker：同分时 level 小的（更精确的 scope）优先
    candidates: dict[str, Hit] = {}

    for level in [2, 3, 4]:
        pool = [e for e in scope(all_entries, domain, level) if e["id"] not in candidates]
        if not pool:
            continue

        fts_map: dict[str, tuple[dict, float]] = {}
        for q in rewrite(query, domain):
            for e, s in fts(q, pool, top_k=top_k * 4):
                if e["id"] not in fts_map or s > fts_map[e["id"]][1]:
                    fts_map[e["id"]] = (e, s)

        fts_ranked = sorted(fts_map.values(), key=lambda x: -x[1])
        if verbose:
            print(f" [Level {level}] pool={len(pool)} fts_candidates={len(fts_ranked)}")
        if not fts_ranked:
            continue

        if hybrid:
            qvec = embed(query, debug=debug_embed)
            if qvec:
                sem_ranked = sorted(
                    [(e, cosine(qvec, embed(e["text"], debug=debug_embed) or [])) for e, _ in fts_ranked[:top_k * 2]],
                    key=lambda x: -x[1]
                )
                fused = rrf([e for e, _ in fts_ranked], [e for e, _ in sem_ranked])
                for e, s, modes in fused:
                    if e["id"] not in candidates:
                        candidates[e["id"]] = Hit(
                            e["id"], e["source"], e["domain"], e["created_at"],
                            e["text"], e.get("entities", []), s, level, modes)
                continue
            elif verbose:
                print(" [hybrid] embedding unavailable, fallback to fts")

        for e, s in fts_ranked:
            if e["id"] not in candidates:
                candidates[e["id"]] = Hit(
                    e["id"], e["source"], e["domain"], e["created_at"],
                    e["text"], e.get("entities", []), s, level, ["fts"])

        # 扩展条件：结果数 >= 2 且 top1 分数 >= 0.3 时停止（绝对低置信度判断，避免差值过敏感）
        if len(candidates) >= 2:
            top_score = max(h.score for h in candidates.values())
            if top_score >= 0.3:
                break

    sorted_hits = sorted(candidates.values(), key=lambda h: (-h.score, h.level))
    return sorted_hits[:top_k]


def main() -> None:
    p = argparse.ArgumentParser(description="longClaw route-aware memory 检索")
    p.add_argument("--query", required=True)
    p.add_argument("--domain")
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--hybrid", action="store_true")
    p.add_argument("--entries", type=Path, default=DEFAULT_ENTRIES)
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--debug-embed", action="store_true")
    args = p.parse_args()

    print("\n=== Memory 检索 ===")
    print(f"Query: {args.query}")
    print(f"Domain: {args.domain or '(全域)'}")
    print(f"Mode: {'hybrid' if args.hybrid else 'fts-only'}\n")

    hits = search(args.query, args.domain, args.top_k, args.hybrid, args.entries, args.verbose, args.debug_embed)
    if not hits:
        print("(无结果)")
        return

    for i, h in enumerate(hits, 1):
        print(f"[{i}] score={h.score:.3f} mode={h.mode_str} level={h.level_label} domain={h.domain}")
        print(f" {h.source} ({h.date})")
        print(f" {h.text[:160]}{'...' if len(h.text) > 160 else ''}")
        if h.entities:
            print(f" 实体: {', '.join(h.entities[:5])}")
        print()


if __name__ == "__main__":
    main()
