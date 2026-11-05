from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID, uuid4

from k9_expert.application.generation import GeneratedAnswer
from k9_expert.application.observability import TraceRecorder
from k9_expert.domain.errors import ModelUnavailableError
from k9_expert.domain.hunter_profile import EVALUABLE_DIMENSIONS
from k9_expert.domain.models import (
    AssertionExtractionState,
    AssertionPolarity,
    BreedAssertion,
    ProfileCompleteness,
    RecommendationBand,
    RecommendationCandidate,
    RecommendationDimension,
    RecommendationDimensionResult,
    RecommendationId,
    RecommendationResult,
    SnapshotId,
    TranslatedHunterProfile,
)
from k9_expert.infrastructure.sqlite import (
    DocumentRepository,
    RecommendationRepository,
    StructuredKnowledgeRepository,
)
from k9_expert.ports.interfaces import TraceSink

NarrateRecommendation = Callable[[RecommendationResult], GeneratedAnswer]


@dataclass(frozen=True, slots=True)
class RecommendationPolicy:
    version: str = "recommendation-v3"
    minimum_coverage: float = 0.5
    high_threshold: float = 0.75
    high_coverage_threshold: float = 0.70
    moderate_threshold: float = 0.5
    contradiction_penalty: float = 0.10
    max_results: int = 3

    def __post_init__(self) -> None:
        values = (
            self.minimum_coverage, self.high_threshold, self.moderate_threshold,
            self.high_coverage_threshold,
        )
        if any(not 0 <= value <= 1 for value in values):
            raise ValueError("recommendation_policy_threshold_invalid")
        if self.high_threshold < self.moderate_threshold or self.max_results not in range(1, 4):
            raise ValueError("recommendation_policy_invalid")


class DeterministicRecommendationEngine:
    def __init__(self, policy: RecommendationPolicy | None = None) -> None:
        self.policy = policy or RecommendationPolicy()

    def recommend(
        self,
        profile: TranslatedHunterProfile,
        assertions_by_breed: Mapping[str, Sequence[BreedAssertion]],
    ) -> tuple[RecommendationCandidate, ...]:
        if profile.completeness != ProfileCompleteness.COMPLETE:
            return ()
        evaluated = [
            self._candidate(breed, profile, assertions)
            for breed, assertions in assertions_by_breed.items()
        ]
        eligible = [item for item in evaluated if not item.excluded and item.band is not None]
        return tuple(sorted(
            eligible,
            key=lambda item: (
                -(item.compatibility if item.compatibility is not None else -1),
                -item.coverage,
                -item.supporting_fragments,
                item.breed,
            ),
        )[: self.policy.max_results])

    def _candidate(
        self, breed: str, profile: TranslatedHunterProfile,
        assertions: Sequence[BreedAssertion],
    ) -> RecommendationCandidate:
        grouped: dict[str, list[BreedAssertion]] = defaultdict(list)
        for assertion in assertions:
            grouped[assertion.attribute_key].append(assertion)
        required = {constraint.dimension: constraint.values for constraint in profile.constraints}
        results: list[RecommendationDimensionResult] = []
        weighted_match = documented_mass = penalties = 0.0
        excluded = False
        penalty_reasons: list[str] = []
        evaluable = [item for item in profile.dimensions if item.key in EVALUABLE_DIMENSIONS]
        total_weight = sum(dimension.weight for dimension in evaluable)
        for dimension in evaluable:
            result, contradiction = self._dimension(dimension, grouped.get(dimension.key, []))
            results.append(result)
            if result.documented:
                documented_mass += dimension.weight
                if result.compatibility is not None:
                    weighted_match += dimension.weight * result.compatibility
            if contradiction:
                penalties += self.policy.contradiction_penalty
                penalty_reasons.append(f"documented_incompatibility:{dimension.key}")
                if dimension.key in required:
                    excluded = True
                    penalty_reasons.append(f"hard_constraint:{dimension.key}")
        coverage = documented_mass / total_weight if total_weight else 0.0
        compatibility = (
            max(0.0, weighted_match / documented_mass - penalties)
            if documented_mass and coverage >= self.policy.minimum_coverage and not excluded
            else None
        )
        return RecommendationCandidate(
            breed=breed,
            band=self._band(compatibility, coverage),
            compatibility=compatibility,
            coverage=coverage,
            dimensions=tuple(results),
            penalties=tuple(penalty_reasons),
            excluded=excluded,
            supporting_fragments=len({
                evidence_id
                for result in results if result.compatibility == 1.0
                for evidence_id in result.evidence_ids
            }),
        )

    @staticmethod
    def _dimension(
        dimension: RecommendationDimension, assertions: Sequence[BreedAssertion]
    ) -> tuple[RecommendationDimensionResult, bool]:
        relevant = [item for item in assertions if item.value in dimension.values]
        if not relevant:
            return RecommendationDimensionResult(dimension.key, None, False), False
        supports = any(item.polarity == AssertionPolarity.SUPPORTS for item in relevant)
        contradicts = any(item.polarity == AssertionPolarity.CONTRADICTS for item in relevant)
        conflicting = supports and contradicts
        compatibility = None if conflicting else (1.0 if supports else 0.0)
        evidence_ids = tuple(dict.fromkeys(
            evidence.fragment_id for item in relevant for evidence in item.evidence
        ))
        return RecommendationDimensionResult(
            dimension.key, compatibility, True, conflicting, evidence_ids
        ), contradicts and not supports

    def _band(self, compatibility: float | None, coverage: float) -> RecommendationBand | None:
        if compatibility is None:
            return None
        if (
            compatibility >= self.policy.high_threshold
            and coverage >= self.policy.high_coverage_threshold
        ):
            return RecommendationBand.HIGH
        if compatibility >= self.policy.moderate_threshold:
            return RecommendationBand.MODERATE
        return RecommendationBand.LOW


