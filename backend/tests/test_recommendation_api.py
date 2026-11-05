from dataclasses import replace
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from k9_expert.application.composition import ApplicationSettings, compose
from k9_expert.application.generation import GeneratedAnswer
from k9_expert.application.recommendation import HunterRecommendationService
from k9_expert.domain.models import (
    AssertionExtractionState,
    AssertionPolarity,
    ReviewDecision,
)
from k9_expert.infrastructure.sqlite import RecommendationRepository, SnapshotRepository
from k9_expert.presentation.api import create_app
from test_structured_knowledge import seeded


def test_recommendation_api_is_deterministic_without_ollama(tmp_path) -> None:
    _database, snapshot, fragment = seeded(tmp_path)
    container = compose(ApplicationSettings(data_dir=tmp_path))
    for key, value in (
        ("prey", "venado"), ("modality", "rastreo"), ("terrain", "monte_denso"),
    ):
        assertion_id = container.structured_knowledge.create_candidate(
            assertion_id=uuid4(), breed="Raza", attribute_key=key, value=value,
            polarity=AssertionPolarity.SUPPORTS, fragment_ids=[fragment],
            extraction_method="human", policy_version="structured-knowledge-v1",
        )
        container.structured_knowledge.review(
            assertion_id, "expert", ReviewDecision.APPROVED, snapshot
        )
    api = TestClient(create_app(container))
    request = {"candidate_breeds": ["Raza"], "answers": [
        {"key": "prey", "values": ["venado"]},
        {"key": "modality", "values": ["rastreo"]},
        {"key": "terrain", "values": ["monte_denso"]},
        {"key": "experience", "values": ["principiante"]},
        {"key": "daily_availability", "values": ["1_2h"]},
    ]}
    first = api.post("/api/v2/recommendations", json=request)
    second = api.post("/api/v2/recommendations", json=request)
    assert first.status_code == 201
    assert first.json()["candidates"] == second.json()["candidates"]
    assert first.json()["candidates"][0]["breed"] == "Raza"
    assert "narrative_unavailable" in first.json()["limitations"]
    assert first.json()["summary"] is None


def test_incomplete_profile_never_scores_or_generates(tmp_path) -> None:
    api = TestClient(create_app(compose(ApplicationSettings(data_dir=tmp_path))))
    response = api.post("/api/v2/recommendations", json={"answers": [
        {"key": "prey", "values": ["venado"]},
    ]})
    assert response.status_code == 201
    assert response.json()["status"] == "incomplete"
    assert response.json()["candidates"] == []
    assert "profile_incomplete" in response.json()["limitations"]


def test_unverified_narrative_cannot_change_api_ranking(tmp_path) -> None:
    database, snapshot, fragment = seeded(tmp_path)
    container = compose(ApplicationSettings(data_dir=tmp_path))
    for key, value in (
        ("prey", "venado"), ("modality", "rastreo"), ("terrain", "monte_denso"),
    ):
        item = container.structured_knowledge.create_candidate(
            assertion_id=uuid4(), breed="Raza", attribute_key=key, value=value,
            polarity=AssertionPolarity.SUPPORTS, fragment_ids=[fragment],
            extraction_method="human", policy_version="structured-knowledge-v1",
        )
        container.structured_knowledge.review(item, "expert", ReviewDecision.APPROVED, snapshot)
    original = container.recommendation_service
    malicious = HunterRecommendationService(
        original.documents, original.knowledge, RecommendationRepository(database),
        original.engine, original.breed_names,
        narrator=lambda _result: GeneratedAnswer(
            "La raza inventada ocupa el primer lugar con 100 %.", (str(uuid4()),)
        ),
    )
    api = TestClient(create_app(replace(container, recommendation_service=malicious)))
    response = api.post("/api/v2/recommendations", json={
        "candidate_breeds": ["Raza"],
        "answers": [
            {"key": "prey", "values": ["venado"]},
            {"key": "modality", "values": ["rastreo"]},
            {"key": "terrain", "values": ["monte_denso"]},
            {"key": "experience", "values": ["principiante"]},
            {"key": "daily_availability", "values": ["1_2h"]},
        ],
    })
    assert response.json()["candidates"][0]["breed"] == "Raza"
    assert response.json()["summary"] is None
    assert "narrative_unavailable" in response.json()["limitations"]


def test_complete_profile_without_supported_candidates_abstains(tmp_path) -> None:
    api = TestClient(create_app(compose(ApplicationSettings(data_dir=tmp_path))))
    response = api.post("/api/v2/recommendations", json={"answers": [
        {"key": "prey", "values": ["venado"]},
        {"key": "modality", "values": ["rastreo"]},
        {"key": "terrain", "values": ["monte_denso"]},
    ]})
    assert response.status_code == 201
    assert response.json()["status"] == "abstained"
    assert response.json()["candidates"] == []


def test_active_snapshot_without_knowledge_explains_the_abstention(tmp_path) -> None:
    seeded(tmp_path)
    api = TestClient(create_app(compose(ApplicationSettings(data_dir=tmp_path))))
    response = api.post("/api/v2/recommendations", json={
        "candidate_breeds": ["Raza"],
        "answers": [
            {"key": "prey", "values": ["venado"]},
            {"key": "modality", "values": ["rastreo"]},
            {"key": "terrain", "values": ["monte_denso"]},
        ],
    })
    assert response.json()["status"] == "abstained"
    assert "no_candidate_reached_coverage" in response.json()["limitations"]


def test_auto_validated_knowledge_recommends_without_review_and_discloses_it(tmp_path) -> None:
    database, snapshot, fragment = seeded(tmp_path)
    container = compose(ApplicationSettings(data_dir=tmp_path))
    for key, value in (("prey", "venado"), ("modality", "rastreo")):
        container.structured_knowledge.create_candidate(
            assertion_id=uuid4(), breed="Raza", attribute_key=key, value=value,
            polarity=AssertionPolarity.SUPPORTS, fragment_ids=[fragment],
            extraction_method="assertion-rules-v2", policy_version="structured-knowledge-v2",
            extraction_state=AssertionExtractionState.AUTO_VALIDATED,
        )
    with database.transaction() as connection:
        SnapshotRepository._stage_eligible_assertions(connection, UUID(snapshot))
    api = TestClient(create_app(container))
    response = api.post("/api/v2/recommendations", json={
        "candidate_breeds": ["Raza"],
        "answers": [
            {"key": "prey", "values": ["venado"]},
            {"key": "modality", "values": ["rastreo"]},
            {"key": "terrain", "values": ["monte_denso"]},
            {"key": "experience", "values": ["principiante"]},
        ],
    })
    body = response.json()
    assert body["status"] == "completed"
    assert body["policy_version"] == "recommendation-v3"
    assert [item["breed"] for item in body["candidates"]] == ["Raza"]
    assert "automatic_extraction_unreviewed" in body["limitations"]
    assert "dimension_not_evaluated:experience" in body["limitations"]
    assert "fewer_supported_candidates" in body["limitations"]
