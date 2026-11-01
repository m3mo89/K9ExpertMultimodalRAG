from __future__ import annotations

from dataclasses import replace
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from k9_expert.application.composition import ApplicationSettings, compose
from k9_expert.application.generation import GeneratedAnswer
from k9_expert.application.query import QueryOrchestrator
from k9_expert.application.query_service import QueryService
from k9_expert.domain.models import (
    DocumentId,
    DocumentVersionId,
    Evidence,
    FragmentId,
    SourceRef,
)
from k9_expert.infrastructure.sqlite import (
    DocumentRepository,
    InteractionRepository,
    SqliteDatabase,
)
from k9_expert.presentation.api import create_app


def seeded_client(tmp_path) -> tuple[TestClient, SqliteDatabase, dict[str, str]]:
    settings = ApplicationSettings(data_dir=tmp_path, admin_secret="secret")
    container = compose(settings)
    database = SqliteDatabase(tmp_path / "k9.sqlite")
    ids = {
        name: str(uuid4())
        for name in ("document", "version", "fragment", "snapshot", "page")
    }
    timestamp = "2026-11-01T00:00:00+00:00"
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO documents VALUES "
            "(?, 'Enciclopedia', 'Autor', 'general', 'active', ?, ?, ?)",
            (ids["document"], ids["version"], timestamp, timestamp),
        )
        connection.execute(
            "INSERT INTO document_versions "
            "(id, document_id, content_hash, source_filename, file_path, edition, status, "
            "created_at) VALUES (?, ?, 'hash', 'book.pdf', '/managed/book.pdf', '1', "
            "'active', ?)",
            (ids["version"], ids["document"], timestamp),
        )
        connection.execute(
            "INSERT INTO pages "
            "(id, version_id, physical_page, printed_page_label, extracted_text, "
            "extraction_method) VALUES (?, ?, 7, '5', 'texto de página', 'direct')",
            (ids["page"], ids["version"]),
        )
        connection.execute(
            "INSERT INTO fragments VALUES "
            "(?, ?, 'fh', 0, 'evidencia', '', 7, 7, 'direct', 'v1')",
            (ids["fragment"], ids["version"]),
        )
        connection.execute(
            "INSERT INTO snapshots VALUES "
            "(?, 'embedding-default', 'model', 3, 'active', ?, ?)",
            (ids["snapshot"], timestamp, timestamp),
        )
        connection.execute(
            "INSERT INTO snapshot_membership VALUES (?, ?)",
            (ids["snapshot"], ids["fragment"]),
        )
        connection.execute(
            "INSERT INTO system_state VALUES ('active_snapshot_id', ?)",
            (ids["snapshot"],),
        )
    evidence = Evidence(
        fragment_id=FragmentId(UUID(ids["fragment"])),
        source=SourceRef(
            DocumentId(UUID(ids["document"])),
            DocumentVersionId(UUID(ids["version"])),
            "Enciclopedia",
            "Autor",
            "1",
            7,
            "5",
        ),
        text="evidencia",
        score=0.9,
    )
    orchestrator = QueryOrchestrator(
        lambda _system, _prompt: GeneratedAnswer("Respuesta", (ids["fragment"],)),
        lambda _request: [evidence],
    )
    query_service = QueryService(
        orchestrator, DocumentRepository(database), InteractionRepository(database)
    )
    return TestClient(create_app(replace(container, query_service=query_service))), database, ids


