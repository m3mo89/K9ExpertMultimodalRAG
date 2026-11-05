"""CLI: `python -m k9_expert.evaluation run --experiment E2`, `... layers` and `... score`."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from k9_expert.application.composition import ApplicationSettings, compose
from k9_expert.application.generation import OllamaTextGateway
from k9_expert.application.routing import ComplexityRouter
from k9_expert.evaluation.assertion_precision import (
    extraction_precision,
    read_labels,
    sample_assertions,
    write_sample,
)
from k9_expert.evaluation.calibration import calibrate_semantic_cache, calibrate_sufficiency
from k9_expert.evaluation.dataset import load_dataset
from k9_expert.evaluation.layers import (
    evaluate_agent,
    evaluate_breed_match,
    evaluate_cache,
    evaluate_guardrails,
    evaluate_router,
    lexical_embedder,
    load_rubric,
)
from k9_expert.evaluation.rubric import criteria_by_case, import_review_sheet, write_review_sheet
from k9_expert.evaluation.runner import (
    NoRagSystem,
    RunContext,
    SemanticRagSystem,
    SystemUnderTest,
    code_version,
    configuration_version,
    environment,
    run_experiment,
)
from k9_expert.infrastructure.sqlite import (
    DocumentRepository,
    SnapshotRepository,
    SqliteDatabase,
    StructuredKnowledgeRepository,
)

DEFAULT_DATASET = Path("evaluation/datasets/k9-reference-v2.json")
DEFAULT_RUBRIC = Path("evaluation/datasets/k9-rubric-v1.json")
DEFAULT_OUTPUT = Path("evaluation/runs")


def _settings(args: argparse.Namespace) -> ApplicationSettings:
    """Data directory plus the embedding identity of the index generation under test."""
    overrides = {
        name: value
        for name, value in (
            ("embedding_model", args.embedding_model),
            ("embedding_dimensions", args.embedding_dimensions),
            ("embedding_query_prefix", args.query_prefix),
            ("embedding_document_prefix", args.document_prefix),
        )
        if value is not None
    }
    return ApplicationSettings(data_dir=args.data_dir, **overrides)


def _embedding_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--embedding-model")
    parser.add_argument("--embedding-dimensions", type=int)
    parser.add_argument("--query-prefix")
    parser.add_argument("--document-prefix")


def run(args: argparse.Namespace) -> Path:
    settings = _settings(args)
    dataset = load_dataset(args.dataset)
    container = compose(settings)
    text_model = args.text_model or settings.text_model
    gateway = OllamaTextGateway(
        text_model, context_window=settings.generation_context_window, think=False
    )
    snapshot_id = container.query_service.documents.active_snapshot_id()
    membership = SnapshotRepository(SqliteDatabase(settings.data_dir / "k9.sqlite"))
    corpus = {
        "snapshot_id": snapshot_id,
        "fragment_count": len(membership.active_membership()) if snapshot_id else 0,
        "documents": [
            {"id": row["id"], "title": row["title"], "active_version_id": row["active_version_id"]}
            for row in container.document_service.list_documents()
            if row["status"] == "active"
        ],
    }
    models: dict[str, object] = {
        "text_alias": gateway.alias,
        "text_model": text_model,
        "think": False,
    }
    system: SystemUnderTest
    retrieval: dict[str, object] | None = None
    if args.experiment == "E1":
        system = NoRagSystem(gateway.generate)
    else:
        orchestrator = container.query_service.orchestrator
        system = SemanticRagSystem(gateway.generate, orchestrator.retrieve, snapshot_id)
        retrieval = orchestrator.retrieval_config
        models["embedding_alias"] = "embedding-default"
        models["embedding_model"] = settings.embedding_model
        models["embedding_dimensions"] = settings.embedding_dimensions
        models["embedding_prefixes"] = [
            settings.embedding_query_prefix, settings.embedding_document_prefix,
        ]
    report = run_experiment(
        system, dataset, RunContext(models, corpus, retrieval, settings.config_path)
    )
    report["manifest"]["models"]["text_resolved_model"] = gateway.resolved_model  # type: ignore[index]
    args.out.mkdir(parents=True, exist_ok=True)
    run_id = report["manifest"]["run_id"]  # type: ignore[index]
    path: Path = args.out / f"{run_id}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_review_sheet(report, criteria_by_case(dataset.cases), path.with_suffix(".review.csv"))
    return path


def layers(args: argparse.Namespace) -> Path:
    """Deterministic layers always; `--live` adds the semantic cache, agent and BreedMatch."""
    settings = _settings(args)
    dataset = load_rubric(args.dataset)
    started_at = datetime.now(UTC)
    results: dict[str, object] = {
        "guardrails": evaluate_guardrails(dataset),
        "router": evaluate_router(dataset, ComplexityRouter(settings.router_policy_version)),
    }
    threshold = args.semantic_threshold or settings.semantic_cache_threshold
    if args.live:
        container = compose(settings)
        snapshot_id = container.query_service.documents.active_snapshot_id()
        if snapshot_id is None:
            raise SystemExit("layers --live needs an active snapshot")
        orchestrator = container.query_service.orchestrator
        breed = container.breed_analysis_service
        embed = breed.cache.embed_request if breed.cache else lexical_embedder
        results["cache"] = evaluate_cache(dataset, embed, threshold, settings.embedding_model)
        results["agent"] = evaluate_agent(
            dataset, orchestrator.retrieve, orchestrator.sufficiency, snapshot_id,
            settings.agent_max_iterations,
        )
        results["breed_match"] = evaluate_breed_match(dataset, breed)
    else:
        results["cache"] = evaluate_cache(
            dataset, lexical_embedder, threshold, "lexical-test-double"
        )
    run_id = f"{started_at:%Y%m%dT%H%M%SZ}-LAYERS-{uuid4().hex[:6]}"
    report = {
        "manifest": {
            "run_id": run_id,
            "experiment": "LAYERS",
            "live": args.live,
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "dataset": {
                "id": dataset["dataset_id"], "version": dataset["version"],
                "sha256": dataset["content_sha256"],
            },
            "human_review": dataset.get("review"),
            "models": {
                "text_simple": settings.text_simple_model,
                "text_complex": settings.text_complex_model,
                "text_fallback": settings.text_fallback_model,
                "embedding": settings.embedding_model,
            },
            "policies": {
                "guardrails": settings.guardrail_policy_version,
                "router": settings.router_policy_version,
                "breed_match": settings.breed_match_policy_version,
                "semantic_cache_threshold": threshold,
                "agent_max_iterations": settings.agent_max_iterations,
                "sufficiency_minimum_score": settings.sufficiency_minimum_score,
            },
            "code": code_version(),
            "configuration": configuration_version(settings.config_path),
            "environment": environment(),
        },
        "summary": {
            name: value["aggregate"]  # type: ignore[index]
            for name, value in results.items()
        },
        "layers": results,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    path: Path = args.out / f"{run_id}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def calibrate(args: argparse.Namespace) -> Path:
    """Applies the pre-registered calibration rules; never edits the configuration."""
    settings = _settings(args)
    container = compose(settings)
    snapshot_id = container.query_service.documents.active_snapshot_id()
    if snapshot_id is None:
        raise SystemExit("calibrate needs an active snapshot")
    rubric = load_rubric(args.rubric)
    breed = container.breed_analysis_service
    if breed.cache is None:
        raise SystemExit("calibrate needs the semantic cache embedder")
    started_at = datetime.now(UTC)
    run_id = f"{started_at:%Y%m%dT%H%M%SZ}-CALIBRATION-{uuid4().hex[:6]}"
    report = {
        "manifest": {
            "run_id": run_id,
            "started_at": started_at.isoformat(),
            "datasets": {
                "reference": str(args.dataset), "rubric": str(args.rubric),
                "rubric_sha256": rubric["content_sha256"],
            },
            "embedding_model": settings.embedding_model,
            "rules": "docs/evaluation/acceptance-gates-v1.md#reglas-de-calibración",
            "code": code_version(),
            "configuration": configuration_version(settings.config_path),
            "environment": environment(),
        },
        "sufficiency": calibrate_sufficiency(
            load_dataset(args.dataset), rubric, container.query_service.orchestrator.retrieve,
            snapshot_id, settings.sufficiency_minimum_score,
        ),
        "semantic_cache": calibrate_semantic_cache(
            rubric, breed.cache.embed_request, settings.semantic_cache_threshold
        ),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    path: Path = args.out / f"{run_id}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def score(args: argparse.Namespace) -> Path:
    path: Path = args.report
    report = json.loads(path.read_text(encoding="utf-8"))
    import_review_sheet(report, args.sheet, args.evaluator, args.evaluator_kind, args.justification)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def assertion_sample(args: argparse.Namespace) -> Path:
    database = SqliteDatabase(args.data_dir / "k9.sqlite")
    snapshot = DocumentRepository(database).active_snapshot_id()
    if snapshot is None:
        raise SystemExit("no_active_snapshot")
    rows = StructuredKnowledgeRepository(database).published_rows(snapshot)
    name = f"assertion-sample-{snapshot[:8]}-seed{args.seed}.csv"
    return write_sample(sample_assertions(rows, args.size, args.seed), args.output / name)


def assertion_precision(args: argparse.Namespace) -> str:
    report = extraction_precision(read_labels(args.sheet))
    return json.dumps(report, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m k9_expert.evaluation")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="Run E1 (no RAG) or E2 (semantic RAG).")
    run_parser.add_argument("--experiment", choices=("E1", "E2"), required=True)
    run_parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    run_parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    run_parser.add_argument("--data-dir", type=Path, default=Path("data"))
    run_parser.add_argument("--text-model", help="Local model to benchmark instead of the default.")
    _embedding_arguments(run_parser)
    run_parser.set_defaults(handler=run)
    layers_parser = commands.add_parser("layers", help="Evaluate the mandatory AI layers.")
    layers_parser.add_argument("--dataset", type=Path, default=DEFAULT_RUBRIC)
    layers_parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    layers_parser.add_argument("--data-dir", type=Path, default=Path("data"))
    layers_parser.add_argument(
        "--live", action="store_true", help="Use the local index and embedding model."
    )
    layers_parser.add_argument(
        "--semantic-threshold", type=float, help="Override the configured cache threshold."
    )
    _embedding_arguments(layers_parser)
    layers_parser.set_defaults(handler=layers)
    calibrate_parser = commands.add_parser("calibrate", help="Calibrate thresholds (8.4).")
    calibrate_parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    calibrate_parser.add_argument("--rubric", type=Path, default=DEFAULT_RUBRIC)
    calibrate_parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    calibrate_parser.add_argument("--data-dir", type=Path, default=Path("data"))
    _embedding_arguments(calibrate_parser)
    calibrate_parser.set_defaults(handler=calibrate)
    score_parser = commands.add_parser("score", help="Import a completed human review sheet.")
    score_parser.add_argument("--report", type=Path, required=True)
    score_parser.add_argument("--sheet", type=Path, required=True)
    score_parser.add_argument("--evaluator", required=True)
    score_parser.add_argument(
        "--evaluator-kind", choices=("human", "independent_model"), default="human"
    )
    score_parser.add_argument("--justification")
    score_parser.set_defaults(handler=score)
    sample_parser = commands.add_parser(
        "assertion-sample", help="Export published assertions for manual labeling."
    )
    sample_parser.add_argument("--data-dir", type=Path, default=Path("data"))
    sample_parser.add_argument("--seed", type=int, default=20261104)
    sample_parser.add_argument("--size", type=int, default=50)
    sample_parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    sample_parser.set_defaults(handler=assertion_sample)
    precision_parser = commands.add_parser(
        "assertion-precision", help="Report extraction precision from a labeled sample."
    )
    precision_parser.add_argument("sheet", type=Path)
    precision_parser.set_defaults(handler=assertion_precision)
    args = parser.parse_args()
    print(args.handler(args))


if __name__ == "__main__":
    main()
