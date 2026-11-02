from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path

import pytest

from k9_expert.application.generation import GeneratedAnswer
from k9_expert.application.query import QueryRequest
from k9_expert.domain.errors import ModelUnavailableError
from k9_expert.domain.models import Evidence
from k9_expert.evaluation.dataset import load_dataset
from k9_expert.evaluation.metrics import (
    Observation,
    aggregate,
    citation_precision,
    evaluate_case,
    recall_at_k,
    reciprocal_rank,
)
from k9_expert.evaluation.rubric import (
    criteria_by_case,
    import_review_sheet,
    write_review_sheet,
)
from k9_expert.evaluation.runner import (
    NoRagSystem,
    RunContext,
    SemanticRagSystem,
    run_experiment,
)
from test_query_policy import evidence

DATASET = Path(__file__).parents[2] / "evaluation" / "datasets" / "k9-reference-v1.json"


def test_reference_dataset_is_versioned_valid_and_reviewed() -> None:
    dataset = load_dataset(DATASET)
    assert (dataset.dataset_id, dataset.version) == ("k9-reference", "1.0.0")
    assert [case.id for case in dataset.cases] == [f"R{n}" for n in range(1, 11)]
    assert all(len(case.review) >= 2 for case in dataset.cases)
    grounded = [case for case in dataset.cases if case.expected_state == "grounded"]
    assert len(grounded) == 8 and all(case.expected_pages for case in grounded)
    assert dataset.cases[9].filters == {"categories": ["Terrier"]}
    reference = dataset.corpus[0]
    assert reference.page_count == 243 and len(reference.sha256) == 64


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda case: case.update(expected_state="maybe"), "expected_state"),
        (lambda case: case.update(review=[]), "review provenance"),
        (lambda case: case.update(expected_evidence=[]), "need expected evidence"),
        (
            lambda case: case["expected_evidence"][0].update(physical_pages=[999]),
            "outside corpus",
        ),
    ],
)
def test_dataset_rejects_unverifiable_cases(tmp_path: Path, mutate, message: str) -> None:  # type: ignore[no-untyped-def]
    raw = json.loads(DATASET.read_text(encoding="utf-8"))
    mutate(raw["cases"][0])
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_dataset(broken)


def test_retrieval_citation_abstention_and_latency_metrics_are_deterministic() -> None:
    assert recall_at_k([5, 104, 9, 106], {104, 106}, 1) == 0.0
    assert recall_at_k([5, 104, 9, 106], {104, 106}, 3) == 0.5
    assert recall_at_k([5, 104, 9, 106], {104, 106}, 5) == 1.0
    assert reciprocal_rank([5, 104, 9], {104, 106}) == 0.5
    assert reciprocal_rank([5, 9], {104}) == 0.0
    assert citation_precision([104, 9], {104, 106}) == 0.5
    assert citation_precision([], {104}) is None

    grounded = evaluate_case(
        "R4",
        "grounded",
        {104, 106},
        Observation("grounded", "x", 100, retrieved_pages=(104, 5), cited_pages=(104,)),
    )
    false_abstention = evaluate_case(
        "R1", "grounded", {27}, Observation("abstained", "", 300, retrieved_pages=())
    )
    correct_abstention = evaluate_case(
        "R9", "abstain", set(), Observation("abstained", "", 50, retrieved_pages=())
    )
    no_rag = evaluate_case("R1", "grounded", {27}, Observation("answered", "x", 200))
    assert grounded.recall_at_k == {1: 0.5, 3: 0.5, 5: 0.5, 8: 0.5}
    assert grounded.citation_precision == 1.0 and grounded.abstention_correct
    assert not false_abstention.abstention_correct and false_abstention.reciprocal_rank == 0.0
    assert correct_abstention.recall_at_k is None and correct_abstention.abstention_correct
    assert no_rag.recall_at_k is None and no_rag.citation_precision is None

    summary = aggregate([grounded, false_abstention, correct_abstention, no_rag])
    assert summary["recall_at_k"] == {1: 0.25, 3: 0.25, 5: 0.25, 8: 0.25}
    assert summary["mrr"] == 0.5
    assert summary["citation_precision"] == 1.0
    assert summary["correct_abstention_rate"] == 1.0
    assert summary["false_abstention_rate"] == 1 / 3
    assert summary["latency_ms"] == {"mean": 162.5, "p50": 100, "p95": 300, "max": 300}


def page_evidence(page: int, score: float = 0.9) -> Evidence:
    item = evidence(score)
    return replace(item, source=replace(item.source, physical_page=page))


