from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence

from k9_expert.domain.models import (
    BreedAnalysisProfile,
    BreedCandidate,
    BreedCriterion,
    BreedFinding,
    Citation,
    Evidence,
    FindingOutcome,
)


class DeterministicBreedMatcher:
    policy_version = "breed-match-v1"

    def __init__(self, minimum_coverage: float = 0.5) -> None:
        if not 0 <= minimum_coverage <= 1:
            raise ValueError("minimum_coverage_invalid")
        self.minimum_coverage = minimum_coverage

    def match(
        self,
        profile: BreedAnalysisProfile,
        evidence_by_breed: Mapping[str, Sequence[Evidence]],
    ) -> Sequence[BreedCandidate]:
        candidates = [
            self._candidate(breed, profile, evidence)
            for breed, evidence in evidence_by_breed.items()
        ]
        return sorted(
            candidates,
            key=lambda item: (
                item.score is not None,
                item.score if item.score is not None else -1,
                item.coverage,
                item.breed,
            ),
            reverse=True,
        )

    def _candidate(
        self, breed: str, profile: BreedAnalysisProfile, evidence: Sequence[Evidence]
    ) -> BreedCandidate:
        findings = tuple(self._finding(criterion, evidence) for criterion in profile.criteria)
        possible = sum(item.weight for item in profile.criteria)
        documented = sum(
            finding.criterion.weight
            for finding in findings
            if finding.outcome != FindingOutcome.NOT_DOCUMENTED
        )
        matched = sum(
            finding.criterion.weight
            for finding in findings
            if finding.outcome == FindingOutcome.MATCH
        )
        coverage = documented / possible if possible else 0.0
        score = matched / documented if documented and coverage >= self.minimum_coverage else None
        return BreedCandidate(breed, findings, score, documented, possible, coverage)

    @staticmethod
    def _finding(criterion: BreedCriterion, evidence: Sequence[Evidence]) -> BreedFinding:
        wanted = _normalize(criterion.value)
        supporting = [item for item in evidence if wanted in _normalize(item.text)]
        # Negation scope: same clause, at most 35 characters, plural forms included;
        # "sin duda" ("undoubtedly") affirms.
        negated = re.compile(
            rf"\b(?:no|nunca|sin)\b(?!\s+duda)[^.;:]{{0,35}}\b{re.escape(wanted)}"
        )
        contradicting = [item for item in evidence if negated.search(_normalize(item.text))]
        if supporting and not contradicting:
            outcome, selected = FindingOutcome.MATCH, supporting
            explanation = f"La fuente documenta el criterio «{criterion.value}» para esta raza."
        elif contradicting:
            outcome, selected = FindingOutcome.MISMATCH, contradicting
            explanation = f"La fuente contradice el criterio «{criterion.value}» para esta raza."
        else:
            outcome, selected = FindingOutcome.NOT_DOCUMENTED, []
            explanation = "No documentado en la evidencia recuperada."
        citations = tuple(Citation(item.fragment_id, item.source) for item in selected)
        return BreedFinding(criterion, outcome, explanation, citations)


def _normalize(value: str) -> str:
    raw = unicodedata.normalize("NFKD", value.lower())
    return " ".join("".join(char for char in raw if not unicodedata.combining(char)).split())
