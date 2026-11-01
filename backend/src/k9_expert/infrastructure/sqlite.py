from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID

from k9_expert.domain.models import DocumentStatus, JobStage

SCHEMA_VERSION = 1

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
"""


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
                    "SELECT id, title, author, category, status, active_version_id FROM documents ORDER BY created_at"
                )
            )

    def versions(self, document_id: str) -> list[sqlite3.Row]:
        with self.database.connect() as connection:
            return list(
                connection.execute(
                    "SELECT id, content_hash, source_filename, edition, status, created_at FROM document_versions WHERE document_id = ? ORDER BY created_at DESC",
                    (document_id,),
                )
            )

    def job(self, job_id: str) -> sqlite3.Row | None:
        with self.database.connect() as connection:
            result = connection.execute(
                "SELECT * FROM ingestion_jobs WHERE id = ?", (job_id,)
            ).fetchone()
        return None if result is None else cast(sqlite3.Row, result)


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
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM fragments WHERE version_id = ?", (version_id,))
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
                "INSERT INTO fragments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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


class CacheInvalidator:
    def __init__(self) -> None:
        self.invalidated_snapshots: list[str] = []

    def invalidate_snapshot(self, snapshot_id: str) -> None:
        self.invalidated_snapshots.append(snapshot_id)


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