def test_e1_and_e2_runs_record_reproducible_configuration(tmp_path: Path) -> None:
    dataset = load_dataset(DATASET)
    pages = {case.question: sorted(case.expected_pages) for case in dataset.cases}
    seen_filters: list[tuple[str, ...]] = []

    def retrieve(request: QueryRequest) -> list[Evidence]:
        seen_filters.append(request.filters.categories)
        if request.filters.categories:
            return []
        return [page_evidence(page) for page in pages[request.text]]

    def generate(_system: str, prompt: str) -> GeneratedAnswer:
        ids = tuple(part.split("'")[0] for part in prompt.split("<evidence id='")[1:])
        return GeneratedAnswer("Según la fuente…", ids[:1])

    context = RunContext(
        models={"text_alias": "text-default", "text_model": "fake"},
        corpus={"snapshot_id": "s1", "fragment_count": 3},
        retrieval={"top_k": 8},
        config_path=Path(__file__).parents[2] / "config" / "k9.defaults.toml",
    )
    e2 = run_experiment(SemanticRagSystem(generate, retrieve, "0" * 32), dataset, context)
    manifest = e2["manifest"]
    assert isinstance(manifest, dict)
    assert manifest["experiment"] == "E2" and manifest["prompt_version"] == "grounded-v4"
    assert manifest["dataset"]["version"] == "1.0.0"
    assert manifest["retrieval"] == {"top_k": 8}
    assert manifest["corpus"] == {"snapshot_id": "s1", "fragment_count": 3}
    assert len(manifest["configuration"]["sha256"]) == 64
    assert "git_commit" in manifest["code"] and manifest["environment"]["python"]
    cases = {case["case_id"]: case for case in e2["cases"]}  # type: ignore[union-attr]
    assert cases["R4"]["retrieved_pages"] == (104, 106)
    assert cases["R10"]["status"] == "abstained", "filters must not widen silently"
    assert ("Terrier",) in seen_filters
    assert cases["R4"]["reciprocal_rank"] == 1.0
    assert cases["R3"]["reciprocal_rank"] == 1.0
    # An abstention before retrieval is recorded as a retrieval miss, never skipped.
    assert (cases["R9"]["retrieved_pages"], cases["R9"]["recall_at_k"]) == ((), None)

    def unavailable(_s: str, _p: str) -> GeneratedAnswer:
        raise ModelUnavailableError()

    e1 = run_experiment(NoRagSystem(unavailable), dataset, replace(context, retrieval=None))
    assert e1["manifest"]["prompt_version"] == "no-rag-v1"  # type: ignore[index]
    assert e1["aggregate"]["recall_at_k"] is None  # type: ignore[index]
    assert {case["status"] for case in e1["cases"]} == {"unavailable"}  # type: ignore[union-attr]


def test_human_rubric_requires_complete_scores_and_independent_evaluator(tmp_path: Path) -> None:
    dataset = load_dataset(DATASET)
    report = run_experiment(
        NoRagSystem(lambda _s, _p: GeneratedAnswer("respuesta", ())),
        dataset,
        RunContext(models={"text_model": "llama3.2:3b"}, corpus={}),
    )
    sheet = tmp_path / "review.csv"
    write_review_sheet(report, criteria_by_case(dataset.cases), sheet)
    rows = list(csv.DictReader(sheet.open(encoding="utf-8")))
    assert rows[0]["answer_criteria"].startswith("cráneo ligeramente convexo")

    with pytest.raises(ValueError, match="invalid_score:R1:accuracy=blank"):
        import_review_sheet(dict(report), sheet, "Revisor")
    for row in rows:
        row.update(accuracy="1", faithfulness="0", attribution="na", safety="na")
    rows[6].update(safety="pass")
    with sheet.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="cannot_judge_itself"):
        import_review_sheet(dict(report), sheet, "llama3.2:3b", "independent_model", "x")

    scored = import_review_sheet(dict(report), sheet, "Revisor humano")
    rubric = scored["human_rubric"]
    assert rubric["evaluator_kind"] == "human" and rubric["rubric_version"] == "human-rubric-v1"
    assert rubric["aggregate"]["accuracy"] == 0.5
    assert rubric["aggregate"]["faithfulness"] == 0.0
    assert rubric["aggregate"]["safety_pass_rate"] == 1.0


def test_rubric_layers_dataset_and_deterministic_layers() -> None:
    from k9_expert.application.routing import ComplexityRouter
    from k9_expert.evaluation.layers import (
        evaluate_cache,
        evaluate_guardrails,
        evaluate_router,
        lexical_embedder,
        load_rubric,
    )

    root = Path(__file__).resolve().parents[2]
    dataset = load_rubric(root / "evaluation/datasets/k9-rubric-v1.json")
    reference = load_dataset(root / "evaluation/datasets/k9-reference-v2.json")
    assert sum(case.expected_state == "grounded" for case in reference.cases) >= 20
    assert len(dataset["breed_match"]) >= 4

    guardrails = evaluate_guardrails(dataset)["aggregate"]
    assert guardrails["detection_rate"] == 1.0  # type: ignore[index]
    assert guardrails["false_block_rate"] == 0.0  # type: ignore[index]
    assert evaluate_router(dataset, ComplexityRouter())["aggregate"]["accuracy"] == 1.0  # type: ignore[index]
    cache = evaluate_cache(dataset, lexical_embedder, 0.92, "lexical")["aggregate"]
    assert cache["separation_violations"] == 0  # type: ignore[index]
    assert cache["exact_hit_rate"] == 1.0  # type: ignore[index]
