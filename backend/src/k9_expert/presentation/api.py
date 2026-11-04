from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import quote
from uuid import UUID, uuid4

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from k9_expert.application.composition import ApplicationContainer, compose
from k9_expert.application.documents import (
    DuplicateDocumentError,
    UploadValidationError,
)
from k9_expert.application.profile_translation import HunterProfileTranslator
from k9_expert.application.query_service import SubmitQuery
from k9_expert.application.recovery import BackupError
from k9_expert.domain.models import (
    BreedAnalysisProfile,
    BreedAnalysisReport,
    BreedCriterion,
    DocumentId,
    HunterProfile,
    HunterProfileAnswer,
    ProfileImportance,
    QueryFilters,
    ReviewDecision,
)


class HealthResponse(BaseModel):
    status: str
    worker_concurrency: int


class ModelConfigurationResponse(BaseModel):
    """Logical aliases and versions only: no runtime addresses, paths or secrets."""

    text_models: dict[str, str]
    embedding_model: str
    router_policy: str
    guardrail_policy: str
    breed_match_policy: str
    semantic_cache_threshold: float
    agent_max_iterations: int
    breed_match_minimum_coverage: float


class UploadResponse(BaseModel):
    document_id: str
    version_id: str
    job_id: str
    status: str = "received"


class DocumentResponse(BaseModel):
    id: str
    title: str
    author: str | None
    category: str | None
    status: str
    active_version_id: str | None
    edition: str | None
    updated_at: str


class JobResponse(BaseModel):
    id: str
    version_id: str
    stage: str
    attempt: int
    error_code: str | None


class VersionResponse(BaseModel):
    id: str
    content_hash: str
    source_filename: str
    edition: str | None
    status: str
    created_at: str
    job_id: str | None
    job_stage: str | None
    job_attempt: int | None
    failed_stage: str | None
    error_code: str | None
    job_updated_at: str | None


class ConversationSummary(BaseModel):
    id: str
    title: str | None
    created_at: str
    updated_at: str


class ConversationResponse(BaseModel):
    id: str
    created_at: str
    updated_at: str
    messages: list[dict[str, object]] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    useful: bool
    comment: str | None = None


class FeedbackResponse(BaseModel):
    id: str
    answer_id: str
    useful: int
    comment: str | None
    created_at: str


class QueryFiltersRequest(BaseModel):
    document_ids: list[UUID] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    breeds: list[str] = Field(default_factory=list)
    sections: list[str] = Field(default_factory=list)


