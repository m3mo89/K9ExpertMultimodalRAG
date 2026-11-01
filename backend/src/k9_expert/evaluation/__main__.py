"""CLI: `python -m k9_expert.evaluation run --experiment E2` and `... score`."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from k9_expert.application.composition import ApplicationSettings, compose
from k9_expert.application.generation import OllamaTextGateway
from k9_expert.evaluation.dataset import load_dataset
from k9_expert.evaluation.rubric import criteria_by_case, import_review_sheet, write_review_sheet
from k9_expert.evaluation.runner import (
    NoRagSystem,
    RunContext,
    SemanticRagSystem,
    SystemUnderTest,
    run_experiment,
)
from k9_expert.infrastructure.sqlite import SnapshotRepository, SqliteDatabase

DEFAULT_DATASET = Path("evaluation/datasets/k9-reference-v1.json")
DEFAULT_OUTPUT = Path("evaluation/runs")


def run(args: argparse.Namespace) -> Path:
    settings = ApplicationSettings(data_dir=args.data_dir)
    dataset = load_dataset(args.dataset)
    container = compose(settings)
    gateway = OllamaTextGateway(settings.text_model)
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
        "text_model": settings.text_model,
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


def score(args: argparse.Namespace) -> Path:
    path: Path = args.report
    report = json.loads(path.read_text(encoding="utf-8"))
    import_review_sheet(report, args.sheet, args.evaluator, args.evaluator_kind, args.justification)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m k9_expert.evaluation")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="Run E1 (no RAG) or E2 (semantic RAG).")
    run_parser.add_argument("--experiment", choices=("E1", "E2"), required=True)
    run_parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    run_parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    run_parser.add_argument("--data-dir", type=Path, default=Path("data"))
    run_parser.set_defaults(handler=run)
    score_parser = commands.add_parser("score", help="Import a completed human review sheet.")
    score_parser.add_argument("--report", type=Path, required=True)
    score_parser.add_argument("--sheet", type=Path, required=True)
    score_parser.add_argument("--evaluator", required=True)
    score_parser.add_argument(
        "--evaluator-kind", choices=("human", "independent_model"), default="human"
    )
    score_parser.add_argument("--justification")
    score_parser.set_defaults(handler=score)
    args = parser.parse_args()
    print(args.handler(args))


if __name__ == "__main__":
    main()
