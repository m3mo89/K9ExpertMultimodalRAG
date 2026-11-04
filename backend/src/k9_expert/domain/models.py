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
RecommendationId = NewType("RecommendationId", UUID)


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


class ProfileImportance(StrEnum):
    PREFERENCE = "preference"
    REQUIRED = "required"


class ProfileCompleteness(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class RecommendationBand(StrEnum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class AssertionPolarity(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"


class AssertionEvidenceState(StrEnum):
    DOCUMENTED = "documented"
    CONFLICTING = "conflicting"


class AssertionExtractionState(StrEnum):
    CANDIDATE = "candidate"
    QUARANTINED = "quarantined"
    REVIEWED = "reviewed"


class ReviewDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


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
class HunterProfileAnswer:
    """Original user answer retained independently from normalized policy dimensions."""

    key: str
    values: tuple[str, ...]
    importance: ProfileImportance = ProfileImportance.PREFERENCE

    def __post_init__(self) -> None:
        if (
            not self.key.strip()
            or not self.values
            or any(not value.strip() for value in self.values)
        ):
            raise ValueError("profile_answer_invalid")


@dataclass(frozen=True, slots=True)
class HunterProfile:
    answers: tuple[HunterProfileAnswer, ...]
    candidate_breeds: tuple[str, ...] = ()
    schema_version: str = "2.0"

    def __post_init__(self) -> None:
        keys = [answer.key for answer in self.answers]
        if len(keys) != len(set(keys)):
            raise ValueError("profile_answer_duplicate")


@dataclass(frozen=True, slots=True)
class RecommendationDimension:
    key: str
    values: tuple[str, ...]
    weight: float
    required: bool = False

    def __post_init__(self) -> None:
        if not self.key or not self.values or self.weight <= 0:
            raise ValueError("recommendation_dimension_invalid")


@dataclass(frozen=True, slots=True)
class ProfileConstraint:
    dimension: str
    values: tuple[str, ...]
    operator: str = "supports_any"


@dataclass(frozen=True, slots=True)
class TranslatedHunterProfile:
    original: HunterProfile
    dimensions: tuple[RecommendationDimension, ...]
    constraints: tuple[ProfileConstraint, ...]
    completeness: ProfileCompleteness
    missing_fields: tuple[str, ...] = ()
    translator_version: str = "hunter-profile-v1"


@dataclass(frozen=True, slots=True)
class RecommendationDimensionResult:
    key: str
    compatibility: float | None
    documented: bool
    conflicting: bool = False
    evidence_ids: tuple[FragmentId, ...] = ()


@dataclass(frozen=True, slots=True)
class RecommendationCandidate:
    breed: str
    band: RecommendationBand | None
    compatibility: float | None
    coverage: float
    dimensions: tuple[RecommendationDimensionResult, ...]
    penalties: tuple[str, ...] = ()
    excluded: bool = False


@dataclass(frozen=True, slots=True)
class RecommendationResult:
    recommendation_id: RecommendationId
    profile: TranslatedHunterProfile
    policy_version: str
    snapshot_id: SnapshotId | None
    candidates: tuple[RecommendationCandidate, ...] = ()
    limitations: tuple[str, ...] = ()
    trace_id: str | None = None
    summary: str | None = None


@dataclass(frozen=True, slots=True)
class BreedAssertionEvidence:
    fragment_id: FragmentId
    source: SourceRef


@dataclass(frozen=True, slots=True)
class BreedAssertion:
    assertion_id: UUID
    breed: str
    attribute_key: str
    value: str
    polarity: AssertionPolarity
    evidence_state: AssertionEvidenceState
    extraction_state: AssertionExtractionState
    extraction_method: str
    policy_version: str
    evidence: tuple[BreedAssertionEvidence, ...]
    review_decision: ReviewDecision | None = None

    def __post_init__(self) -> None:
        if not all((self.breed.strip(), self.attribute_key.strip(), self.value.strip())):
            raise ValueError("assertion_field_invalid")
        if not self.evidence:
            raise ValueError("assertion_evidence_required")


@dataclass(frozen=True, slots=True)
class BreedAttributeProfile:
    key: str
    assertions: tuple[BreedAssertion, ...]
    evidence_state: str


@dataclass(frozen=True, slots=True)
class StructuredBreedProfile:
    breed: str
    snapshot_id: SnapshotId
    attributes: tuple[BreedAttributeProfile, ...]
    policy_version: str


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
