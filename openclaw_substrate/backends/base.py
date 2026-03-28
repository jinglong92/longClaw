from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..schemas import AdapterRecord


class TrainingBackend(ABC):
    name: str

    @abstractmethod
    def prepare_dataset(self, source_path: Path, out_dir: Path, dataset_name: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def train_adapter(self, dataset_ref: dict[str, Any], out_dir: Path, run_name: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def evaluate_adapter(self, adapter_path: Path, eval_input: Path, out_path: Path) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def export_adapter(self, adapter_path: Path, out_dir: Path) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def list_adapters(self) -> list[AdapterRecord]:
        raise NotImplementedError
