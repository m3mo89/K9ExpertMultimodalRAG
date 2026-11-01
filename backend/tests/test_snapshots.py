from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from k9_expert.infrastructure.sqlite import (
    CacheInvalidator,
    ContentRepository,
    DocumentRepository,
    SnapshotRepository,
    SqliteDatabase,
    reconciliation_report,
)


def setup_snapshot_data(tmp_path: Path):
    database = SqliteDatabase(tmp_path / "k9.sqlite")
    database.migrate()
    document_id, version_id, fragment_id = uuid4(), uuid4(), uuid4()
    document = DocumentRepository(database)
    document.create_document(document_id, "Libro", None, None)
    source = tmp_path / "book.pdf"
    source.write_bytes(b"%PDF")
    document.create_version(version_id, document_id, "hash", "book.pdf", str(source))
    ContentRepository(database).add_fragment(
        fragment_id, version_id, "fragment-hash", 1, "texto", 1, 1, "direct", "v1"
    )
    return database, version_id, fragment_id


def test_snapshot_activation_rollback_and_invalidation_are_atomic(tmp_path: Path) -> None:
    database, version_id, fragment_id = setup_snapshot_data(tmp_path)
    snapshots = SnapshotRepository(database)
    first, second = uuid4(), uuid4()
    snapshots.create(first, "embed", "model", 2)
    snapshots.activate(first, version_id, [fragment_id])
    assert snapshots.active_membership() == [str(fragment_id)]
    snapshots.create(second, "embed", "model", 2)
    snapshots.activate(second, version_id, [fragment_id])
    snapshots.rollback(first)
    assert snapshots.active_membership() == [str(fragment_id)]
    with pytest.raises(ValueError, match="snapshot_not_candidate"):
        snapshots.activate(first, version_id, [fragment_id])
    assert snapshots.active_membership() == [str(fragment_id)]
    invalidator = CacheInvalidator()
    invalidator.invalidate_snapshot(str(second))
    assert invalidator.invalidated_snapshots == [str(second)]


def test_reconciliation_report_is_read_only_and_reports_divergence(tmp_path: Path) -> None:
    database, _, fragment_id = setup_snapshot_data(tmp_path)
    report = reconciliation_report(database, {str(uuid4())})
    assert report["missing_vectors"] == [str(fragment_id)]
    assert len(report["orphan_vectors"]) == 1