class QueryRequestBody(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    conversation_id: UUID | None = None
    filters: QueryFiltersRequest = Field(default_factory=QueryFiltersRequest)


class QueryResponse(BaseModel):
    query_id: str
    answer_id: str | None
    status: str
    answer: str
    snapshot_id: str | None
    reason: str | None
    citations: list[dict[str, object]]
    conversation_id: str | None = None
    trace_id: str | None = None
    discrepancy: bool = False


class BreedCriterionRequest(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=200)
    weight: float = Field(default=1.0, gt=0, le=10)


class BreedAnalysisRequest(BaseModel):
    schema_version: str = Field(default="1.0", pattern=r"^1(?:\.\d+)?$")
    criteria: list[BreedCriterionRequest] = Field(min_length=1, max_length=12)
    candidate_breeds: list[str] = Field(default_factory=list, max_length=12)
    document_ids: list[UUID] = Field(default_factory=list, max_length=20)


class HunterProfileAnswerRequest(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    values: list[str] = Field(min_length=1, max_length=12)
    importance: ProfileImportance = ProfileImportance.PREFERENCE


class HunterProfileRequest(BaseModel):
    schema_version: str = Field(default="2.0", pattern=r"^2(?:\.\d+)?$")
    answers: list[HunterProfileAnswerRequest] = Field(min_length=1, max_length=20)
    candidate_breeds: list[str] = Field(default_factory=list, max_length=12)


class RecommendationDimensionResponse(BaseModel):
    key: str
    values: list[str]
    weight: float
    required: bool


class HunterProfileValidationResponse(BaseModel):
    schema_version: str = "2.0"
    translator_version: str
    completeness: str
    missing_fields: list[str]
    dimensions: list[RecommendationDimensionResponse]
    constraints: list[str]


class RecommendationCandidateResponse(BaseModel):
    breed: str
    band: str | None
    compatibility: float | None
    coverage: float
    penalties: list[str] = Field(default_factory=list)
    excluded: bool = False
    dimensions: list[dict[str, object]] = Field(default_factory=list)


class HunterRecommendationResponse(BaseModel):
    schema_version: str = "2.0"
    recommendation_id: str
    status: str
    policy_version: str
    snapshot_id: str | None
    candidates: list[RecommendationCandidateResponse] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    trace_id: str | None = None
    summary: str | None = None


class RecommendationContextRequest(BaseModel):
    selected_breeds: list[str] = Field(min_length=1, max_length=3)


class RecommendationContextQueryRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class AnalysisCitationResponse(BaseModel):
    id: str | None = None
    fragment_id: str
    document_id: str
    version_id: str
    title: str
    physical_page: int
    printed_page_label: str | None = None


class BreedFindingResponse(BaseModel):
    criterion_key: str
    criterion_value: str
    outcome: str
    explanation: str
    citations: list[AnalysisCitationResponse] = Field(default_factory=list)


class BreedCandidateResponse(BaseModel):
    breed: str
    score: float | None
    documented_weight: float
    possible_weight: float
    coverage: float
    findings: list[BreedFindingResponse] = Field(default_factory=list)


class AnalysisExecutionResponse(BaseModel):
    route: str | None = None
    resolved_model: str | None = None
    cache_hit: str = "miss"
    agent_iterations: int = 0
    latency_ms: float | None = None
    route_reason: str | None = None
    cache_similarity: float | None = None
    fallback_used: bool = False
    input_guardrail: str | None = None
    output_guardrail: str | None = None


class BreedAnalysisResponse(BaseModel):
    schema_version: str = "1.0"
    analysis_id: str
    status: str
    snapshot_id: str | None
    criteria: list[BreedCriterionRequest]
    candidates: list[BreedCandidateResponse] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    trace_id: str | None = None
    reason: str | None = None
    execution: AnalysisExecutionResponse = Field(default_factory=AnalysisExecutionResponse)
    summary: str | None = None


class BreedProfileSectionResponse(BaseModel):
    heading: str
    text: str
    citation: AnalysisCitationResponse


class BreedListItem(BaseModel):
    name: str
    group: str | None = None
    fragment_count: int


class BreedProfileResponse(BaseModel):
    breed: str
    sections: list[BreedProfileSectionResponse]
    photo_url: str | None = None
    photo_caption: str | None = None
    photo_page: int | None = None


class AnalysisFeedbackRequest(BaseModel):
    useful: bool
    comment: str | None = Field(default=None, max_length=1000)


class AnalysisFeedbackResponse(BaseModel):
    id: str
    analysis_id: str
    trace_id: str
    useful: int
    comment: str | None
    created_at: str


class ErrorEnvelope(BaseModel):
    code: str
    message: str
    details: object | None
    trace_id: str
    retryable: bool


class ConfirmationRequest(BaseModel):
    resource_id: str = Field(min_length=1, max_length=200)
    operation: str = Field(min_length=1, max_length=100)
    resource_version: str = Field(min_length=1, max_length=200)


class ConfirmationResponse(BaseModel):
    token: str
    expires_at: str


class PublicationResponse(BaseModel):
    document_id: str
    snapshot_id: str
    status: str


class DeleteDocumentRequest(BaseModel):
    confirmation_token: str = Field(min_length=1)
    resource_version: str = Field(min_length=1)


class CompleteReindexRequest(BaseModel):
    explicitly_requested: bool = False


class BackupRequest(BaseModel):
    include_indexes: bool = False


class RestoreRequest(BaseModel):
    confirmation_token: str = Field(min_length=1)


class AssertionReviewRequest(BaseModel):
    decision: ReviewDecision
    snapshot_id: UUID | None = None
    comment: str | None = Field(default=None, max_length=1000)


def error_response(status_code: int, code: str, details: object | None = None) -> JSONResponse:
    payload = ErrorEnvelope(
        code=code,
        message=code.replace("_", " "),
        details=details,
        trace_id=str(uuid4()),
        retryable=status_code >= 500,
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def admin_guard(container: ApplicationContainer) -> Callable[..., str]:
    def require_admin(
        x_k9_admin_secret: Annotated[str | None, Header()] = None,
        x_k9_actor: Annotated[str, Header(min_length=1, max_length=100)] = "local-admin",
    ) -> str:
        if not container.admin_security.authenticate(x_k9_admin_secret, x_k9_actor):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="admin_unauthorized"
            )
        return x_k9_actor

    return require_admin


def breed_analysis_response(report: BreedAnalysisReport) -> BreedAnalysisResponse:
    return BreedAnalysisResponse(
        analysis_id=str(report.analysis_id), status=str(report.status),
        snapshot_id=str(report.snapshot_id) if report.snapshot_id else None,
        criteria=[BreedCriterionRequest(key=item.key, value=item.value, weight=item.weight)
                  for item in report.profile.criteria],
        candidates=[BreedCandidateResponse(
            breed=candidate.breed, score=candidate.score,
            documented_weight=candidate.documented_weight,
            possible_weight=candidate.possible_weight, coverage=candidate.coverage,
            findings=[BreedFindingResponse(
                criterion_key=finding.criterion.key,
                criterion_value=finding.criterion.value, outcome=str(finding.outcome),
                explanation=finding.explanation,
                citations=[AnalysisCitationResponse(
                    fragment_id=str(citation.evidence_id),
                    document_id=str(citation.source.document_id),
                    version_id=str(citation.source.version_id), title=citation.source.title,
                    physical_page=citation.source.physical_page,
                    printed_page_label=citation.source.printed_page_label,
                ) for citation in finding.citations],
            ) for finding in candidate.findings],
        ) for candidate in report.candidates],
        limitations=list(report.limitations), trace_id=report.trace_id, reason=report.reason,
        execution=AnalysisExecutionResponse(
            route=report.execution.route, resolved_model=report.execution.resolved_model,
            cache_hit=str(report.execution.cache_hit),
            agent_iterations=report.execution.agent_iterations,
            latency_ms=report.execution.latency_ms,
            route_reason=report.execution.route_reason,
            cache_similarity=report.execution.cache_similarity,
            fallback_used=report.execution.fallback_used,
            input_guardrail=report.execution.input_guardrail,
            output_guardrail=report.execution.output_guardrail,
        ),
        summary=report.summary,
    )


def create_app(container: ApplicationContainer | None = None) -> FastAPI:
    resolved = container or compose()
    app = FastAPI(title="K9 Expert", version="0.1.0")
    require_admin = admin_guard(resolved)

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, error: HTTPException) -> JSONResponse:
        code = str(error.detail) if isinstance(error.detail, str) else "request_failed"
        return error_response(error.status_code, code, error.detail)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
        return error_response(422, "request_validation_failed", error.errors())

    @app.exception_handler(Exception)
    async def unexpected_error(_request: Request, _error: Exception) -> JSONResponse:
        # Unhandled failures still answer with the envelope; details stay in the server log.
        return error_response(500, "internal_error")

    @app.get("/api/v1/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", worker_concurrency=resolved.settings.worker_concurrency)

    @app.get("/api/v1/configuration", response_model=ModelConfigurationResponse)
    def configuration() -> ModelConfigurationResponse:
        settings = resolved.settings
        return ModelConfigurationResponse(
            text_models={
                "simple": settings.text_simple_model,
                "complex": settings.text_complex_model,
                "fallback": settings.text_fallback_model,
            },
            embedding_model=settings.embedding_model,
            router_policy=settings.router_policy_version,
            guardrail_policy=settings.guardrail_policy_version,
            breed_match_policy=settings.breed_match_policy_version,
            semantic_cache_threshold=settings.semantic_cache_threshold,
            agent_max_iterations=settings.agent_max_iterations,
            breed_match_minimum_coverage=settings.breed_match_minimum_coverage,
        )

    @app.post(
        "/api/v1/admin/confirmations",
        response_model=ConfirmationResponse,
        dependencies=[Depends(require_admin)],
    )
    def create_confirmation(
        request: ConfirmationRequest,
        x_k9_actor: Annotated[str, Header(min_length=1, max_length=100)] = "local-admin",
    ) -> ConfirmationResponse:
        token, expires_at = resolved.admin_security.issue_confirmation(
            x_k9_actor, request.resource_id, request.operation, request.resource_version
        )
        return ConfirmationResponse(token=token, expires_at=expires_at)

    @app.get("/api/v2/admin/assertions", dependencies=[Depends(require_admin)])
    def list_assertion_candidates(state: str | None = None) -> list[dict[str, object]]:
        return resolved.structured_knowledge.candidates(state)

    @app.post(
        "/api/v2/admin/assertions/{assertion_id}/review",
        dependencies=[Depends(require_admin)],
    )
    def review_assertion(
        assertion_id: str,
        request: AssertionReviewRequest,
        x_k9_actor: Annotated[str, Header(min_length=1, max_length=100)] = "local-admin",
    ) -> dict[str, str]:
        try:
            resolved.structured_knowledge.review(
                assertion_id,
                x_k9_actor,
                request.decision,
                str(request.snapshot_id) if request.snapshot_id else None,
                request.comment,
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error.args[0])) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        resolved.admin_security.record(
            x_k9_actor, f"assertion_{request.decision}", assertion_id
        )
        return {"assertion_id": assertion_id, "decision": str(request.decision)}

    @app.post(
        "/api/v1/documents/{document_id}/deactivate",
        response_model=PublicationResponse,
        dependencies=[Depends(require_admin)],
    )
    def deactivate_document(document_id: str) -> PublicationResponse:
        try:
            snapshot_id = resolved.lifecycle_service.deactivate(document_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error.args[0])) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return PublicationResponse(
            document_id=document_id, snapshot_id=snapshot_id, status="deactivated"
        )

    @app.post(
        "/api/v1/documents/{document_id}/reactivate",
        response_model=PublicationResponse,
        dependencies=[Depends(require_admin)],
    )
    def reactivate_document(document_id: str) -> PublicationResponse:
        try:
            snapshot_id = resolved.lifecycle_service.reactivate(document_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error.args[0])) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return PublicationResponse(
            document_id=document_id, snapshot_id=snapshot_id, status="active"
        )

    @app.post(
        "/api/v1/admin/snapshots/{snapshot_id}/rollback",
        dependencies=[Depends(require_admin)],
    )
    def rollback_snapshot(
        snapshot_id: str,
        x_k9_actor: Annotated[str, Header(min_length=1, max_length=100)] = "local-admin",
    ) -> dict[str, str]:
        try:
            active = resolved.lifecycle_service.rollback(snapshot_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error.args[0])) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        resolved.admin_security.record(x_k9_actor, "snapshot_rolled_back", snapshot_id)
        return {"snapshot_id": active, "status": "active"}

    @app.delete(
        "/api/v1/documents/{document_id}",
        response_model=PublicationResponse,
        dependencies=[Depends(require_admin)],
    )
    def delete_document(
        document_id: str,
        request: DeleteDocumentRequest,
        x_k9_actor: Annotated[str, Header(min_length=1, max_length=100)] = "local-admin",
    ) -> PublicationResponse:
        try:
            snapshot_id = resolved.lifecycle_service.delete(
                document_id,
                x_k9_actor,
                request.confirmation_token,
                request.resource_version,
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error.args[0])) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        resolved.admin_security.record(x_k9_actor, "document_deleted", document_id)
        return PublicationResponse(
            document_id=document_id, snapshot_id=snapshot_id, status="deleted"
        )

    @app.post("/api/v1/admin/cleanup", dependencies=[Depends(require_admin)])
    def run_cleanup(
        x_k9_actor: Annotated[str, Header(min_length=1, max_length=100)] = "local-admin",
    ) -> dict[str, object]:
        report = resolved.lifecycle_service.run_due_cleanup()
        resolved.admin_security.record(x_k9_actor, "cleanup_run")
        return {
            "removed": len(report.removed),
            "already_absent": len(report.already_absent),
            "kept_shared": len(report.kept_shared),
            "refused": len(report.refused),
        }

    @app.post(
        "/api/v1/documents/{document_id}/reindex",
        status_code=202,
        dependencies=[Depends(require_admin)],
    )
    def reindex_document(
        document_id: str,
        x_k9_actor: Annotated[str, Header(min_length=1, max_length=100)] = "local-admin",
    ) -> dict[str, object]:
        try:
            progress = resolved.reindex_service.reindex_document(document_id, x_k9_actor)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error.args[0])) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        resolved.admin_security.record(x_k9_actor, "reindex_requested", document_id)
        return progress

    @app.post("/api/v1/admin/reindex", status_code=202, dependencies=[Depends(require_admin)])
    def reindex_all(
        request: CompleteReindexRequest,
        x_k9_actor: Annotated[str, Header(min_length=1, max_length=100)] = "local-admin",
    ) -> dict[str, object]:
        try:
            progress = resolved.reindex_service.reindex_all(
                x_k9_actor, request.explicitly_requested
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        resolved.admin_security.record(x_k9_actor, "complete_reindex_requested")
        return progress

    @app.get("/api/v1/admin/reindex/{request_id}", dependencies=[Depends(require_admin)])
    def reindex_progress(request_id: str) -> dict[str, object]:
        try:
            return resolved.reindex_service.progress(request_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error.args[0])) from error

    @app.get("/api/v1/admin/health", dependencies=[Depends(require_admin)])
    def diagnostics() -> dict[str, object]:
        return resolved.health_service.report()

    @app.get("/api/v1/admin/metrics", dependencies=[Depends(require_admin)])
    def metrics() -> dict[str, object]:
        return resolved.metrics_service.report()

    @app.get("/api/v1/admin/traces", dependencies=[Depends(require_admin)])
    def list_traces(
        kind: Annotated[str | None, Query(pattern="^(query|ingestion)$")] = None,
        job_id: str | None = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> list[dict[str, object]]:
        return resolved.telemetry.recent(kind=kind, job_id=job_id, limit=limit)

    @app.get("/api/v1/admin/traces/{trace_id}", dependencies=[Depends(require_admin)])
    def export_trace(
        trace_id: str,
        x_k9_actor: Annotated[str, Header(min_length=1, max_length=100)] = "local-admin",
        include_protected: bool = False,
    ) -> dict[str, object]:
        exported = resolved.telemetry.export(trace_id, include_protected)
        if exported is None:
            raise HTTPException(status_code=404, detail="trace_not_found")
        if include_protected:
            resolved.admin_security.record(x_k9_actor, "trace_protected_export", trace_id)
        return exported

    @app.get("/api/v1/admin/backups", dependencies=[Depends(require_admin)])
    def list_backups() -> list[dict[str, object]]:
        return resolved.backup_service.list()

    @app.post("/api/v1/admin/backups", status_code=201, dependencies=[Depends(require_admin)])
    def create_backup(
        request: BackupRequest,
        x_k9_actor: Annotated[str, Header(min_length=1, max_length=100)] = "local-admin",
    ) -> dict[str, object]:
        manifest = resolved.backup_service.create(request.include_indexes)
        resolved.admin_security.record(x_k9_actor, "backup_created", str(manifest["backup_id"]))
        return {key: value for key, value in manifest.items() if key != "entries"}

    @app.post("/api/v1/admin/backups/{backup_id}/restore", dependencies=[Depends(require_admin)])
    def restore_backup(
        backup_id: str,
        request: RestoreRequest,
        x_k9_actor: Annotated[str, Header(min_length=1, max_length=100)] = "local-admin",
    ) -> dict[str, object]:
        try:
            resource_version = resolved.restore_service.resource_version(backup_id)
            if not resolved.admin_security.consume_confirmation(
                request.confirmation_token, x_k9_actor, backup_id, "restore", resource_version
            ):
                raise HTTPException(status_code=409, detail="invalid_confirmation")
            report = resolved.restore_service.restore(backup_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error.args[0])) from error
        except BackupError as error:
            raise HTTPException(status_code=422, detail=error.code) from error
        # The audit trail lives in the restored database, so record after the swap.
        resolved.admin_security.record(x_k9_actor, "backup_restored", backup_id)
        return report

    @app.post("/api/v1/queries", response_model=QueryResponse)
    def submit_query(request: QueryRequestBody) -> QueryResponse:
        breeds = tuple(request.filters.breeds)
        # Filter values must be registered canonical names; an unknown breed would silently
        # match nothing. Without a registry (no active snapshot) the query reports that instead.
        if breeds and resolved.breed_registry.names():
            canonical = [resolved.breed_registry.resolve(name) for name in breeds]
            if None in canonical:
                raise HTTPException(status_code=422, detail="breed_not_found")
            breeds = tuple(name for name in canonical if name is not None)
        filters = QueryFilters(
            document_ids=tuple(DocumentId(item) for item in request.filters.document_ids),
            categories=tuple(request.filters.categories),
            breeds=breeds,
            sections=tuple(request.filters.sections),
        )
        try:
            stored = resolved.query_service.submit(
                SubmitQuery(
                    text=request.text,
                    conversation_id=(
                        str(request.conversation_id) if request.conversation_id else None
                    ),
                    filters=filters,
                )
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error.args[0])) from error
        result = stored.result
        citation_ids: list[str | None] = list(stored.citation_ids) or [None] * len(
            result.citations
        )
        return QueryResponse(
            query_id=str(result.query_id), answer_id=stored.answer_id,
            status=str(result.status), answer=result.answer,
            snapshot_id=str(result.snapshot_id) if result.snapshot_id else None,
            reason=result.reason, trace_id=result.trace_id,
            discrepancy=result.discrepancy,
            conversation_id=str(request.conversation_id) if request.conversation_id else None,
            citations=[{
                "id": citation_id, "fragment_id": str(citation.evidence_id),
                "document_id": str(citation.source.document_id),
                "version_id": str(citation.source.version_id), "title": citation.source.title,
                "author": citation.source.author, "edition": citation.source.edition,
                "physical_page": citation.source.physical_page,
                "printed_page_label": citation.source.printed_page_label,
                "source_status": "active",
            } for citation_id, citation in zip(citation_ids, result.citations, strict=True)],
        )

    @app.post(
        "/api/v1/breed-analyses", response_model=BreedAnalysisResponse, status_code=201
    )
    def analyze_breeds(request: BreedAnalysisRequest) -> BreedAnalysisResponse:
        profile = BreedAnalysisProfile(
            tuple(BreedCriterion(item.key, item.value, item.weight) for item in request.criteria),
            tuple(request.candidate_breeds),
            tuple(DocumentId(item) for item in request.document_ids),
        )
        return breed_analysis_response(resolved.breed_analysis_service.analyze(profile))

    @app.post(
        "/api/v2/hunter-profiles/validate", response_model=HunterProfileValidationResponse
    )
    def validate_hunter_profile(request: HunterProfileRequest) -> HunterProfileValidationResponse:
        if not resolved.settings.recommendation_api_enabled:
            raise HTTPException(status_code=404, detail="recommendation_api_disabled")
        try:
            translated = HunterProfileTranslator().translate(HunterProfile(
                answers=tuple(
                    HunterProfileAnswer(
                        key=answer.key,
                        values=tuple(answer.values),
                        importance=answer.importance,
                    )
                    for answer in request.answers
                ),
                candidate_breeds=tuple(request.candidate_breeds),
                schema_version=request.schema_version,
            ))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return HunterProfileValidationResponse(
            translator_version=translated.translator_version,
            completeness=str(translated.completeness),
            missing_fields=list(translated.missing_fields),
            dimensions=[
                RecommendationDimensionResponse(
                    key=item.key, values=list(item.values), weight=item.weight,
                    required=item.required,
                )
                for item in translated.dimensions
            ],
            constraints=[item.dimension for item in translated.constraints],
        )

    @app.post(
        "/api/v2/recommendations", response_model=HunterRecommendationResponse, status_code=201
    )
    def create_hunter_recommendation(
        request: HunterProfileRequest,
    ) -> HunterRecommendationResponse:
        if not resolved.settings.recommendation_api_enabled:
            raise HTTPException(status_code=404, detail="recommendation_api_disabled")
        try:
            translated = HunterProfileTranslator().translate(HunterProfile(
                answers=tuple(
                    HunterProfileAnswer(
                        answer.key, tuple(answer.values), answer.importance
                    )
                    for answer in request.answers
                ),
                candidate_breeds=tuple(request.candidate_breeds),
                schema_version=request.schema_version,
            ))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        result = resolved.recommendation_service.recommend(translated)
        return HunterRecommendationResponse(
            recommendation_id=str(result.recommendation_id),
            status=(
                "completed" if result.candidates
                else "incomplete" if translated.missing_fields else "abstained"
            ),
            policy_version=result.policy_version,
            snapshot_id=str(result.snapshot_id) if result.snapshot_id else None,
            candidates=[
                RecommendationCandidateResponse(
                    breed=item.breed,
                    band=str(item.band) if item.band else None,
                    compatibility=item.compatibility,
                    coverage=item.coverage,
                    penalties=list(item.penalties),
                    excluded=item.excluded,
                    dimensions=[
                        {
                            "key": dimension.key,
                            "compatibility": dimension.compatibility,
                            "documented": dimension.documented,
                            "conflicting": dimension.conflicting,
                            "evidence_ids": [
                                str(evidence_id) for evidence_id in dimension.evidence_ids
                            ],
                        }
                        for dimension in item.dimensions
                    ],
                )
                for item in result.candidates
            ],
            limitations=list(result.limitations),
            trace_id=result.trace_id,
            summary=result.summary,
        )

    @app.post("/api/v2/recommendations/{recommendation_id}/chat-context", status_code=201)
    def create_recommendation_context(
        recommendation_id: str, request: RecommendationContextRequest
    ) -> dict[str, object]:
        try:
            return resolved.recommendation_context_service.create(
                recommendation_id, request.selected_breeds
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error.args[0])) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/api/v2/recommendation-contexts/{context_id}/queries")
    def query_recommendation_context(
        context_id: str, request: RecommendationContextQueryRequest
    ) -> dict[str, object]:
        try:
            return resolved.recommendation_context_service.answer(context_id, request.text)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error.args[0])) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/v1/breeds", response_model=list[BreedListItem])
    def list_breeds() -> list[BreedListItem]:
        return [
            BreedListItem(name=item.name, group=item.group, fragment_count=item.fragment_count)
            for item in resolved.breed_registry.breeds()
        ]

    @app.get("/api/v1/breeds/{breed}/profile", response_model=BreedProfileResponse)
    def get_breed_profile(breed: str) -> BreedProfileResponse:
        try:
            profile = resolved.breed_profile_service.profile(breed)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="breed_not_found") from error
        return BreedProfileResponse(
            breed=profile.breed,
            sections=[BreedProfileSectionResponse(
                heading=item.heading, text=item.text,
                citation=AnalysisCitationResponse(
                    fragment_id=str(item.citation.evidence_id),
                    document_id=str(item.citation.source.document_id),
                    version_id=str(item.citation.source.version_id),
                    title=item.citation.source.title,
                    physical_page=item.citation.source.physical_page,
                    printed_page_label=item.citation.source.printed_page_label,
                ),
            ) for item in profile.sections],
            photo_url=(
                f"/api/v1/breeds/{quote(profile.breed)}/photo" if profile.photo_page else None
            ),
            photo_caption=profile.photo_caption, photo_page=profile.photo_page,
        )

    @app.get("/api/v2/breeds/{breed}/structured-profile")
    def get_structured_breed_profile(breed: str, snapshot_id: UUID) -> dict[str, object]:
        profile = resolved.structured_breed_profiles.profile(str(snapshot_id), breed)
        return {
            "breed": profile.breed,
            "snapshot_id": str(profile.snapshot_id),
            "policy_version": profile.policy_version,
            "attributes": [
                {
                    "key": attribute.key,
                    "evidence_state": attribute.evidence_state,
                    "assertions": [
                        {
                            "id": str(assertion.assertion_id),
                            "value": assertion.value,
                            "polarity": str(assertion.polarity),
                            "evidence": [
                                {
                                    "fragment_id": str(item.fragment_id),
                                    "title": item.source.title,
                                    "physical_page": item.source.physical_page,
                                }
                                for item in assertion.evidence
                            ],
                        }
                        for assertion in attribute.assertions
                    ],
                }
                for attribute in profile.attributes
            ],
        }

    @app.get("/api/v1/breeds/{breed}/photo", response_class=Response)
    def get_breed_photo(breed: str) -> Response:
        try:
            data = resolved.breed_profile_service.photo(breed)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="breed_not_found") from error
        if data is None:
            raise HTTPException(status_code=404, detail="photo_not_found")
        return Response(data, media_type="image/png", headers={"Cache-Control": "max-age=3600"})

    @app.get("/api/v1/breed-analyses/{analysis_id}", response_model=BreedAnalysisResponse)
    def get_breed_analysis(analysis_id: str) -> BreedAnalysisResponse:
        try:
            return breed_analysis_response(resolved.breed_analysis_service.get(analysis_id))
        except (KeyError, ValueError) as error:
            raise HTTPException(status_code=404, detail="analysis_not_found") from error

    @app.post(
        "/api/v1/breed-analyses/{analysis_id}/feedback",
        response_model=AnalysisFeedbackResponse, status_code=201,
    )
    def submit_analysis_feedback(
        analysis_id: str, request: AnalysisFeedbackRequest
    ) -> AnalysisFeedbackResponse:
        try:
            report = resolved.breed_analysis_service.get(analysis_id)
            feedback_id = resolved.breed_analysis_service.feedback(
                analysis_id, request.useful, request.comment
            )
        except (KeyError, ValueError) as error:
            raise HTTPException(status_code=404, detail="analysis_not_found") from error
        return AnalysisFeedbackResponse(
            id=feedback_id, analysis_id=analysis_id, trace_id=report.trace_id or "",
            useful=int(request.useful), comment=request.comment,
            created_at=datetime.now(UTC).isoformat(),
        )

    @app.get("/api/v1/documents", response_model=list[DocumentResponse])
    def list_documents() -> list[DocumentResponse]:
        return [DocumentResponse(**dict(row)) for row in resolved.document_service.list_documents()]

    @app.get(
        "/api/v1/jobs/{job_id}", response_model=JobResponse, dependencies=[Depends(require_admin)]
    )
    def get_job(job_id: str) -> JobResponse:
        job = resolved.document_service.job(job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job_not_found")
        return JobResponse(
            id=job["id"],
            version_id=job["version_id"],
            stage=job["stage"],
            attempt=job["attempt"],
            error_code=job["error_code"],
        )

    @app.get("/api/v1/documents/{document_id}/versions", response_model=list[VersionResponse])
    def list_versions(document_id: str) -> list[VersionResponse]:
        versions = resolved.document_service.versions(document_id)
        return [VersionResponse(**dict(row)) for row in versions]

    @app.get("/api/v1/conversations", response_model=list[ConversationSummary])
    def list_conversations() -> list[ConversationSummary]:
        return [
            ConversationSummary.model_validate(row)
            for row in resolved.interaction_service.conversations()
        ]

    @app.post("/api/v1/conversations", response_model=ConversationResponse, status_code=201)
    def create_conversation() -> ConversationResponse:
        return ConversationResponse.model_validate(
            resolved.interaction_service.create_conversation()
        )

    @app.get("/api/v1/conversations/{conversation_id}", response_model=ConversationResponse)
    def get_conversation(conversation_id: str) -> ConversationResponse:
        try:
            return ConversationResponse.model_validate(
                resolved.interaction_service.conversation(conversation_id)
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error.args[0])) from error

    @app.get("/api/v1/answers/{answer_id}")
    def get_answer(answer_id: str) -> dict[str, object]:
        try:
            return resolved.interaction_service.answer(answer_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error.args[0])) from error

    @app.get("/api/v1/citations/{citation_id}")
    def get_citation(citation_id: str) -> dict[str, object]:
        try:
            return resolved.interaction_service.citation(citation_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error.args[0])) from error

    @app.get("/api/v1/citations/{citation_id}/page")
    def get_citation_page(
        citation_id: str, physical_page: Annotated[int, Query(ge=1, le=5000)]
    ) -> dict[str, object]:
        try:
            return resolved.interaction_service.page(citation_id, physical_page)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error.args[0])) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post(
        "/api/v1/answers/{answer_id}/feedback",
        response_model=FeedbackResponse,
        status_code=201,
    )
    def submit_feedback(answer_id: str, request: FeedbackRequest) -> FeedbackResponse:
        try:
            return FeedbackResponse.model_validate(
                resolved.interaction_service.feedback(answer_id, request.useful, request.comment)
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error.args[0])) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post(
        "/api/v1/documents",
        response_model=UploadResponse,
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[Depends(require_admin)],
    )
    def upload_document(
        file: Annotated[UploadFile, File()],
        title: Annotated[str, Form(min_length=1, max_length=300)],
        author: Annotated[str | None, Form(max_length=200)] = None,
        category: Annotated[str | None, Form(max_length=100)] = None,
    ) -> UploadResponse:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="invalid_pdf_filename"
            )
        try:
            document_id, version_id, job_id = resolved.document_service.register(
                file.file, title, author, category, file.filename
            )
        except UploadValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
            ) from error
        except DuplicateDocumentError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=f"duplicate:{error}"
            ) from error
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
            ) from error
        finally:
            file.file.close()
        return UploadResponse(
            document_id=str(document_id), version_id=str(version_id), job_id=str(job_id)
        )

    @app.post(
        "/api/v1/documents/{document_id}/versions",
        response_model=UploadResponse,
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[Depends(require_admin)],
    )
    def replace_document(
        document_id: str,
        file: Annotated[UploadFile, File()],
    ) -> UploadResponse:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="invalid_pdf_filename"
            )
        try:
            version_id, job_id = resolved.document_service.replace(
                document_id, file.file, file.filename
            )
        except KeyError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        except UploadValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
            ) from error
        except DuplicateDocumentError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=f"duplicate:{error}"
            ) from error
        finally:
            file.file.close()
        return UploadResponse(
            document_id=document_id, version_id=str(version_id), job_id=str(job_id)
        )

    return app


app = create_app()
