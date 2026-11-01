from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from k9_expert.application.composition import ApplicationSettings, compose
from k9_expert.application.generation import GeneratedAnswer
from k9_expert.application.ingestion import IngestionWorker
from k9_expert.application.maintenance import ComponentHealth, OperationalMetricsService
from k9_expert.application.observability import TelemetryService
from k9_expert.application.query import QueryOrchestrator, QueryRequest
from k9_expert.application.query_service import QueryService
from k9_expert.domain.errors import ModelUnavailableError
from k9_expert.domain.models import DocumentId, Evidence, FragmentId, QueryFilters, QueryStatus
from k9_expert.infrastructure.sqlite import (
    ContentRepository,
    DocumentRepository,
    InteractionRepository,
    JobRepository,
    SqliteDatabase,
    TraceRepository,
)
from k9_expert.presentation.api import create_app
from test_ingestion import source_pdf
from test_interaction_api import seeded_client
from test_query_policy import evidence

QUESTION = "¿Qué dice del teckel y su salud?"


def off_domain_aware(item: Evidence):  # type: ignore[no-untyped-def]
    """Retrieval double: off-domain questions only find weak evidence."""
    return lambda request: [evidence(0.3) if "Francia" in request.text else item]


def database(tmp_path: Path) -> SqliteDatabase:
    db = SqliteDatabase(tmp_path / "k9.sqlite")
    db.migrate()
    return db


def test_grounded_query_trace_has_versions_timings_and_no_question(tmp_path: Path) -> None:
    traces = TraceRepository(database(tmp_path))
    item = evidence(0.9)
    orchestrator = QueryOrchestrator(
        lambda _s, _p: GeneratedAnswer("respuesta", (str(item.fragment_id),)),
        lambda _r: [item],
        sink=traces,
        resolved_model=lambda: "llama3.2:3b",
        retrieval_config={"top_k": 8},
    )
    snapshot = str(uuid4())
    result = orchestrator.run(QueryRequest(QUESTION), snapshot)

    assert result.status == QueryStatus.GROUNDED and result.trace_id
    stored = traces.get(result.trace_id)
    assert stored is not None
    attributes = stored["attributes"]
    assert isinstance(attributes, dict)
    assert attributes["query_id"] == str(result.query_id)
    assert attributes["snapshot_id"] == snapshot
    assert attributes["prompt_version"] == "grounded-v4"
    assert attributes["resolved_model"] == "llama3.2:3b"
    assert attributes["route"] == "in_domain"
    assert attributes["retrieval"] == {"top_k": 8, "sufficiency_min": 0.68}
    assert attributes["evidence"] == [{"fragment_id": str(item.fragment_id), "score": 0.9}]
    assert attributes["generation_called"] is True and attributes["cache_hit"] is False
    assert attributes["terminal_stage"] == "verification"
    assert [stage["name"] for stage in attributes["stages"]] == [
        "input_policy",
        "cache",
        "route",
        "retrieval",
        "sufficiency",
        "generation",
        "verification",
    ]
    assert attributes["question_characters"] == len(QUESTION)
    assert "teckel" not in json.dumps(stored)


