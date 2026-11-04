from fastapi.testclient import TestClient

from k9_expert.application.composition import ApplicationSettings, compose
from k9_expert.presentation.api import create_app


def client(tmp_path) -> TestClient:  # type: ignore[no-untyped-def]
    return TestClient(create_app(compose(ApplicationSettings(data_dir=tmp_path))))


def test_profile_validation_is_versioned_and_does_not_change_v1_contract(tmp_path) -> None:
    api = client(tmp_path)
    response = api.post("/api/v2/hunter-profiles/validate", json={"answers": [
        {"key": "prey", "values": ["venado"]},
        {"key": "modality", "values": ["rastreo"], "importance": "required"},
        {"key": "terrain", "values": ["monte_denso"]},
        {"key": "experience", "values": ["principiante"]},
        {"key": "daily_availability", "values": ["1_2h"]},
    ]})
    assert response.status_code == 200
    assert response.json()["completeness"] == "complete"
    assert response.json()["constraints"] == ["modality"]
    paths = api.get("/openapi.json").json()["paths"]
    assert "/api/v1/breed-analyses" in paths
    assert "/api/v2/hunter-profiles/validate" in paths


def test_profile_validation_reports_missing_fields_and_stable_value_error(tmp_path) -> None:
    api = client(tmp_path)
    incomplete = api.post("/api/v2/hunter-profiles/validate", json={"answers": [
        {"key": "prey", "values": ["venado"]},
        {"key": "hunting_frequency", "values": ["ocasional"]},
    ]})
    assert incomplete.status_code == 200
    assert "daily_availability" in incomplete.json()["missing_fields"]
    invalid = api.post("/api/v2/hunter-profiles/validate", json={"answers": [
        {"key": "prey", "values": ["dragon"]},
    ]})
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "profile_value_unsupported:prey"


def test_recommendation_api_can_be_disabled_without_affecting_v1(tmp_path) -> None:
    api = TestClient(create_app(compose(ApplicationSettings(
        data_dir=tmp_path, recommendation_api_enabled=False
    ))))
    disabled = api.post("/api/v2/hunter-profiles/validate", json={
        "answers": [{"key": "prey", "values": ["venado"]}],
    })
    assert disabled.status_code == 404
    assert api.get("/api/v1/health").status_code == 200
