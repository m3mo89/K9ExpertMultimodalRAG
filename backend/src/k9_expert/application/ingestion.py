from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from k9_expert.domain.models import JobStage
from k9_expert.infrastructure.extraction import OcrPolicy, PdfExtractor
from k9_expert.infrastructure.sqlite import ContentRepository, JobRepository
from k9_expert.infrastructure.structuring import HeadingDetector, PageAwareChunker


class IngestionWorker:
    """Single-concurrency durable worker for the extraction-to-fragment checkpoint."""

    def __init__(
        self,
        jobs: JobRepository,
        content: ContentRepository,
        extractor: PdfExtractor | None = None,
        ocr_policy: OcrPolicy | None = None,
    ) -> None:
        self.jobs = jobs
        self.content = content
        self.extractor = extractor or PdfExtractor()
        self.ocr_policy = ocr_policy or OcrPolicy()

    def run_once(self) -> bool:
        lease = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
        job = self.jobs.claim_next(lease)
        if job is None:
            return False
        job_id = str(job["id"])
        try:
            context = self.jobs.context(job_id)
            if context is None:
                raise RuntimeError("missing_job_context")
            version_id = str(context["version_id"])
            self.jobs.update_stage(job_id, JobStage.EXTRACTING, "extracting")
            pages = self.extractor.extract_path(context["file_path"])
            self.jobs.update_stage(job_id, JobStage.CHUNKING, "persisting")
            self.content.clear_version_content(version_id)
            for page in pages:
                method = "ocr_requested" if self.ocr_policy.decide(page).required else "direct"
                self.content.add_page(
                    uuid4(), UUID(version_id), page.physical_page, page.text, method
                )
            blocks = HeadingDetector().structure(pages)
            chunks = PageAwareChunker().chunk(blocks)
            for chunk in chunks:
                self.content.add_fragment(
                    uuid4(),
                    UUID(version_id),
                    chunk.content_hash,
                    chunk.ordinal,
                    chunk.text,
                    min(chunk.covered_pages),
                    max(chunk.covered_pages),
                    "direct",
                    chunk.chunking_version,
                    "/".join(chunk.section_path),
                )
            self.jobs.update_stage(job_id, JobStage.AVAILABLE, "fragments_persisted")
        except Exception as error:
            self.jobs.fail(job_id, "ingestion_failed", str(error))
        return True