def test_abstention_cache_filters_and_model_failure_are_traced(tmp_path: Path) -> None:
    traces = TraceRepository(database(tmp_path))
    item = evidence(0.9)
    calls = 0

    def generate(_s: str, _p: str) -> GeneratedAnswer:
        nonlocal calls
        calls += 1
        return GeneratedAnswer("respuesta", (str(item.fragment_id),))

    orchestrator = QueryOrchestrator(generate, off_domain_aware(item), sink=traces)
    snapshot = str(uuid4())

    abstained = orchestrator.run(QueryRequest("¿Capital de Francia?"), snapshot)
    trace = traces.get(str(abstained.trace_id))
    assert trace is not None
    attributes = trace["attributes"]
    assert isinstance(attributes, dict)
    assert (attributes["terminal_stage"], attributes["reason"]) == ("sufficiency", "out_of_domain")
    assert attributes["route"] == "uncertain"
    assert attributes["generation_called"] is False

    first = orchestrator.run(QueryRequest("teckel"), snapshot)
    cached = orchestrator.run(QueryRequest("teckel"), snapshot)
    assert cached.query_id != first.query_id
    cached_trace = traces.get(str(cached.trace_id))
    assert cached_trace is not None and cached_trace["attributes"]["cache_hit"] is True  # type: ignore[index]
    filtered = QueryRequest("teckel", QueryFilters(document_ids=(DocumentId(uuid4()),)))
    orchestrator.run(filtered, snapshot)
    assert calls == 2, "a filtered query must not be served from the unfiltered cache entry"

    def unavailable(_s: str, _p: str) -> GeneratedAnswer:
        raise ModelUnavailableError()

    failed = QueryOrchestrator(unavailable, lambda _r: [item], sink=traces).run(
        QueryRequest("teckel"), snapshot
    )
    assert (failed.status, failed.reason) == (QueryStatus.UNAVAILABLE, "model_unavailable")
    failed_trace = traces.get(str(failed.trace_id))
    assert failed_trace is not None
    assert failed_trace["attributes"]["error"] == {  # type: ignore[index]
        "code": "model_unavailable",
        "retryable": True,
    }
    assert failed_trace["attributes"]["terminal_stage"] == "generation"  # type: ignore[index]


def test_ingestion_trace_exposes_stage_timings_counts_and_safe_errors(tmp_path: Path) -> None:
    db = database(tmp_path)
    traces = TraceRepository(db)
    documents, jobs = DocumentRepository(db), JobRepository(db)
    source = tmp_path / "source.pdf"
    source_pdf(source)
    document_id, version_id, job_id = uuid4(), uuid4(), uuid4()
    documents.create_document(document_id, "Teckel", None, None)
    documents.create_version(version_id, document_id, "hash", "source.pdf", str(source))
    jobs.enqueue(job_id, version_id)
    worker = IngestionWorker(
        jobs, ContentRepository(db), sink=traces, embedding_config={"model": "nomic"}
    )
    assert worker.run_once()

    [trace] = traces.list(kind="ingestion", job_id=str(job_id))
    attributes = trace["attributes"]
    assert isinstance(attributes, dict)
    assert attributes["status"] == "completed" and attributes["attempt"] == 1
    assert attributes["page_count"] == 1 and attributes["ocr_page_count"] == 0
    assert attributes["fragment_count"] > 0
    assert attributes["embedding"] == {"model": "nomic"}
    assert attributes["publication"] == {"result": "not_attempted"}
    assert {stage["name"] for stage in attributes["stages"]} == {
        "extracting",
        "ocr",
        "persisting_pages",
        "chunking",
        "persisting_fragments",
    }

    missing_id, missing_job = uuid4(), uuid4()
    secret_path = str(tmp_path / "private" / "missing.pdf")
    documents.create_version(missing_id, document_id, "other", "missing.pdf", secret_path)
    jobs.enqueue(missing_job, missing_id)
    assert worker.run_once()
    [failed] = traces.list(kind="ingestion", job_id=str(missing_job))
    assert failed["attributes"]["status"] == "failed"  # type: ignore[index]
    assert "code" in failed["attributes"]["error"]  # type: ignore[index]
    assert secret_path not in json.dumps(failed)


def test_redaction_privileged_export_and_retention(tmp_path: Path) -> None:
    db = database(tmp_path)
    interactions = InteractionRepository(db)
    item = evidence(0.9)

    def run(store_protected: bool) -> str:
        orchestrator = QueryOrchestrator(
            lambda _s, _p: GeneratedAnswer("respuesta", (str(item.fragment_id),)),
            lambda _r: [item],
            sink=TraceRepository(db, store_protected=store_protected),
        )
        return str(orchestrator.run(QueryRequest(QUESTION), str(uuid4())).trace_id)

    telemetry = TelemetryService(TraceRepository(db), interactions)
    default_trace = run(store_protected=False)
    assert "question" not in telemetry.export(default_trace, include_protected=True)["attributes"]  # type: ignore[index,operator]
    privileged_trace = run(store_protected=True)
    assert "question" not in telemetry.export(privileged_trace)["attributes"]  # type: ignore[index,operator]
    exported = telemetry.export(privileged_trace, include_protected=True)
    assert exported is not None and exported["attributes"]["question"] == QUESTION  # type: ignore[index]

    old = (datetime.now(UTC) - timedelta(days=200)).isoformat()
    with db.transaction() as connection:
        connection.execute("UPDATE traces SET created_at = ? WHERE id = ?", (old, default_trace))
        connection.execute(
            "INSERT INTO queries VALUES ('q', NULL, NULL, NULL, 'grounded', ?)", (old,)
        )
        connection.execute("INSERT INTO answers VALUES ('a', 'q', 'x', 'grounded', ?)", (old,))
        connection.execute("INSERT INTO feedback VALUES ('f', 'a', 0, 'comentario', ?)", (old,))
    assert telemetry.apply_retention() == {"traces_purged": 1, "comments_expired": 1}
    assert telemetry.export(default_trace) is None
    with db.connect() as connection:
        row = connection.execute("SELECT useful, comment FROM feedback").fetchone()
    assert (row["useful"], row["comment"]) == (0, None)


