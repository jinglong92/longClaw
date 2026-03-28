from __future__ import annotations

import shlex
import subprocess

from .config import SubstrateConfig
from .jsonlog import emit_log


def build_mlx_server_cmd(config: SubstrateConfig, host: str = "127.0.0.1", port: int = 8080) -> list[str]:
    return [
        "python3",
        "-m",
        "mlx_lm.server",
        "--model",
        config.mlx.default_base_model,
        "--host",
        host,
        "--port",
        str(port),
    ]


def run_mlx_server(config: SubstrateConfig, dry_run: bool = False) -> int:
    cmd = build_mlx_server_cmd(config)
    emit_log("mlx.server.command", {"cmd": shlex.join(cmd), "dry_run": dry_run})
    if dry_run:
        return 0
    proc = subprocess.run(cmd, check=False)
    return proc.returncode
