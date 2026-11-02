"""Per-layer rubric evaluation: guardrails, router, caches, agent cycle and BreedMatch.

Labels come from the versioned dataset and were fixed before measurement. Deterministic layers
run offline; `live` layers need the local index and embedding model and never write analyses
to the production database.
"""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path
from statistics import fmean
from time import perf_counter
from typing import Any
from uuid import uuid4

from k9_expert.application.agent import DomainPreservingReformulator
from k9_expert.application.breed_analysis import BreedAnalysisService
from k9_expert.application.generation import GeneratedAnswer
from k9_expert.application.guardrails import InputGuardrailChain
from k9_expert.application.query import EvidenceSufficiencyPolicy, QueryOrchestrator, QueryRequest
from k9_expert.application.response_cache import AnalysisResponseCache
from k9_expert.application.routing import ComplexityRouter
from k9_expert.domain.models import (
    BreedAnalysisProfile,
    BreedAnalysisReport,
    BreedCriterion,
    Evidence,
    TraceEvent,
)
from k9_expert.infrastructure.sqlite import SqliteDatabase, SqliteResponseCache

Embed = Callable[[str], Sequence[float]]
Retrieve = Callable[[QueryRequest], list[Evidence]]


def load_rubric(path: Path) -> dict[str, Any]:
    raw_bytes = path.read_bytes()
    raw: dict[str, Any] = json.loads(raw_bytes)
    guardrails = raw["guardrails"]
    if len(guardrails["problematic"]) < 10 or len(guardrails["normal"]) < 10:
        raise ValueError("invalid_rubric_dataset: at least 10 problematic and 10 normal inputs")
    for section in ("breed_match", "cache", "router", "agent"):
        if not raw.get(section):
            raise ValueError(f"invalid_rubric_dataset: empty {section}")
    raw["content_sha256"] = hashlib.sha256(raw_bytes).hexdigest()
    return raw


def evaluate_guardrails(dataset: dict[str, Any]) -> dict[str, object]:
    chain = InputGuardrailChain()
    cases = []
    for kind in ("problematic", "normal"):
        for item in dataset["guardrails"][kind]:
            repeat = item.get("text_repeat")
            text = repeat["value"] * repeat["times"] if repeat else item["text"]
            started = perf_counter()
            decision = chain.evaluate(text)
            cases.append({
                "id": item["id"], "kind": kind,
                "expected_action": item["expected_action"],
                "expected_reason": item.get("expected_reason"),
                "action": str(decision.action), "reason": decision.reason,
                "action_correct": str(decision.action) == item["expected_action"],
                "reason_correct": item.get("expected_reason") in (None, decision.reason),
                "latency_ms": _ms(started),
            })
    problematic = [case for case in cases if case["kind"] == "problematic"]
    normal = [case for case in cases if case["kind"] == "normal"]
    return {
        "policy": chain.name,
        "aggregate": {
            "cases": len(cases),
            "accuracy": fmean(bool(case["action_correct"]) for case in cases),
            "detection_rate": fmean(case["action"] != "allow" for case in problematic),
            "false_block_rate": fmean(case["action"] != "allow" for case in normal),
            "reason_accuracy": fmean(bool(case["reason_correct"]) for case in problematic),
            "by_reason": dict(Counter(str(case["reason"]) for case in problematic)),
        },
        "cases": cases,
    }


def evaluate_router(dataset: dict[str, Any], router: ComplexityRouter) -> dict[str, object]:
    cases = []
    for item in dataset["router"]:
        decision = router.route(item["features"])
        cases.append({
            "id": item["id"], "expected_alias": item["expected_alias"],
            "expected_reason": item["expected_reason"],
            "alias": decision.alias, "reason": decision.reason,
            "correct": decision.alias == item["expected_alias"]
            and decision.reason == item["expected_reason"],
        })
    return {
        "policy": router.policy_version,
        "aggregate": {
            "cases": len(cases),
            "accuracy": fmean(bool(case["correct"]) for case in cases),
            "distribution": dict(Counter(str(case["alias"]) for case in cases)),
        },
        "cases": cases,
    }


