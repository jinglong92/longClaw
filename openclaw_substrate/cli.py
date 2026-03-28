from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .backend_factory import make_backend
from .config import SubstrateConfig, dump_default_config, load_config
from .dataset_builder import DatasetBuilder
from .gateway import run_gateway
from .judge_plane import JudgePlane, load_judged_records, save_judged_records
from .jsonlog import emit_log, read_jsonl
from .mlx_runtime import run_mlx_server
from .schemas import TraceRecord
from .shadow_eval import compare_baseline_vs_candidate
from .trace_plane import TracePlane, save_next_state


def _load_cfg(path: str | None) -> SubstrateConfig:
    return load_config(path)


def _load_traces(path: Path) -> list[TraceRecord]:
    rows = read_jsonl(path)
    return [TraceRecord(**row) for row in rows]


def cmd_dump_default_config(args: argparse.Namespace) -> int:
    dump_default_config(args.path)
    emit_log("config.default_dumped", {"path": args.path})
    return 0


def cmd_gateway_serve(args: argparse.Namespace) -> int:
    cfg = _load_cfg(args.config)
    run_gateway(cfg)
    return 0


def cmd_mlx_serve(args: argparse.Namespace) -> int:
    cfg = _load_cfg(args.config)
    return run_mlx_server(cfg, dry_run=args.dry_run)


def cmd_trace_assemble(args: argparse.Namespace) -> int:
    cfg = _load_cfg(args.config)
    plane = TracePlane(cfg)
    state = plane.assemble_next_state(args.session_id, args.history_turns)
    save_next_state(state, Path(args.out))
    return 0


