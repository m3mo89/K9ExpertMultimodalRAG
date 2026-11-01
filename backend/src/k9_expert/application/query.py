from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from k9_expert.application.generation import (
    PROMPT_VERSION,
    GeneratedAnswer,
    PromptBuilder,
    safety_frame,
    verify_answer,
)
from k9_expert.application.observability import TraceRecorder
from k9_expert.domain.errors import DomainError
from k9_expert.domain.models import (
    Citation,
    Evidence,
    QueryFilters,
    QueryId,
    QueryResult,
    QueryStatus,
    SnapshotId,
)
from k9_expert.ports.interfaces import TraceSink


@dataclass(frozen=True, slots=True)
class QueryRequest:
    text: str
    filters: QueryFilters = QueryFilters()
    # Bound by the orchestrator so retrieval never reads a newer active snapshot.
    snapshot_id: str | None = None


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
    """Lexical routing signal; it never blocks, because breed names are open-ended.

    `uncertain` questions still reach retrieval, and the sufficiency policy reports them as
    `out_of_domain` when the library offers no strong evidence.
    """

    alias = "text-default"
    terms = (
        "perr", "can", "raza", "cachorr", "caza", "cazador", "sabueso", "lebrel", "terrier",
        "teckel", "beagle", "basset", "setter", "pointer", "braco", "spaniel", "retriever",
        "spitz", "elghund", "veterinari", "adiestramiento", "alimentación", "manto", "pelaje",
        "hocico", "jauría", "rastro", "muestra", "cobro",
    )

    def route(self, text: str) -> str:
        lowered = text.lower()
        return "in_domain" if any(term in lowered for term in self.terms) else "uncertain"


class SemanticRetriever:
    def __init__(
        self,
        top_k: int = 8,
        minimum_score: float = 0.0,
        context_tokens: int = 6000,
        max_per_section: int = 1,
    ) -> None:
        self.top_k = top_k
        self.minimum_score = minimum_score
        self.context_tokens = context_tokens
        self.max_per_section = max_per_section

    def select(self, candidates: list[Evidence], filters: QueryFilters) -> list[Evidence]:
        allowed_documents = {str(identifier) for identifier in filters.document_ids}
        selected: list[Evidence] = []
        per_section: dict[tuple[str, ...], int] = {}
        budget = 0
        for item in sorted(candidates, key=lambda candidate: candidate.score, reverse=True):
            if item.score < self.minimum_score:
                continue
            if allowed_documents and str(item.source.document_id) not in allowed_documents:
                continue
            tokens = len(item.text.split())
            used = per_section.get(item.section_path, 0)
            if budget + tokens > self.context_tokens or used >= self.max_per_section:
                continue
            selected.append(item)
            per_section[item.section_path] = used + 1
            budget += tokens
            if len(selected) == self.top_k:
                break
        return selected


class EvidenceSufficiencyPolicy:
    """Top-score gate. The default is calibrated for nomic-embed-text on the reference
    corpus (docs/evaluation/baseline-2026-11-01.md) and is provisional: supported questions
    scored >= 0.693 and off-domain ones <= 0.679.
    """

    def __init__(self, minimum_score: float = 0.68) -> None:
        self.minimum_score = minimum_score

    def evaluate(self, evidence: list[Evidence], route: str = "in_domain") -> InputPolicyResult:
        if not evidence:
            return InputPolicyResult(QueryStatus.ABSTAINED, "no_evidence")
        if max(item.score for item in evidence) < self.minimum_score:
            reason = "out_of_domain" if route == "uncertain" else "weak_evidence"
            return InputPolicyResult(QueryStatus.ABSTAINED, reason)
        return InputPolicyResult(None, None)


