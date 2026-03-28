from __future__ import annotations

from .adapter_registry import AdapterRegistry
from .backends import LlamaFactoryBackend, MlxLmBackend, TrainingBackend
from .config import SubstrateConfig


def make_backend(config: SubstrateConfig, backend_name: str) -> TrainingBackend:
    registry = AdapterRegistry(config)
    if backend_name == "mlx-lm":
        if not config.flags.mlx_backend_enabled:
            raise RuntimeError("mlx_backend_enabled=false")
        return MlxLmBackend(config, registry)
    if backend_name == "llamafactory":
        if not config.flags.llamafactory_backend_enabled:
            raise RuntimeError("llamafactory_backend_enabled=false")
        return LlamaFactoryBackend(config, registry)
    raise ValueError(f"unsupported backend: {backend_name}")
