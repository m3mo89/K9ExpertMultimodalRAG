"""Human answer-accuracy and faithfulness rubric: review sheets and score import.

The generation model under evaluation is never accepted as the evaluator.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean
from typing import Any

from k9_expert.evaluation.dataset import EvaluationCase

RUBRIC_VERSION = "human-rubric-v1"
# Score -> meaning; documented in docs/evaluation/human-rubric-v1.md.
SCALES: dict[str, tuple[str, ...]] = {
    "accuracy": ("0", "1", "2"),
    "faithfulness": ("0", "1", "2"),
    "attribution": ("0", "1", "2", "na"),
    "safety": ("pass", "fail", "na"),
}
SHEET_COLUMNS = (
    "case_id",
    "difficulty_class",
    "expected_state",
    "question",
    "answer_criteria",
    "status",
    "answer",
    "cited_pages",
    "expected_pages",
    *SCALES,
    "notes",
)


def write_review_sheet(
    report: Mapping[str, Any], criteria: Mapping[str, tuple[str, ...]], path: Path
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        for case in report["cases"]:
            writer.writerow(
                {
                    "case_id": case["case_id"],
                    "difficulty_class": case["difficulty_class"],
                    "expected_state": case["expected_state"],
                    "question": case["question"],
                    "answer_criteria": "; ".join(criteria.get(case["case_id"], ())),
                    "status": case["status"],
                    "answer": case["answer"],
                    "cited_pages": " ".join(str(page) for page in case["cited_pages"] or ()),
                    "expected_pages": " ".join(str(page) for page in case["expected_pages"]),
                }
            )


def import_review_sheet(
    report: dict[str, Any],
    path: Path,
    evaluator: str,
    evaluator_kind: str = "human",
    justification: str | None = None,
) -> dict[str, Any]:
    """Attach validated rubric scores and their provenance to a run report."""
    generation_model = str(report["manifest"]["models"].get("text_model", ""))
    if evaluator_kind not in {"human", "independent_model"}:
        raise ValueError("evaluator_kind_must_be_human_or_independent_model")
    if evaluator_kind == "independent_model":
        if not justification:
            raise ValueError("independent_evaluator_requires_justification")
        if evaluator.strip() == generation_model:
            raise ValueError("generation_model_cannot_judge_itself")
    case_ids = {case["case_id"] for case in report["cases"]}
    scores: dict[str, dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            case_id = row["case_id"]
            if case_id not in case_ids:
                raise ValueError(f"unknown_case:{case_id}")
            entry = {name: (row.get(name) or "").strip().lower() for name in SCALES}
            for name, value in entry.items():
                if value not in SCALES[name]:
                    raise ValueError(f"invalid_score:{case_id}:{name}={value or 'blank'}")
            scores[case_id] = {**entry, "notes": (row.get("notes") or "").strip()}
    missing = case_ids - scores.keys()
    if missing:
        raise ValueError(f"unscored_cases:{','.join(sorted(missing))}")
    report["human_rubric"] = {
        "rubric_version": RUBRIC_VERSION,
        "evaluator": evaluator,
        "evaluator_kind": evaluator_kind,
        "justification": justification,
        "imported_at": datetime.now(UTC).isoformat(),
        "aggregate": _aggregate(scores),
        "cases": scores,
    }
    return report


def _aggregate(scores: Mapping[str, Mapping[str, str]]) -> dict[str, object]:
    def mean_of(name: str) -> float | None:
        values = [int(entry[name]) for entry in scores.values() if entry[name] != "na"]
        return fmean(values) / 2 if values else None

    safety = [entry["safety"] for entry in scores.values() if entry["safety"] != "na"]
    return {
        "accuracy": mean_of("accuracy"),
        "faithfulness": mean_of("faithfulness"),
        "attribution": mean_of("attribution"),
        "safety_pass_rate": (
            sum(value == "pass" for value in safety) / len(safety) if safety else None
        ),
        "scale": "0..1 (mean score / 2)",
    }


def criteria_by_case(cases: Sequence[EvaluationCase]) -> dict[str, tuple[str, ...]]:
    return {case.id: case.answer_criteria for case in cases}
