"""Deterministic, model-independent metrics for structured recommendations."""

from __future__ import annotations

import math
from collections.abc import Sequence


def ndcg_at_k(actual: Sequence[str], ideal: Sequence[str], k: int = 3) -> float:
    if k < 1 or not ideal:
        return 0.0
    relevance = {breed: len(ideal) - index for index, breed in enumerate(ideal)}
    dcg = sum(
        relevance.get(breed, 0) / math.log2(index + 2)
        for index, breed in enumerate(actual[:k])
    )
    best = sum(
        relevance[breed] / math.log2(index + 2)
        for index, breed in enumerate(ideal[:k])
    )
    return dcg / best if best else 0.0


def dimension_accuracy(expected: dict[str, str], actual: dict[str, str]) -> float | None:
    labeled = [key for key in expected if key in actual]
    if not labeled:
        return None
    return sum(expected[key] == actual[key] for key in labeled) / len(labeled)


def unknown_handling(expected_unknown: Sequence[str], actual: dict[str, str]) -> bool:
    return all(actual.get(key) == "unknown" for key in expected_unknown)


def citation_page_accuracy(
    expected_pages: set[tuple[str, int]], actual_pages: set[tuple[str, int]]
) -> float | None:
    if not actual_pages:
        return None
    return len(expected_pages & actual_pages) / len(actual_pages)


def structured_coverage(total_attributes: int, documented_attributes: int) -> float:
    return documented_attributes / total_attributes if total_attributes else 0.0
