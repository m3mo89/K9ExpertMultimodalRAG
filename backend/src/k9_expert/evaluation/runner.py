"""Reproducible E1 (no-RAG) and E2 (semantic RAG) runs over a versioned dataset."""

from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import sys
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Protocol
from uuid import uuid4

from k9_expert.application.generation import PROMPT_VERSION, GeneratedAnswer
from k9_expert.application.query import QueryOrchestrator, QueryRequest
from k9_expert.domain.errors import DomainError
from k9_expert.domain.models import Evidence, QueryFilters
from k9_expert.evaluation.dataset import EvaluationCase, EvaluationDataset
from k9_expert.evaluation.metrics import Observation, aggregate, evaluate_case

NO_RAG_PROMPT_VERSION = "no-rag-v1"
NO_RAG_SYSTEM_PROMPT = (
    "Responde en español sólo con tu conocimiento general; no tienes documentos. "
    "Si no sabes la respuesta o requiere consejo veterinario individual, devuelve answer vacío. "
    'Devuelve JSON con "answer" y "evidence_ids" como lista vacía.'
)

Generate = Callable[[str, str], GeneratedAnswer]
Retrieve = Callable[[QueryRequest], list[Evidence]]


class SystemUnderTest(Protocol):
    experiment: str
    prompt_version: str

    def answer(self, case: EvaluationCase) -> Observation: ...


class NoRagSystem:
    """E1: the generation model alone, with no retrieval and therefore no citations."""

    experiment = "E1"
    prompt_version = NO_RAG_PROMPT_VERSION

    def __init__(self, generate: Generate) -> None:
        self.generate = generate

    def answer(self, case: EvaluationCase) -> Observation:
        started = perf_counter()
        try:
            draft = self.generate(NO_RAG_SYSTEM_PROMPT, f"Pregunta: {case.question}")
        except DomainError as error:
            return Observation("unavailable", "", _elapsed(started), reason=error.code)
        status = "answered" if draft.answer.strip() else "abstained"
        return Observation(status, draft.answer, _elapsed(started))


class SemanticRagSystem:
    """E2: the production orchestrator with a retrieval recorder for page-level metrics."""

    experiment = "E2"
    prompt_version = PROMPT_VERSION

    def __init__(self, generate: Generate, retrieve: Retrieve, snapshot_id: str | None) -> None:
        self.snapshot_id = snapshot_id
        self._retrieved: list[Evidence] = []

        def recording(request: QueryRequest) -> list[Evidence]:
            found = retrieve(request)
            self._retrieved = list(found)
            return found

        self.orchestrator = QueryOrchestrator(generate, recording)

    def answer(self, case: EvaluationCase) -> Observation:
        self._retrieved = []
        filters = QueryFilters(
            categories=tuple(case.filters.get("categories", ())),
            breeds=tuple(case.filters.get("breeds", ())),
            sections=tuple(case.filters.get("sections", ())),
        )
        started = perf_counter()
        result = self.orchestrator.run(QueryRequest(case.question, filters), self.snapshot_id)
        return Observation(
            status=str(result.status),
            answer=result.answer,
            latency_ms=_elapsed(started),
            retrieved_pages=_unique(item.source.physical_page for item in self._retrieved),
            cited_pages=tuple(citation.source.physical_page for citation in result.citations),
            reason=result.reason,
            trace_id=result.trace_id,
        )


@dataclass(frozen=True, slots=True)
class RunContext:
    """Everything needed to reproduce a run besides the code itself."""

    models: Mapping[str, object]
    corpus: Mapping[str, object]
    retrieval: Mapping[str, object] | None = None
    config_path: Path | None = None
    extra: Mapping[str, object] = field(default_factory=dict)


def run_experiment(
    system: SystemUnderTest, dataset: EvaluationDataset, context: RunContext
) -> dict[str, object]:
    started_at = datetime.now(UTC)
    cases: list[dict[str, object]] = []
    metrics = []
    for case in dataset.cases:
        observation = system.answer(case)
        scored = evaluate_case(case.id, case.expected_state, case.expected_pages, observation)
        metrics.append(scored)
        cases.append(
            {
                **scored.as_dict(),
                "difficulty_class": case.difficulty_class,
                "question": case.question,
                "answer": observation.answer,
                "reason": observation.reason,
                "retrieved_pages": observation.retrieved_pages,
                "cited_pages": observation.cited_pages,
                "expected_pages": sorted(case.expected_pages),
                "trace_id": observation.trace_id,
            }
        )
    return {
        "manifest": {
            "run_id": f"{started_at:%Y%m%dT%H%M%SZ}-{system.experiment}-{uuid4().hex[:6]}",
            "experiment": system.experiment,
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "dataset": {
                "id": dataset.dataset_id,
                "version": dataset.version,
                "sha256": dataset.content_sha256,
            },
            "prompt_version": system.prompt_version,
            "models": dict(context.models),
            "retrieval": dict(context.retrieval) if context.retrieval is not None else None,
            "corpus": dict(context.corpus),
            "code": code_version(),
            "configuration": configuration_version(context.config_path),
            "environment": environment(),
            **dict(context.extra),
        },
        "aggregate": aggregate(metrics),
        "by_class": {
            name: aggregate(
                [
                    scored
                    for scored, case in zip(metrics, dataset.cases, strict=True)
                    if case.difficulty_class == name
                ]
            )
            for name in sorted({case.difficulty_class for case in dataset.cases})
        },
        "cases": cases,
    }


def code_version() -> dict[str, object]:
    def git(*args: str) -> str | None:
        try:
            completed = subprocess.run(
                ["git", *args], capture_output=True, text=True, check=True, timeout=5
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return completed.stdout.strip()

    status = git("status", "--porcelain")
    return {
        "git_commit": git("rev-parse", "HEAD"),
        "git_dirty": bool(status) if status is not None else None,
    }


def configuration_version(path: Path | None) -> dict[str, object] | None:
    if path is None or not path.is_file():
        return None
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def environment() -> dict[str, object]:
    memory: int | None
    try:
        memory = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        memory = None
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "memory_bytes": memory,
    }


def _elapsed(started: float) -> float:
    return round((perf_counter() - started) * 1000, 3)


def _unique(pages: Iterable[int]) -> tuple[int, ...]:
    """Rank-ordered distinct pages: several fragments may come from one page."""
    return tuple(dict.fromkeys(pages))
