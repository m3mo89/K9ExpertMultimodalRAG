from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from k9_expert.domain.breed_vocabulary import BREED_ALIASES
from k9_expert.domain.models import (
    BreedAnalysisProfile,
    FindingOutcome,
    GuardrailAction,
    GuardrailDecision,
)

SUPPORTED_CRITERIA = frozenset(
    {"hunting_function", "size", "morphology", "coat", "work_aptitude"}
)
INJECTION_PATTERNS = (
    re.compile(r"\bignora (?:todas? )?(?:las )?instrucciones\b", re.I),
    re.compile(r"\b(?:revela|muestra) (?:el )?(?:prompt|mensaje del sistema)\b", re.I),
    re.compile(r"\b(?:system|assistant)\s*:", re.I),
    re.compile(r"<\s*(?:system|assistant|tool)\b", re.I),
)
SENSITIVE_PATTERNS = (
    re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"(?:\+?\d[\s().-]*){10,}"),
)
HEALTH_TERMS = frozenset({"salud", "enfermedad", "dosis", "tratamiento", "diagnóstico"})
SAFETY_MARKERS = ("fuente", "document", "veterin", "no sustituye")
# Breed names are open-ended, so the lexicon also takes the distinctive words of the
# controlled vocabulary's breed aliases (e.g. "beagle", "basset", "elghund"); nationality and
# colour qualifiers are skipped because they say nothing about the domain on their own.
_QUALIFIERS = frozenset({"aleman", "ingles", "english", "golden", "norsk", "hound"})
DOMAIN_TERMS = tuple(sorted({
    "perr", "raza", "caza", "cazador", "rastro", "muestra", "cobro", "busca", "teckel",
    "sabues", "lebrel", "podenco", "terrier", "retriever", "spaniel", "setter", "pointer",
    "braco", "bloodhound", "manto", "pelaje", "jauría", "cachorr",
    *(
        word for alias in BREED_ALIASES for word in alias.split()
        if len(word) > 3 and word not in _QUALIFIERS
    ),
}))


class InputGuardrailChain:
    name = "input-guardrails-v1"

    def __init__(self, max_characters: int = 2000) -> None:
        self.max_characters = max_characters

    def evaluate(
        self, text: str, profile: BreedAnalysisProfile | None = None
    ) -> GuardrailDecision:
        normalized = text.strip()
        if not normalized or len(normalized) > self.max_characters:
            return GuardrailDecision(GuardrailAction.BLOCK, "input_bounds_invalid")
        if any(pattern.search(normalized) for pattern in INJECTION_PATTERNS):
            return GuardrailDecision(GuardrailAction.BLOCK, "prompt_injection_detected")
        if any(pattern.search(normalized) for pattern in SENSITIVE_PATTERNS):
            return GuardrailDecision(GuardrailAction.BLOCK, "sensitive_data_detected")
        if not any(term in normalized.lower() for term in DOMAIN_TERMS):
            return GuardrailDecision(GuardrailAction.BLOCK, "out_of_domain")
        if profile is not None:
            if not profile.criteria:
                return GuardrailDecision(GuardrailAction.BLOCK, "criteria_required")
            if any(item.key not in SUPPORTED_CRITERIA for item in profile.criteria):
                return GuardrailDecision(GuardrailAction.BLOCK, "criterion_not_supported")
            if any(
                not item.value.strip() or not 0 < item.weight <= 10
                for item in profile.criteria
            ):
                return GuardrailDecision(GuardrailAction.BLOCK, "criterion_invalid")
        return GuardrailDecision(GuardrailAction.ALLOW)


class OutputGuardrailChain:
    name = "output-guardrails-v1"

    def evaluate(
        self,
        payload: Mapping[str, object],
        *,
        allowed_evidence_ids: frozenset[str],
        allowed_candidates: frozenset[str] = frozenset(),
        health_related: bool = False,
    ) -> GuardrailDecision:
        candidates = payload.get("candidates")
        if not isinstance(candidates, list):
            return GuardrailDecision(GuardrailAction.RETRY, "output_schema_invalid")
        for candidate in candidates:
            if not isinstance(candidate, dict):
                return GuardrailDecision(GuardrailAction.RETRY, "output_schema_invalid")
            breed = candidate.get("breed")
            if allowed_candidates and breed not in allowed_candidates:
                return GuardrailDecision(GuardrailAction.ABSTAIN, "candidate_not_allowed")
            findings = candidate.get("findings")
            if not isinstance(findings, list):
                return GuardrailDecision(GuardrailAction.RETRY, "output_schema_invalid")
            decision = self._findings(findings, allowed_evidence_ids)
            if decision.action != GuardrailAction.ALLOW:
                return decision
        narrative = str(payload.get("summary", ""))
        if health_related and not any(marker in narrative.lower() for marker in SAFETY_MARKERS):
            return GuardrailDecision(GuardrailAction.RETRY, "health_framing_missing")
        return GuardrailDecision(GuardrailAction.ALLOW)

    @staticmethod
    def _findings(
        findings: Sequence[object], allowed_evidence_ids: frozenset[str]
    ) -> GuardrailDecision:
        allowed_outcomes = {str(item) for item in FindingOutcome}
        for finding in findings:
            if not isinstance(finding, dict) or finding.get("outcome") not in allowed_outcomes:
                return GuardrailDecision(GuardrailAction.RETRY, "finding_value_invalid")
            citations = finding.get("evidence_ids", [])
            if not isinstance(citations, list) or any(
                not isinstance(item, str) or item not in allowed_evidence_ids for item in citations
            ):
                return GuardrailDecision(GuardrailAction.ABSTAIN, "citation_not_allowed")
            if finding.get("outcome") != FindingOutcome.NOT_DOCUMENTED and not citations:
                return GuardrailDecision(GuardrailAction.ABSTAIN, "citation_required")
        return GuardrailDecision(GuardrailAction.ALLOW)
