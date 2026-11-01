from __future__ import annotations

import hashlib
import secrets
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

from k9_expert.domain.models import DocumentStatus, JobStage

SCHEMA_VERSION = 3

CLEANUP_QUEUE_TABLE = """
CREATE TABLE IF NOT EXISTS cleanup_queue (id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
  file_path TEXT NOT NULL, cleanup_after TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
"""

REINDEX_TABLES = """
CREATE TABLE IF NOT EXISTS reindex_requests (id TEXT PRIMARY KEY, scope TEXT NOT NULL, document_id TEXT,
  actor_id TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reindex_jobs (request_id TEXT NOT NULL REFERENCES reindex_requests(id),
  job_id TEXT NOT NULL REFERENCES ingestion_jobs(id), PRIMARY KEY(request_id, job_id));
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, author TEXT, category TEXT, status TEXT NOT NULL,
  active_version_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS document_versions (
  id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id), content_hash TEXT NOT NULL,
  source_filename TEXT NOT NULL, file_path TEXT NOT NULL, edition TEXT, isbn TEXT,
  status TEXT NOT NULL, extractor_version TEXT, chunking_version TEXT, created_at TEXT NOT NULL,
  UNIQUE(document_id, content_hash)
);
CREATE TABLE IF NOT EXISTS pages (
  id TEXT PRIMARY KEY, version_id TEXT NOT NULL REFERENCES document_versions(id), physical_page INTEGER NOT NULL,
  printed_page_label TEXT, extracted_text TEXT, text_quality REAL, used_ocr INTEGER NOT NULL DEFAULT 0,
  extraction_method TEXT NOT NULL, UNIQUE(version_id, physical_page)
);
CREATE TABLE IF NOT EXISTS fragments (
  id TEXT PRIMARY KEY, version_id TEXT NOT NULL REFERENCES document_versions(id), content_hash TEXT NOT NULL,
  ordinal INTEGER NOT NULL, text TEXT NOT NULL, section_path TEXT NOT NULL DEFAULT '',
  page_start INTEGER NOT NULL, page_end INTEGER NOT NULL, extraction_method TEXT NOT NULL,
  chunking_version TEXT NOT NULL, UNIQUE(version_id, content_hash)
);
CREATE TABLE IF NOT EXISTS snapshots (
  id TEXT PRIMARY KEY, embedding_alias TEXT NOT NULL, embedding_model TEXT NOT NULL,
  embedding_dimensions INTEGER NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, published_at TEXT
);
CREATE TABLE IF NOT EXISTS snapshot_membership (
  snapshot_id TEXT NOT NULL REFERENCES snapshots(id), fragment_id TEXT NOT NULL REFERENCES fragments(id),
  PRIMARY KEY(snapshot_id, fragment_id)
);
CREATE TABLE IF NOT EXISTS system_state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ingestion_jobs (
  id TEXT PRIMARY KEY, version_id TEXT NOT NULL REFERENCES document_versions(id), stage TEXT NOT NULL,
  attempt INTEGER NOT NULL DEFAULT 0, lease_until TEXT, checkpoint TEXT, error_code TEXT, error_message TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS queries (id TEXT PRIMARY KEY, conversation_id TEXT REFERENCES conversations(id),
  question_redacted TEXT, snapshot_id TEXT REFERENCES snapshots(id), status TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS answers (id TEXT PRIMARY KEY, query_id TEXT NOT NULL REFERENCES queries(id), text TEXT NOT NULL,
  status TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS citation_snapshots (id TEXT PRIMARY KEY, answer_id TEXT NOT NULL REFERENCES answers(id),
  fragment_id TEXT, title TEXT NOT NULL, author TEXT, edition TEXT, physical_page INTEGER NOT NULL,
  printed_page_label TEXT, excerpt TEXT, source_status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS feedback (id TEXT PRIMARY KEY, answer_id TEXT NOT NULL REFERENCES answers(id), useful INTEGER NOT NULL,
  comment TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS traces (id TEXT PRIMARY KEY, event TEXT NOT NULL, attributes_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS confirmation_tokens (token_hash TEXT PRIMARY KEY, actor_id TEXT NOT NULL, resource_id TEXT NOT NULL,
  operation TEXT NOT NULL, resource_version TEXT NOT NULL, expires_at TEXT NOT NULL, consumed_at TEXT);
CREATE TABLE IF NOT EXISTS audit_events (id TEXT PRIMARY KEY, actor_id TEXT, action TEXT NOT NULL, resource_id TEXT,
  attributes_json TEXT NOT NULL, created_at TEXT NOT NULL);
""" + CLEANUP_QUEUE_TABLE + REINDEX_TABLES


