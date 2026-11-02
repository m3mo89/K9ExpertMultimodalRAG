from uuid import uuid4

from k9_expert.application.breed_match import DeterministicBreedMatcher
from k9_expert.domain.models import (
    BreedAnalysisProfile,
    BreedCriterion,
    DocumentId,
    DocumentVersionId,
    Evidence,
    FindingOutcome,
    FragmentId,
    SourceRef,
)


def evidence(text: str) -> Evidence:
    return Evidence(
        FragmentId(uuid4()),
        SourceRef(DocumentId(uuid4()), DocumentVersionId(uuid4()), "Libro", None, None, 1, None),
        text, 0.9,
    )


def test_matcher_produces_documented_and_unknown_findings_with_citations() -> None:
    profile = BreedAnalysisProfile((
        BreedCriterion("hunting_function", "rastro", 2),
        BreedCriterion("coat", "pelo duro", 1),
    ))
    [candidate] = DeterministicBreedMatcher(minimum_coverage=0.5).match(
        profile, {"Teckel alemán": [evidence("Se utiliza para el rastro de la pieza.")]}
    )
    assert [item.outcome for item in candidate.findings] == [
        FindingOutcome.MATCH, FindingOutcome.NOT_DOCUMENTED,
    ]
    assert len(candidate.findings[0].citations) == 1
    assert candidate.findings[1].citations == ()
    assert candidate.score == 1.0
    assert candidate.coverage == 2 / 3


def test_score_is_omitted_below_coverage_and_order_is_reproducible() -> None:
    profile = BreedAnalysisProfile((
        BreedCriterion("hunting_function", "rastro", 1),
        BreedCriterion("coat", "pelo duro", 1),
        BreedCriterion("size", "pequeño", 1),
    ))
    candidates = DeterministicBreedMatcher(minimum_coverage=0.5).match(profile, {
        "Basset hound": [evidence("Trabaja sin rastro documentado.")],
        "Teckel alemán": [evidence("Apto para rastro y de tamaño pequeño.")],
    })
    assert candidates[0].breed == "Teckel alemán"
    assert candidates[0].score == 1.0
    assert candidates[1].score is None


def test_explicit_negation_is_a_mismatch_not_an_llm_inference() -> None:
    profile = BreedAnalysisProfile((BreedCriterion("work_aptitude", "cobro", 1),))
    [candidate] = DeterministicBreedMatcher().match(
        profile, {"Raza": [evidence("No presenta aptitud para cobro en el trabajo descrito.")]}
    )
    assert candidate.findings[0].outcome == FindingOutcome.MISMATCH
    assert candidate.score == 0.0


def test_negation_covers_plurals_stays_in_its_clause_and_ignores_sin_duda() -> None:
    profile = BreedAnalysisProfile((
        BreedCriterion("coat", "ondulado", 1),
        BreedCriterion("coat", "impermeable", 1),
        BreedCriterion("work_aptitude", "cubil", 1),
    ))
    [labrador] = DeterministicBreedMatcher().match(profile, {
        "Labrador": [evidence("El pelo es corto y denso, sin flecos ondulados.")],
    })
    [golden] = DeterministicBreedMatcher().match(profile, {
        "Golden": [evidence("Liso u ondulado, nunca rizado. El entrepelo es denso e impermeable.")],
    })
    [teckel] = DeterministicBreedMatcher().match(profile, {
        "Teckel": [evidence("Su trabajo es sin duda el que se desarrolla en el cubil.")],
    })
    assert labrador.findings[0].outcome == FindingOutcome.MISMATCH
    assert golden.findings[1].outcome == FindingOutcome.MATCH
    assert teckel.findings[2].outcome == FindingOutcome.MATCH


def test_hunting_function_needs_a_heading_or_de_function_not_the_verb() -> None:
    profile = BreedAnalysisProfile((BreedCriterion("hunting_function", "muestra", 1),))
    candidates = DeterministicBreedMatcher().match(profile, {
        "Teckel": [evidence("Teckel › Carácter\nSe muestra valiente ante el tejón.")],
        "Pointer": [evidence("Perros de muestra › Pointer › Manto\nEl pelo es corto.")],
        "Braco": [evidence("Braco › Trabajo\nExcelente perro de muestra.")],
    })
    outcomes = {item.breed: item.findings[0].outcome for item in candidates}
    assert outcomes == {
        "Teckel": FindingOutcome.NOT_DOCUMENTED,
        "Pointer": FindingOutcome.MATCH,
        "Braco": FindingOutcome.MATCH,
    }


def test_verb_negation_does_not_contradict_the_pointing_function() -> None:
    profile = BreedAnalysisProfile((BreedCriterion("hunting_function", "muestra", 1),))
    [pointer] = DeterministicBreedMatcher().match(profile, {
        "Pointer": [evidence("Perros de muestra › Pointer\nNo se muestra agresivo.")],
    })
    assert pointer.findings[0].outcome == FindingOutcome.MATCH
