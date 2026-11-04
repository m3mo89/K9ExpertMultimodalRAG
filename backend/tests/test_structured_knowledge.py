from uuid import uuid4

import pytest

from k9_expert.application.structured_knowledge import StructuredBreedProfileService
from k9_expert.domain.models import AssertionPolarity, ReviewDecision
from k9_expert.infrastructure.sqlite import SqliteDatabase, StructuredKnowledgeRepository


def seeded(tmp_path):  # type: ignore[no-untyped-def]
    database = SqliteDatabase(tmp_path / "k9.sqlite")
    database.migrate()
    document_id, version_id, snapshot_id, fragment_id = (uuid4() for _ in range(4))
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO documents VALUES (?, 'Libro', 'Autor', 'caza', 'active', ?, 'now', 'now')",
            (str(document_id), str(version_id)),
        )
        connection.execute(
            """INSERT INTO document_versions
            (id, document_id, content_hash, source_filename, file_path, status, created_at)
            VALUES (?, ?, 'hash', 'book.pdf', '/tmp/book.pdf', 'active', 'now')""",
            (str(version_id), str(document_id)),
        )
        connection.execute(
            "INSERT INTO pages VALUES (?, ?, 7, '5', 'texto', 1, 0, 'direct')",
            (str(uuid4()), str(version_id)),
        )
        connection.execute(
            """INSERT INTO fragments VALUES
            (?, ?, 'fragment-hash', 1, 'Apto para rastreo', 'Raza/Trabajo', 7, 7,
            'direct', 'v1')""",
            (str(fragment_id), str(version_id)),
        )
        connection.execute(
            "INSERT INTO snapshots VALUES (?, 'e', 'm', 3, 'active', 'now', 'now')",
            (str(snapshot_id),),
        )
        connection.execute(
            "INSERT INTO snapshot_membership VALUES (?, ?)",
            (str(snapshot_id), str(fragment_id)),
        )
        connection.execute(
            "INSERT INTO system_state VALUES ('active_snapshot_id', ?)", (str(snapshot_id),)
        )
    return database, str(snapshot_id), str(fragment_id)


def candidate(
    repository: StructuredKnowledgeRepository, fragment_id: str,
    polarity: AssertionPolarity = AssertionPolarity.SUPPORTS, value: str = "rastreo",
) -> str:
    return repository.create_candidate(
        assertion_id=uuid4(), breed="Raza", attribute_key="modality", value=value,
        polarity=polarity, fragment_ids=[fragment_id], extraction_method="rule-v1",
        policy_version="structured-knowledge-v1",
    )


def test_additive_migration_and_duplicate_candidate_reconciliation(tmp_path) -> None:
    database, _snapshot, fragment = seeded(tmp_path)
    repository = StructuredKnowledgeRepository(database)
    first = candidate(repository, fragment)
    second = candidate(repository, fragment)
    assert first == second
    with database.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 10
        assert connection.execute("SELECT COUNT(*) FROM assertion_candidates").fetchone()[0] == 1


def test_approved_profile_unknown_conflict_and_historical_snapshot(tmp_path) -> None:
    database, snapshot, fragment = seeded(tmp_path)
    repository = StructuredKnowledgeRepository(database)
    support = candidate(repository, fragment)
    contradict = candidate(repository, fragment, AssertionPolarity.CONTRADICTS)
    repository.review(support, "expert", ReviewDecision.APPROVED, snapshot)
    repository.review(contradict, "expert", ReviewDecision.APPROVED, snapshot)
    service = StructuredBreedProfileService(repository)
    profile = service.profile(snapshot, "Raza")
    assert profile.attributes[0].evidence_state == "conflicting"
    assert profile.attributes[0].assertions[0].evidence[0].source.physical_page == 7
    assert service.attribute(snapshot, "Raza", "climate").evidence_state == "unknown"


def test_rejected_and_withdrawn_assertions_are_not_resolved(tmp_path) -> None:
    database, snapshot, fragment = seeded(tmp_path)
    repository = StructuredKnowledgeRepository(database)
    rejected = candidate(repository, fragment)
    repository.review(rejected, "expert", ReviewDecision.REJECTED, None)
    assert repository.approved(snapshot, "Raza") == ()
    approved = candidate(repository, fragment, value="rastro_herido")
    repository.review(approved, "expert", ReviewDecision.APPROVED, snapshot)
    with database.transaction() as connection:
        connection.execute(
            "DELETE FROM snapshot_membership WHERE snapshot_id = ?", (snapshot,)
        )
    assert repository.approved(snapshot, "Raza") == ()


def test_review_requires_identity_snapshot_and_existing_evidence(tmp_path) -> None:
    database, snapshot, fragment = seeded(tmp_path)
    repository = StructuredKnowledgeRepository(database)
    item = candidate(repository, fragment)
    with pytest.raises(ValueError, match="reviewer_required"):
        repository.review(item, "", ReviewDecision.APPROVED, snapshot)
    with pytest.raises(ValueError, match="snapshot_required"):
        repository.review(item, "expert", ReviewDecision.APPROVED, None)
    with pytest.raises(ValueError, match="assertion_evidence_invalid"):
        candidate(repository, str(uuid4()))
