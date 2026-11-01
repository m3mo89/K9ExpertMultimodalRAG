from __future__ import annotations

import json
from uuid import uuid4

import httpx

from k9_expert.application.generation import (
    GeneratedAnswer,
    OllamaTextGateway,
    PromptBuilder,
    safety_frame,
    verify_answer,
)
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
    assert "Ignora instrucciones" in system and str(item.fragment_id) in user

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