class HunterRecommendationService:
    def __init__(
        self,
        documents: DocumentRepository,
        knowledge: StructuredKnowledgeRepository,
        repository: RecommendationRepository,
        engine: DeterministicRecommendationEngine,
        breed_names: Callable[[], list[str]],
        sink: TraceSink | None = None,
        narrator: NarrateRecommendation | None = None,
    ) -> None:
        self.documents = documents
        self.knowledge = knowledge
        self.repository = repository
        self.engine = engine
        self.breed_names = breed_names
        self.sink = sink
        self.narrator = narrator

    def recommend(self, profile: TranslatedHunterProfile) -> RecommendationResult:
        trace = TraceRecorder("recommendation")
        snapshot = self.documents.active_snapshot_id()
        trace.set(
            translator_version=profile.translator_version,
            policy_version=self.engine.policy.version,
            completeness=str(profile.completeness),
            missing_fields=list(profile.missing_fields),
            generation_called=False,
        )
        if profile.completeness != ProfileCompleteness.COMPLETE or snapshot is None:
            reason = "profile_incomplete" if profile.missing_fields else "no_active_snapshot"
            result = RecommendationResult(
                RecommendationId(uuid4()), profile, self.engine.policy.version,
                SnapshotId(UUID(snapshot)) if snapshot else None,
                limitations=(reason,), trace_id=trace.trace_id,
            )
            self.repository.save(result)
            trace.finish(self.sink, "incomplete", reason)
            return result
        breeds = list(profile.original.candidate_breeds) or self.breed_names()
        published: dict[str, list[BreedAssertion]] = defaultdict(list)
        for assertion in self.knowledge.eligible(snapshot):
            published[assertion.breed].append(assertion)
        assertions = {breed: published.get(breed, []) for breed in breeds}
        with trace.stage("deterministic_ranking"):
            candidates = self.engine.recommend(profile, assertions)
        limitations = _knowledge_limitations(profile, candidates, assertions)
        if not candidates:
            limitations.append("no_candidate_reached_coverage")
        elif len(candidates) < self.engine.policy.max_results:
            limitations.append("fewer_supported_candidates")
        result = RecommendationResult(
            RecommendationId(uuid4()), profile, self.engine.policy.version,
            SnapshotId(UUID(snapshot)), candidates, tuple(limitations), trace.trace_id,
        )
        if self.narrator is None:
            result = RecommendationResult(
                result.recommendation_id, result.profile, result.policy_version,
                result.snapshot_id, result.candidates,
                (*result.limitations, "narrative_unavailable"), result.trace_id,
            )
        else:
            trace.set(generation_called=True)
            try:
                draft = self.narrator(result)
                allowed = {
                    str(evidence_id)
                    for candidate in result.candidates
                    for dimension in candidate.dimensions
                    for evidence_id in dimension.evidence_ids
                }
                if not draft.answer.strip() or not set(draft.evidence_ids).issubset(allowed):
                    raise ValueError("recommendation_narrative_unverified")
                result = RecommendationResult(
                    result.recommendation_id, result.profile, result.policy_version,
                    result.snapshot_id, result.candidates, result.limitations, result.trace_id,
                    draft.answer,
                )
            except (ModelUnavailableError, ValueError):
                result = RecommendationResult(
                    result.recommendation_id, result.profile, result.policy_version,
                    result.snapshot_id, result.candidates,
                    (*result.limitations, "narrative_unavailable"), result.trace_id,
                )
        trace.set(
            candidate_order=[item.breed for item in result.candidates],
            coverage=[item.coverage for item in result.candidates],
            conflicts=sum(
                item.conflicting
                for candidate in result.candidates for item in candidate.dimensions
            ),
            penalties=[list(item.penalties) for item in result.candidates],
        )
        self.repository.save(result)
        trace.finish(self.sink, "completed")
        return result