def evaluate_cache(
    dataset: dict[str, Any], embed: Embed, threshold: float, embedder: str
) -> dict[str, object]:
    """Stores profile `a`, then looks up `b` in an isolated temporary cache."""
    cases = []
    snapshot = str(uuid4())
    with tempfile.TemporaryDirectory() as directory:
        database = SqliteDatabase(Path(directory) / "cache.sqlite")
        database.migrate()
        for item in dataset["cache"]:
            # A fresh identity per pair keeps cases independent inside one store.
            cache = AnalysisResponseCache(
                SqliteResponseCache(database), embed, identity=f"eval:{item['id']}",
                semantic_threshold=threshold,
            )
            first = _profile(item["a"], item.get("candidates_a", []))
            second = _profile(item["b"], item.get("candidates_b", []))
            cache.store(first, snapshot, f"source-{item['id']}")
            started = perf_counter()
            hit = cache.get(second, snapshot)
            outcome = "miss" if hit is None else str(hit.hit_type)
            similarity = _cosine(embed(_text(first)), embed(_text(second)))
            cases.append({
                "id": item["id"], "expected": item["expected"], "outcome": outcome,
                "similarity": round(similarity, 6), "threshold": threshold,
                "correct": _cache_correct(item["expected"], outcome),
                "latency_ms": _ms(started),
            })
    separation = [case for case in cases if str(case["expected"]).startswith("separate")]
    paraphrases = [case for case in cases if case["expected"] == "semantic_or_miss"]
    exact = [case for case in cases if case["expected"] == "exact"]
    return {
        "embedder": embedder,
        "threshold": threshold,
        "aggregate": {
            "cases": len(cases),
            "exact_hit_rate": (
                fmean(case["outcome"] == "exact" for case in exact) if exact else None
            ),
            "semantic_hit_rate_on_paraphrases": (
                fmean(case["outcome"] == "semantic" for case in paraphrases)
                if paraphrases else None
            ),
            "separation_violations": sum(case["outcome"] != "miss" for case in separation),
            "profile_separation_rate": (
                fmean(case["outcome"] == "miss" for case in separation) if separation else None
            ),
            "accuracy": fmean(bool(case["correct"]) for case in cases),
        },
        "cases": cases,
    }


def evaluate_agent(
    dataset: dict[str, Any],
    retrieve: Retrieve,
    sufficiency: EvidenceSufficiencyPolicy,
    snapshot_id: str,
    max_iterations: int,
) -> dict[str, object]:
    """Runs the bounded agent with a declining generator, so no model is called."""
    cases = []
    for item in dataset["agent"]:
        sink = _CollectingSink()
        orchestrator = QueryOrchestrator(
            lambda _s, _p: GeneratedAnswer("", ()), retrieve, sink=sink,
            sufficiency=sufficiency, reformulate=DomainPreservingReformulator(),
            agent_max_iterations=max_iterations,
        )
        started = perf_counter()
        orchestrator.run(QueryRequest(item["question"]), snapshot_id)
        attributes = sink.events[0].attributes
        iterations = int(str(attributes.get("agent_iterations", 0)))
        final = "generate" if attributes.get("generation_called") else "abstain"
        cases.append({
            "id": item["id"], "expected_final": item["expected_final"], "final": final,
            "iterations": iterations, "decisions": attributes.get("agent_decisions"),
            "terminated_within_max": iterations <= item["expected_max_iterations"],
            "correct": item["expected_final"] in ("any", final),
            "latency_ms": _ms(started),
        })
    return {
        "max_iterations": max_iterations,
        "sufficiency_min": sufficiency.minimum_score,
        "aggregate": {
            "cases": len(cases),
            "termination_rate": fmean(bool(case["terminated_within_max"]) for case in cases),
            "final_decision_accuracy": fmean(bool(case["correct"]) for case in cases),
            "reformulation_rate": fmean(int(str(case["iterations"])) > 1 for case in cases),
            # Share of reformulated cases whose second retrieval was sufficient to generate.
            "improved_after_reformulation": (
                fmean(case["final"] == "generate" for case in reformulated)
                if (reformulated := [c for c in cases if int(str(c["iterations"])) > 1])
                else None
            ),
            "iterations": dict(Counter(str(case["iterations"]) for case in cases)),
        },
        "cases": cases,
    }


class _CollectingSink:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def emit(self, event: TraceEvent) -> None:
        self.events.append(event)


