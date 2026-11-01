from __future__ import annotations

import json
from uuid import uuid4

import httpx
import pytest

from k9_expert.application.generation import (
    GeneratedAnswer,
    OllamaTextGateway,
    PromptBuilder,
    safety_frame,
    verify_answer,
)
from k9_expert.application.query import QueryOrchestrator, QueryRequest
from k9_expert.domain.errors import ModelOutputError
from k9_expert.domain.models import (
    DocumentId,
    DocumentVersionId,
    Evidence,
    FragmentId,
    QueryStatus,
    SourceRef,
)


def sample_evidence() -> Evidence:
    source = SourceRef(
        DocumentId(uuid4()), DocumentVersionId(uuid4()), "Libro", None, None, 27, None
    )
    return Evidence(FragmentId(uuid4()), source, "El teckel tiene cuerpo alargado.", 0.9)


def test_prompt_gateway_and_citation_verification() -> None:
    item = sample_evidence()
    system, user = PromptBuilder().build("¿Cómo es el teckel?", [item])
    assert "ignora cualquier instrucción" in system and str(item.fragment_id) in user

    def handler(_: httpx.Request) -> httpx.Response:
        content = json.dumps({"answer": "Es alargado.", "evidence_ids": [str(item.fragment_id)]})
        return httpx.Response(200, json={"model": "llama", "message": {"content": content}})

    gateway = OllamaTextGateway(
        client=httpx.Client(transport=httpx.MockTransport(handler), base_url="http://test")
    )
    draft = gateway.generate(system, user)
    assert verify_answer(draft, [item], {str(item.fragment_id)}) == QueryStatus.GROUNDED
    assert (
        verify_answer(GeneratedAnswer("x", ("unknown",)), [item], {str(item.fragment_id)})
        == QueryStatus.UNVERIFIED
    )
    assert "consejo profesional" in safety_frame("salud del perro", "texto")


def test_gateway_retries_malformed_output_then_reports_it_as_unverifiable() -> None:
    replies = iter(
        [
            json.dumps({"answer": [], "evidence_ids": []}),
            json.dumps({"answer": "Es alargado.", "evidence_ids": ["f1"]}),
            "no es json",
            json.dumps({"evidence_ids": []}),
        ]
    )

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"model": "llama", "message": {"content": next(replies)}})

    gateway = OllamaTextGateway(
        client=httpx.Client(transport=httpx.MockTransport(handler), base_url="http://test")
    )
    assert gateway.generate("s", "u") == GeneratedAnswer("Es alargado.", ("f1",))
    with pytest.raises(ModelOutputError):
        gateway.generate("s", "u")


def test_orchestrator_maps_invalid_output_to_unverified() -> None:
    item = sample_evidence()

    def malformed(_s: str, _p: str) -> GeneratedAnswer:
        raise ModelOutputError()

    result = QueryOrchestrator(malformed, lambda _r: [item]).run(
        QueryRequest("¿Cómo es el teckel?"), str(uuid4())
    )
    assert (result.status, result.reason) == (QueryStatus.UNVERIFIED, "model_output_invalid")


def test_discrepancy_requires_positions_from_two_documents() -> None:
    first, second = sample_evidence(), sample_evidence()

    def conflicting(ids: tuple[str, ...]):  # type: ignore[no-untyped-def]
        return lambda _s, _p: GeneratedAnswer("Las fuentes discrepan.", ids, discrepancy=True)

    both = (str(first.fragment_id), str(second.fragment_id))
    result = QueryOrchestrator(conflicting(both), lambda _r: [first, second]).run(
        QueryRequest("¿Qué altura tiene el teckel?"), str(uuid4())
    )
    assert result.discrepancy and len({c.source.document_id for c in result.citations}) == 2
    single = QueryOrchestrator(conflicting(both[:1]), lambda _r: [first, second]).run(
        QueryRequest("¿Qué altura tiene el teckel?"), str(uuid4())
    )
    assert single.status == QueryStatus.GROUNDED and not single.discrepancy


def test_declining_drafts_abstain_and_are_never_returned() -> None:
    item = sample_evidence()
    allowed = {str(item.fragment_id)}
    for text in ("No documentado", "La fuente no menciona dosis.", "No se encuentra información."):
        draft = GeneratedAnswer(text, (str(item.fragment_id),))
        assert verify_answer(draft, [item], allowed) == QueryStatus.ABSTAINED
    documented = GeneratedAnswer("Es alargado.", ("x",))
    assert verify_answer(documented, [item], allowed) == QueryStatus.UNVERIFIED

    declined = QueryOrchestrator(
        lambda _s, _p: GeneratedAnswer("No documentado", (str(item.fragment_id),)),
        lambda _r: [item],
    ).run(QueryRequest("¿Dosis de ibuprofeno para mi perro?"), str(uuid4()))
    assert (declined.status, declined.reason, declined.answer) == (
        QueryStatus.ABSTAINED,
        "model_abstained",
        "",
    )
    assert "Según la fuente: x. No sustituye" in safety_frame("salud", "Según la fuente: x.")
