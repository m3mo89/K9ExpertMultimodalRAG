import csv
from uuid import uuid4

import pytest

from k9_expert.domain.models import AssertionExtractionState
from k9_expert.evaluation.assertion_precision import (
    extraction_precision,
    read_labels,
    sample_assertions,
    write_sample,
)
from k9_expert.infrastructure.sqlite import StructuredKnowledgeRepository
from test_structured_knowledge import candidate, seeded, stage


def rows(count: int) -> list[dict[str, object]]:
    return [{"assertion_id": f"{index:03d}", "breed": "Raza"} for index in range(count)]


def test_sample_is_reproducible_independent_of_input_order() -> None:
    first = sample_assertions(rows(100), 50, seed=7)
    second = sample_assertions(list(reversed(rows(100))), 50, seed=7)
    assert first == second
    assert len(first) == 50
    assert first != sample_assertions(rows(100), 50, seed=8)
    assert len(sample_assertions(rows(3), 50, seed=7)) == 3
    with pytest.raises(ValueError, match="assertion_sample_size_invalid"):
        sample_assertions(rows(3), 0, seed=7)


def test_precision_excludes_unlabeled_rows_and_reports_per_attribute() -> None:
    report = extraction_precision([
        {"attribute_key": "prey", "label": "correct"},
        {"attribute_key": "prey", "label": "incorrect"},
        {"attribute_key": "terrain", "label": " Correct "},
        {"attribute_key": "terrain", "label": ""},
    ])
    assert report["labeled"] == 3
    assert report["precision"] == 2 / 3
    assert report["attributes"] == {
        "prey": {"labeled": 2, "precision": 0.5},
        "terrain": {"labeled": 1, "precision": 1.0},
    }
    assert extraction_precision([{"attribute_key": "prey", "label": ""}])["precision"] is None
    with pytest.raises(ValueError, match="assertion_label_invalid:quizá"):
        extraction_precision([{"attribute_key": "prey", "label": "quizá"}])


def test_sample_sheet_round_trips_published_assertions(tmp_path) -> None:
    database, snapshot, fragment = seeded(tmp_path)
    repository = StructuredKnowledgeRepository(database)
    candidate(repository, fragment, state=AssertionExtractionState.AUTO_VALIDATED)
    stage(database, snapshot)
    sheet = write_sample(
        sample_assertions(repository.published_rows(snapshot), 5, seed=1),
        tmp_path / "out" / f"{uuid4()}.csv",
    )
    [row] = read_labels(sheet)
    assert (row["breed"], row["value"], row["physical_page"], row["label"]) == (
        "Raza", "rastreo", "7", "",
    )
    assert row["fragment_text"] == "Apto para rastreo"
    with sheet.open(encoding="utf-8", newline="") as stream:
        assert "citation_order" not in next(csv.reader(stream))
