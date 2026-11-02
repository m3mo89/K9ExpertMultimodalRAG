from __future__ import annotations

from uuid import uuid4

from k9_expert.application.agent import DomainPreservingReformulator
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


def test_agent_reformulates_once_then_generates_or_terminates() -> None:
    item = evidence(0.9)
    requests: list[QueryRequest] = []

    def retrieve(request: QueryRequest):  # type: ignore[no-untyped-def]
        requests.append(request)
        return [] if len(requests) == 1 else [item]

    worker = QueryOrchestrator(
        lambda _s, _p: GeneratedAnswer("respuesta", (str(item.fragment_id),)),
        retrieve,
        reformulate=DomainPreservingReformulator(),
        agent_max_iterations=2,
    )
    result = worker.run(QueryRequest("aptitudes del teckel"), str(uuid4()))
    assert result.status == QueryStatus.GROUNDED
    assert len(requests) == 2
    assert requests[1].filters == requests[0].filters
    assert requests[1].text.startswith("Información documental")

    attempts = 0

    def empty(_request: QueryRequest) -> list[object]:
        nonlocal attempts
        attempts += 1
        return []

    abstained = QueryOrchestrator(
        lambda _s, _p: (_ for _ in ()).throw(AssertionError("generation must not run")),
        empty,
        reformulate=DomainPreservingReformulator(),
        agent_max_iterations=2,
    ).run(QueryRequest("aptitudes del teckel"), str(uuid4()))
    assert abstained.status == QueryStatus.ABSTAINED
    assert attempts == 2


def test_grounded_query_routes_through_logical_aliases_and_traces_fallback() -> None:
    from k9_expert.application.generation import GatewayAttempt
    from k9_expert.application.routing import ComplexityRouter

    item = evidence(0.9)
    events = []

    class Gateway:
        attempts: list[GatewayAttempt] = []

        def generate(self, alias: str, _s: str, _p: str) -> GeneratedAnswer:
            self.attempts += [GatewayAttempt(alias, "m1", "unavailable"),
                              GatewayAttempt("fallback", "m2", "success")]
            return GeneratedAnswer("respuesta", (str(item.fragment_id),))

        def resolved_model(self, alias: str) -> str | None:
            return f"resolved-{alias}"

    class Sink:
        def emit(self, event) -> None:  # type: ignore[no-untyped-def]
            events.append(event)

    worker = QueryOrchestrator(
        lambda _s, _p: (_ for _ in ()).throw(AssertionError("unrouted generation")),
        lambda _: [item], sink=Sink(), model_router=ComplexityRouter(), routed_gateway=Gateway(),
    )
    assert worker.run(QueryRequest("teckel"), str(uuid4())).status == QueryStatus.GROUNDED
    attributes = events[0].attributes
    assert attributes["operation"] == "grounded_query"
    assert attributes["model_route"] == "simple"
    assert attributes["route_reason"] == "bounded_request"
    assert attributes["resolved_model"] == "resolved-fallback"
    assert attributes["fallback_used"] is True
