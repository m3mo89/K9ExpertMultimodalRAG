from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from k9_expert.application.admin import AdminSecurityService
from k9_expert.infrastructure.sqlite import (
    CacheInvalidator,
    DocumentRepository,
    SnapshotRepository,
)


class DocumentLifecycleService:
    def __init__(
        self,
        snapshots: SnapshotRepository,
        cache: CacheInvalidator,
        documents: DocumentRepository | None = None,
        security: AdminSecurityService | None = None,
        retention_days: int = 30,
    ) -> None:
        self.snapshots = snapshots
        self.cache = cache
        self.documents = documents
        self.security = security
        self.retention_days = retention_days

    def deactivate(self, document_id: str) -> str:
        previous, published = self.snapshots.publish_document_membership(
            uuid4(), document_id, include=False
        )
        self.cache.invalidate_snapshot(previous)
        return published

    def reactivate(self, document_id: str) -> str:
        previous, published = self.snapshots.publish_document_membership(
            uuid4(), document_id, include=True
        )
        self.cache.invalidate_snapshot(previous)
        return published

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
            document_id, cleanup_after.isoformat()
        )
        return published
