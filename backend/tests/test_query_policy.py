from __future__ import annotations

from uuid import uuid4

from k9_expert.application.query import (
    DomainRouter,
    EvidenceSufficiencyPolicy,
    QueryInputPolicy,
    QueryRequest,
    SemanticRetriever,
)
from k9_expert.domain.models import (
    DocumentId,
    DocumentVersionId,
    Evidence,
    FragmentId,
    QueryStatus,
    SourceRef,
)


def evidence(score: float) -> Evidence:
    source = SourceRef(
        DocumentId(uuid4()), DocumentVersionId(uuid4()), "Libro", None, None, 27, None
    )
    return Evidence(FragmentId(uuid4()), source, "El teckel", score)


def test_query_policy_binds_snapshot_and_rejects_invalid_input() -> None:
    policy = QueryInputPolicy(max_characters=10)
    assert policy.evaluate(QueryRequest(""), "snapshot").status == QueryStatus.REJECTED
    assert policy.evaluate(QueryRequest("teckel"), None).reason == "no_active_snapshot"
    assert policy.evaluate(QueryRequest("teckel"), "snapshot").status is None


def test_router_and_evidence_policy_use_explicit_safe_outcomes() -> None:
    assert DomainRouter().route("¿Cuál es la capital de Francia?") == "uncertain"
    assert DomainRouter().route("¿Qué cola tiene el norsk elghund?") == "in_domain"
    policy = EvidenceSufficiencyPolicy()
    assert policy.evaluate([]).reason == "no_evidence"
    assert policy.evaluate([evidence(0.2)]).reason == "weak_evidence"
    assert policy.evaluate([evidence(0.2)], route="uncertain").reason == "out_of_domain"
    assert policy.evaluate([evidence(0.7)]).status is None
    assert policy.evaluate([evidence(0.8)]).status is None


def test_retriever_applies_score_document_and_context_filters() -> None:
    matching = evidence(0.9)
    filters = QueryRequest("teckel").filters
    retrieved = SemanticRetriever(top_k=1, minimum_score=0.5).select(
        [matching, evidence(0.2)], filters
    )
    assert retrieved == [matching]
