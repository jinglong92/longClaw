from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLES = ROOT / "eval" / "memory_retrieval_samples_2026-04-21.json"
DEFAULT_CUSTOM_ENTRIES = ROOT / "tools" / "artifacts" / "memory_entries.jsonl"
DEFAULT_OUTPUT = ROOT / "eval" / "memory_retrieval_eval_custom_2026-04-21.json"


@dataclass
class CaseResult:
    sample_id: str
    query: str
    domain: str
    expected_sources: list[str]
    expected_keywords: list[str]
    top1_source: str | None
    top3_sources: list[str]
    top1_text: str | None
    hit_at_1: bool
    hit_at_3: bool
    mrr: float
    keyword_hit_at_1: bool
    keyword_hit_at_3: bool


def load_samples(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def import_custom_search_module() -> Any:
    mod_path = ROOT / "tools" / "memory_search.py"
    spec = importlib.util.spec_from_file_location("memory_search_local", mod_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {mod_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def contains_keywords(text: str | None, keywords: list[str]) -> bool:
    if not text:
        return False
    low = text.lower()
    return sum(1 for kw in keywords if kw.lower() in low) >= max(1, min(2, len(keywords)))


def normalize_builtin_result(obj: dict[str, Any]) -> tuple[str | None, list[str], str | None]:
    results = obj.get("results", [])
    if not results:
        return None, [], None
    top1 = results[0]
    return top1.get("path"), [r.get("path") for r in results[:3]], top1.get("snippet")


def evaluate_custom(samples: list[dict[str, Any]], entries_path: Path, top_k: int, hybrid: bool) -> list[CaseResult]:
    mod = import_custom_search_module()
    out: list[CaseResult] = []
    for s in samples:
        hits = mod.search(s["query"], s["domain"], top_k, hybrid, entries_path, False, False)
        top1_source = hits[0].source if hits else None
        top3_sources = [h.source for h in hits[:3]]
        top1_text = hits[0].text if hits else None
        expected_sources = s["expected_sources"]
        hit1 = top1_source in expected_sources
        hit3 = any(src in expected_sources for src in top3_sources)
        mrr = 0.0
        for rank, h in enumerate(hits, start=1):
            if h.source in expected_sources:
                mrr = 1.0 / rank
                break
        out.append(CaseResult(
            sample_id=s["id"],
            query=s["query"],
            domain=s["domain"],
            expected_sources=expected_sources,
            expected_keywords=s["expected_keywords"],
            top1_source=top1_source,
            top3_sources=top3_sources,
            top1_text=top1_text,
            hit_at_1=hit1,
            hit_at_3=hit3,
            mrr=mrr,
            keyword_hit_at_1=contains_keywords(top1_text, s["expected_keywords"]),
            keyword_hit_at_3=any(contains_keywords(h.text, s["expected_keywords"]) for h in hits[:3]),
        ))
    return out


def evaluate_builtin(samples: list[dict[str, Any]], builtin_path: Path) -> list[CaseResult]:
    rows = {row["id"]: row for row in json.loads(builtin_path.read_text(encoding="utf-8"))}
    out: list[CaseResult] = []
    for s in samples:
        row = rows.get(s["id"], {})
        top1_source, top3_sources, top1_text = normalize_builtin_result(row)
        expected_sources = s["expected_sources"]
        hit1 = top1_source in expected_sources
        hit3 = any(src in expected_sources for src in top3_sources)
        mrr = 0.0
        for rank, src in enumerate(top3_sources, start=1):
            if src in expected_sources:
                mrr = 1.0 / rank
                break
        out.append(CaseResult(
            sample_id=s["id"],
            query=s["query"],
            domain=s["domain"],
            expected_sources=expected_sources,
            expected_keywords=s["expected_keywords"],
            top1_source=top1_source,
            top3_sources=top3_sources,
            top1_text=top1_text,
            hit_at_1=hit1,
            hit_at_3=hit3,
            mrr=mrr,
            keyword_hit_at_1=contains_keywords(top1_text, s["expected_keywords"]),
            keyword_hit_at_3=contains_keywords(top1_text, s["expected_keywords"]),
        ))
    return out


def summarize(case_results: list[CaseResult]) -> dict[str, Any]:
    n = len(case_results)
    by_domain: dict[str, list[CaseResult]] = {}
    for r in case_results:
        by_domain.setdefault(r.domain, []).append(r)

    def agg(rows: list[CaseResult]) -> dict[str, float]:
        if not rows:
            return {"n": 0, "hit_at_1": 0.0, "hit_at_3": 0.0, "mrr": 0.0, "keyword_hit_at_1": 0.0, "keyword_hit_at_3": 0.0}
        return {
            "n": len(rows),
            "hit_at_1": round(sum(r.hit_at_1 for r in rows) / len(rows), 4),
            "hit_at_3": round(sum(r.hit_at_3 for r in rows) / len(rows), 4),
            "mrr": round(sum(r.mrr for r in rows) / len(rows), 4),
            "keyword_hit_at_1": round(sum(r.keyword_hit_at_1 for r in rows) / len(rows), 4),
            "keyword_hit_at_3": round(sum(r.keyword_hit_at_3 for r in rows) / len(rows), 4),
        }

    return {
        "overall": agg(case_results),
        "by_domain": {k: agg(v) for k, v in sorted(by_domain.items())},
        "failures_top1": [
            {
                "id": r.sample_id,
                "query": r.query,
                "expected_sources": r.expected_sources,
                "top1_source": r.top1_source,
                "top1_text": r.top1_text,
            }
            for r in case_results if not r.hit_at_1
        ],
    }


def to_jsonable(results: list[CaseResult]) -> list[dict[str, Any]]:
    return [r.__dict__ for r in results]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--samples", type=Path, default=DEFAULT_SAMPLES)
    p.add_argument("--mode", choices=["custom", "builtin"], default="custom")
    p.add_argument("--entries", type=Path, default=DEFAULT_CUSTOM_ENTRIES)
    p.add_argument("--builtin-results", type=Path)
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--fts-only", action="store_true")
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = p.parse_args()

    samples = load_samples(args.samples)
    if args.mode == "custom":
        results = evaluate_custom(samples, args.entries, args.top_k, hybrid=not args.fts_only)
    else:
        if not args.builtin_results:
            raise SystemExit("--builtin-results is required when --mode=builtin")
        results = evaluate_builtin(samples, args.builtin_results)

    report = {
        "mode": args.mode,
        "samples": str(args.samples.relative_to(ROOT)),
        "summary": summarize(results),
        "results": to_jsonable(results),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"]["overall"], ensure_ascii=False, indent=2))
    print(f"[saved] {args.output}")


if __name__ == "__main__":
    main()
