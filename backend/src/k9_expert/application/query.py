from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from k9_expert.application.generation import (
    GeneratedAnswer,
    PromptBuilder,
    safety_frame,
    verify_answer,
)
from k9_expert.domain.models import (
    Citation,
    Evidence,
    QueryFilters,
    QueryId,
    QueryResult,
    QueryStatus,
    SnapshotId,
)


@dataclass(frozen=True, slots=True)
class QueryRequest:
    text: str
    filters: QueryFilters = QueryFilters()


@dataclass(frozen=True, slots=True)
class InputPolicyResult:
    status: QueryStatus | None
    reason: str | None


class QueryInputPolicy:
    def __init__(self, max_characters: int = 2000) -> None:
        self.max_characters = max_characters

    def evaluate(self, request: QueryRequest, snapshot_id: str | None) -> InputPolicyResult:
        if not request.text.strip() or len(request.text) > self.max_characters:
            return InputPolicyResult(QueryStatus.REJECTED, "invalid_query")
        if snapshot_id is None:
            return InputPolicyResult(QueryStatus.UNAVAILABLE, "no_active_snapshot")
        return InputPolicyResult(None, None)


class DomainRouter:
    alias = "text-default"

    def route(self, text: str) -> InputPolicyResult:
        terms = {"perro", "raza", "caza", "teckel", "beagle", "adiestramiento", "alimentación"}
        if not any(term in text.lower() for term in terms):
            return InputPolicyResult(QueryStatus.ABSTAINED, "out_of_domain")
        return InputPolicyResult(None, None)


class SemanticRetriever:
    def __init__(
        self, top_k: int = 8, minimum_score: float = 0.0, context_tokens: int = 6000
    ) -> None:
        self.top_k = top_k
        self.minimum_score = minimum_score
        self.context_tokens = context_tokens

    def select(self, candidates: list[Evidence], filters: QueryFilters) -> list[Evidence]:
        allowed_documents = {str(identifier) for identifier in filters.document_ids}
        selected: list[Evidence] = []
        used_sections: set[tuple[str, ...]] = set()
        budget = 0
        for item in sorted(candidates, key=lambda candidate: candidate.score, reverse=True):
            if item.score < self.minimum_score:
                continue
            if allowed_documents and str(item.source.document_id) not in allowed_documents:
                continue
            tokens = len(item.text.split())
            if budget + tokens > self.context_tokens or item.section_path in used_sections:
                continue
            selected.append(item)
            used_sections.add(item.section_path)
            budget += tokens
            if len(selected) == self.top_k:
                break
        return selected


class EvidenceSufficiencyPolicy:
    def __init__(self, minimum_score: float = 0.4) -> None:
        self.minimum_score = minimum_score

    def evaluate(self, evidence: list[Evidence]) -> InputPolicyResult:
        if not evidence:
            return InputPolicyResult(QueryStatus.ABSTAINED, "no_evidence")
        if max(item.score for item in evidence) < self.minimum_score:
            return InputPolicyResult(QueryStatus.ABSTAINED, "weak_evidence")
        return InputPolicyResult(None, None)


class QueryOrchestrator:
    def __init__(self, generate, retrieve) -> None:  # type: ignore[no-untyped-def]
        self.generate = generate
        self.retrieve = retrieve
        self.cache: dict[tuple[str, str], QueryResult] = {}
        self.traces: list[str] = []

    def run(self, request: QueryRequest, snapshot_id: str | None) -> QueryResult:
        query_id = QueryId(uuid4())
        policy = QueryInputPolicy().evaluate(request, snapshot_id)
        if policy.status is not None:
            return self._result(query_id, policy.status, snapshot_id, policy.reason)
        assert snapshot_id is not None
        key = (snapshot_id, request.text)
        if key in self.cache:
            return self.cache[key]
        route = DomainRouter().route(request.text)
        if route.status is not None:
            return self._result(query_id, route.status, snapshot_id, route.reason)
        evidence = self.retrieve(request)
        sufficient = EvidenceSufficiencyPolicy().evaluate(evidence)
        if sufficient.status is not None:
            return self._result(query_id, sufficient.status, snapshot_id, sufficient.reason)
        system, prompt = PromptBuilder().build(request.text, evidence)
        draft: GeneratedAnswer = self.generate(system, prompt)
        status = verify_answer(draft, evidence, {str(item.fragment_id) for item in evidence})
        cited_ids = set(draft.evidence_ids) if status == QueryStatus.GROUNDED else set()
        citations = tuple(
            Citation(item.fragment_id, item.source)
            for item in evidence
            if str(item.fragment_id) in cited_ids
        )
        result = QueryResult(
            query_id,
            status,
            safety_frame(request.text, draft.answer),
            SnapshotId(UUID(snapshot_id)),
            citations=citations,
            reason=None,
        )
        self.traces.append(status)
        if status == QueryStatus.GROUNDED:
            self.cache[key] = result
        return result

    @staticmethod
    def _result(
        query_id: QueryId, status: QueryStatus, snapshot_id: str | None, reason: str | None
    ) -> QueryResult:
        bound_snapshot = SnapshotId(UUID(snapshot_id)) if snapshot_id is not None else None
        return QueryResult(query_id, status, "", bound_snapshot, reason=reason)