def test_aggregate_metrics_cover_states_latency_cache_ingestion_and_models(
    tmp_path: Path,
) -> None:
    db = database(tmp_path)
    traces = TraceRepository(db)
    item = evidence(0.9)
    orchestrator = QueryOrchestrator(
        lambda _s, _p: GeneratedAnswer("respuesta", (str(item.fragment_id),)),
        off_domain_aware(item),
        sink=traces,
    )
    snapshot = str(uuid4())
    for text in ("teckel", "teckel", "¿Capital de Francia?"):
        orchestrator.run(QueryRequest(text), snapshot)
    metrics = OperationalMetricsService(
        db,
        TelemetryService(traces, InteractionRepository(db)),
        lambda: ComponentHealth("degraded", "model_not_installed"),
    ).report()

    recent = metrics["recent"]
    assert isinstance(recent, dict)
    assert recent["query_states"] == {"grounded": 2, "abstained": 1}
    assert recent["abstention_rate"] == 1 / 3
    assert recent["cache"] == {"hits": 1, "misses": 2}
    assert recent["generation_calls"] == 1
    assert recent["latency_ms"]["count"] == 3 and recent["latency_ms"]["p95"] is not None
    assert recent["ingestion"]["jobs_completed"] == 0
    assert metrics["model_availability"] == {
        "status": "degraded",
        "detail": "model_not_installed",
    }
    assert "queries" in metrics and "jobs" in metrics


def test_query_response_trace_is_admin_only_and_correlates_with_answer(tmp_path: Path) -> None:
    _client, db, ids = seeded_client(tmp_path)
    container = compose(
        ApplicationSettings(data_dir=tmp_path, admin_secret="secret"),
        model_probe=lambda: ComponentHealth("ok", "models_available"),
    )
    item = replace(evidence(0.9), fragment_id=FragmentId(UUID(ids["fragment"])))
    orchestrator = QueryOrchestrator(
        lambda _s, _p: GeneratedAnswer("Respuesta", (ids["fragment"],)),
        lambda _r: [item],
        sink=container.telemetry.traces,
    )
    service = QueryService(orchestrator, DocumentRepository(db), InteractionRepository(db))
    client = TestClient(create_app(replace(container, query_service=service)))

    result = client.post("/api/v1/queries", json={"text": QUESTION}).json()
    assert result["trace_id"]
    assert client.get(f"/api/v1/admin/traces/{result['trace_id']}").status_code == 401
    headers = {"X-K9-Admin-Secret": "secret"}
    trace = client.get(f"/api/v1/admin/traces/{result['trace_id']}", headers=headers).json()
    assert trace["attributes"]["query_id"] == result["query_id"]
    answer = client.get(f"/api/v1/answers/{result['answer_id']}").json()
    assert answer["query_id"] == trace["attributes"]["query_id"]
    listed = client.get("/api/v1/admin/traces", params={"kind": "query"}, headers=headers).json()
    assert [item["trace_id"] for item in listed] == [result["trace_id"]]
    metrics = client.get("/api/v1/admin/metrics", headers=headers).json()
    assert metrics["recent"]["query_states"] == {"grounded": 1}
    assert metrics["model_availability"]["status"] == "ok"
