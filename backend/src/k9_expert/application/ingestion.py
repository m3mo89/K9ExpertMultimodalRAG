from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from k9_expert.application.indexing import EmbedFragments
from k9_expert.application.observability import TraceRecorder
from k9_expert.domain.errors import DomainError, OcrUnavailableError
from k9_expert.domain.models import JobStage
from k9_expert.infrastructure.extraction import (
    ExtractedPage,
    OcrPolicy,
    OcrResult,
    PdfExtractor,
    TextBlock,
)
from k9_expert.infrastructure.sqlite import ContentRepository, JobRepository, PrepareIndex
from k9_expert.infrastructure.structuring import (
    CHUNKING_VERSION,
    HeadingDetector,
    PageAwareChunker,
)
from k9_expert.ports.interfaces import TraceSink

RunOcr = Callable[[Path, int], OcrResult]
# (snapshot_id, version_id, fragment_ids, prepare_index) -> (previous_id, published_id)
PublishVersion = Callable[[UUID, str, list[str], PrepareIndex], tuple[str | None, str]]


class IngestionWorker:
    """Single-concurrency durable worker: extraction, OCR, chunking, embedding, publication.

    Every stage is idempotent, so a retried job restarts safely; publication is the only
    step that changes what queries see, and it is atomic.
    """

    def __init__(
        self,
        jobs: JobRepository,
        content: ContentRepository,
        extractor: PdfExtractor | None = None,
        ocr_policy: OcrPolicy | None = None,
        sink: TraceSink | None = None,
        embedding_config: Mapping[str, object] | None = None,
        ocr: RunOcr | None = None,
        embed_fragments: EmbedFragments | None = None,
        publish: PublishVersion | None = None,
        prepare_index: PrepareIndex | None = None,
        on_published: Callable[[str], None] | None = None,
        embedding_counter: Callable[[], tuple[int, int]] | None = None,
        index_stats: Callable[[], Mapping[str, int]] | None = None,
    ) -> None:
        self.jobs = jobs
        self.content = content
        self.extractor = extractor or PdfExtractor()
        self.ocr_policy = ocr_policy or OcrPolicy()
        self.sink = sink
        self.embedding_config = dict(embedding_config or {})
        self.ocr = ocr
        self.embed_fragments = embed_fragments
        self.publish = publish
        self.prepare_index = prepare_index
        self.on_published = on_published
        # (cache hits, model computations) so traces prove incremental embedding.
        self.embedding_counter = embedding_counter
        self.index_stats = index_stats

    def run_once(self) -> bool:
        lease = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
        job = self.jobs.claim_next(lease)
        if job is None:
            return False
        job_id = str(job["id"])
        trace = TraceRecorder("ingestion")
        trace.set(
            job_id=job_id,
            version_id=str(job["version_id"]),
            attempt=int(job["attempt"]),
            extractor_version=self.extractor.version,
            chunking_version=CHUNKING_VERSION,
            embedding=self.embedding_config,
            publication={"result": "not_attempted"},
        )
        version_id = str(job["version_id"])
        try:
            context = self.jobs.context(job_id)
            if context is None:
                raise RuntimeError("missing_job_context")
            source = Path(context["file_path"])
            self.jobs.update_stage(job_id, JobStage.EXTRACTING, "extracting")
            with trace.stage("extracting"):
                pages = self.extractor.extract_path(str(source))
            self.jobs.update_stage(job_id, JobStage.OCR, "ocr")
            with trace.stage("ocr"):
                pages, methods = self._apply_ocr(source, pages)
            trace.set(
                page_count=len(pages),
                ocr_page_count=sum(method != "direct" for method in methods.values()),
                ocr_outcomes={
                    outcome: list(methods.values()).count(outcome)
                    for outcome in sorted(set(methods.values()))
                },
            )
            self.jobs.update_stage(job_id, JobStage.CHUNKING, "persisting")
            with trace.stage("persisting_pages"):
                self.content.clear_version_content(version_id)
                for page in pages:
                    self.content.add_page(
                        uuid4(),
                        UUID(version_id),
                        page.physical_page,
                        page.text,
                        methods[page.physical_page],
                    )
            with trace.stage("chunking"):
                blocks = HeadingDetector().structure(pages)
                chunks = PageAwareChunker().chunk(blocks)
            with trace.stage("persisting_fragments"):
                for chunk in chunks:
                    used_ocr = any(methods[page] == "ocr" for page in chunk.covered_pages)
                    self.content.add_fragment(
                        uuid4(),
                        UUID(version_id),
                        chunk.content_hash,
                        chunk.ordinal,
                        chunk.text,
                        min(chunk.covered_pages),
                        max(chunk.covered_pages),
                        "ocr" if used_ocr else "direct",
                        chunk.chunking_version,
                        "/".join(chunk.section_path),
                        chunk.classification,
                    )
            trace.set(
                fragment_count=len(chunks),
                classified_fragments=sum(
                    1 for chunk in chunks if chunk.classification.provenance
                ),
                classification_policy=(
                    chunks[0].classification.policy_version if chunks else None
                ),
            )
            if self.publish is None or self.prepare_index is None:
                self.jobs.update_stage(job_id, JobStage.AVAILABLE, "fragments_persisted")
                trace.finish(self.sink, "completed")
                return True
            texts = {chunk.content_hash: chunk.text for chunk in chunks}
            hashes = list(texts)
            fragment_ids = self.content.fragment_ids_by_hash(version_id, hashes)
            counted = self.embedding_counter() if self.embedding_counter else (0, 0)
            self.jobs.update_stage(job_id, JobStage.EMBEDDING, "embedding")
            with trace.stage("embedding"):
                # Fills the content-addressed cache before publication takes the write lock.
                if self.embed_fragments is not None:
                    self.embed_fragments(list(texts.items()))
            self.jobs.update_stage(job_id, JobStage.PUBLISHING, "publishing")
            with trace.stage("publishing"):
                previous, published = self.publish(
                    uuid4(), version_id, [fragment_ids[h] for h in hashes], self.prepare_index
                )
            trace.set(
                publication={"result": "published", "snapshot_id": published, "previous": previous}
            )
            if self.embedding_counter is not None:
                hits, misses = self.embedding_counter()
                trace.set(
                    embeddings_computed=misses - counted[1],
                    embedding_cache_hits=hits - counted[0],
                )
            if self.index_stats is not None:
                trace.set(index=dict(self.index_stats()))
            if self.on_published is not None and previous is not None:
                self.on_published(previous)
            self.jobs.update_stage(job_id, JobStage.AVAILABLE, "published")
            trace.finish(self.sink, "completed")
        except Exception as error:
            code = error.code if isinstance(error, DomainError) else "ingestion_failed"
            self.jobs.fail(job_id, code, str(error))
            self.content.mark_candidate_version_failed(version_id)
            trace.set(publication={"result": "not_published"})
            trace.fail(error)
            trace.finish(self.sink, "failed", code)
        return True

    def _apply_ocr(
        self, source: Path, pages: Sequence[ExtractedPage]
    ) -> tuple[list[ExtractedPage], dict[int, str]]:
        """Selective OCR; without an engine the direct text is kept and the gap recorded."""
        result: list[ExtractedPage] = []
        methods: dict[int, str] = {}
        for page in pages:
            if not self.ocr_policy.decide(page).required:
                methods[page.physical_page] = "direct"
                result.append(page)
                continue
            if self.ocr is None:
                methods[page.physical_page] = "ocr_unavailable"
                result.append(page)
                continue
            try:
                ocr = self.ocr(source, page.physical_page)
            except OcrUnavailableError:
                methods[page.physical_page] = "ocr_unavailable"
                result.append(page)
                continue
            except DomainError:
                methods[page.physical_page] = "ocr_failed"
                result.append(page)
                continue
            methods[page.physical_page] = "ocr"
            block = TextBlock(ocr.text, 0, 0, page.width, page.height)
            result.append(replace(page, text=ocr.text, blocks=(block,), extraction_method="ocr"))
        return result, methods
