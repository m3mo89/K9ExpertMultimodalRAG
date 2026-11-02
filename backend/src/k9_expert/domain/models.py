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
BreedAnalysisId = NewType("BreedAnalysisId", UUID)


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


class AnalysisStatus(StrEnum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    ABSTAINED = "abstained"
    REJECTED = "rejected"
    UNAVAILABLE = "unavailable"


class FindingOutcome(StrEnum):
    MATCH = "match"
    MISMATCH = "mismatch"
    NOT_DOCUMENTED = "not_documented"


class GuardrailAction(StrEnum):
    ALLOW = "allow"
    BLOCK = "block"
    RETRY = "retry"
    ABSTAIN = "abstain"


class CacheHitType(StrEnum):
    MISS = "miss"
    EXACT = "exact"
    SEMANTIC = "semantic"


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
class BreedCriterion:
    """One normalized, documentable preference in a versioned profile."""

    key: str
    value: str
    weight: float = 1.0


@dataclass(frozen=True, slots=True)
class BreedAnalysisProfile:
    criteria: tuple[BreedCriterion, ...]
    candidate_breeds: tuple[str, ...] = ()
    document_ids: tuple[DocumentId, ...] = ()
    policy_version: str = "breed-match-v1"


@dataclass(frozen=True, slots=True)
class BreedFinding:
    criterion: BreedCriterion
    outcome: FindingOutcome
    explanation: str
    citations: tuple[Citation, ...] = ()


@dataclass(frozen=True, slots=True)
class BreedCandidate:
    breed: str
    findings: tuple[BreedFinding, ...]
    score: float | None
    documented_weight: float
    possible_weight: float
    coverage: float


@dataclass(frozen=True, slots=True)
class ExecutionMetadata:
    route: str | None = None
    resolved_model: str | None = None
    cache_hit: CacheHitType = CacheHitType.MISS
    agent_iterations: int = 0
    latency_ms: float | None = None
    route_reason: str | None = None
    cache_similarity: float | None = None
    fallback_used: bool = False
    # "action" or "action:reason" for each guardrail stage that ran.
    input_guardrail: str | None = None
    output_guardrail: str | None = None


@dataclass(frozen=True, slots=True)
class BreedAnalysisReport:
    analysis_id: BreedAnalysisId
    status: AnalysisStatus
    profile: BreedAnalysisProfile
    snapshot_id: SnapshotId | None
    candidates: tuple[BreedCandidate, ...] = ()
    limitations: tuple[str, ...] = ()
    trace_id: str | None = None
    reason: str | None = None
    execution: ExecutionMetadata = field(default_factory=ExecutionMetadata)
    # Model narrative over verified findings; it never alters candidates or scores.
    summary: str | None = None


@dataclass(frozen=True, slots=True)
class AnalysisFeedback:
    analysis_id: BreedAnalysisId
    useful: bool
    comment: str | None = None


@dataclass(frozen=True, slots=True)
class GuardrailDecision:
    action: GuardrailAction
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class RouteDecision:
    alias: str
    reason: str
    policy_version: str


@dataclass(frozen=True, slots=True)
class CacheLookup:
    hit_type: CacheHitType
    value: str | None = None
    similarity: float | None = None


@dataclass(frozen=True, slots=True)
class QueryResult:
    query_id: QueryId
    status: QueryStatus
    answer: str
    snapshot_id: SnapshotId | None
    citations: tuple[Citation, ...] = ()
    trace_id: str | None = None
    reason: str | None = None
    # Cited evidence from different documents holds incompatible positions.
    discrepancy: bool = False


@dataclass(frozen=True, slots=True)
class TraceEvent:
    trace_id: str
    event: str
    occurred_at: datetime
    # JSON-serializable; telemetry sinks must store only redacted attributes.
    attributes: dict[str, object]
