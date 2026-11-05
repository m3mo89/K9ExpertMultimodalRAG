"""Bounded candidate extraction: document text is data, never executable instructions."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from uuid import uuid4

from k9_expert.domain.models import AssertionExtractionState, AssertionPolarity
from k9_expert.infrastructure.sqlite import StructuredKnowledgeRepository


@dataclass(frozen=True, slots=True)
class AssertionCandidate:
    breed: str
    attribute_key: str
    value: str
    polarity: AssertionPolarity
    fragment_id: str
    extraction_method: str


# Candidate values are hunter-profile codes so published assertions match profile dimensions;
# each code lists the word-bounded document wording (lowercase) that may support it.
ATTRIBUTE_PATTERNS: dict[str, dict[str, tuple[str, ...]]] = {
    "prey": {
        "venado": (
            r"\bvenados?\b", r"\bciervos?\b", r"\bcorzos?\b", r"\bgamos?\b", r"\bcaza mayor\b",
        ),
        "jabalí": (r"\bjabal[ií](?:es)?\b", r"\bcaza mayor\b"),
        "conejo": (r"\bconejos?\b",),
        "liebre": (r"\bliebres?\b",),
        "aves": (
            r"\baves?\b", r"\bperdi(?:z|ces)\b", r"\bcodorni(?:z|ces)\b", r"\bbecadas?\b",
            r"\bfais[aá]n(?:es)?\b", r"\bpatos?\b", r"\bcaza de pluma\b",
        ),
    },
    "modality": {
        "rastreo": (r"\brastreos?\b", r"\brastros?\b", r"\brastread(?:or|ora|ores|oras)\b"),
        "rastro_herido": (
            r"\bpistas? de sangre\b", r"\brastros? de sangre\b", r"\bpiezas? heridas?\b",
            r"\banimal(?:es)? heridos?\b", r"\bcaza herida\b",
        ),
        # Noun phrases only: "se muestra afectuoso" or "una muestra de afecto" are not pointing.
        "muestra": (
            r"\b(?:perros?|trabajo|caza|razas?) de muestra\b",
            r"\b(?:la|una|su) muestra\b(?!\s+de\b)",
        ),
        "cobro": (r"\bcobro\b", r"\bcobrar\b", r"\bcobrad(?:or|ora|ores|oras)\b"),
        # "levanta la cola" is anatomy, so lifting verbs need game as their object.
        "levantamiento": (
            r"\blevantamiento\b", r"\bojeo\b", r"\bespantar\b", r"\bhac(?:e|er) salir\b",
            r"\blevant(?:a|ar)\s+(?:la caza|las? piezas?|las? presas?|perdi\w+|conejos?"
            r"|liebres?|aves?)\b",
        ),
        "agua": (
            r"\b(?:en|de|del)(?:\s+el)?\s+agua\b", r"\baguas\b", r"\bnadador(?:a|es|as)?\b",
            r"\bacu[aá]tic[oa]s?\b",
        ),
    },
    "terrain": {
        "monte_denso": (
            r"\bmonte denso\b", r"\bmaleza\b", r"\bmatorral(?:es)?\b", r"\bespesuras?\b",
            r"\bzarzal(?:es)?\b",
        ),
        "bosque": (r"\bbosques?\b", r"\bboscos[oa]s?\b"),
        "campo_abierto": (
            r"\bcampo abierto\b", r"\bllanuras?\b", r"\bterrenos? abiertos?\b", r"\bestepas?\b",
        ),
        "montana": (r"\bmonta[nñ]as?\b", r"\bmonta[nñ]os[oa]s?\b", r"\bsierras?\b"),
        "accidentado": (
            r"\baccidentad[oa]s?\b", r"\bterrenos? dif[ií]cil(?:es)?\b", r"\bescarpad[oa]s?\b",
            r"\babrupt[oa]s?\b",
        ),
        "humedal": (
            r"\bhumedal(?:es)?\b", r"\bpantan(?:o|os|osa|osas|oso|osos)\b", r"\bmarismas?\b",
            r"\blagunas?\b", r"\bci[eé]nagas?\b",
        ),
    },
}

# Breed-group functions from the heading structure; `terrier` names no guided modality.
FUNCTION_MODALITIES = {
    "muestra": "muestra",
    "rastro": "rastreo",
    "cobro": "cobro",
    "busca": "levantamiento",
    "agua": "agua",
}

NEGATOR = r"\b(?:no\b(?!\s+(?:s[oó]lo|[uú]nicamente))|nunca\b|sin\b(?!\s+(?:duda|embargo)))"
SENTENCE_BOUNDARY = re.compile(r"(?<=[.;:!?])\s+")
_MATCHERS = {
    (key, code): (
        re.compile("|".join(patterns)),
        re.compile(rf"{NEGATOR}[^.;:,]{{0,35}}(?:{'|'.join(patterns)})"),
        re.compile(rf"\baunque\b[^.;:]*(?:{'|'.join(patterns)})[^.;:]*,\s*no\b"),
    )
    for key, codes in ATTRIBUTE_PATTERNS.items()
    for code, patterns in codes.items()
}


class RuleAssertionExtractor:
    version = "assertion-rules-v2"
    group_version = f"{version}:group"

    def extract(
        self, breed: str | None, text: str, fragment_id: str, section_path: Sequence[str] = ()
    ) -> tuple[AssertionCandidate, ...]:
        if breed is None or not breed.strip():
            return ()
        found: dict[tuple[str, str, AssertionPolarity], AssertionCandidate] = {}
        for sentence in SENTENCE_BOUNDARY.split(self._body(text, section_path)):
            for (key, code), (term, negated, concessive) in _MATCHERS.items():
                if term.search(sentence) is None:
                    continue
                polarity = (
                    AssertionPolarity.CONTRADICTS
                    if negated.search(sentence) or concessive.search(sentence)
                    else AssertionPolarity.SUPPORTS
                )
                found.setdefault((key, code, polarity), AssertionCandidate(
                    breed, key, code, polarity, fragment_id, self.version
                ))
        return tuple(found.values())

    def extract_group_functions(
        self, fragments: Iterable[tuple[str | None, Sequence[str], str]]
    ) -> tuple[AssertionCandidate, ...]:
        """One modality per breed and value, citing the breed's first attributed fragment."""
        found: dict[tuple[str, str], AssertionCandidate] = {}
        for breed, functions, fragment_id in fragments:
            if breed is None or not breed.strip():
                continue
            for function in functions:
                value = FUNCTION_MODALITIES.get(function)
                if value is not None:
                    found.setdefault((breed, value), AssertionCandidate(
                        breed, "modality", value, AssertionPolarity.SUPPORTS, fragment_id,
                        self.group_version,
                    ))
        return tuple(found.values())

    @staticmethod
    def _body(text: str, section_path: Sequence[str]) -> str:
        """Drop the repeated breadcrumb: a heading is structure, not a claim in this passage."""
        header = " › ".join(section_path)
        body = text.removeprefix(f"{header}\n") if header else text
        return " ".join(body.lower().split())


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
            "allowed_attributes": sorted(ATTRIBUTE_PATTERNS),
            "allowed_values": {key: sorted(codes) for key, codes in ATTRIBUTE_PATTERNS.items()},
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
                key not in ATTRIBUTE_PATTERNS or value not in ATTRIBUTE_PATTERNS[key]
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
    """Only rules publish without a person: model output stays a candidate because PDF text can
    steer it, and anything outside the closed vocabulary is dropped."""
    stored = 0
    for candidate in candidates:
        if candidate.value not in ATTRIBUTE_PATTERNS.get(candidate.attribute_key, {}):
            continue
        automatic = candidate.extraction_method in {
            RuleAssertionExtractor.version, RuleAssertionExtractor.group_version,
        }
        try:
            repository.create_candidate(
                assertion_id=uuid4(), breed=candidate.breed, attribute_key=candidate.attribute_key,
                value=candidate.value, polarity=candidate.polarity,
                fragment_ids=[candidate.fragment_id], extraction_method=candidate.extraction_method,
                policy_version="structured-knowledge-v2",
                extraction_state=(
                    AssertionExtractionState.AUTO_VALIDATED if automatic
                    else AssertionExtractionState.CANDIDATE
                ),
            )
            stored += 1
        except ValueError:
            # Invalid/unlinked output is quarantined by omission; it never reaches scoring.
            continue
    return stored
