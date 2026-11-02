from pathlib import Path
from uuid import uuid4

import pytest

from k9_expert.domain.breed_vocabulary import classify_section
from k9_expert.infrastructure.filesystem import (
    ManagedFileStore,
    StagedFile,
    StagedFileNotFoundError,
)
from k9_expert.infrastructure.sqlite import (
    BREED_MATCH_TABLES,
    SCHEMA_VERSION,
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


def test_v3_migration_is_additive_and_preserves_existing_rows(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "legacy.sqlite")
    database.migrate()
    document_id = str(uuid4())
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO documents VALUES (?, 'Legacy', NULL, NULL, 'active', NULL, 'a', 'b')",
            (document_id,),
        )
        for table in (
            "breed_analysis_citations",
            "breed_analysis_findings",
            "breed_analysis_candidates",
            "analysis_feedback",
            "breed_analyses",
            "exact_response_cache",
            "semantic_response_cache",
        ):
            connection.execute(f"DROP TABLE {table}")
        connection.execute("PRAGMA user_version = 3")

    database.migrate()

    with database.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert connection.execute(
            "SELECT title FROM documents WHERE id = ?", (document_id,)
        ).fetchone()["title"] == "Legacy"
        tables = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    assert "breed_analyses" in tables
    assert "semantic_response_cache" in tables
    assert "CREATE TABLE" in BREED_MATCH_TABLES


def test_managed_file_store_uses_content_hash_and_atomic_destination(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-1.7 sample")
    store = ManagedFileStore(tmp_path / "managed")
    with source.open("rb") as handle:
        staged = store.stage(handle, max_bytes=1024)
    destination = store.promote(staged)
    assert destination.read_bytes() == source.read_bytes()
    assert destination.parent.parent == (tmp_path / "managed" / "documents").resolve()
    assert not staged.path.exists()


def test_file_store_rejects_oversized_and_external_staging_paths(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"012345")
    store = ManagedFileStore(tmp_path / "managed")
    with source.open("rb") as handle:
        with pytest.raises(ValueError, match="upload_too_large"):
            store.stage(handle, max_bytes=5)
    invalid = StagedFile(source, "not-used", source.stat().st_size)
    with pytest.raises(StagedFileNotFoundError):
        store.discard(invalid)


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


def test_content_persists_versioned_optional_classification(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "k9.sqlite")
    database.migrate()
    documents = DocumentRepository(database)
    document_id, version_id, fragment_id = uuid4(), uuid4(), uuid4()
    documents.create_document(document_id, "Enciclopedia", None, None)
    documents.create_version(version_id, document_id, "hash", "book.pdf", "files/book.pdf")
    ContentRepository(database).add_fragment(
        fragment_id, version_id, "fragment", 1, "Texto", 27, 27, "direct", "v3",
        "Perros de rastro/Teckel alemán/Manto",
        classify_section(("Perros de rastro", "Teckel alemán", "Manto")),
    )
    with database.connect() as connection:
        row = connection.execute(
            "SELECT * FROM fragment_classification WHERE fragment_id = ?", (str(fragment_id),)
        ).fetchone()
    assert row["breed"] == "Teckel alemán"
    assert row["breed_group"] == "perros de rastro"
    assert row["hunting_functions_json"] == '["rastro"]'
    assert row["section"] == "morfologia:manto"
