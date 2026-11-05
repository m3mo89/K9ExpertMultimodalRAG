from uuid import uuid4

from k9_expert.application.profile_translation import HunterProfileTranslator
from k9_expert.application.recommendation import (
    DeterministicRecommendationEngine,
    RecommendationPolicy,
)
from k9_expert.domain.models import (
    AssertionEvidenceState,
    AssertionExtractionState,
    AssertionPolarity,
    BreedAssertion,
    BreedAssertionEvidence,
    DocumentId,
    DocumentVersionId,
    FragmentId,
    HunterProfile,
    HunterProfileAnswer,
    ProfileImportance,
    RecommendationBand,
    SourceRef,
)


def translated(*, required_modality: bool = False):  # type: ignore[no-untyped-def]
    importance = ProfileImportance.REQUIRED if required_modality else ProfileImportance.PREFERENCE
    return HunterProfileTranslator().translate(HunterProfile((
        HunterProfileAnswer("prey", ("venado",)),
        HunterProfileAnswer("modality", ("rastreo",), importance),
        HunterProfileAnswer("terrain", ("monte_denso",)),
        HunterProfileAnswer("experience", ("principiante",)),
        HunterProfileAnswer("daily_availability", ("1_2h",)),
    )))


def assertion(
    key: str, value: str, polarity: AssertionPolarity = AssertionPolarity.SUPPORTS
) -> BreedAssertion:
    evidence = BreedAssertionEvidence(
        FragmentId(uuid4()),
        SourceRef(DocumentId(uuid4()), DocumentVersionId(uuid4()), "Libro", None, None, 1, None),
    )
    return BreedAssertion(
        uuid4(), "Raza", key, value, polarity, AssertionEvidenceState.DOCUMENTED,
        AssertionExtractionState.REVIEWED, "human", "v1", (evidence,),
    )


def test_scoring_unknowns_coverage_penalty_and_band_are_separate() -> None:
    engine = DeterministicRecommendationEngine(RecommendationPolicy(minimum_coverage=0.4))
    [candidate] = engine.recommend(translated(), {"Raza": (
        assertion("prey", "venado"),
        assertion("modality", "rastreo"),
        assertion("terrain", "monte_denso", AssertionPolarity.CONTRADICTS),
    )})
    assert candidate.coverage > 0.5
    assert candidate.compatibility is not None and candidate.compatibility < 1
    assert candidate.band == RecommendationBand.MODERATE
    assert {item.key for item in candidate.dimensions} == {"prey", "modality", "terrain"}
    assert candidate.penalties == ("documented_incompatibility:terrain",)


def test_required_documented_contradiction_excludes_but_unknown_does_not() -> None:
    engine = DeterministicRecommendationEngine(RecommendationPolicy(minimum_coverage=0))
    excluded = engine.recommend(translated(required_modality=True), {"Excluded": (
        assertion("modality", "rastreo", AssertionPolarity.CONTRADICTS),
    )})
    assert excluded == ()
    [unknown_allowed] = engine.recommend(translated(required_modality=True), {"Allowed": (
        assertion("prey", "venado"),
    )})
    assert unknown_allowed.breed == "Allowed"


def test_conflicts_do_not_create_compatibility_and_order_is_reproducible() -> None:
    engine = DeterministicRecommendationEngine(RecommendationPolicy(minimum_coverage=0))
    conflict = (
        assertion("modality", "rastreo"),
        assertion("modality", "rastreo", AssertionPolarity.CONTRADICTS),
    )
    complete = (assertion("prey", "venado"), assertion("modality", "rastreo"))
    first = engine.recommend(
        translated(), {"Zulu": complete, "Conflict": conflict, "Alpha": complete}
    )
    second = engine.recommend(
        translated(), {"Alpha": complete, "Zulu": complete, "Conflict": conflict}
    )
    assert [item.breed for item in first] == [item.breed for item in second]
    assert [item.breed for item in first][:2] == ["Alpha", "Zulu"]
    conflict_result = next(item for item in first if item.breed == "Conflict")
    assert conflict_result.dimensions[1].conflicting is True


def test_maximum_three_and_sparse_candidates_are_omitted() -> None:
    engine = DeterministicRecommendationEngine(RecommendationPolicy(minimum_coverage=0.5))
    supported = tuple(
        assertion(key, value) for key, value in (
            ("prey", "venado"), ("modality", "rastreo"), ("terrain", "monte_denso")
        )
    )
    results = engine.recommend(translated(), {
        **{f"Raza {index}": supported for index in range(5)},
        "Sparse": (assertion("prey", "venado"),),
    })
    assert len(results) == 3
    assert all(item.breed != "Sparse" for item in results)


def profile_with(*extra: HunterProfileAnswer):  # type: ignore[no-untyped-def]
    return HunterProfileTranslator().translate(HunterProfile((
        HunterProfileAnswer("prey", ("venado",)),
        HunterProfileAnswer("modality", ("rastreo",)),
        HunterProfileAnswer("terrain", ("monte_denso",)),
        *extra,
    )))


def test_coverage_uses_only_evaluable_dimensions_and_optional_answers_change_nothing() -> None:
    engine = DeterministicRecommendationEngine()
    documented = {"Raza": (assertion("prey", "venado"), assertion("modality", "rastreo"))}
    [plain] = engine.recommend(profile_with(), documented)
    [answered] = engine.recommend(profile_with(
        HunterProfileAnswer("experience", ("principiante",)),
        HunterProfileAnswer("climate", ("frio",)),
        HunterProfileAnswer("space", ("reducido",)),
        HunterProfileAnswer("care_preference", ("bajo",)),
    ), documented)
    assert plain.coverage == answered.coverage == 0.6 / 0.85
    assert plain.compatibility == answered.compatibility == 1.0
    assert plain.band == answered.band == RecommendationBand.HIGH


def test_single_documented_dimension_does_not_qualify_a_breed() -> None:
    engine = DeterministicRecommendationEngine()
    assert engine.recommend(profile_with(), {"Raza": (assertion("prey", "venado"),)}) == ()


def test_required_non_evaluable_answer_cannot_exclude_a_breed() -> None:
    engine = DeterministicRecommendationEngine()
    required = HunterProfileAnswer("experience", ("principiante",), ProfileImportance.REQUIRED)
    documented = (assertion("prey", "venado"), assertion("modality", "rastreo"))
    results = engine.recommend(profile_with(required), {"Raza": documented})
    assert [item.breed for item in results] == ["Raza"]


def test_supporting_fragments_break_ties_before_alphabetical_order() -> None:
    engine = DeterministicRecommendationEngine()
    base = (assertion("prey", "venado"), assertion("modality", "rastreo"))
    results = engine.recommend(profile_with(), {
        "Alpha": base,
        "Zulu": (*base, assertion("modality", "rastreo")),
    })
    assert [(item.breed, item.supporting_fragments) for item in results] == [
        ("Zulu", 3), ("Alpha", 2),
    ]
    replay = engine.recommend(profile_with(), {
        "Zulu": (*base, assertion("modality", "rastreo")),
        "Alpha": base,
    })
    assert [item.breed for item in replay] == ["Zulu", "Alpha"]


def test_high_band_requires_coverage_as_well_as_compatibility() -> None:
    engine = DeterministicRecommendationEngine()
    [limited] = engine.recommend(profile_with(), {"Raza": (
        assertion("prey", "venado"), assertion("terrain", "monte_denso"),
    )})
    assert limited.compatibility == 1.0
    assert limited.coverage < engine.policy.high_coverage_threshold
    assert limited.band == RecommendationBand.MODERATE
