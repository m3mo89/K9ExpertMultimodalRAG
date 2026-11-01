from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import UUID, uuid4

import fitz  # type: ignore[import-untyped]

from k9_expert.infrastructure.filesystem import ManagedFileStore, StagedFile
from k9_expert.infrastructure.sqlite import DocumentRepository, JobRepository


class UploadValidationError(ValueError):
    pass


class DuplicateDocumentError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ValidatedPdf:
    staged: StagedFile
    page_count: int


class PdfValidator:
    def __init__(self, max_pages: int) -> None:
        self.max_pages = max_pages

    def validate(self, staged: StagedFile) -> ValidatedPdf:
        with staged.path.open("rb") as handle:
            if handle.read(5) != b"%PDF-":
                raise UploadValidationError("invalid_pdf_signature")
        try:
            document = fitz.open(staged.path)
        except fitz.FileDataError as error:
            raise UploadValidationError("invalid_pdf_integrity") from error
        try:
            if document.is_encrypted:
                raise UploadValidationError("encrypted_pdf")
            if document.page_count < 1 or document.page_count > self.max_pages:
                raise UploadValidationError("invalid_pdf_page_count")
            return ValidatedPdf(staged=staged, page_count=document.page_count)
        finally:
            document.close()


class DocumentRegistrationService:
    def __init__(
        self,
        file_store: ManagedFileStore,
        documents: DocumentRepository,
        jobs: JobRepository,
        validator: PdfValidator,
        max_file_bytes: int,
    ) -> None:
        self.file_store = file_store
        self.documents = documents
        self.jobs = jobs
        self.validator = validator
        self.max_file_bytes = max_file_bytes

    def register(
        self,
        stream: BinaryIO,
        title: str,
        author: str | None,
        category: str | None,
        filename: str,
    ) -> tuple[UUID, UUID, UUID]:
        staged = self.file_store.stage(stream, max_bytes=self.max_file_bytes)
        try:
            validated = self.validator.validate(staged)
            existing = self.documents.find_version_by_content_hash(validated.staged.content_hash)
            if existing is not None:
                raise DuplicateDocumentError(existing)
            document_id, version_id, job_id = uuid4(), uuid4(), uuid4()
            destination = self.file_store.promote(validated.staged)
            self.documents.create_document_version_and_job(
                document_id,
                version_id,
                job_id,
                title,
                author,
                category,
                validated.staged.content_hash,
                Path(filename).name,
                str(destination),
            )
            return document_id, version_id, job_id
        except BaseException:
            if staged.path.exists():
                self.file_store.discard(staged)
            raise

    def replace(self, document_id: str, stream: BinaryIO, filename: str) -> tuple[UUID, UUID]:
        staged = self.file_store.stage(stream, max_bytes=self.max_file_bytes)
        try:
            validated = self.validator.validate(staged)
            existing = self.documents.find_version_by_content_hash(validated.staged.content_hash)
            if existing is not None:
                raise DuplicateDocumentError(existing)
            version_id, job_id = uuid4(), uuid4()
            destination = self.file_store.promote(validated.staged)
            self.documents.create_version_and_job(
                version_id,
                job_id,
                document_id,
                validated.staged.content_hash,
                Path(filename).name,
                str(destination),
            )
            return version_id, job_id
        except BaseException:
            if staged.path.exists():
                self.file_store.discard(staged)
            raise

    def list_documents(self) -> list[sqlite3.Row]:
        return self.documents.list_documents()

    def job(self, job_id: str) -> sqlite3.Row | None:
        return self.documents.job(job_id)

    def versions(self, document_id: str) -> list[sqlite3.Row]:
        return self.documents.versions(document_id)
