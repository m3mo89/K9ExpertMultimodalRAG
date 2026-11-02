from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol

from k9_expert.domain.models import (
    AnalysisFeedback,
    BreedAnalysisId,
    BreedAnalysisProfile,
    BreedAnalysisReport,
    BreedCandidate,
    BreedCriterion,
    CacheLookup,
    Evidence,
    GuardrailDecision,
    QueryFilters,
    RouteDecision,
    SnapshotId,
    TraceEvent,
)


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


class InputGuardrail(Protocol):
    name: str

    def evaluate(
        self, text: str, profile: BreedAnalysisProfile | None = None
    ) -> GuardrailDecision: ...


class OutputGuardrail(Protocol):
    name: str

    def evaluate(
        self, value: str, allowed_evidence_ids: frozenset[str]
    ) -> GuardrailDecision: ...


class ResponseCache(Protocol):
    def lookup(
        self,
        exact_key: str,
        *,
        partition: str,
        snapshot_id: str,
        request_vector: Sequence[float] | None = None,
        semantic_threshold: float | None = None,
    ) -> CacheLookup: ...

    def store(
        self,
        exact_key: str,
        value: str,
        *,
        partition: str,
        snapshot_id: str,
        expires_at: str,
        request_vector: Sequence[float] | None = None,
    ) -> None: ...

    def invalidate_snapshot(self, snapshot_id: str) -> int: ...


class ModelRouter(Protocol):
    def route(self, features: Mapping[str, object]) -> RouteDecision: ...


class ModelGateway(Protocol):
    def generate(self, alias: str, system_prompt: str, user_prompt: str) -> str: ...

    def resolved_model(self, alias: str) -> str | None: ...


class QueryReformulator(Protocol):
    def reformulate(
        self, text: str, evidence: Sequence[Evidence], immutable_terms: Sequence[str] = ()
    ) -> str: ...


class BreedMatcher(Protocol):
    policy_version: str

    def match(
        self,
        profile: BreedAnalysisProfile,
        evidence_by_breed: Mapping[str, Sequence[Evidence]],
    ) -> Sequence[BreedCandidate]: ...


class AnalysisRepository(Protocol):
    def save(self, report: BreedAnalysisReport) -> None: ...

    def get(self, analysis_id: BreedAnalysisId) -> BreedAnalysisReport | None: ...

    def add_feedback(self, feedback: AnalysisFeedback, trace_id: str) -> str: ...


class CriteriaEvidenceRetriever(Protocol):
    def retrieve(
        self,
        criterion: BreedCriterion,
        profile: BreedAnalysisProfile,
        snapshot_id: SnapshotId,
    ) -> Sequence[Evidence]: ...


class TraceSink(Protocol):
    def emit(self, event: TraceEvent) -> None: ...


class JobExecutor(Protocol):
    def run_once(self) -> bool: ...
