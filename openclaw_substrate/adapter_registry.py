from __future__ import annotations

from pathlib import Path

from .config import SubstrateConfig
from .jsonlog import append_jsonl, emit_log, read_jsonl
from .schemas import AdapterRecord


class AdapterRegistry:
    def __init__(self, config: SubstrateConfig):
        self.config = config
        self.path = config.resolve_path(config.paths.adapter_registry_path)

    def register(self, record: AdapterRecord) -> AdapterRecord:
        append_jsonl(self.path, record.to_dict())
        emit_log("adapter.registered", {"adapter_id": record.adapter_id, "backend": record.backend, "status": record.status})
        return record

    def list_adapters(self, backend: str | None = None) -> list[AdapterRecord]:
        rows = read_jsonl(self.path)
        adapters = [AdapterRecord(**row) for row in rows]
        if backend:
            adapters = [a for a in adapters if a.backend == backend]
        return adapters

    def update_status(self, adapter_id: str, status: str, metrics: dict[str, float] | None = None) -> AdapterRecord:
        rows = read_jsonl(self.path)
        updated: AdapterRecord | None = None

        with self.path.open("w", encoding="utf-8") as f:
            for row in rows:
                if row.get("adapter_id") == adapter_id:
                    row["status"] = status
                    if metrics is not None:
                        row["metrics"] = metrics
                    updated = AdapterRecord(**row)
                f.write(__import__("json").dumps(row, ensure_ascii=False) + "\n")

        if updated is None:
            raise KeyError(f"adapter_id not found: {adapter_id}")

        emit_log("adapter.status.updated", {"adapter_id": adapter_id, "status": status})
        return updated

    def get(self, adapter_id: str) -> AdapterRecord:
        for adapter in self.list_adapters():
            if adapter.adapter_id == adapter_id:
                return adapter
        raise KeyError(f"adapter_id not found: {adapter_id}")
