from pathlib import Path
from uuid import uuid4

import pytest

from k9_expert.infrastructure.filesystem import ManagedFileStore
from k9_expert.infrastructure.sqlite import (
    ContentRepository,
    DocumentRepository,
    JobRepository,
    SqliteDatabase,
    UnsupportedSchemaError,
)


def test_document_version_and_job_are_persisted(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "k9.sqlite")
    database.migrate()
    documents = DocumentRepository(database)
    jobs = JobRepository(database)
    document_id, version_id, job_id = uuid4(), uuid4(), uuid4()
    documents.create_document(document_id, "Enciclopedia", "Claudio De Giuliani", "Caza")
    documents.create_version(version_id, document_id, "abc", "libro.pdf", "files/abc.pdf")
    jobs.enqueue(job_id, version_id)
    claimed = jobs.claim_next("2099-01-01T00:00:00+00:00")
    assert claimed is not None
    assert claimed["id"] == str(job_id)
    assert documents.active_snapshot_id() is None


def test_newer_schema_fails_without_mutating(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "future.sqlite")
    database.migrate()
    with database.connect() as connection:
        connection.execute("PRAGMA user_version = 999")
    with pytest.raises(UnsupportedSchemaError):
        database.migrate()


def test_managed_file_store_uses_content_hash_and_atomic_destination(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-1.7 sample")
    store = ManagedFileStore(tmp_path / "managed")
    digest = store.sha256(source)
    destination = store.put(source, digest)
    assert destination.read_bytes() == source.read_bytes()
    assert destination.parent.parent == (tmp_path / "managed").resolve()


def test_content_preserves_page_provenance_and_fragment_coverage(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "k9.sqlite")
    database.migrate()
    documents = DocumentRepository(database)
    document_id, version_id = uuid4(), uuid4()
    documents.create_document(document_id, "Enciclopedia", None, None)
    documents.create_version(version_id, document_id, "content", "book.pdf", "files/book.pdf")
    content = ContentRepository(database)
    content.add_page(uuid4(), version_id, 27, "Texto", "direct", "15")
    content.add_fragment(
        uuid4(), version_id, "fragment", 1, "Texto", 27, 28, "direct", "v1", "Teckel"
    )
    with database.connect() as connection:
        page = connection.execute("SELECT printed_page_label FROM pages").fetchone()
        fragment = connection.execute(
            "SELECT page_start, page_end, section_path FROM fragments"
        ).fetchone()
    assert page["printed_page_label"] == "15"
    assert tuple(fragment) == (27, 28, "Teckel")
