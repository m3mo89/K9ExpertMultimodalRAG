"""Reproducible sample of published assertions and precision from its human labels."""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

SAMPLE_COLUMNS = (
    "assertion_id", "breed", "attribute_key", "value", "polarity", "extraction_method",
    "source_title", "physical_page", "fragment_text", "label",
)
CORRECT = "correct"
INCORRECT = "incorrect"


def sample_assertions(
    rows: Sequence[Mapping[str, object]], size: int, seed: int
) -> list[Mapping[str, object]]:
    if size < 1:
        raise ValueError("assertion_sample_size_invalid")
    ordered = sorted(rows, key=lambda row: str(row["assertion_id"]))
    return random.Random(seed).sample(ordered, min(size, len(ordered)))


def write_sample(rows: Iterable[Mapping[str, object]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=SAMPLE_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({**row, "label": ""} for row in rows)
    return path


def _precision(labels: Sequence[str]) -> float | None:
    return labels.count(CORRECT) / len(labels) if labels else None


def extraction_precision(rows: Iterable[Mapping[str, str]]) -> dict[str, object]:
    """Blank labels stay out of the denominator, so a partial review cannot look better or worse
    than what was actually checked."""
    labeled: list[str] = []
    by_attribute: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        label = row["label"].strip().lower()
        if not label:
            continue
        if label not in {CORRECT, INCORRECT}:
            raise ValueError(f"assertion_label_invalid:{label}")
        labeled.append(label)
        by_attribute[row["attribute_key"]].append(label)
    return {
        "labeled": len(labeled),
        "precision": _precision(labeled),
        "attributes": {
            key: {"labeled": len(values), "precision": _precision(values)}
            for key, values in sorted(by_attribute.items())
        },
    }


def read_labels(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))
