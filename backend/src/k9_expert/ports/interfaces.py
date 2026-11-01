from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from k9_expert.domain.models import Evidence, QueryFilters, SnapshotId, TraceEvent


class DocumentRepository(Protocol):
    def active_snapshot_id(self) -> SnapshotId | None: ...


class FileStore(Protocol):
    def put(self, source: Path, content_hash: str) -> Path: ...


class VectorIndex(Protocol):
    def query(
        self, vector: Sequence[float], snapshot_id: SnapshotId, filters: QueryFilters, limit: int
    ) -> Sequence[Evidence]: ...


class TextGenerator(Protocol):
    alias: str

    def generate(self, system_prompt: str, user_prompt: str) -> str: ...


class Embedder(Protocol):
    alias: str

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...


class OcrEngine(Protocol):
    def extract(self, page_image: Path, language: str) -> str: ...


class Clock(Protocol):
    def now_iso(self) -> str: ...


class Cache(Protocol):
    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str) -> None: ...


class TraceSink(Protocol):
    def emit(self, event: TraceEvent) -> None: ...


class JobExecutor(Protocol):
    def run_once(self) -> bool: ...

