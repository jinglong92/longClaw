"""Local-first, backend-pluggable training substrate for OpenClaw."""

from .config import SubstrateConfig, load_config
from .schemas import JudgedTraceRecord, JudgeResult, RewardRecord, TraceRecord

__all__ = [
    "SubstrateConfig",
    "TraceRecord",
    "JudgeResult",
    "JudgedTraceRecord",
    "RewardRecord",
    "load_config",
]