def test_query_citation_history_withdrawal_and_feedback_errors(tmp_path) -> None:
    client, database, ids = seeded_client(tmp_path)
    conversation = client.post("/api/v1/conversations").json()
    conversation_id = conversation["id"]
    response = client.post(
        "/api/v1/queries",
        json={"text": "¿Qué dice del perro?", "conversation_id": conversation_id},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["conversation_id"] == conversation_id
    answer = client.get(f"/api/v1/answers/{result['answer_id']}").json()
    citation_id = answer["citations"][0]["id"]
    assert result["citations"][0] == {
        "id": citation_id,
        "fragment_id": ids["fragment"],
        "document_id": ids["document"],
        "version_id": ids["version"],
        "title": "Enciclopedia",
        "author": "Autor",
        "edition": "1",
        "physical_page": 7,
        "printed_page_label": "5",
        "source_status": "active",
    }
    assert client.get(
        f"/api/v1/citations/{citation_id}/page", params={"physical_page": 7}
    ).json()["extracted_text"] == "texto de página"
    invalid = client.post(
        f"/api/v1/answers/{result['answer_id']}/feedback",
        json={"useful": False, "comment": "x" * 1001},
    )
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "feedback_comment_too_long"
    assert invalid.json()["trace_id"]
    with database.transaction() as connection:
        connection.execute(
            "UPDATE documents SET status = 'deactivated' WHERE id = ?", (ids["document"],)
        )
    citation = client.get(f"/api/v1/citations/{citation_id}").json()
    assert citation["source_status"] == "deactivated"
    assert citation["title"] == "Enciclopedia"

    for index in range(25):
        assert client.post(
            "/api/v1/queries",
            json={"text": f"perro seguimiento {index}", "conversation_id": conversation_id},
        ).status_code == 200
    history = client.get(f"/api/v1/conversations/{conversation_id}").json()["messages"]
    assert len(history) == 20
    assert history[-1]["question"] == "perro seguimiento 24"


def test_common_validation_error_envelope(tmp_path) -> None:
    client, _, _ = seeded_client(tmp_path)
    response = client.post("/api/v1/queries", json={"text": ""})
    assert response.status_code == 422
    assert response.json()["code"] == "request_validation_failed"
    assert response.json()["retryable"] is False


def test_conversation_listing_history_citations_and_current_source_state(tmp_path) -> None:
    client, database, ids = seeded_client(tmp_path)
    conversation_id = client.post("/api/v1/conversations").json()["id"]
    client.post(
        "/api/v1/queries",
        json={"text": "¿Qué dice del perro?", "conversation_id": conversation_id},
    )
    listed = client.get("/api/v1/conversations").json()
    assert listed[0]["id"] == conversation_id
    assert listed[0]["title"] == "¿Qué dice del perro?"
    with database.transaction() as connection:
        connection.execute(
            "UPDATE documents SET status = 'deleted' WHERE id = ?", (ids["document"],)
        )
    message = client.get(f"/api/v1/conversations/{conversation_id}").json()["messages"][0]
    citation = message["citations"][0]
    assert citation["source_status"] == "active"
    assert citation["current_source_status"] == "deleted"
    assert citation["physical_page"] == 7


def test_library_contracts_expose_edition_resource_version_and_safe_job_state(tmp_path) -> None:
    client, database, ids = seeded_client(tmp_path)
    document = client.get("/api/v1/documents").json()[0]
    assert document["edition"] == "1"
    assert document["updated_at"] == "2026-11-01T00:00:00+00:00"
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO ingestion_jobs (id, version_id, stage, attempt, checkpoint, error_code, "
            "error_message, created_at, updated_at) VALUES (?, ?, 'error', 2, 'extracting', "
            "'ingestion_failed', 'Traceback: /secret/path', ?, ?)",
            (str(uuid4()), ids["version"], "2026-11-02T00:00:00Z", "2026-11-02T00:00:00Z"),
        )
    version = client.get(f"/api/v1/documents/{ids['document']}/versions").json()[0]
    assert version["job_stage"] == "error"
    assert version["failed_stage"] == "extracting"
    assert version["error_code"] == "ingestion_failed"
    assert "Traceback" not in str(version)


def test_admin_metrics_require_authorization_and_count_states(tmp_path) -> None:
    client, _, _ = seeded_client(tmp_path)
    client.post("/api/v1/queries", json={"text": "¿Qué dice del perro?"})
    assert client.get("/api/v1/admin/metrics").status_code == 401
    metrics = client.get(
        "/api/v1/admin/metrics", headers={"X-K9-Admin-Secret": "secret"}
    ).json()
    assert metrics["queries"] == {"grounded": 1}
    assert metrics["documents"] == {"active": 1}
