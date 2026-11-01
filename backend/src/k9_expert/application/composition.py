"""Dependency composition. Concrete adapters are added without leaking into domain code."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from k9_expert.application.documents import DocumentRegistrationService, PdfValidator
from k9_expert.infrastructure.filesystem import ManagedFileStore
from k9_expert.infrastructure.sqlite import DocumentRepository, JobRepository, SqliteDatabase


@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    data_dir: Path = Path("data")
    host: str = "127.0.0.1"
    port: int = 8000
    worker_concurrency: int = 1
    admin_secret: str | None = None


@dataclass(frozen=True, slots=True)
class ApplicationContainer:
    settings: ApplicationSettings
    document_service: DocumentRegistrationService


def compose(settings: ApplicationSettings | None = None) -> ApplicationContainer:
    """Build the production container; adapters are wired here as capabilities land."""
    resolved = settings or ApplicationSettings(admin_secret=os.getenv("K9_ADMIN_SECRET"))
    database = SqliteDatabase(resolved.data_dir / "k9.sqlite")
    database.migrate()
    service = DocumentRegistrationService(
        ManagedFileStore(resolved.data_dir / "files"),
        DocumentRepository(database),
        JobRepository(database),
        PdfValidator(max_pages=1000),
        max_file_bytes=100 * 1024 * 1024,
    )
    return ApplicationContainer(settings=resolved, document_service=service)
