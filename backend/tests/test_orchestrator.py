from __future__ import annotations

from uuid import uuid4

from k9_expert.application.generation import GeneratedAnswer
from k9_expert.application.query import QueryOrchestrator, QueryRequest
from k9_expert.domain.models import QueryStatus
from test_query_policy import evidence


def test_orchestrator_handles_rejection_cache_and_invalid_citation() -> None:
    item = evidence(0.9)
    calls = 0

    def generate(_, __):
        nonlocal calls
        calls += 1
        return GeneratedAnswer("respuesta", (str(item.fragment_id),))

    worker = QueryOrchestrator(generate, lambda _: [item])
    snapshot = str(uuid4())
    assert worker.run(QueryRequest(""), snapshot).status == QueryStatus.REJECTED
    assert worker.run(QueryRequest("teckel"), snapshot).status == QueryStatus.GROUNDED
    assert worker.run(QueryRequest("teckel"), snapshot).status == QueryStatus.GROUNDED
    assert calls == 1
    invalid = QueryOrchestrator(lambda _, __: GeneratedAnswer("x", ("bad",)), lambda _: [item])
    assert invalid.run(QueryRequest("teckel"), snapshot).status == QueryStatus.UNVERIFIED
