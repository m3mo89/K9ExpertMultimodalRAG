from __future__ import annotations

from collections.abc import Callable
from typing import Annotated
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
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from k9_expert.application.composition import ApplicationContainer, compose
from k9_expert.application.documents import (
    DuplicateDocumentError,
    UploadValidationError,
)
from k9_expert.application.query_service import SubmitQuery
from k9_expert.domain.models import DocumentId, QueryFilters


class HealthResponse(BaseModel):
    status: str
    worker_concurrency: int


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

    @app.get("/api/v1/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", worker_concurrency=resolved.settings.worker_concurrency)

    @app.post(
        "/api/v1/admin/confirmations",
        response_model=ConfirmationResponse,
        dependencies=[Depends(require_admin)],
    )
    def create_confirmation(
        request: ConfirmationRequest,
        x_k9_actor: Annotated[
            str, Header(min_length=1, max_length=100)
        ] = "local-admin",
    ) -> ConfirmationResponse:
        token, expires_at = resolved.admin_security.issue_confirmation(
            x_k9_actor, request.resource_id, request.operation, request.resource_version
        )
        return ConfirmationResponse(token=token, expires_at=expires_at)

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

    @app.delete(
        "/api/v1/documents/{document_id}",
        response_model=PublicationResponse,
        dependencies=[Depends(require_admin)],
    )
    def delete_document(
        document_id: str,
        request: DeleteDocumentRequest,
        x_k9_actor: Annotated[
            str, Header(min_length=1, max_length=100)
        ] = "local-admin",
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
        return PublicationResponse(
            document_id=document_id, snapshot_id=snapshot_id, status="deleted"
        )

    @app.post("/api/v1/queries", response_model=QueryResponse)
    def submit_query(request: QueryRequestBody) -> QueryResponse:
        filters = QueryFilters(
            document_ids=tuple(DocumentId(item) for item in request.filters.document_ids),
            categories=tuple(request.filters.categories),
            breeds=tuple(request.filters.breeds),
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
        return QueryResponse(
            query_id=str(result.query_id),
            answer_id=stored.answer_id,
            status=str(result.status),
            answer=result.answer,
            snapshot_id=str(result.snapshot_id) if result.snapshot_id else None,
            reason=result.reason,
            citations=[
                {
                    "fragment_id": str(citation.evidence_id),
                    "document_id": str(citation.source.document_id),
                    "version_id": str(citation.source.version_id),
                    "title": citation.source.title,
                    "author": citation.source.author,
                    "edition": citation.source.edition,
                    "physical_page": citation.source.physical_page,
                    "printed_page_label": citation.source.printed_page_label,
                }
                for citation in result.citations
            ],
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
