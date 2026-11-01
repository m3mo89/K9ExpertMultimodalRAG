"""Versioned evaluation dataset: questions, expected evidence, criteria and review provenance."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

ExpectedState = Literal["grounded", "abstain", "filtered_abstain"]
DIFFICULTY_CLASSES = frozenset({"explicit", "comparison", "safety", "unsupported", "filtered"})
EXPECTED_STATES = frozenset({"grounded", "abstain", "filtered_abstain"})


@dataclass(frozen=True, slots=True)
class CorpusSource:
    key: str
    title: str
    sha256: str
    page_count: int
    reference_path: str | None = None


@dataclass(frozen=True, slots=True)
class ExpectedEvidence:
    corpus_key: str
    physical_pages: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    id: str
    difficulty_class: str
    question: str
    expected_evidence: tuple[ExpectedEvidence, ...]
    answer_criteria: tuple[str, ...]
    expected_state: ExpectedState
    filters: dict[str, list[str]]
    review: tuple[dict[str, Any], ...]

    @property
    def expected_pages(self) -> frozenset[int]:
        return frozenset(page for item in self.expected_evidence for page in item.physical_pages)


@dataclass(frozen=True, slots=True)
class EvaluationDataset:
    dataset_id: str
    version: str
    content_sha256: str
    corpus: tuple[CorpusSource, ...]
    cases: tuple[EvaluationCase, ...]


def load_dataset(path: Path) -> EvaluationDataset:
    raw_bytes = path.read_bytes()
    raw = json.loads(raw_bytes)
    corpus = tuple(
        CorpusSource(
            key=str(item["key"]),
            title=str(item["title"]),
            sha256=str(item["sha256"]),
            page_count=int(item["page_count"]),
            reference_path=item.get("reference_path"),
        )
        for item in raw["corpus"]
    )
    pages_by_source = {source.key: source.page_count for source in corpus}
    cases: list[EvaluationCase] = []
    for item in raw["cases"]:
        case_id = str(item["id"])
        evidence = tuple(
            ExpectedEvidence(str(ref["corpus_key"]), tuple(int(p) for p in ref["physical_pages"]))
            for ref in item["expected_evidence"]
        )
        state = str(item["expected_state"])
        _check(state in EXPECTED_STATES, f"{case_id}: unknown expected_state {state}")
        _check(
            item["difficulty_class"] in DIFFICULTY_CLASSES,
            f"{case_id}: unknown difficulty_class {item['difficulty_class']}",
        )
        _check(bool(item.get("review")), f"{case_id}: missing review provenance")
        _check(
            state != "grounded" or bool(evidence),
            f"{case_id}: grounded cases need expected evidence",
        )
        for ref in evidence:
            _check(ref.corpus_key in pages_by_source, f"{case_id}: unknown corpus {ref.corpus_key}")
            _check(
                all(1 <= page <= pages_by_source[ref.corpus_key] for page in ref.physical_pages),
                f"{case_id}: page outside corpus range",
            )
        cases.append(
            EvaluationCase(
                id=case_id,
                difficulty_class=str(item["difficulty_class"]),
                question=str(item["question"]),
                expected_evidence=evidence,
                answer_criteria=tuple(str(value) for value in item["answer_criteria"]),
                expected_state=state,  # type: ignore[arg-type]
                filters={key: list(value) for key, value in item.get("filters", {}).items()},
                review=tuple(item["review"]),
            )
        )
    _check(len({case.id for case in cases}) == len(cases), "duplicate case ids")
    return EvaluationDataset(
        dataset_id=str(raw["dataset_id"]),
        version=str(raw["version"]),
        content_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        corpus=corpus,
        cases=tuple(cases),
    )


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(f"invalid_evaluation_dataset: {message}")
