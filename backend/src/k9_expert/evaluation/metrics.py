"""Deterministic evaluation metrics; no model judges any of these values."""

from __future__ import annotations

import math
from collections.abc import Collection, Sequence
from dataclasses import asdict, dataclass
from statistics import fmean

ABSTAINING_STATES = frozenset({"abstained", "rejected", "unavailable", "unverified"})
# Outcomes that prove the model was called: a draft was returned and checked.
MODEL_CALL_REASONS = frozenset({"model_abstained", "invalid_citations", "model_output_invalid"})


@dataclass(frozen=True, slots=True)
class Observation:
    """What a system under test produced for one case."""

    status: str
    answer: str
    latency_ms: float
    retrieved_pages: tuple[int, ...] | None = None  # rank order; None when no retrieval ran
    cited_pages: tuple[int, ...] = ()
    reason: str | None = None
    trace_id: str | None = None


@dataclass(frozen=True, slots=True)
class CaseMetrics:
    case_id: str
    expected_state: str
    status: str
    abstained: bool
    abstention_correct: bool
    recall_at_k: dict[int, float] | None
    reciprocal_rank: float | None
    citation_precision: float | None
    latency_ms: float
    reason: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def recall_at_k(ranked: Sequence[int], expected: Collection[int], k: int) -> float:
    """Fraction of distinct expected pages present in the top-k retrieved pages."""
    if not expected:
        raise ValueError("recall_requires_expected_pages")
    return len(set(ranked[:k]) & set(expected)) / len(set(expected))


def reciprocal_rank(ranked: Sequence[int], expected: Collection[int]) -> float:
    for rank, page in enumerate(ranked, start=1):
        if page in expected:
            return 1 / rank
    return 0.0


def citation_precision(cited: Sequence[int], expected: Collection[int]) -> float | None:
    if not cited:
        return None
    return sum(1 for page in cited if page in expected) / len(cited)


def evaluate_case(
    case_id: str,
    expected_state: str,
    expected_pages: Collection[int],
    observation: Observation,
    ks: Sequence[int] = (1, 3, 5, 8),
) -> CaseMetrics:
    abstained = observation.status in ABSTAINING_STATES
    should_abstain = expected_state != "grounded"
    retrieval = observation.retrieved_pages is not None and bool(expected_pages)
    ranked = observation.retrieved_pages or ()
    return CaseMetrics(
        case_id=case_id,
        expected_state=expected_state,
        status=observation.status,
        abstained=abstained,
        abstention_correct=abstained == should_abstain,
        recall_at_k={k: recall_at_k(ranked, expected_pages, k) for k in ks} if retrieval else None,
        reciprocal_rank=reciprocal_rank(ranked, expected_pages) if retrieval else None,
        citation_precision=(
            citation_precision(observation.cited_pages, expected_pages) if expected_pages else None
        ),
        latency_ms=observation.latency_ms,
        reason=observation.reason,
    )


def aggregate(cases: Sequence[CaseMetrics]) -> dict[str, object]:
    retrieval = [case for case in cases if case.recall_at_k is not None]
    cited = [case for case in cases if case.citation_precision is not None]
    should_abstain = [case for case in cases if case.expected_state != "grounded"]
    should_answer = [case for case in cases if case.expected_state == "grounded"]
    latencies = sorted(case.latency_ms for case in cases)
    ks = sorted({k for case in retrieval for k in (case.recall_at_k or {})})
    called = [
        case for case in cases
        if case.status == "grounded" or case.reason in MODEL_CALL_REASONS
    ]
    return {
        "cases": len(cases),
        "recall_at_k": {
            k: fmean((case.recall_at_k or {})[k] for case in retrieval) for k in ks
        }
        if retrieval
        else None,
        # Hit@K: at least one expected page in the top K (recall > 0).
        "hit_at_k": {
            k: fmean(bool((case.recall_at_k or {})[k]) for case in retrieval) for k in ks
        }
        if retrieval
        else None,
        "mrr": fmean(case.reciprocal_rank or 0.0 for case in retrieval) if retrieval else None,
        "citation_precision": fmean(case.citation_precision or 0.0 for case in cited)
        if cited
        else None,
        "grounded_cases_with_citations": len(cited),
        "structured_output_rate": fmean(
            case.status == "grounded" or case.reason == "model_abstained" for case in called
        )
        if called
        else None,
        "abstention_accuracy": fmean(case.abstention_correct for case in cases) if cases else None,
        "correct_abstention_rate": fmean(case.abstained for case in should_abstain)
        if should_abstain
        else None,
        "false_abstention_rate": fmean(case.abstained for case in should_answer)
        if should_answer
        else None,
        "latency_ms": {
            "mean": fmean(latencies) if latencies else None,
            "p50": _nearest_rank(latencies, 0.50),
            "p95": _nearest_rank(latencies, 0.95),
            "max": latencies[-1] if latencies else None,
        },
    }


def _nearest_rank(sorted_values: Sequence[float], fraction: float) -> float | None:
    if not sorted_values:
        return None
    return sorted_values[max(1, math.ceil(fraction * len(sorted_values))) - 1]