class _DiscardingRepository:
    """Evaluation never persists analyses into the production database."""

    def save(self, _report: BreedAnalysisReport) -> None:
        return None


def evaluate_breed_match(
    dataset: dict[str, Any], service: BreedAnalysisService
) -> dict[str, object]:
    isolated = _isolated(service)
    cases = []
    findings_total = findings_correct = 0
    cited_in_expected: list[float] = []
    for item in dataset["breed_match"]:
        profile = _profile(item["profile"]["criteria"], item["profile"]["candidate_breeds"])
        started = perf_counter()
        report = isolated.analyze(profile)
        latency = _ms(started)
        actual = {
            (candidate.breed, finding.criterion.key, finding.criterion.value): finding
            for candidate in report.candidates for finding in candidate.findings
        }
        rows = []
        for expected in item["expected_findings"]:
            key = (expected["breed"], expected["criterion_key"], expected["criterion_value"])
            found = actual.get(key)
            outcome = str(found.outcome) if found else "missing"
            pages = sorted({c.source.physical_page for c in found.citations}) if found else []
            if pages and expected["physical_pages"]:
                cited_in_expected.append(
                    sum(page in expected["physical_pages"] for page in pages) / len(pages)
                )
            findings_total += 1
            findings_correct += outcome == expected["outcome"]
            rows.append({**expected, "actual_outcome": outcome, "cited_pages": pages})
        order = [candidate.breed for candidate in report.candidates]
        expected_status = item["expected_status"]
        cases.append({
            "id": item["id"], "expected_status": expected_status, "status": str(report.status),
            "status_correct": str(report.status) in expected_status.split("_or_"),
            "expected_order": item.get("expected_order"), "order": order,
            "order_correct": item.get("expected_order") in (None, order),
            "scores": {c.breed: c.score for c in report.candidates},
            "agent_iterations": report.execution.agent_iterations,
            "findings": rows, "reason": report.reason, "latency_ms": latency,
        })
    return {
        "policy": service.matcher.policy_version,
        "aggregate": {
            "cases": len(cases),
            "status_accuracy": fmean(bool(case["status_correct"]) for case in cases),
            "finding_accuracy": findings_correct / findings_total if findings_total else None,
            "order_accuracy": fmean(bool(case["order_correct"]) for case in cases),
            "citation_page_precision": fmean(cited_in_expected) if cited_in_expected else None,
            "latency_ms_p50": _median([float(str(case["latency_ms"])) for case in cases]),
        },
        "cases": cases,
    }


def _isolated(service: BreedAnalysisService) -> BreedAnalysisService:
    """Same retrieval and matching policy, without cache, narrative or persistence."""
    return BreedAnalysisService(
        service.documents, service.retrieve, service.discover_breeds,
        _DiscardingRepository(),  # type: ignore[arg-type]
        service.matcher, max_candidates=service.max_candidates, router=service.router,
        sufficiency=service.sufficiency, reformulate=service.reformulate,
        agent_max_iterations=service.agent_max_iterations,
        registry=service.registry, discovery_pool=service.discovery_pool,
    )


def lexical_embedder(text: str) -> list[float]:
    """Deterministic hashed bag of words; offline stand-in for the semantic model."""
    vector = [0.0] * 64
    for token in text.lower().replace(":", " ").replace(";", " ").split():
        vector[int(hashlib.sha256(token.encode()).hexdigest(), 16) % 64] += 1.0
    return vector


def _profile(criteria: Sequence[dict[str, Any]], candidates: Sequence[str]) -> BreedAnalysisProfile:
    return BreedAnalysisProfile(
        tuple(BreedCriterion(item["key"], item["value"], float(item.get("weight", 1)))
              for item in criteria),
        tuple(candidates),
    )


def _text(profile: BreedAnalysisProfile) -> str:
    return "; ".join(f"{item.key}: {item.value}" for item in profile.criteria)


def _cache_correct(expected: str, outcome: str) -> bool:
    if expected == "exact":
        return outcome == "exact"
    if expected == "semantic_or_miss":
        return outcome in ("semantic", "miss")
    return outcome == "miss"


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    return dot / norm if norm else 0.0


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(1, math.ceil(0.5 * len(ordered))) - 1]


def _ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 3)