class QueryOrchestrator:
    """Ordered barriers: input policy, exact cache, router, retrieval, generation, verification.

    Every run emits one trace (the sink redacts it); model failures become typed results.
    """

    def __init__(  # type: ignore[no-untyped-def]
        self,
        generate,
        retrieve,
        *,
        sink: TraceSink | None = None,
        text_alias: str = "text-default",
        resolved_model: Callable[[], str | None] = lambda: None,
        retrieval_config: Mapping[str, object] | None = None,
        sufficiency: EvidenceSufficiencyPolicy | None = None,
    ) -> None:
        self.generate = generate
        self.sufficiency = sufficiency or EvidenceSufficiencyPolicy()
        self.retrieve = retrieve
        self.sink = sink
        self.text_alias = text_alias
        self.resolved_model = resolved_model
        self.retrieval_config = dict(retrieval_config or {})
        self.cache: dict[tuple[str, str, QueryFilters], QueryResult] = {}

    def run(self, request: QueryRequest, snapshot_id: str | None) -> QueryResult:
        query_id = QueryId(uuid4())
        trace = TraceRecorder("query")
        trace.set(
            query_id=str(query_id),
            snapshot_id=snapshot_id,
            prompt_version=PROMPT_VERSION,
            text_alias=self.text_alias,
            router_alias=DomainRouter.alias,
            retrieval={**self.retrieval_config, "sufficiency_min": self.sufficiency.minimum_score},
            filters=_filters_attribute(request.filters),
            question=request.text,
            question_characters=len(request.text),
            cache_hit=False,
            generation_called=False,
        )
        status, answer, reason = QueryStatus.UNAVAILABLE, "", None
        citations: tuple[Citation, ...] = ()
        discrepancy = False
        try:
            status, answer, reason, citations, discrepancy = self._run(
                request, snapshot_id, trace
            )
        except DomainError as error:
            trace.fail(error)
            # Unverifiable model output is a quality outcome; anything else is availability.
            invalid_output = error.code == "model_output_invalid"
            status = QueryStatus.UNVERIFIED if invalid_output else QueryStatus.UNAVAILABLE
            reason = error.code
        bound = SnapshotId(UUID(snapshot_id)) if snapshot_id is not None else None
        result = QueryResult(
            query_id,
            status,
            answer,
            bound,
            citations,
            trace_id=trace.trace_id,
            reason=reason,
            discrepancy=discrepancy,
        )
        trace.finish(self.sink, str(status), reason)
        return result

    def _run(
        self, request: QueryRequest, snapshot_id: str | None, trace: TraceRecorder
    ) -> tuple[QueryStatus, str, str | None, tuple[Citation, ...], bool]:
        with trace.stage("input_policy"):
            policy = QueryInputPolicy().evaluate(request, snapshot_id)
        if policy.status is not None:
            return policy.status, "", policy.reason, (), False
        assert snapshot_id is not None
        key = (snapshot_id, request.text, request.filters)
        with trace.stage("cache"):
            cached = self.cache.get(key)
        if cached is not None:
            trace.set(cache_hit=True)
            return cached.status, cached.answer, cached.reason, cached.citations, cached.discrepancy
        with trace.stage("route"):
            route = DomainRouter().route(request.text)
        trace.set(route=route)
        with trace.stage("retrieval"):
            evidence = self.retrieve(replace(request, snapshot_id=snapshot_id))
        trace.set(
            evidence=[
                {"fragment_id": str(item.fragment_id), "score": round(item.score, 6)}
                for item in evidence
            ]
        )
        with trace.stage("sufficiency"):
            sufficient = self.sufficiency.evaluate(evidence, route)
        if sufficient.status is not None:
            return sufficient.status, "", sufficient.reason, (), False
        system, prompt = PromptBuilder().build(request.text, evidence)
        trace.set(generation_called=True)
        with trace.stage("generation"):
            draft: GeneratedAnswer = self.generate(system, prompt)
        trace.set(resolved_model=self.resolved_model())
        with trace.stage("verification"):
            status = verify_answer(draft, evidence, {str(item.fragment_id) for item in evidence})
        cited_ids = set(draft.evidence_ids) if status == QueryStatus.GROUNDED else set()
        citations = tuple(
            Citation(item.fragment_id, item.source)
            for item in evidence
            if str(item.fragment_id) in cited_ids
        )
        trace.set(cited_fragment_ids=sorted(cited_ids))
        if status != QueryStatus.GROUNDED:
            # The output barrier never returns an unverified or declined draft.
            reason = "invalid_citations" if status == QueryStatus.UNVERIFIED else "model_abstained"
            return status, "", reason, (), False
        # A discrepancy needs separately attributed positions: at least two cited documents.
        discrepancy = draft.discrepancy and (
            len({citation.source.document_id for citation in citations}) >= 2
        )
        trace.set(discrepancy=discrepancy)
        answer = safety_frame(request.text, draft.answer)
        self.cache[key] = QueryResult(
            QueryId(uuid4()),
            status,
            answer,
            SnapshotId(UUID(snapshot_id)),
            citations,
            discrepancy=discrepancy,
        )
        return status, answer, None, citations, discrepancy


def _filters_attribute(filters: QueryFilters) -> dict[str, list[str]]:
    return {
        "document_ids": [str(item) for item in filters.document_ids],
        "categories": list(filters.categories),
        "breeds": list(filters.breeds),
        "sections": list(filters.sections),
    }
