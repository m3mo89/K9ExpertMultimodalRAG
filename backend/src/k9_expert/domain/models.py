"""Stable value objects shared by application use cases and adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import NewType
from uuid import UUID

DocumentId = NewType("DocumentId", UUID)
DocumentVersionId = NewType("DocumentVersionId", UUID)
FragmentId = NewType("FragmentId", UUID)
SnapshotId = NewType("SnapshotId", UUID)
QueryId = NewType("QueryId", UUID)
ConversationId = NewType("ConversationId", UUID)
JobId = NewType("JobId", UUID)


class DocumentStatus(StrEnum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    DELETED = "deleted"
    ERROR = "error"


class JobStage(StrEnum):
    RECEIVED = "received"
    VALIDATING = "validating"
    EXTRACTING = "extracting"
    OCR = "ocr"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    BUILDING_INDEX = "building_index"
    VALIDATING_INDEX = "validating_index"
    PUBLISHING = "publishing"
    AVAILABLE = "available"
    ERROR = "error"


class QueryStatus(StrEnum):
    GROUNDED = "grounded"
    ABSTAINED = "abstained"
    REJECTED = "rejected"
    UNVERIFIED = "unverified"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class SourceRef:
    document_id: DocumentId
    version_id: DocumentVersionId
    title: str
    author: str | None
    edition: str | None
    physical_page: int
    printed_page_label: str | None


@dataclass(frozen=True, slots=True)
class Evidence:
    fragment_id: FragmentId
    source: SourceRef
    text: str
    score: float
    section_path: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class QueryFilters:
    document_ids: tuple[DocumentId, ...] = ()
    categories: tuple[str, ...] = ()
    breeds: tuple[str, ...] = ()
    sections: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class QueryCommand:
    query_id: QueryId
    text: str
    filters: QueryFilters = field(default_factory=QueryFilters)
    conversation_id: ConversationId | None = None


@dataclass(frozen=True, slots=True)
class Citation:
    evidence_id: FragmentId
    source: SourceRef


@dataclass(frozen=True, slots=True)
class QueryResult:
    query_id: QueryId
    status: QueryStatus
    answer: str
    snapshot_id: SnapshotId | None
    citations: tuple[Citation, ...] = ()
    trace_id: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class TraceEvent:
    trace_id: str
    event: str
    occurred_at: datetime
    attributes: dict[str, str | int | float | bool | None]

