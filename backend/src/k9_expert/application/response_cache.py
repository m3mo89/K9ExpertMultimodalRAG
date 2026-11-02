from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from k9_expert.application.query import QueryRequest
from k9_expert.domain.breed_vocabulary import ALLOWED_FUNCTIONS, normalize
from k9_expert.domain.models import (
    BreedAnalysisProfile,
    CacheHitType,
    Citation,
    DocumentId,
    DocumentVersionId,
    FragmentId,
    QueryStatus,
    SourceRef,
)
from k9_expert.ports.interfaces import ResponseCache

EmbedRequest = Callable[[str], Sequence[float]]


@dataclass(frozen=True, slots=True)
class CachedQuery:
    status: QueryStatus
    answer: str
    reason: str | None
    citations: tuple[Citation, ...]
    discrepancy: bool
    hit_type: CacheHitType
    similarity: float | None = None


class QueryResponseCache:
    def __init__(self, backend: ResponseCache, embed_request: EmbedRequest, *, identity: str,
                 exact_ttl_seconds: int = 3600, semantic_ttl_seconds: int = 1800,
                 semantic_threshold: float = 0.92) -> None:
        self.backend, self.embed_request, self.identity = backend, embed_request, identity
        self.exact_ttl, self.semantic_ttl = exact_ttl_seconds, semantic_ttl_seconds
        self.semantic_threshold = semantic_threshold

    def get(self, request: QueryRequest, snapshot_id: str) -> CachedQuery | None:
        canonical, partition = self._keys(request)
        vector = tuple(float(value) for value in self.embed_request(request.text))
        found = self.backend.lookup(
            hashlib.sha256(canonical.encode()).hexdigest(), partition=partition,
            snapshot_id=snapshot_id, request_vector=vector,
            semantic_threshold=self.semantic_threshold,
        )
        return None if found.value is None else _decode(
            found.value, found.hit_type, found.similarity
        )

    def store(self, request: QueryRequest, snapshot_id: str, value: CachedQuery) -> None:
        canonical, partition = self._keys(request)
        vector = tuple(float(item) for item in self.embed_request(request.text))
        current = datetime.now(UTC)
        exact_expires = current + timedelta(seconds=self.exact_ttl)
        semantic_expires = current + timedelta(seconds=self.semantic_ttl)
        self.backend.store(
            hashlib.sha256(canonical.encode()).hexdigest(), _encode(value),
            partition=partition, snapshot_id=snapshot_id,
            expires_at=exact_expires.isoformat(),
            semantic_expires_at=semantic_expires.isoformat(),
            request_vector=vector,
        )

    def _keys(self, request: QueryRequest) -> tuple[str, str]:
        filters = {
            "documents": sorted(str(item) for item in request.filters.document_ids),
            "categories": sorted(request.filters.categories),
            "breeds": sorted(request.filters.breeds),
            "sections": sorted(request.filters.sections),
        }
        partition = json.dumps({"identity": self.identity, "filters": filters}, sort_keys=True)
        canonical = json.dumps({"partition": partition,
                                "text": " ".join(request.text.lower().split())}, sort_keys=True)
        return canonical, partition


def _encode(value: CachedQuery) -> str:
    return json.dumps({"status": str(value.status), "answer": value.answer,
                       "reason": value.reason, "discrepancy": value.discrepancy,
                       "citations": [{"evidence_id": str(item.evidence_id),
                                      "document_id": str(item.source.document_id),
                                      "version_id": str(item.source.version_id),
                                      "title": item.source.title, "author": item.source.author,
                                      "edition": item.source.edition,
                                      "physical_page": item.source.physical_page,
                                      "printed_page_label": item.source.printed_page_label}
                                     for item in value.citations]})


def _decode(raw: str, hit_type: CacheHitType, similarity: float | None) -> CachedQuery:
    data = json.loads(raw)
    citations = tuple(Citation(FragmentId(UUID(item["evidence_id"])), SourceRef(
        DocumentId(UUID(item["document_id"])), DocumentVersionId(UUID(item["version_id"])),
        item["title"], item["author"], item["edition"], item["physical_page"],
        item["printed_page_label"],
    )) for item in data["citations"])
    return CachedQuery(QueryStatus(data["status"]), data["answer"], data["reason"], citations,
                       bool(data["discrepancy"]), hit_type, similarity)


@dataclass(frozen=True, slots=True)
class CachedAnalysis:
    analysis_id: str
    hit_type: CacheHitType
    similarity: float | None = None


class AnalysisResponseCache:
    """BreedMatch cache. Entries point at the persisted source report.

    The partition fixes criterion keys, weights, candidate scope and documents, so semantic
    lookup only compares criterion wording; a hit is also rejected when the controlled hunting
    functions named by any criterion differ.
    """

    def __init__(self, backend: ResponseCache, embed_request: EmbedRequest, *, identity: str,
                 exact_ttl_seconds: int = 3600, semantic_ttl_seconds: int = 1800,
                 semantic_threshold: float = 0.92) -> None:
        self.backend, self.embed_request, self.identity = backend, embed_request, identity
        self.exact_ttl, self.semantic_ttl = exact_ttl_seconds, semantic_ttl_seconds
        self.semantic_threshold = semantic_threshold

    def get(self, profile: BreedAnalysisProfile, snapshot_id: str) -> CachedAnalysis | None:
        exact_key, partition, text = self._keys(profile)
        found = self.backend.lookup(
            exact_key, partition=partition, snapshot_id=snapshot_id,
            request_vector=tuple(float(value) for value in self.embed_request(text)),
            semantic_threshold=self.semantic_threshold,
        )
        if found.value is None:
            return None
        data = json.loads(found.value)
        if data["functions"] != _functions(profile):
            return None
        return CachedAnalysis(data["analysis_id"], found.hit_type, found.similarity)

    def store(self, profile: BreedAnalysisProfile, snapshot_id: str, analysis_id: str) -> None:
        exact_key, partition, text = self._keys(profile)
        current = datetime.now(UTC)
        self.backend.store(
            exact_key,
            json.dumps({"analysis_id": analysis_id, "functions": _functions(profile)}),
            partition=partition, snapshot_id=snapshot_id,
            expires_at=(current + timedelta(seconds=self.exact_ttl)).isoformat(),
            semantic_expires_at=(current + timedelta(seconds=self.semantic_ttl)).isoformat(),
            request_vector=tuple(float(value) for value in self.embed_request(text)),
        )

    def _keys(self, profile: BreedAnalysisProfile) -> tuple[str, str, str]:
        return analysis_keys(profile, self.identity)


def analysis_keys(profile: BreedAnalysisProfile, identity: str) -> tuple[str, str, str]:
    """Exact key, semantic partition and embedded text of a BreedMatch profile."""
    partition = json.dumps({
        "operation": "breed_match", "identity": identity,
        "policy": profile.policy_version,
        "criteria": [[item.key, item.weight] for item in profile.criteria],
        "candidates": sorted(normalize(item) for item in profile.candidate_breeds),
        "documents": sorted(str(item) for item in profile.document_ids),
    }, sort_keys=True)
    text = "; ".join(f"{item.key}: {item.value}" for item in profile.criteria)
    canonical = json.dumps({"partition": partition, "values": [
        normalize(item.value) for item in profile.criteria
    ]}, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest(), partition, text


def _functions(profile: BreedAnalysisProfile) -> list[list[str]]:
    return [
        sorted(term for term in ALLOWED_FUNCTIONS if term in normalize(item.value).split())
        for item in profile.criteria
    ]