class UnsupportedSchemaError(RuntimeError):
    pass


class SqliteDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def migrate(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            current = connection.execute("PRAGMA user_version").fetchone()[0]
            if current > SCHEMA_VERSION:
                raise UnsupportedSchemaError(
                    f"database schema {current} is newer than {SCHEMA_VERSION}"
                )
            if current == 0:
                connection.executescript(SCHEMA)
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                return
            # Additive, ordered upgrades; each step leaves a valid schema version behind.
            if current == 1:
                connection.executescript(CLEANUP_QUEUE_TABLE)
                connection.execute("PRAGMA user_version = 2")
                current = 2
            if current == 2:
                connection.executescript(REINDEX_TABLES)
                connection.execute("PRAGMA user_version = 3")

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                connection.rollback()
                raise
            else:
                connection.commit()


def now() -> str:
    return datetime.now(UTC).isoformat()


class DocumentRepository:
    def __init__(self, database: SqliteDatabase) -> None:
        self.database = database

    def create_document(
        self, document_id: UUID, title: str, author: str | None, category: str | None
    ) -> None:
        timestamp = now()
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO documents VALUES (?, ?, ?, ?, ?, NULL, ?, ?)",
                (
                    str(document_id),
                    title,
                    author,
                    category,
                    DocumentStatus.CANDIDATE,
                    timestamp,
                    timestamp,
                ),
            )

    def create_version(
        self, version_id: UUID, document_id: UUID, content_hash: str, filename: str, file_path: str
    ) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO document_versions (id, document_id, content_hash, source_filename, file_path, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    str(version_id),
                    str(document_id),
                    content_hash,
                    filename,
                    file_path,
                    DocumentStatus.CANDIDATE,
                    now(),
                ),
            )

    def create_document_version_and_job(
        self,
        document_id: UUID,
        version_id: UUID,
        job_id: UUID,
        title: str,
        author: str | None,
        category: str | None,
        content_hash: str,
        filename: str,
        file_path: str,
    ) -> None:
        timestamp = now()
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO documents VALUES (?, ?, ?, ?, ?, NULL, ?, ?)",
                (
                    str(document_id),
                    title,
                    author,
                    category,
                    DocumentStatus.CANDIDATE,
                    timestamp,
                    timestamp,
                ),
            )
            connection.execute(
                "INSERT INTO document_versions (id, document_id, content_hash, source_filename, file_path, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    str(version_id),
                    str(document_id),
                    content_hash,
                    filename,
                    file_path,
                    DocumentStatus.CANDIDATE,
                    timestamp,
                ),
            )
            connection.execute(
                "INSERT INTO ingestion_jobs (id, version_id, stage, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (str(job_id), str(version_id), JobStage.RECEIVED, timestamp, timestamp),
            )

    def create_version_and_job(
        self,
        version_id: UUID,
        job_id: UUID,
        document_id: str,
        content_hash: str,
        filename: str,
        file_path: str,
    ) -> None:
        timestamp = now()
        with self.database.transaction() as connection:
            existing = connection.execute(
                "SELECT 1 FROM documents WHERE id = ?", (document_id,)
            ).fetchone()
            if existing is None:
                raise KeyError("document_not_found")
            connection.execute(
                "INSERT INTO document_versions (id, document_id, content_hash, source_filename, file_path, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    str(version_id),
                    document_id,
                    content_hash,
                    filename,
                    file_path,
                    DocumentStatus.CANDIDATE,
                    timestamp,
                ),
            )
            connection.execute(
                "INSERT INTO ingestion_jobs (id, version_id, stage, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (str(job_id), str(version_id), JobStage.RECEIVED, timestamp, timestamp),
            )

    def active_snapshot_id(self) -> str | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT value FROM system_state WHERE key = 'active_snapshot_id'"
            ).fetchone()
        return None if row is None else str(row["value"])

    def find_version_by_content_hash(self, content_hash: str) -> str | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT id FROM document_versions WHERE content_hash = ?", (content_hash,)
            ).fetchone()
        return None if row is None else str(row["id"])

    def list_documents(self) -> list[sqlite3.Row]:
        with self.database.connect() as connection:
            return list(
                connection.execute(
                    """SELECT d.id, d.title, d.author, d.category, d.status, d.active_version_id,
                    v.edition, d.updated_at FROM documents d
                    LEFT JOIN document_versions v ON v.id = d.active_version_id
                    ORDER BY d.created_at"""
                )
            )

    def versions(self, document_id: str) -> list[sqlite3.Row]:
        with self.database.connect() as connection:
            return list(
                connection.execute(
                    # Only the stable error code is exposed; error_message may hold raw exception text.
                    """SELECT v.id, v.content_hash, v.source_filename, v.edition, v.status, v.created_at,
                    j.id AS job_id, j.stage AS job_stage, j.attempt AS job_attempt,
                    CASE WHEN j.stage = 'error' THEN j.checkpoint END AS failed_stage,
                    j.error_code, j.updated_at AS job_updated_at
                    FROM document_versions v
                    LEFT JOIN ingestion_jobs j ON j.id = (
                      SELECT id FROM ingestion_jobs WHERE version_id = v.id
                      ORDER BY created_at DESC LIMIT 1)
                    WHERE v.document_id = ? ORDER BY v.created_at DESC""",
                    (document_id,),
                )
            )

    def job(self, job_id: str) -> sqlite3.Row | None:
        with self.database.connect() as connection:
            result = connection.execute(
                "SELECT * FROM ingestion_jobs WHERE id = ?", (job_id,)
            ).fetchone()
        return None if result is None else cast(sqlite3.Row, result)

    def resource_version(self, document_id: str) -> str:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT updated_at FROM documents WHERE id = ?", (document_id,)
            ).fetchone()
        if row is None:
            raise KeyError("document_not_found")
        return str(row["updated_at"])

    def mark_deleted_and_schedule_cleanup(
        self, document_id: str, cleanup_after: str, retain_excerpts: bool = True
    ) -> list[str]:
        timestamp = now()
        with self.database.transaction() as connection:
            updated = connection.execute(
                "UPDATE documents SET status = ?, updated_at = ? WHERE id = ?",
                (DocumentStatus.DELETED, timestamp, document_id),
            )
            if updated.rowcount != 1:
                raise KeyError("document_not_found")
            paths = [
                str(row["file_path"])
                for row in connection.execute(
                    "SELECT file_path FROM document_versions WHERE document_id = ?", (document_id,)
                )
            ]
            connection.executemany(
                "INSERT INTO cleanup_queue VALUES (?, ?, ?, ?, 'scheduled', ?)",
                [(str(uuid4()), document_id, path, cleanup_after, timestamp) for path in paths],
            )
            # Bibliographic identity and page always survive; the excerpt follows retention policy.
            if not retain_excerpts:
                connection.execute(
                    """UPDATE citation_snapshots SET excerpt = NULL
                    WHERE fragment_id IN (SELECT f.id FROM fragments f
                      JOIN document_versions v ON v.id = f.version_id WHERE v.document_id = ?)""",
                    (document_id,),
                )
        return paths

    def due_cleanups(self, as_of: str) -> list[sqlite3.Row]:
        with self.database.connect() as connection:
            return list(
                connection.execute(
                    "SELECT * FROM cleanup_queue WHERE status = 'scheduled' AND cleanup_after <= ? ORDER BY cleanup_after",
                    (as_of,),
                )
            )

    def file_referenced_by_live_document(self, file_path: str) -> bool:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM document_versions v JOIN documents d ON d.id = v.document_id WHERE v.file_path = ? AND d.status != ?",
                (file_path, DocumentStatus.DELETED),
            ).fetchone()
        return row is not None

    def finish_cleanup(self, cleanup_id: str, status: str) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "UPDATE cleanup_queue SET status = ? WHERE id = ? AND status = 'scheduled'",
                (status, cleanup_id),
            )

    def reindex_version_ids(self, document_id: str | None) -> list[str]:
        """Current version of one document, or of every non-deleted document."""
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT d.id, COALESCE(d.active_version_id, (SELECT v.id FROM document_versions v
                  WHERE v.document_id = d.id ORDER BY v.created_at DESC LIMIT 1)) AS version_id
                FROM documents d WHERE d.status != ? AND (? IS NULL OR d.id = ?)
                ORDER BY d.created_at""",
                (DocumentStatus.DELETED, document_id, document_id),
            ).fetchall()
            if document_id is not None and not rows:
                exists = connection.execute(
                    "SELECT 1 FROM documents WHERE id = ?", (document_id,)
                ).fetchone()
                raise KeyError("document_not_found" if exists is None else "document_deleted")
        return [str(row["version_id"]) for row in rows if row["version_id"] is not None]

    def create_reindex_request(
        self,
        request_id: UUID,
        scope: str,
        document_id: str | None,
        actor_id: str,
        version_ids: list[str],
    ) -> list[str]:
        timestamp = now()
        job_ids: list[str] = []
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO reindex_requests VALUES (?, ?, ?, ?, ?)",
                (str(request_id), scope, document_id, actor_id, timestamp),
            )
            for version_id in version_ids:
                # Reuse an in-flight job instead of racing two jobs over the same version.
                pending = connection.execute(
                    "SELECT id FROM ingestion_jobs WHERE version_id = ? AND stage NOT IN (?, ?) ORDER BY created_at DESC LIMIT 1",
                    (version_id, JobStage.AVAILABLE, JobStage.ERROR),
                ).fetchone()
                job_id = str(pending["id"]) if pending is not None else str(uuid4())
                if pending is None:
                    connection.execute(
                        "INSERT INTO ingestion_jobs (id, version_id, stage, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                        (job_id, version_id, JobStage.RECEIVED, timestamp, timestamp),
                    )
                connection.execute(
                    "INSERT INTO reindex_jobs VALUES (?, ?)", (str(request_id), job_id)
                )
                job_ids.append(job_id)
        return job_ids

    def reindex_request(self, request_id: str) -> tuple[sqlite3.Row, list[sqlite3.Row]] | None:
        with self.database.connect() as connection:
            request = connection.execute(
                "SELECT * FROM reindex_requests WHERE id = ?", (request_id,)
            ).fetchone()
            if request is None:
                return None
            jobs = connection.execute(
                """SELECT j.id, j.version_id, j.stage, j.attempt, j.error_code FROM reindex_jobs r
                JOIN ingestion_jobs j ON j.id = r.job_id WHERE r.request_id = ? ORDER BY j.created_at""",
                (request_id,),
            ).fetchall()
        return cast(sqlite3.Row, request), list(jobs)


class SystemStateRepository:
    """Process-independent operational flags such as worker heartbeat and query gating."""

    def __init__(self, database: SqliteDatabase) -> None:
        self.database = database

    def get(self, key: str) -> str | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT value FROM system_state WHERE key = ?", (key,)
            ).fetchone()
        return None if row is None else str(row["value"])

    def set(self, key: str, value: str) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO system_state (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def delete(self, key: str) -> None:
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM system_state WHERE key = ?", (key,))

    def record_worker_heartbeat(self) -> None:
        self.set("worker_heartbeat", now())

    def queries_disabled_reason(self) -> str | None:
        return self.get("queries_disabled_reason")

    def disable_queries(self, reason: str) -> None:
        self.set("queries_disabled_reason", reason)

    def enable_queries(self) -> None:
        self.delete("queries_disabled_reason")


class JobRepository:
    def __init__(self, database: SqliteDatabase) -> None:
        self.database = database

    def enqueue(self, job_id: UUID, version_id: UUID) -> None:
        timestamp = now()
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO ingestion_jobs (id, version_id, stage, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (str(job_id), str(version_id), JobStage.RECEIVED, timestamp, timestamp),
            )

    def claim_next(self, lease_until: str) -> sqlite3.Row | None:
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM ingestion_jobs WHERE stage NOT IN (?, ?) AND (lease_until IS NULL OR lease_until < ?) ORDER BY created_at LIMIT 1",
                (JobStage.AVAILABLE, JobStage.ERROR, now()),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "UPDATE ingestion_jobs SET lease_until = ?, attempt = attempt + 1, updated_at = ? WHERE id = ?",
                (lease_until, now(), row["id"]),
            )
            claimed = connection.execute(
                "SELECT * FROM ingestion_jobs WHERE id = ?", (row["id"],)
            ).fetchone()
            return cast(sqlite3.Row, claimed)

    def update_stage(self, job_id: str, stage: JobStage, checkpoint: str | None = None) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "UPDATE ingestion_jobs SET stage = ?, checkpoint = ?, lease_until = NULL, updated_at = ? WHERE id = ?",
                (stage, checkpoint, now(), job_id),
            )

    def fail(self, job_id: str, code: str, message: str) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "UPDATE ingestion_jobs SET stage = ?, error_code = ?, error_message = ?, lease_until = NULL, updated_at = ? WHERE id = ?",
                (JobStage.ERROR, code, message, now(), job_id),
            )

    def retry(self, job_id: str) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "UPDATE ingestion_jobs SET stage = ?, error_code = NULL, error_message = NULL, lease_until = NULL, updated_at = ? WHERE id = ? AND stage = ?",
                (JobStage.RECEIVED, now(), job_id, JobStage.ERROR),
            )

    def context(self, job_id: str) -> sqlite3.Row | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT j.id, j.version_id, v.file_path FROM ingestion_jobs j JOIN document_versions v ON v.id = j.version_id WHERE j.id = ?",
                (job_id,),
            ).fetchone()
        return None if row is None else cast(sqlite3.Row, row)


class ContentRepository:
    def __init__(self, database: SqliteDatabase) -> None:
        self.database = database

    def add_page(
        self,
        page_id: UUID,
        version_id: UUID,
        physical_page: int,
        text: str,
        extraction_method: str,
        printed_page_label: str | None = None,
    ) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO pages (id, version_id, physical_page, printed_page_label, extracted_text, extraction_method) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(page_id),
                    str(version_id),
                    physical_page,
                    printed_page_label,
                    text,
                    extraction_method,
                ),
            )

    def clear_version_content(self, version_id: str) -> None:
        # Fragments referenced by a published or retained snapshot are immutable evidence.
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM fragments WHERE version_id = ? AND id NOT IN (SELECT fragment_id FROM snapshot_membership)",
                (version_id,),
            )
            connection.execute("DELETE FROM pages WHERE version_id = ?", (version_id,))

    def add_fragment(
        self,
        fragment_id: UUID,
        version_id: UUID,
        content_hash: str,
        ordinal: int,
        text: str,
        page_start: int,
        page_end: int,
        extraction_method: str,
        chunking_version: str,
        section_path: str = "",
    ) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO fragments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(version_id, content_hash) DO NOTHING",
                (
                    str(fragment_id),
                    str(version_id),
                    content_hash,
                    ordinal,
                    text,
                    section_path,
                    page_start,
                    page_end,
                    extraction_method,
                    chunking_version,
                ),
            )


class SnapshotRepository:
    def __init__(self, database: SqliteDatabase) -> None:
        self.database = database

    def create(self, snapshot_id: UUID, alias: str, model: str, dimensions: int) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO snapshots VALUES (?, ?, ?, ?, ?, ?, NULL)",
                (str(snapshot_id), alias, model, dimensions, "candidate", now()),
            )

    def activate(self, snapshot_id: UUID, version_id: UUID, fragment_ids: list[UUID]) -> None:
        timestamp = now()
        with self.database.transaction() as connection:
            current = connection.execute(
                "SELECT value FROM system_state WHERE key = 'active_snapshot_id'"
            ).fetchone()
            if current is not None:
                connection.execute("UPDATE snapshots SET status = 'retained' WHERE id = ?", (current["value"],))
            activated = connection.execute(
                "UPDATE snapshots SET status = 'active', published_at = ? WHERE id = ? AND status = 'candidate'",
                (timestamp, str(snapshot_id)),
            )
            if activated.rowcount != 1:
                raise ValueError("snapshot_not_candidate")
            connection.executemany(
                "INSERT INTO snapshot_membership (snapshot_id, fragment_id) VALUES (?, ?)",
                [(str(snapshot_id), str(fragment_id)) for fragment_id in fragment_ids],
            )
            connection.execute(
                "UPDATE document_versions SET status = 'active' WHERE id = ?", (str(version_id),)
            )
            connection.execute(
                "UPDATE documents SET active_version_id = ?, status = 'active', updated_at = ? WHERE id = (SELECT document_id FROM document_versions WHERE id = ?)",
                (str(version_id), timestamp, str(version_id)),
            )
            connection.execute(
                "INSERT INTO system_state (key, value) VALUES ('active_snapshot_id', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (str(snapshot_id),),
            )

    def rollback(self, snapshot_id: UUID) -> None:
        with self.database.transaction() as connection:
            candidate = connection.execute(
                "SELECT id FROM snapshots WHERE id = ? AND status IN ('retained', 'active')", (str(snapshot_id),)
            ).fetchone()
            if candidate is None:
                raise ValueError("snapshot_not_retained")
            deleted = connection.execute(
                """SELECT 1 FROM snapshot_membership m JOIN fragments f ON f.id = m.fragment_id
                JOIN document_versions v ON v.id = f.version_id JOIN documents d ON d.id = v.document_id
                WHERE m.snapshot_id = ? AND d.status = ? LIMIT 1""",
                (str(snapshot_id), DocumentStatus.DELETED),
            ).fetchone()
            if deleted is not None:
                raise ValueError("snapshot_contains_deleted_source")
            connection.execute("UPDATE snapshots SET status = 'retained' WHERE status = 'active'")
            connection.execute("UPDATE snapshots SET status = 'active' WHERE id = ?", (str(snapshot_id),))
            connection.execute(
                "INSERT INTO system_state (key, value) VALUES ('active_snapshot_id', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (str(snapshot_id),),
            )

    def active_membership(self) -> list[str]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT fragment_id FROM snapshot_membership WHERE snapshot_id = (SELECT value FROM system_state WHERE key = 'active_snapshot_id')"
            )
            return [str(row["fragment_id"]) for row in rows]

    def snapshot(self, snapshot_id: str) -> sqlite3.Row | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone()
        return None if row is None else cast(sqlite3.Row, row)

    def index_fragments(self, snapshot_id: str) -> list[sqlite3.Row]:
        """Everything needed to rebuild a snapshot's vector generation from authoritative data."""
        with self.database.connect() as connection:
            return list(
                connection.execute(
                    """SELECT f.id, f.text, f.version_id, f.page_start, f.section_path,
                    v.document_id, v.file_path, d.category FROM snapshot_membership m
                    JOIN fragments f ON f.id = m.fragment_id
                    JOIN document_versions v ON v.id = f.version_id
                    JOIN documents d ON d.id = v.document_id
                    WHERE m.snapshot_id = ? ORDER BY f.version_id, f.ordinal""",
                    (snapshot_id,),
                )
            )

    def publish_document_membership(
        self, snapshot_id: UUID, document_id: str, include: bool
    ) -> tuple[str, str]:
        timestamp = now()
        with self.database.transaction() as connection:
            document = connection.execute(
                "SELECT active_version_id, status FROM documents WHERE id = ?", (document_id,)
            ).fetchone()
            if document is None:
                raise KeyError("document_not_found")
            active = connection.execute(
                """SELECT s.* FROM snapshots s JOIN system_state state
                ON state.key = 'active_snapshot_id' AND state.value = s.id"""
            ).fetchone()
            if active is None:
                raise ValueError("no_active_snapshot")
            if include and document["active_version_id"] is None:
                raise ValueError("document_has_no_active_version")
            connection.execute(
                "INSERT INTO snapshots VALUES (?, ?, ?, ?, 'candidate', ?, NULL)",
                (
                    str(snapshot_id),
                    active["embedding_alias"],
                    active["embedding_model"],
                    active["embedding_dimensions"],
                    timestamp,
                ),
            )
            connection.execute(
                """INSERT INTO snapshot_membership (snapshot_id, fragment_id)
                SELECT ?, membership.fragment_id FROM snapshot_membership membership
                JOIN fragments fragment ON fragment.id = membership.fragment_id
                JOIN document_versions version ON version.id = fragment.version_id
                WHERE membership.snapshot_id = ? AND version.document_id != ?""",
                (str(snapshot_id), active["id"], document_id),
            )
            if include:
                connection.execute(
                    """INSERT OR IGNORE INTO snapshot_membership (snapshot_id, fragment_id)
                    SELECT ?, id FROM fragments WHERE version_id = ?""",
                    (str(snapshot_id), document["active_version_id"]),
                )
            invalid = connection.execute(
                """SELECT COUNT(*) AS count FROM snapshot_membership membership
                LEFT JOIN fragments fragment ON fragment.id = membership.fragment_id
                WHERE membership.snapshot_id = ? AND fragment.id IS NULL""",
                (str(snapshot_id),),
            ).fetchone()
            if invalid is None or invalid["count"]:
                raise ValueError("invalid_snapshot_membership")
            connection.execute(
                "UPDATE snapshots SET status = 'retained' WHERE id = ?", (active["id"],)
            )
            connection.execute(
                "UPDATE snapshots SET status = 'active', published_at = ? WHERE id = ?",
                (timestamp, str(snapshot_id)),
            )
            connection.execute(
                "UPDATE documents SET status = ?, updated_at = ? WHERE id = ?",
                (DocumentStatus.ACTIVE if include else DocumentStatus.DEACTIVATED, timestamp, document_id),
            )
            connection.execute(
                "UPDATE system_state SET value = ? WHERE key = 'active_snapshot_id'",
                (str(snapshot_id),),
            )
        return str(active["id"]), str(snapshot_id)


