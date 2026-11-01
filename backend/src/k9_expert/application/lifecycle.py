from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from k9_expert.application.admin import AdminSecurityService
from k9_expert.infrastructure.filesystem import ManagedFileStore
from k9_expert.infrastructure.sqlite import (
    CacheInvalidator,
    DocumentRepository,
    PrepareIndex,
    SnapshotRepository,
)


@dataclass(slots=True)
class CleanupReport:
    removed: list[str] = field(default_factory=list)
    already_absent: list[str] = field(default_factory=list)
    kept_shared: list[str] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)


class DocumentLifecycleService:
    def __init__(
        self,
        snapshots: SnapshotRepository,
        cache: CacheInvalidator,
        documents: DocumentRepository | None = None,
        security: AdminSecurityService | None = None,
        retention_days: int = 30,
        file_store: ManagedFileStore | None = None,
        retain_deleted_excerpts: bool = True,
        prepare_index: PrepareIndex | None = None,
        indexed_ids: Callable[[str], set[str]] | None = None,
    ) -> None:
        self.snapshots = snapshots
        self.cache = cache
        self.documents = documents
        self.security = security
        self.retention_days = retention_days
        self.file_store = file_store
        self.retain_deleted_excerpts = retain_deleted_excerpts
        # Builds the candidate's vector generation before activation commits.
        self.prepare_index = prepare_index
        self.indexed_ids = indexed_ids

    def deactivate(self, document_id: str) -> str:
        previous, published = self.snapshots.publish_document_membership(
            uuid4(), document_id, include=False, prepare_index=self.prepare_index
        )
        self.cache.invalidate_snapshot(previous)
        return published

    def reactivate(self, document_id: str) -> str:
        previous, published = self.snapshots.publish_document_membership(
            uuid4(), document_id, include=True, prepare_index=self.prepare_index
        )
        self.cache.invalidate_snapshot(previous)
        return published

    def rollback(self, snapshot_id: str) -> str:
        """Reactivate a retained snapshot whose vector generation is still complete."""
        snapshot = self.snapshots.snapshot(snapshot_id)
        if snapshot is None:
            raise KeyError("snapshot_not_found")
        if self.indexed_ids is None:
            raise RuntimeError("rollback_not_configured")
        if self.indexed_ids(snapshot_id) != set(self.snapshots.membership(snapshot_id)):
            raise ValueError("snapshot_index_incomplete")
        previous = self.snapshots.active_membership_snapshot_id()
        self.snapshots.rollback(UUID(snapshot_id))
        if previous is not None:
            self.cache.invalidate_snapshot(previous)
        return snapshot_id

    def delete(
        self, document_id: str, actor_id: str, confirmation: str, resource_version: str
    ) -> str:
        if self.documents is None or self.security is None:
            raise RuntimeError("deletion_not_configured")
        current_version = self.documents.resource_version(document_id)
        if current_version != resource_version:
            raise ValueError("stale_resource_version")
        if not self.security.consume_confirmation(
            confirmation, actor_id, document_id, "delete", resource_version
        ):
            raise ValueError("invalid_confirmation")
        published = self.deactivate(document_id)
        cleanup_after = datetime.now(UTC) + timedelta(days=self.retention_days)
        self.documents.mark_deleted_and_schedule_cleanup(
            document_id, cleanup_after.isoformat(), self.retain_deleted_excerpts
        )
        return published

    def run_due_cleanup(self, as_of: datetime | None = None) -> CleanupReport:
        """Physically remove source files of deleted documents whose retention has elapsed."""
        if self.documents is None or self.file_store is None:
            raise RuntimeError("cleanup_not_configured")
        report = CleanupReport()
        for entry in self.documents.due_cleanups((as_of or datetime.now(UTC)).isoformat()):
            cleanup_id, file_path = str(entry["id"]), str(entry["file_path"])
            # Storage is content-addressed, so another live document may share the file.
            if self.documents.file_referenced_by_live_document(file_path):
                self.documents.finish_cleanup(cleanup_id, "kept_shared")
                report.kept_shared.append(cleanup_id)
                continue
            try:
                removed = self.file_store.remove_document_file(Path(file_path))
            except ValueError:
                self.documents.finish_cleanup(cleanup_id, "refused")
                report.refused.append(cleanup_id)
                continue
            self.documents.finish_cleanup(cleanup_id, "completed")
            (report.removed if removed else report.already_absent).append(cleanup_id)
        return report
