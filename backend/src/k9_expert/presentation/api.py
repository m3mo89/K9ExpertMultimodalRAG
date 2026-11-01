from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile, status
from pydantic import BaseModel

from k9_expert.application.composition import ApplicationContainer, compose
from k9_expert.application.documents import (
    DuplicateDocumentError,
    UploadValidationError,
)


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


def admin_guard(container: ApplicationContainer) -> Callable[..., None]:
    def require_admin(x_k9_admin_secret: Annotated[str | None, Header()] = None) -> None:
        secret = container.settings.admin_secret
        if not secret or x_k9_admin_secret != secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="admin_unauthorized"
            )

    return require_admin


def create_app(container: ApplicationContainer | None = None) -> FastAPI:
    resolved = container or compose()
    app = FastAPI(title="K9 Expert", version="0.1.0")
    require_admin = admin_guard(resolved)

    @app.get("/api/v1/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", worker_concurrency=resolved.settings.worker_concurrency)

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