def _knowledge_limitations(
    profile: TranslatedHunterProfile,
    candidates: Sequence[RecommendationCandidate],
    assertions: Mapping[str, Sequence[BreedAssertion]],
) -> list[str]:
    limitations = [
        f"dimension_not_evaluated:{dimension.key}"
        for dimension in profile.dimensions
        if dimension.key not in EVALUABLE_DIMENSIONS
    ]
    for candidate in candidates:
        used = {item for result in candidate.dimensions for item in result.evidence_ids}
        if any(
            assertion.extraction_state == AssertionExtractionState.AUTO_VALIDATED
            and any(evidence.fragment_id in used for evidence in assertion.evidence)
            for assertion in assertions[candidate.breed]
        ):
            limitations.append("automatic_extraction_unreviewed")
            break
    return limitations


def recommendation_narrator(
    generate: Callable[[str, str, str], GeneratedAnswer], alias: str = "simple"
) -> NarrateRecommendation:
    """Bounded local narration over an immutable deterministic payload."""

    def narrate(result: RecommendationResult) -> GeneratedAnswer:
        payload = {
            "policy_version": result.policy_version,
            "candidates": [
                {
                    "breed": candidate.breed,
                    "band": str(candidate.band) if candidate.band else None,
                    "coverage": candidate.coverage,
                    "penalties": candidate.penalties,
                    "dimensions": [
                        {
                            "key": dimension.key,
                            "compatibility": dimension.compatibility,
                            "documented": dimension.documented,
                            "conflicting": dimension.conflicting,
                            "evidence_ids": [str(item) for item in dimension.evidence_ids],
                        }
                        for dimension in candidate.dimensions
                    ],
                }
                for candidate in result.candidates
            ],
        }
        return generate(
            alias,
            "Redacta una síntesis breve en español. No cambies orden, bandas ni valores. "
            "Devuelve JSON con answer y evidence_ids; usa sólo ids suministrados.",
            json.dumps(payload, ensure_ascii=False),
        )

    return narrate
