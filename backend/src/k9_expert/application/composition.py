"""Dependency composition. Concrete adapters are added without leaking into domain code."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from k9_expert.application.admin import AdminSecurityService
from k9_expert.application.documents import DocumentRegistrationService, PdfValidator
from k9_expert.application.generation import OllamaTextGateway
from k9_expert.application.ingestion import IngestionWorker
from k9_expert.application.interactions import InteractionService
from k9_expert.application.lifecycle import DocumentLifecycleService
from k9_expert.application.maintenance import (
    ComponentHealth,
    HealthService,
    OllamaModelProbe,
    ReindexService,
)
from k9_expert.application.query import QueryOrchestrator
from k9_expert.application.query_service import QueryService
from k9_expert.application.recovery import BackupService, IndexMaintainer, RestoreService
from k9_expert.infrastructure.embeddings import OllamaEmbedder
from k9_expert.infrastructure.filesystem import ManagedFileStore
from k9_expert.infrastructure.sqlite import (
    CacheInvalidator,
    ContentRepository,
    DocumentRepository,
    InteractionRepository,
    JobRepository,
    SecurityRepository,
    SnapshotRepository,
    SqliteDatabase,
    SystemStateRepository,
)
from k9_expert.ports.interfaces import Embedder


@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    data_dir: Path = Path("data")
    host: str = "127.0.0.1"
    port: int = 8000
    worker_concurrency: int = 1
    admin_secret: str | None = None
    config_path: Path = Path("config/k9.defaults.toml")
    deleted_source_retention_days: int = 30
    retain_deleted_excerpts: bool = True
    text_model: str = "llama3.2:3b"
    embedding_model: str = "nomic-embed-text:latest"

    @property
    def files_dir(self) -> Path:
        return self.data_dir / "files"

    @property
    def index_dir(self) -> Path:
        return self.data_dir / "index"

    @property
    def backup_dir(self) -> Path:
        return self.data_dir / "backups"


@dataclass(frozen=True, slots=True)
class ApplicationContainer:
    settings: ApplicationSettings
    document_service: DocumentRegistrationService
    interaction_service: InteractionService
    query_service: QueryService
    admin_security: AdminSecurityService
    lifecycle_service: DocumentLifecycleService
    reindex_service: ReindexService
    health_service: HealthService
    backup_service: BackupService
    restore_service: RestoreService
    ingestion_worker: IngestionWorker
    system_state: SystemStateRepository


def compose(
    settings: ApplicationSettings | None = None,
    model_probe: Callable[[], ComponentHealth] | None = None,
    embedder: Embedder | None = None,
) -> ApplicationContainer:
    """Build the production container; tests may substitute local-model adapters."""
    resolved = settings or ApplicationSettings(admin_secret=os.getenv("K9_ADMIN_SECRET"))
    database = SqliteDatabase(resolved.data_dir / "k9.sqlite")
    database.migrate()
    file_store = ManagedFileStore(resolved.files_dir)
    documents = DocumentRepository(database)
    jobs = JobRepository(database)
    snapshots = SnapshotRepository(database)
    state = SystemStateRepository(database)
    service = DocumentRegistrationService(
        file_store,
        documents,
        jobs,
        PdfValidator(max_pages=1000),
        max_file_bytes=100 * 1024 * 1024,
    )
    interactions = InteractionRepository(database)
    admin_security = AdminSecurityService(SecurityRepository(database), resolved.admin_secret)
    lifecycle_service = DocumentLifecycleService(
        snapshots,
        CacheInvalidator(),
        documents,
        admin_security,
        retention_days=resolved.deleted_source_retention_days,
        file_store=file_store,
        retain_deleted_excerpts=resolved.retain_deleted_excerpts,
    )
    query_service = QueryService(
        QueryOrchestrator(OllamaTextGateway(resolved.text_model).generate, lambda _request: []),
        documents,
        interactions,
        state,
    )
    # Rebuilt vectors must use the same document prefix as ingestion.
    embed = (
        embedder.embed
        if embedder
        else OllamaEmbedder(model=resolved.embedding_model).embed_documents
    )
    index = IndexMaintainer(snapshots, resolved.index_dir, embed)
    return ApplicationContainer(
        settings=resolved,
        document_service=service,
        interaction_service=InteractionService(interactions),
        query_service=query_service,
        admin_security=admin_security,
        lifecycle_service=lifecycle_service,
        reindex_service=ReindexService(documents),
        health_service=HealthService(
            database,
            state,
            resolved.files_dir,
            resolved.index_dir,
            model_probe
            or OllamaModelProbe((resolved.text_model, resolved.embedding_model)),
        ),
        backup_service=BackupService(
            database,
            resolved.files_dir,
            resolved.index_dir,
            resolved.backup_dir,
            resolved.config_path,
        ),
        restore_service=RestoreService(
            database,
            state,
            snapshots,
            index,
            resolved.files_dir,
            resolved.backup_dir,
            resolved.config_path,
        ),
        ingestion_worker=IngestionWorker(jobs, ContentRepository(database)),
        system_state=state,
    )
