from uuid import uuid4

from fastapi.testclient import TestClient

from k9_expert.application.composition import ApplicationSettings, compose
from k9_expert.domain.models import AssertionPolarity
from k9_expert.infrastructure.sqlite import SqliteDatabase
from k9_expert.presentation.api import create_app
from test_structured_knowledge import seeded


def test_assertion_admin_requires_auth_reviews_and_audits(tmp_path) -> None:
    database, snapshot, fragment = seeded(tmp_path)
    container = compose(ApplicationSettings(data_dir=tmp_path, admin_secret="secret"))
    assertion_id = container.structured_knowledge.create_candidate(
        assertion_id=uuid4(), breed="Raza", attribute_key="modality", value="rastreo",
        polarity=AssertionPolarity.SUPPORTS, fragment_ids=[fragment],
        extraction_method="rule-v1", policy_version="structured-knowledge-v1",
    )
    api = TestClient(create_app(container))
    assert api.get("/api/v2/admin/assertions").status_code == 401
    headers = {"X-K9-Admin-Secret": "secret", "X-K9-Actor": "expert-1"}
    assert api.get("/api/v2/admin/assertions", headers=headers).status_code == 200
    reviewed = api.post(
        f"/api/v2/admin/assertions/{assertion_id}/review", headers=headers,
        json={"decision": "approved", "snapshot_id": snapshot, "comment": "verificado"},
    )
    assert reviewed.status_code == 200
    profile = api.get(
        "/api/v2/breeds/Raza/structured-profile", params={"snapshot_id": snapshot}
    )
    assert profile.status_code == 200
    assert profile.json()["attributes"][0]["assertions"][0]["value"] == "rastreo"
    with SqliteDatabase(tmp_path / "k9.sqlite").connect() as connection:
        actions = {row[0] for row in connection.execute("SELECT action FROM audit_events")}
    assert "assertion_approved" in actions
