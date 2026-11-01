from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from k9_expert.application.admin import AdminSecurityService
from k9_expert.application.composition import ApplicationSettings, compose
from k9_expert.infrastructure.sqlite import SecurityRepository, SqliteDatabase
from k9_expert.presentation.api import create_app


def test_admin_auth_is_audited_and_confirmation_is_bound_and_single_use(tmp_path) -> None:
    settings = ApplicationSettings(data_dir=tmp_path, admin_secret="correct-secret")
    client = TestClient(create_app(compose(settings)))
    denied = client.post(
        "/api/v1/admin/confirmations",
        headers={"x-k9-admin-secret": "wrong", "x-k9-actor": "alice"},
        json={"resource_id": "doc-1", "operation": "delete", "resource_version": "v1"},
    )
    assert denied.status_code == 401
    issued = client.post(
        "/api/v1/admin/confirmations",
        headers={"x-k9-admin-secret": "correct-secret", "x-k9-actor": "alice"},
        json={"resource_id": "doc-1", "operation": "delete", "resource_version": "v1"},
    )
    assert issued.status_code == 200
    token = issued.json()["token"]
    repository = SecurityRepository(SqliteDatabase(tmp_path / "k9.sqlite"))
    security = AdminSecurityService(repository, "correct-secret")
    assert not security.consume_confirmation(token, "bob", "doc-1", "delete", "v1")
    assert not security.consume_confirmation(token, "alice", "doc-1", "delete", "v2")
    assert security.consume_confirmation(token, "alice", "doc-1", "delete", "v1")
    assert not security.consume_confirmation(token, "alice", "doc-1", "delete", "v1")
    actions = [row["action"] for row in repository.audit_events()]
    assert "admin_denied" in actions
    assert "admin_authenticated" in actions
    assert "confirmation_issued" in actions
    assert "confirmation_consumed" in actions


def test_expired_confirmation_is_rejected(tmp_path) -> None:
    database = SqliteDatabase(tmp_path / "k9.sqlite")
    database.migrate()
    repository = SecurityRepository(database)
    expired = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    token = repository.issue_confirmation("alice", "doc-1", "delete", "v1", expired)
    security = AdminSecurityService(repository, "secret")
    assert not security.consume_confirmation(token, "alice", "doc-1", "delete", "v1")
