from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import fitz

from k9_expert.application.ingestion import IngestionWorker
from k9_expert.infrastructure.sqlite import (
    ContentRepository,
    DocumentRepository,
    JobRepository,
    SqliteDatabase,
)


def source_pdf(path: Path) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "El teckel es un perro de caza con cuerpo alargado.")
    document.save(path)
    document.close()


def test_worker_persists_idempotent_extraction_and_fragments_after_retry(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source_pdf(source)
    database = SqliteDatabase(tmp_path / "k9.sqlite")
    database.migrate()
    documents = DocumentRepository(database)
    jobs = JobRepository(database)
    content = ContentRepository(database)
    document_id, version_id, job_id = uuid4(), uuid4(), uuid4()
    documents.create_document(document_id, "Teckel", None, None)
    documents.create_version(version_id, document_id, "hash", "source.pdf", str(source))
    jobs.enqueue(job_id, version_id)
    worker = IngestionWorker(jobs, content)
    assert worker.run_once() is True
    assert documents.job(str(job_id))["stage"] == "available"
    with database.connect() as connection:
        first_pages = connection.execute("SELECT count(*) FROM pages").fetchone()[0]
        first_fragments = connection.execute("SELECT count(*) FROM fragments").fetchone()[0]
    assert first_pages == 1 and first_fragments > 0

    jobs.fail(str(job_id), "simulated", "restart")
    jobs.retry(str(job_id))
    assert worker.run_once() is True
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM pages").fetchone()[0] == first_pages
        assert connection.execute("SELECT count(*) FROM fragments").fetchone()[0] == first_fragments
