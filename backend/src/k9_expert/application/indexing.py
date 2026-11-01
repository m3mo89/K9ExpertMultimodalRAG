"""Snapshot vector generations: incremental build before activation, and bound retrieval."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Sequence
from pathlib import Path
from uuid import UUID

from k9_expert.application.query import QueryRequest, SemanticRetriever
from k9_expert.domain.models import (
    DocumentId,
    DocumentVersionId,
    Evidence,
    FragmentId,
    QueryFilters,
    SourceRef,
)
from k9_expert.infrastructure.sqlite import SnapshotRepository
from k9_expert.infrastructure.vector_index import (
    ChromaGenerationIndex,
    VectorRecord,
    validate_generation,
)

# (content_hash, text) pairs -> document vectors; implementations should cache by hash.
EmbedFragments = Callable[[Sequence[tuple[str, str]]], Sequence[Sequence[float]]]
EmbedQuery = Callable[[str], Sequence[float]]


class SnapshotIndexBuilder:
    """Builds a candidate snapshot's generation, reusing vectors of unchanged fragments.

    Used as the `prepare_index` hook of snapshot publication, so a failure here rolls the
    SQLite publication back and leaves the previous snapshot and its generation active.
    """

    def __init__(
        self, index_root: Path, embed_fragments: EmbedFragments, dimensions: int
    ) -> None:
        self.index_root = index_root
        self.embed_fragments = embed_fragments
        self.dimensions = dimensions
        self.last_embedded = 0
        self.last_reused = 0

    def __call__(
        self, snapshot_id: str, previous_id: str | None, rows: list[sqlite3.Row]
    ) -> None:
        reusable: dict[str, tuple[float, ...]] = {}
        if previous_id is not None:
            reusable = {
                record.fragment_id: record.vector
                for record in ChromaGenerationIndex(self.index_root, previous_id).records()
            }
        missing = [row for row in rows if str(row["id"]) not in reusable]
        fresh = self.embed_fragments(
            [(str(row["content_hash"]), str(row["text"])) for row in missing]
        )
        for row, vector in zip(missing, fresh, strict=True):
            reusable[str(row["id"])] = tuple(float(value) for value in vector)
        index = ChromaGenerationIndex(self.index_root, snapshot_id)
        try:
            index.reset()
            index.add([_record(snapshot_id, row, reusable[str(row["id"])]) for row in rows])
            validate_generation(index, len(rows), self.dimensions)
        except BaseException:
            index.drop()
            raise
        self.last_embedded, self.last_reused = len(missing), len(rows) - len(missing)


class SnapshotRetriever:
    """Semantic retrieval within the query's bound snapshot and strict metadata filters."""

    def __init__(
        self,
        index_root: Path,
        snapshots: SnapshotRepository,
        embed_query: EmbedQuery,
        selector: SemanticRetriever,
        candidates: int = 24,
    ) -> None:
        self.index_root = index_root
        self.snapshots = snapshots
        self.embed_query = embed_query
        self.selector = selector
        self.candidates = candidates

    def __call__(self, request: QueryRequest) -> list[Evidence]:
        if request.snapshot_id is None:
            return []
        index = ChromaGenerationIndex(self.index_root, request.snapshot_id)
        hits = index.search(
            self.embed_query(request.text), self.candidates, metadata_filter(request.filters)
        )
        scores = dict(hits)
        rows = self.snapshots.evidence_rows(request.snapshot_id, list(scores))
        evidence = [_evidence(row, scores[str(row["id"])]) for row in rows]
        return self.selector.select(evidence, request.filters)


def metadata_filter(filters: QueryFilters) -> dict[str, object] | None:
    """Strict Chroma `where` clause; an empty filter list means no restriction."""
    clauses: list[dict[str, object]] = []
    for field, values in (
        ("document_id", [str(item) for item in filters.document_ids]),
        ("category", list(filters.categories)),
        ("breed", list(filters.breeds)),
        ("section", list(filters.sections)),
    ):
        if values:
            clauses.append({field: {"$in": values}})
    if not clauses:
        return None
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def _record(snapshot_id: str, row: sqlite3.Row, vector: tuple[float, ...]) -> VectorRecord:
    return VectorRecord(
        fragment_id=str(row["id"]),
        text=str(row["text"]),
        vector=vector,
        snapshot_id=snapshot_id,
        document_id=str(row["document_id"]),
        version_id=str(row["version_id"]),
        physical_page=int(row["page_start"]),
        category=row["category"],
        section=row["section_path"] or None,
    )


def _evidence(row: sqlite3.Row, score: float) -> Evidence:
    return Evidence(
        fragment_id=FragmentId(UUID(str(row["id"]))),
        source=SourceRef(
            DocumentId(UUID(str(row["document_id"]))),
            DocumentVersionId(UUID(str(row["version_id"]))),
            str(row["title"]),
            row["author"],
            row["edition"],
            int(row["page_start"]),
            row["printed_page_label"],
        ),
        text=str(row["text"]),
        score=score,
        section_path=tuple(part for part in str(row["section_path"]).split("/") if part),
    )
