from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from k9_expert.application.admin import AdminSecurityService
from k9_expert.application.lifecycle import DocumentLifecycleService
from k9_expert.infrastructure.sqlite import (
    SCHEMA_VERSION,
    CacheInvalidator,
    DocumentRepository,
    SecurityRepository,
    SnapshotRepository,
    SqliteDatabase,
)


def test_confirmed_delete_preserves_citations_and_schedules_cleanup(tmp_path) -> None:
    database = SqliteDatabase(tmp_path / "k9.sqlite")
    database.migrate()
    document_id, version_id, fragment_id, snapshot_id = (str(uuid4()) for _ in range(4))
    query_id, answer_id, citation_id = (str(uuid4()) for _ in range(3))
    timestamp = "2026-11-01T00:00:00+00:00"
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO documents VALUES (?, 'Book', NULL, NULL, 'active', ?, ?, ?)",
            (document_id, version_id, timestamp, timestamp),
        )
        connection.execute(
            "INSERT INTO document_versions "
            "(id, document_id, content_hash, source_filename, file_path, status, created_at) "
            "VALUES (?, ?, 'hash', 'book.pdf', '/managed/book.pdf', 'active', ?)",
            (version_id, document_id, timestamp),
        )
        connection.execute(
            "INSERT INTO fragments VALUES "
            "(?, ?, 'fh', 0, 'evidence', '', 1, 1, 'direct', 'v1')",
            (fragment_id, version_id),
        )
        connection.execute(
            "INSERT INTO snapshots VALUES (?, 'alias', 'model', 3, 'active', ?, ?)",
            (snapshot_id, timestamp, timestamp),
        )
        connection.execute(
            "INSERT INTO snapshot_membership VALUES (?, ?)", (snapshot_id, fragment_id)
        )
        connection.execute(
            "INSERT INTO system_state VALUES ('active_snapshot_id', ?)", (snapshot_id,)
        )
        connection.execute(
            "INSERT INTO queries VALUES (?, NULL, 'redacted', ?, 'grounded', ?)",
            (query_id, snapshot_id, timestamp),
        )
        connection.execute(
            "INSERT INTO answers VALUES (?, ?, 'answer', 'grounded', ?)",
            (answer_id, query_id, timestamp),
        )
        connection.execute(
            "INSERT INTO citation_snapshots VALUES "
            "(?, ?, ?, 'Book', NULL, NULL, 1, NULL, 'evidence', 'active')",
            (citation_id, answer_id, fragment_id),
        )
    documents = DocumentRepository(database)
    security = AdminSecurityService(SecurityRepository(database), "secret")
    service = DocumentLifecycleService(
        SnapshotRepository(database), CacheInvalidator(), documents, security, retention_days=7
    )
    resource_version = documents.resource_version(document_id)
    token, _ = security.issue_confirmation("alice", document_id, "delete", resource_version)
    service.delete(document_id, "alice", token, resource_version)
    with database.connect() as connection:
        assert connection.execute(
            "SELECT status FROM documents WHERE id = ?", (document_id,)
        ).fetchone()["status"] == "deleted"
        citation = connection.execute(
            "SELECT title, excerpt FROM citation_snapshots WHERE id = ?", (citation_id,)
        ).fetchone()
        cleanup = connection.execute("SELECT * FROM cleanup_queue").fetchone()
    assert tuple(citation) == ("Book", "evidence")
    assert cleanup["file_path"] == "/managed/book.pdf"
    assert datetime.fromisoformat(cleanup["cleanup_after"]) > datetime.now(UTC) + timedelta(days=6)
    with pytest.raises(ValueError, match="invalid_confirmation"):
        service.delete(document_id, "alice", token, documents.resource_version(document_id))


def test_schema_one_migrates_cleanup_queue(tmp_path) -> None:
    database = SqliteDatabase(tmp_path / "legacy.sqlite")
    database.migrate()
    with database.connect() as connection:
        connection.execute("DROP TABLE cleanup_queue")
        connection.execute("PRAGMA user_version = 1")
    database.migrate()
    with database.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'cleanup_queue'"
        ).fetchone() is not None
