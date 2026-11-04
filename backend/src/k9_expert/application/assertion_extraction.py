"""Bounded candidate extraction: document text is data, never executable instructions."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from uuid import uuid4

from k9_expert.domain.models import AssertionPolarity
from k9_expert.infrastructure.sqlite import StructuredKnowledgeRepository


@dataclass(frozen=True, slots=True)
class AssertionCandidate:
    breed: str
    attribute_key: str
    value: str
    polarity: AssertionPolarity
    fragment_id: str
    extraction_method: str


# Candidate values are hunter-profile codes so approved assertions match profile dimensions;
# each code lists the document wording that may support it.
ATTRIBUTE_TERMS: dict[str, dict[str, tuple[str, ...]]] = {
    "modality": {
        "rastreo": ("rastreo", "rastro"),
        "rastro_herido": ("pista de sangre", "rastro de sangre", "pieza herida"),
        "muestra": ("muestra",),
        "cobro": ("cobro",),
        "agua": ("agua",),
    },
    "terrain": {
        "monte_denso": ("monte denso",),
        "bosque": ("bosque",),
        "campo_abierto": ("campo abierto",),
        "montana": ("montaña",),
        "humedal": ("humedal",),
    },
}


class RuleAssertionExtractor:
    version = "assertion-rules-v1"

    def extract(
        self, breed: str | None, text: str, fragment_id: str
    ) -> tuple[AssertionCandidate, ...]:
        if breed is None or not breed.strip():
            return ()
        normalized = " ".join(text.lower().split())
        result: list[AssertionCandidate] = []
        for key, codes in ATTRIBUTE_TERMS.items():
            for code, terms in codes.items():
                found = [term for term in terms if term in normalized]
                if not found:
                    continue
                polarity = (
                    AssertionPolarity.CONTRADICTS
                    if any(
                        re.search(
                            rf"\b(?:no|nunca|sin)\b[^.;:]{{0,35}}\b{re.escape(term)}",
                            normalized,
                        )
                        for term in found
                    )
                    else AssertionPolarity.SUPPORTS
                )
                result.append(
                    AssertionCandidate(breed, key, code, polarity, fragment_id, self.version)
                )
        return tuple(result)


ModelExtract = Callable[[str], str]


class OllamaAssertionExtractor:
    """Optional JSON candidate extractor with no tools or publication authority."""

    version = "assertion-ollama-v1"

    def __init__(self, generate: ModelExtract, max_characters: int = 6000) -> None:
        self.generate = generate
        self.max_characters = max_characters

    def extract(
        self, breed: str | None, text: str, fragment_id: str
    ) -> tuple[AssertionCandidate, ...]:
        if breed is None or len(text) > self.max_characters:
            return ()
        prompt = json.dumps({
            "breed": breed,
            "fragment_id": fragment_id,
            "allowed_attributes": sorted(ATTRIBUTE_TERMS),
            "allowed_values": {key: sorted(codes) for key, codes in ATTRIBUTE_TERMS.items()},
            "document_data": text,
            "output": "JSON array: attribute_key, value, polarity, fragment_id only",
        }, ensure_ascii=False)
        try:
            raw = json.loads(self.generate(prompt))
        except (json.JSONDecodeError, ValueError, TypeError):
            return ()
        if not isinstance(raw, list):
            return ()
        candidates = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            key, value, polarity, cited = (
                item.get("attribute_key"),
                item.get("value"),
                item.get("polarity"),
                item.get("fragment_id"),
            )
            if (
                key not in ATTRIBUTE_TERMS or value not in ATTRIBUTE_TERMS[key]
                or cited != fragment_id or polarity not in {"supports", "contradicts"}
            ):
                continue
            candidates.append(AssertionCandidate(
                breed, key, value, AssertionPolarity(polarity), fragment_id, self.version
            ))
        return tuple(candidates)


def persist_candidates(
    repository: StructuredKnowledgeRepository, candidates: Sequence[AssertionCandidate]
) -> int:
    stored = 0
    for candidate in candidates:
        try:
            repository.create_candidate(
                assertion_id=uuid4(), breed=candidate.breed, attribute_key=candidate.attribute_key,
                value=candidate.value, polarity=candidate.polarity,
                fragment_ids=[candidate.fragment_id], extraction_method=candidate.extraction_method,
                policy_version="structured-knowledge-v1",
            )
            stored += 1
        except ValueError:
            # Invalid/unlinked output is quarantined by omission; it never reaches scoring.
            continue
    return stored
