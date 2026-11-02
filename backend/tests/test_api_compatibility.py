from fastapi.testclient import TestClient

from k9_expert.application.composition import ApplicationSettings, compose
from k9_expert.presentation.api import create_app


def test_existing_api_routes_remain_available(tmp_path) -> None:
    """Contract fence for clients that predate the BreedMatch change."""
    container = compose(ApplicationSettings(data_dir=tmp_path, admin_secret="secret"))
    app = create_app(container)
    operations = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }
    required = {
        ("GET", "/api/v1/health"),
        ("POST", "/api/v1/queries"),
        ("GET", "/api/v1/documents"),
        ("POST", "/api/v1/documents"),
        ("POST", "/api/v1/documents/{document_id}/versions"),
        ("DELETE", "/api/v1/documents/{document_id}"),
        ("GET", "/api/v1/conversations"),
        ("POST", "/api/v1/conversations"),
        ("GET", "/api/v1/conversations/{conversation_id}"),
        ("GET", "/api/v1/answers/{answer_id}"),
        ("POST", "/api/v1/answers/{answer_id}/feedback"),
        ("GET", "/api/v1/citations/{citation_id}"),
        ("GET", "/api/v1/citations/{citation_id}/page"),
        ("GET", "/api/v1/admin/metrics"),
        ("GET", "/api/v1/admin/backups"),
        ("POST", "/api/v1/admin/backups"),
        ("POST", "/api/v1/admin/backups/{backup_id}/restore"),
    }
    assert required <= operations


def test_existing_openapi_schemas_and_error_envelope_are_stable(tmp_path) -> None:
    container = compose(ApplicationSettings(data_dir=tmp_path, admin_secret="secret"))
    client = TestClient(create_app(container))
    document_schema = client.get("/openapi.json").json()["components"]["schemas"]
    assert set(document_schema["QueryResponse"]["properties"]) >= {
        "query_id",
        "answer_id",
        "status",
        "answer",
        "snapshot_id",
        "reason",
        "citations",
        "conversation_id",
        "trace_id",
        "discrepancy",
    }
    assert set(document_schema["DocumentResponse"]["properties"]) >= {
        "id",
        "title",
        "status",
        "active_version_id",
        "updated_at",
    }
    invalid = client.post("/api/v1/queries", json={"text": ""})
    assert invalid.status_code == 422
    assert set(invalid.json()) == {"code", "message", "details", "trace_id", "retryable"}
