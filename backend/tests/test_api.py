from fastapi.testclient import TestClient

from k9_expert.presentation.api import create_app


def test_health_is_loopback_application_contract() -> None:
    response = TestClient(create_app()).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "worker_concurrency": 1}
