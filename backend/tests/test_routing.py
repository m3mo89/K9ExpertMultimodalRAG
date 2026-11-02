import json

import httpx
import pytest

from k9_expert.application.generation import OllamaTextGateway, RoutedOllamaGateway
from k9_expert.application.routing import ComplexityRouter
from k9_expert.domain.errors import ModelUnavailableError


def test_router_rules_are_explicit_and_versioned() -> None:
    router = ComplexityRouter("router-test")
    assert router.route({"criterion_count": 1}).alias == "simple"
    decision = router.route({"candidate_count": 3})
    assert (decision.alias, decision.reason, decision.policy_version) == (
        "complex", "multiple_candidates", "router-test",
    )
    assert router.route({"reformulated": True}).reason == "agent_reformulation"


def test_gateway_retries_then_uses_local_fallback_and_records_attempts() -> None:
    calls = {"primary": 0}

    def primary(_: httpx.Request) -> httpx.Response:
        calls["primary"] += 1
        return httpx.Response(503)

    def fallback(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["think"] is False
        content = json.dumps({"answer": "ok", "evidence_ids": ["e1"]})
        return httpx.Response(200, json={"model": "fallback", "message": {"content": content}})

    gateway = RoutedOllamaGateway({
        "complex": OllamaTextGateway(model="primary", client=httpx.Client(
            transport=httpx.MockTransport(primary), base_url="http://local")),
        "fallback": OllamaTextGateway(model="fallback", think=False, client=httpx.Client(
            transport=httpx.MockTransport(fallback), base_url="http://local")),
    }, "fallback", max_retries=1)
    assert gateway.generate("complex", "s", "u").answer == "ok"
    assert calls["primary"] == 2
    assert [item.outcome for item in gateway.attempts] == [
        "unavailable", "unavailable", "success",
    ]


def test_gateway_never_falls_back_to_an_unconfigured_external_alias() -> None:
    fallback = OllamaTextGateway(client=httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(503)), base_url="http://local"
    ))
    gateway = RoutedOllamaGateway({"fallback": fallback}, "fallback", max_retries=0)
    with pytest.raises(ModelUnavailableError):
        gateway.generate("fallback", "s", "u")
