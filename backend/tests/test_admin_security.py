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


def test_settings_load_from_toml_and_lan_exposure_is_explicit(tmp_path) -> None:
    import pytest

    from k9_expert.application.composition import load_settings
    from k9_expert.serve import check_exposure

    config = tmp_path / "k9.toml"
    config.write_text(
        '[server]\nhost = "0.0.0.0"\nallow_lan = false\n'
        "[retrieval]\ntop_k = 4\nsufficiency_minimum_score = 0.7\n"
        "[telemetry]\nstore_protected = false\n"
    )
    env = {"K9_CONFIG": str(config), "K9_DATA_DIR": str(tmp_path / "d")}
    settings = load_settings(env)
    assert (settings.retrieval_top_k, settings.sufficiency_minimum_score) == (4, 0.7)
    assert settings.data_dir == tmp_path / "d" and settings.admin_secret is None
    with pytest.raises(SystemExit, match="allow_lan"):
        check_exposure(settings)
    config.write_text('[server]\nhost = "0.0.0.0"\nallow_lan = true\n')
    with pytest.raises(SystemExit, match="K9_ADMIN_SECRET"):
        check_exposure(load_settings(env))
    check_exposure(load_settings({**env, "K9_ADMIN_SECRET": "s"}))
    check_exposure(load_settings({"K9_CONFIG": str(tmp_path / "absent.toml")}))
    defaults = load_settings({"K9_CONFIG": "config/k9.defaults.toml"})
    assert defaults.host == "127.0.0.1" and defaults.retrieval_top_k == 6
