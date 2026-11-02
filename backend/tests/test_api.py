import sqlite3

from fastapi.testclient import TestClient

from k9_expert.application.composition import ApplicationSettings, compose
from k9_expert.presentation.api import create_app


def test_health_is_loopback_application_contract() -> None:
    response = TestClient(create_app()).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "worker_concurrency": 1}


def test_unexpected_failures_answer_with_a_retryable_envelope(tmp_path, monkeypatch) -> None:
    container = compose(ApplicationSettings(data_dir=tmp_path, admin_secret="secret"))

    def locked(_job_id: str) -> None:
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(container.document_service, "job", locked)
    client = TestClient(create_app(container), raise_server_exceptions=False)
    response = client.get("/api/v1/jobs/job-1", headers={"x-k9-admin-secret": "secret"})
    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "internal_error"
    assert body["retryable"] is True
    assert "locked" not in response.text
