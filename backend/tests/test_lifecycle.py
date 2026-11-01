from __future__ import annotations

from uuid import uuid4

from k9_expert.application.lifecycle import DocumentLifecycleService
from k9_expert.infrastructure.sqlite import (
    CacheInvalidator,
    SnapshotRepository,
    SqliteDatabase,
)


def test_deactivate_and_reactivate_publish_isolated_snapshots(tmp_path) -> None:
    database = SqliteDatabase(tmp_path / "k9.sqlite")
    database.migrate()
    document_id, version_id, fragment_id, other_fragment, active_snapshot = (
        str(uuid4()) for _ in range(5)
    )
    other_document, other_version = str(uuid4()), str(uuid4())
    timestamp = "2026-11-01T00:00:00+00:00"
    with database.transaction() as connection:
        for doc, version, title in (
            (document_id, version_id, "Target"),
            (other_document, other_version, "Other"),
        ):
            connection.execute(
                "INSERT INTO documents VALUES (?, ?, NULL, NULL, 'active', ?, ?, ?)",
                (doc, title, version, timestamp, timestamp),
            )
            connection.execute(
                "INSERT INTO document_versions "
                "(id, document_id, content_hash, source_filename, file_path, status, created_at) "
                "VALUES (?, ?, ?, 'book.pdf', '/managed/book.pdf', 'active', ?)",
                (version, doc, f"hash-{doc}", timestamp),
            )
        for fragment, version in ((fragment_id, version_id), (other_fragment, other_version)):
            connection.execute(
                "INSERT INTO fragments VALUES "
                "(?, ?, ?, 0, 'text', '', 1, 1, 'direct', 'v1')",
                (fragment, version, f"hash-{fragment}"),
            )
        connection.execute(
            "INSERT INTO snapshots VALUES (?, 'alias', 'model', 3, 'active', ?, ?)",
            (active_snapshot, timestamp, timestamp),
        )
        connection.executemany(
            "INSERT INTO snapshot_membership VALUES (?, ?)",
            [(active_snapshot, fragment_id), (active_snapshot, other_fragment)],
        )
        connection.execute(
            "INSERT INTO system_state VALUES ('active_snapshot_id', ?)", (active_snapshot,)
        )
    snapshots = SnapshotRepository(database)
    cache = CacheInvalidator()
    service = DocumentLifecycleService(snapshots, cache)
    deactivated_snapshot = service.deactivate(document_id)
    assert snapshots.active_membership() == [other_fragment]
    with database.connect() as connection:
        assert connection.execute(
            "SELECT status FROM documents WHERE id = ?", (document_id,)
        ).fetchone()["status"] == "deactivated"
    reactivated_snapshot = service.reactivate(document_id)
    assert set(snapshots.active_membership()) == {fragment_id, other_fragment}
    assert cache.invalidated_snapshots == [active_snapshot, deactivated_snapshot]
    assert reactivated_snapshot != deactivated_snapshot
