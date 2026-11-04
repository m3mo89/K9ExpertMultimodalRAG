from uuid import uuid4

import pytest

from k9_expert.application.recommendation_context import RecommendationContextService
from k9_expert.infrastructure.sqlite import (
    RecommendationContextRepository,
    RecommendationRepository,
    SqliteDatabase,
)


def save_record(database: SqliteDatabase) -> str:
    with database.transaction() as connection:
        connection.execute(
            """INSERT INTO recommendations VALUES (?, '{}', 'v2', NULL, ?, 'trace-1', 'now')""",
            (
                str(uuid4()),
                '{"candidates":[{"breed":"Raza A","dimensions":[{"evidence_ids":["f1"]}]},'
                '{"breed":"Raza B","dimensions":[{"evidence_ids":["f2"]}]}]}',
            ),
        )
        return str(connection.execute("SELECT id FROM recommendations").fetchone()[0])


def test_context_is_immutable_and_restricts_breeds_and_evidence(tmp_path) -> None:
    database = SqliteDatabase(tmp_path / "k9.sqlite")
    database.migrate()
    recommendation_id = save_record(database)
    service = RecommendationContextService(
        RecommendationRepository(database), RecommendationContextRepository(database)
    )
    context = service.create(recommendation_id, ["Raza A"])
    assert context["selected_breeds"] == ["Raza A"]
    assert context["allowed_evidence"] == ["f1"]
    answer = service.answer(str(context["id"]), "¿Por qué recomiendas esta raza?")
    assert answer["status"] == "grounded"
    assert answer["bibliographic_evidence"] == ["f1"]
    assert answer["policy_inference"][0]["breed"] == "Raza A"
    changed = service.answer(str(context["id"]), "Prefiero menos tiempo")
    assert changed["status"] == "new_recommendation_required"
    with pytest.raises(ValueError, match="context_breed_not_in_recommendation"):
        service.create(recommendation_id, ["Inventada"])
    with pytest.raises(ValueError, match="context_breed_selection_invalid"):
        service.create(recommendation_id, ["Raza A", "Raza A"])