class CacheInvalidator:
    def __init__(self) -> None:
        self.invalidated_snapshots: list[str] = []

    def invalidate_snapshot(self, snapshot_id: str) -> None:
        self.invalidated_snapshots.append(snapshot_id)


class InteractionRepository:
    """Transactional persistence for immutable query, answer, citation and feedback records."""

    def __init__(self, database: SqliteDatabase) -> None:
        self.database = database

    def create_conversation(self, conversation_id: UUID) -> sqlite3.Row:
        timestamp = now()
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO conversations (id, created_at, updated_at) VALUES (?, ?, ?)",
                (str(conversation_id), timestamp, timestamp),
            )
            return cast(
                sqlite3.Row,
                connection.execute(
                    "SELECT * FROM conversations WHERE id = ?", (str(conversation_id),)
                ).fetchone(),
            )

    def conversation(self, conversation_id: str) -> sqlite3.Row | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
        return None if row is None else cast(sqlite3.Row, row)

    def list_conversations(self, limit: int = 50) -> list[sqlite3.Row]:
        with self.database.connect() as connection:
            return list(
                connection.execute(
                    """SELECT c.id, c.created_at, c.updated_at,
                    (SELECT q.question_redacted FROM queries q WHERE q.conversation_id = c.id
                     ORDER BY q.created_at LIMIT 1) AS title
                    FROM conversations c ORDER BY c.updated_at DESC LIMIT ?""",
                    (limit,),
                )
            )

    def save_answer(
        self,
        *,
        query_id: UUID,
        answer_id: UUID,
        conversation_id: str | None,
        question_redacted: str,
        snapshot_id: str,
        status: str,
        text: str,
        citations: list[dict[str, object]],
    ) -> None:
        timestamp = now()
        with self.database.transaction() as connection:
            if conversation_id is not None:
                exists = connection.execute(
                    "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
                ).fetchone()
                if exists is None:
                    raise KeyError("conversation_not_found")
            connection.execute(
                "INSERT INTO queries VALUES (?, ?, ?, ?, ?, ?)",
                (str(query_id), conversation_id, question_redacted, snapshot_id, status, timestamp),
            )
            connection.execute(
                "INSERT INTO answers VALUES (?, ?, ?, ?, ?)",
                (str(answer_id), str(query_id), text, status, timestamp),
            )
            for citation in citations:
                connection.execute(
                    """INSERT INTO citation_snapshots
                    (id, answer_id, fragment_id, title, author, edition, physical_page,
                     printed_page_label, excerpt, source_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(citation["id"]), str(answer_id), str(citation["fragment_id"]),
                        citation["title"], citation.get("author"), citation.get("edition"),
                        citation["physical_page"], citation.get("printed_page_label"),
                        citation.get("excerpt"), citation["source_status"],
                    ),
                )
            if conversation_id is not None:
                connection.execute(
                    "UPDATE conversations SET updated_at = ? WHERE id = ?",
                    (timestamp, conversation_id),
                )

    def conversation_history(self, conversation_id: str, limit: int = 20) -> list[sqlite3.Row]:
        with self.database.connect() as connection:
            return list(
                connection.execute(
                    """SELECT q.id AS query_id, q.question_redacted AS question,
                    q.snapshot_id, q.status, q.created_at, a.id AS answer_id, a.text AS answer
                    FROM queries q JOIN answers a ON a.query_id = q.id
                    WHERE q.conversation_id = ? ORDER BY q.created_at DESC LIMIT ?""",
                    (conversation_id, limit),
                )
            )[::-1]

    def answer(self, answer_id: str) -> sqlite3.Row | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """SELECT a.*, q.snapshot_id, q.conversation_id, q.question_redacted AS question
                FROM answers a JOIN queries q ON q.id = a.query_id WHERE a.id = ?""",
                (answer_id,),
            ).fetchone()
        return None if row is None else cast(sqlite3.Row, row)

    def citations_for_answer(self, answer_id: str) -> list[sqlite3.Row]:
        with self.database.connect() as connection:
            return list(
                connection.execute(
                    """SELECT c.*, COALESCE(d.status, 'withdrawn') AS current_source_status
                    FROM citation_snapshots c
                    LEFT JOIN fragments f ON f.id = c.fragment_id
                    LEFT JOIN document_versions v ON v.id = f.version_id
                    LEFT JOIN documents d ON d.id = v.document_id
                    WHERE c.answer_id = ? ORDER BY c.physical_page, c.id""",
                    (answer_id,),
                )
            )

    def resolve_citation(self, citation_id: str) -> sqlite3.Row | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """SELECT c.*, q.snapshot_id, f.version_id, f.page_start, f.page_end,
                f.text AS current_excerpt, v.document_id, v.file_path, d.status AS current_source_status
                FROM citation_snapshots c
                JOIN answers a ON a.id = c.answer_id
                JOIN queries q ON q.id = a.query_id
                LEFT JOIN fragments f ON f.id = c.fragment_id
                LEFT JOIN document_versions v ON v.id = f.version_id
                LEFT JOIN documents d ON d.id = v.document_id
                WHERE c.id = ?""",
                (citation_id,),
            ).fetchone()
        return None if row is None else cast(sqlite3.Row, row)

    def citation_is_in_snapshot(self, citation_id: str) -> bool:
        with self.database.connect() as connection:
            row = connection.execute(
                """SELECT 1 FROM citation_snapshots c
                JOIN answers a ON a.id = c.answer_id JOIN queries q ON q.id = a.query_id
                JOIN snapshot_membership m ON m.snapshot_id = q.snapshot_id
                  AND m.fragment_id = c.fragment_id WHERE c.id = ?""",
                (citation_id,),
            ).fetchone()
        return row is not None

    def page(self, citation_id: str, physical_page: int) -> sqlite3.Row | None:
        citation = self.resolve_citation(citation_id)
        if citation is None or citation["version_id"] is None:
            return None
        if physical_page < citation["page_start"] or physical_page > citation["page_end"]:
            raise ValueError("page_outside_citation_range")
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT id, version_id, physical_page, printed_page_label, extracted_text, extraction_method FROM pages WHERE version_id = ? AND physical_page = ?",
                (citation["version_id"], physical_page),
            ).fetchone()
        return None if row is None else cast(sqlite3.Row, row)

    def add_feedback(
        self, feedback_id: UUID, answer_id: str, useful: bool, comment: str | None
    ) -> sqlite3.Row:
        with self.database.transaction() as connection:
            if connection.execute("SELECT 1 FROM answers WHERE id = ?", (answer_id,)).fetchone() is None:
                raise KeyError("answer_not_found")
            connection.execute(
                "INSERT INTO feedback VALUES (?, ?, ?, ?, ?)",
                (str(feedback_id), answer_id, int(useful), comment, now()),
            )
            return cast(
                sqlite3.Row,
                connection.execute("SELECT * FROM feedback WHERE id = ?", (str(feedback_id),)).fetchone(),
            )


class SecurityRepository:
    def __init__(self, database: SqliteDatabase) -> None:
        self.database = database

    def audit(
        self,
        event_id: UUID,
        actor_id: str | None,
        action: str,
        resource_id: str | None = None,
        attributes_json: str = "{}",
    ) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?)",
                (str(event_id), actor_id, action, resource_id, attributes_json, now()),
            )

    def issue_confirmation(
        self,
        actor_id: str,
        resource_id: str,
        operation: str,
        resource_version: str,
        expires_at: str,
    ) -> str:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO confirmation_tokens VALUES (?, ?, ?, ?, ?, ?, NULL)",
                (token_hash, actor_id, resource_id, operation, resource_version, expires_at),
            )
        return token

    def consume_confirmation(
        self,
        token: str,
        actor_id: str,
        resource_id: str,
        operation: str,
        resource_version: str,
        consumed_at: str,
    ) -> bool:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with self.database.transaction() as connection:
            result = connection.execute(
                """UPDATE confirmation_tokens SET consumed_at = ?
                WHERE token_hash = ? AND actor_id = ? AND resource_id = ? AND operation = ?
                AND resource_version = ? AND consumed_at IS NULL AND expires_at > ?""",
                (
                    consumed_at,
                    token_hash,
                    actor_id,
                    resource_id,
                    operation,
                    resource_version,
                    consumed_at,
                ),
            )
        return result.rowcount == 1

    def audit_events(self) -> list[sqlite3.Row]:
        with self.database.connect() as connection:
            return list(connection.execute("SELECT * FROM audit_events ORDER BY created_at, id"))


def operational_counts(database: SqliteDatabase) -> dict[str, dict[str, int]]:
    """Aggregate counts by state; the basic operational view before full trace metrics."""
    queries = {
        "queries": "SELECT status AS key, COUNT(*) AS count FROM queries GROUP BY status",
        "documents": "SELECT status AS key, COUNT(*) AS count FROM documents GROUP BY status",
        "jobs": "SELECT stage AS key, COUNT(*) AS count FROM ingestion_jobs GROUP BY stage",
        "feedback": """SELECT CASE useful WHEN 1 THEN 'useful' ELSE 'not_useful' END AS key,
            COUNT(*) AS count FROM feedback GROUP BY useful""",
    }
    with database.connect() as connection:
        return {
            name: {str(row["key"]): int(row["count"]) for row in connection.execute(sql)}
            for name, sql in queries.items()
        }


def reconciliation_report(database: SqliteDatabase, indexed_fragment_ids: set[str]) -> dict[str, list[str]]:
    with database.connect() as connection:
        files = connection.execute("SELECT id, file_path FROM document_versions").fetchall()
        fragments = connection.execute("SELECT id FROM fragments").fetchall()
        membership = connection.execute(
            "SELECT m.fragment_id FROM snapshot_membership m LEFT JOIN fragments f ON f.id = m.fragment_id WHERE f.id IS NULL"
        ).fetchall()
    stored_fragments = {str(row["id"]) for row in fragments}
    return {
        "missing_files": [str(row["id"]) for row in files if not Path(row["file_path"]).is_file()],
        "missing_vectors": sorted(stored_fragments - indexed_fragment_ids),
        "orphan_vectors": sorted(indexed_fragment_ids - stored_fragments),
        "invalid_membership": [str(row["fragment_id"]) for row in membership],
    }
