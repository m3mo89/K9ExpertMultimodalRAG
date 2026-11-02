"""Threshold calibration on development cases, validated on held-out cases (task 8.4).

The split and the selection rules are fixed in docs/evaluation/acceptance-gates-v1.md before
any score is computed; this module only applies them.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Sequence
from typing import Any

from k9_expert.application.query import QueryRequest
from k9_expert.application.response_cache import analysis_keys
from k9_expert.domain.models import Evidence, QueryFilters
from k9_expert.evaluation.dataset import EvaluationDataset
from k9_expert.evaluation.layers import _cosine, _profile, _text

Retrieve = Callable[[QueryRequest], list[Evidence]]
Embed = Callable[[str], Sequence[float]]

CACHE_DEVELOPMENT = frozenset({"C3", "C5", "C7", "C9"})
CACHE_HELD_OUT = frozenset({"C4", "C6", "C8", "C10"})
EXTRA_NEGATIVES = ("A5", "A6", "G-P07", "G-P08")


def calibrate_sufficiency(
    reference: EvaluationDataset,
    rubric: dict[str, Any],
    retrieve: Retrieve,
    snapshot_id: str,
    current: float,
) -> dict[str, object]:
    samples: list[dict[str, object]] = []
    for case in reference.cases:
        filters = QueryFilters(
            categories=tuple(case.filters.get("categories", ())),
            breeds=tuple(case.filters.get("breeds", ())),
            sections=tuple(case.filters.get("sections", ())),
        )
        samples.append(_sample(case.id, case.question, case.expected_state == "grounded",
                               retrieve, QueryRequest(case.question, filters, snapshot_id)))
    by_id = {item["id"]: item for item in rubric["agent"]}
    by_id |= {item["id"]: item for item in rubric["guardrails"]["problematic"]}
    for identifier in EXTRA_NEGATIVES:
        text = str(by_id[identifier].get("question") or by_id[identifier]["text"])
        samples.append(_sample(identifier, text, False, retrieve,
                               QueryRequest(text, QueryFilters(), snapshot_id)))
    development = [item for item in samples if _number(str(item["id"])) % 2 == 1]
    held_out = [item for item in samples if _number(str(item["id"])) % 2 == 0]
    negatives = [float(str(item["top_score"])) for item in development if not item["positive"]]
    positives = [float(str(item["top_score"])) for item in development if item["positive"]]
    separable = bool(negatives and positives) and max(negatives) < min(positives)
    proposed = (
        round(round((max(negatives) + min(positives)) / 2 / 0.005) * 0.005, 3)
        if separable else current
    )
    return {
        "rule": "midpoint of dev max-negative and min-positive top scores; else keep current",
        "current": current,
        "proposed": proposed,
        "development_separable": separable,
        "development_max_negative": max(negatives) if negatives else None,
        "development_min_positive": min(positives) if positives else None,
        "held_out": _validate(held_out, proposed),
        "held_out_with_current": _validate(held_out, current),
        "samples": samples,
    }


def calibrate_semantic_cache(
    rubric: dict[str, Any], embed: Embed, current: float, floor: float = 0.85
) -> dict[str, object]:
    pairs = []
    for item in rubric["cache"]:
        first = _profile(item["a"], item.get("candidates_a", []))
        second = _profile(item["b"], item.get("candidates_b", []))
        pairs.append({
            "id": item["id"], "expected": item["expected"],
            "split": "development" if item["id"] in CACHE_DEVELOPMENT
            else "held_out" if item["id"] in CACHE_HELD_OUT else "fixed",
            "same_partition": (
                analysis_keys(first, "calibration")[1] == analysis_keys(second, "calibration")[1]
            ),
            "similarity": round(_cosine(embed(_text(first)), embed(_text(second))), 6),
        })
    blocking = [
        float(str(pair["similarity"])) for pair in pairs
        if pair["split"] == "development" and str(pair["expected"]).startswith("separate")
        and pair["same_partition"]
    ]
    proposed = (
        max(floor, math.floor(max(blocking) * 100 + 1) / 100) if blocking else current
    )

    def validate(threshold: float) -> dict[str, object]:
        held = [pair for pair in pairs if pair["split"] == "held_out"]
        return {
            "threshold": threshold,
            # Pairs in different partitions can never be compared by the cache.
            "separation_violations": sum(
                1 for pair in held
                if str(pair["expected"]).startswith("separate") and pair["same_partition"]
                and float(str(pair["similarity"])) >= threshold
            ),
            "paraphrase_hits": sum(
                1 for pair in held
                if pair["expected"] == "semantic_or_miss"
                and float(str(pair["similarity"])) >= threshold
            ),
            "paraphrases": sum(1 for pair in held if pair["expected"] == "semantic_or_miss"),
        }

    return {
        "rule": "lowest 0.01 step above every same-partition dev 'separate' pair, min 0.85",
        "current": current,
        "proposed": proposed,
        "held_out": validate(proposed),
        "held_out_with_current": validate(current),
        "pairs": pairs,
    }


def _sample(
    identifier: str, text: str, positive: bool, retrieve: Retrieve, request: QueryRequest
) -> dict[str, object]:
    evidence = retrieve(request)
    top = max((item.score for item in evidence), default=0.0)
    return {"id": identifier, "positive": positive, "top_score": round(top, 6),
            "question_characters": len(text)}


def _validate(samples: Sequence[dict[str, object]], threshold: float) -> dict[str, object]:
    positives = [item for item in samples if item["positive"]]
    negatives = [item for item in samples if not item["positive"]]
    return {
        "threshold": threshold,
        "false_abstentions": sum(float(str(i["top_score"])) < threshold for i in positives),
        "positives": len(positives),
        "false_passes": sum(float(str(i["top_score"])) >= threshold for i in negatives),
        "negatives": len(negatives),
    }


def _number(identifier: str) -> int:
    found = re.search(r"(\d+)$", identifier)
    return int(found.group(1)) if found else 0
