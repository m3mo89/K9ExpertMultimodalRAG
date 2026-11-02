from datetime import UTC, datetime, timedelta
from uuid import uuid4

from k9_expert.application.recovery import BackupService
from k9_expert.domain.models import (
    AnalysisFeedback,
    AnalysisStatus,
    BreedAnalysisId,
    BreedAnalysisProfile,
    BreedAnalysisReport,
    BreedCandidate,
    BreedCriterion,
    BreedFinding,
    CacheHitType,
    Citation,
    DocumentId,
    DocumentVersionId,
    ExecutionMetadata,
    FindingOutcome,
    FragmentId,
    SnapshotId,
    SourceRef,
)
from k9_expert.infrastructure.sqlite import (
    BreedAnalysisRepository,
    SqliteDatabase,
    SqliteResponseCache,
)


def test_analysis_round_trip_and_feedback_integrity(tmp_path) -> None:
    database = SqliteDatabase(tmp_path / "k9.sqlite")
    database.migrate()
    snapshot_id = uuid4()
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO snapshots VALUES (?, 'e', 'm', 3, 'active', 'now', 'now')",
            (str(snapshot_id),),
        )
    analysis_id = BreedAnalysisId(uuid4())
    source = SourceRef(
        DocumentId(uuid4()), DocumentVersionId(uuid4()), "Enciclopedia", "Autor", "2019", 27, None
    )
    criterion = BreedCriterion("hunting_function", "rastro", 2.0)
    finding = BreedFinding(
        criterion, FindingOutcome.MATCH, "Documentado",
        (Citation(FragmentId(uuid4()), source),),
    )
    report = BreedAnalysisReport(
        analysis_id, AnalysisStatus.COMPLETED, BreedAnalysisProfile((criterion,)),
        SnapshotId(snapshot_id), (BreedCandidate("Teckel", (finding,), 1.0, 2.0, 2.0, 1.0),),
        ("Fuente histórica",), "trace-1", execution=ExecutionMetadata(route="simple"),
    )
    repository = BreedAnalysisRepository(database)
    repository.save(report)
    stored = repository.get(analysis_id)
    assert stored is not None
    assert stored.candidates[0].breed == "Teckel"
    assert stored.candidates[0].findings[0].citations[0].source.physical_page == 27
    feedback_id = repository.add_feedback(AnalysisFeedback(analysis_id, True, "útil"), "trace-1")
    with database.connect() as connection:
        feedback = connection.execute(
            "SELECT useful, trace_id FROM analysis_feedback WHERE id = ?", (feedback_id,)
        ).fetchone()
    assert tuple(feedback) == (1, "trace-1")


def test_exact_semantic_partition_and_snapshot_invalidation(tmp_path) -> None:
    database = SqliteDatabase(tmp_path / "k9.sqlite")
    database.migrate()
    cache = SqliteResponseCache(database)
    future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    cache.store("one", '{"report": 1}', partition="breed:p1", snapshot_id="s1",
                expires_at=future, request_vector=[1.0, 0.0])
    exact = cache.lookup("one", partition="breed:p1", snapshot_id="s1")
    assert exact.hit_type == CacheHitType.EXACT
    semantic = cache.lookup("two", partition="breed:p1", snapshot_id="s1",
                            request_vector=[0.99, 0.01], semantic_threshold=0.95)
    assert semantic.hit_type == CacheHitType.SEMANTIC
    wrong_profile = cache.lookup(
        "two", partition="breed:p2", snapshot_id="s1",
        request_vector=[1.0, 0.0], semantic_threshold=0.95,
    )
    wrong_snapshot = cache.lookup(
        "two", partition="breed:p1", snapshot_id="s2",
        request_vector=[1.0, 0.0], semantic_threshold=0.95,
    )
    assert wrong_profile.hit_type == CacheHitType.MISS
    assert wrong_snapshot.hit_type == CacheHitType.MISS
    assert cache.invalidate_snapshot("s1") == 2
    assert cache.lookup("one", partition="breed:p1", snapshot_id="s1").hit_type == CacheHitType.MISS


def test_new_records_are_backed_up_and_retention_is_additive(tmp_path) -> None:
    data = tmp_path / "data"
    database = SqliteDatabase(data / "k9.sqlite")
    database.migrate()
    cache = SqliteResponseCache(database)
    expired = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    cache.store("old", "{}", partition="p", snapshot_id="s", expires_at=expired,
                request_vector=[1.0])
    assert cache.purge_expired(datetime.now(UTC).isoformat()) == 2
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM exact_response_cache").fetchone()[0] == 0

    service = BackupService(database, data / "files", data / "index", data / "backups")
    manifest = service.create()
    backup_db = data / "backups" / str(manifest["backup_id"]) / "k9.sqlite"
    backup = SqliteDatabase(backup_db)
    with backup.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 4
        tables = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    assert {"breed_analyses", "analysis_feedback", "semantic_response_cache"} <= tables