def cmd_trace_split(args: argparse.Namespace) -> int:
    cfg = _load_cfg(args.config)
    plane = TracePlane(cfg)
    mainline, sideline = plane.split_mainline_sideline()
    payload = {
        "mainline": len(mainline),
        "sideline": len(sideline),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_judge_run(args: argparse.Namespace) -> int:
    cfg = _load_cfg(args.config)
    in_path = Path(args.input) if args.input else cfg.resolve_path(cfg.paths.traces_raw_jsonl)
    traces = _load_traces(in_path)

    plane = JudgePlane(cfg)
    judged = plane.run(traces)

    out_path = Path(args.output) if args.output else cfg.resolve_path(cfg.paths.traces_rewarded_jsonl)
    save_judged_records(out_path, judged)
    return 0


def cmd_dataset_build(args: argparse.Namespace) -> int:
    cfg = _load_cfg(args.config)
    in_path = Path(args.input) if args.input else cfg.resolve_path(cfg.paths.traces_rewarded_jsonl)
    records = load_judged_records(in_path)

    builder = DatasetBuilder(cfg)
    paths = builder.build_all(records, dataset_name=args.dataset_name)
    print(json.dumps(paths, ensure_ascii=False, indent=2))
    return 0


def cmd_shadow_eval(args: argparse.Namespace) -> int:
    baseline = load_judged_records(Path(args.baseline))
    candidate = load_judged_records(Path(args.candidate))
    report = compare_baseline_vs_candidate(baseline, candidate, Path(args.out))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def cmd_backend_prepare(args: argparse.Namespace) -> int:
    cfg = _load_cfg(args.config)
    backend = make_backend(cfg, args.backend)
    ref = backend.prepare_dataset(Path(args.source), Path(args.out_dir), args.dataset_name)
    print(json.dumps(ref, ensure_ascii=False, indent=2))
    return 0


def cmd_backend_train(args: argparse.Namespace) -> int:
    cfg = _load_cfg(args.config)
    backend = make_backend(cfg, args.backend)

    dataset_ref = {
        "dataset_name": args.dataset_name,
        "path": args.dataset_path,
        "dataset_path": args.dataset_path,
    }
    result = backend.train_adapter(dataset_ref, Path(args.out_dir), args.run_name)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_backend_eval(args: argparse.Namespace) -> int:
    cfg = _load_cfg(args.config)
    backend = make_backend(cfg, args.backend)
    result = backend.evaluate_adapter(Path(args.adapter_path), Path(args.eval_input), Path(args.out))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_backend_export(args: argparse.Namespace) -> int:
    cfg = _load_cfg(args.config)
    backend = make_backend(cfg, args.backend)
    result = backend.export_adapter(Path(args.adapter_path), Path(args.out_dir))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_backend_list(args: argparse.Namespace) -> int:
    cfg = _load_cfg(args.config)
    backend = make_backend(cfg, args.backend)
    adapters = [a.to_dict() for a in backend.list_adapters()]
    print(json.dumps(adapters, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="OpenClaw local-first training substrate CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    cfg = sub.add_parser("config-dump-default", help="Dump default config JSON")
    cfg.add_argument("--path", required=True)
    cfg.set_defaults(func=cmd_dump_default_config)

    g = sub.add_parser("gateway-serve", help="Run OpenAI-compatible local gateway")
    g.add_argument("--config", default=None)
    g.set_defaults(func=cmd_gateway_serve)

    ms = sub.add_parser("mlx-serve", help="Run local MLX-LM server command")
    ms.add_argument("--config", default=None)
    ms.add_argument("--dry-run", action="store_true")
    ms.set_defaults(func=cmd_mlx_serve)

    ta = sub.add_parser("trace-assemble-next-state", help="Assemble next_state from raw traces")
    ta.add_argument("--config", default=None)
    ta.add_argument("--session-id", required=True)
    ta.add_argument("--out", required=True)
    ta.add_argument("--history-turns", type=int, default=None)
    ta.set_defaults(func=cmd_trace_assemble)

    ts = sub.add_parser("trace-split", help="Split mainline vs sideline counts")
    ts.add_argument("--config", default=None)
    ts.set_defaults(func=cmd_trace_split)

    j = sub.add_parser("judge-run", help="Run rule-based judge over traces")
    j.add_argument("--config", default=None)
    j.add_argument("--input", default=None)
    j.add_argument("--output", default=None)
    j.set_defaults(func=cmd_judge_run)

    d = sub.add_parser("dataset-build", help="Build normalized datasets")
    d.add_argument("--config", default=None)
    d.add_argument("--input", default=None)
    d.add_argument("--dataset-name", default="openclaw_trace")
    d.set_defaults(func=cmd_dataset_build)

    se = sub.add_parser("shadow-eval", help="Compare baseline vs candidate judged traces")
    se.add_argument("--baseline", required=True)
    se.add_argument("--candidate", required=True)
    se.add_argument("--out", required=True)
    se.set_defaults(func=cmd_shadow_eval)

    bp = sub.add_parser("backend-prepare-dataset", help="Backend-specific dataset prepare")
    bp.add_argument("--config", default=None)
    bp.add_argument("--backend", choices=["mlx-lm", "llamafactory"], required=True)
    bp.add_argument("--source", required=True)
    bp.add_argument("--out-dir", required=True)
    bp.add_argument("--dataset-name", required=True)
    bp.set_defaults(func=cmd_backend_prepare)

    bt = sub.add_parser("backend-train-adapter", help="Generate adapter training artifacts/templates")
    bt.add_argument("--config", default=None)
    bt.add_argument("--backend", choices=["mlx-lm", "llamafactory"], required=True)
    bt.add_argument("--dataset-name", required=True)
    bt.add_argument("--dataset-path", required=True)
    bt.add_argument("--out-dir", required=True)
    bt.add_argument("--run-name", required=True)
    bt.set_defaults(func=cmd_backend_train)

    be = sub.add_parser("backend-eval-adapter", help="Generate adapter eval artifact")
    be.add_argument("--config", default=None)
    be.add_argument("--backend", choices=["mlx-lm", "llamafactory"], required=True)
    be.add_argument("--adapter-path", required=True)
    be.add_argument("--eval-input", required=True)
    be.add_argument("--out", required=True)
    be.set_defaults(func=cmd_backend_eval)

    bx = sub.add_parser("backend-export-adapter", help="Export adapter artifacts")
    bx.add_argument("--config", default=None)
    bx.add_argument("--backend", choices=["mlx-lm", "llamafactory"], required=True)
    bx.add_argument("--adapter-path", required=True)
    bx.add_argument("--out-dir", required=True)
    bx.set_defaults(func=cmd_backend_export)

    bl = sub.add_parser("backend-list-adapters", help="List registered adapters")
    bl.add_argument("--config", default=None)
    bl.add_argument("--backend", choices=["mlx-lm", "llamafactory"], required=True)
    bl.set_defaults(func=cmd_backend_list)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
