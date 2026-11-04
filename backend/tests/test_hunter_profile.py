import pytest

from k9_expert.application.profile_translation import HunterProfileTranslator
from k9_expert.domain.models import (
    HunterProfile,
    HunterProfileAnswer,
    ProfileCompleteness,
    ProfileImportance,
)


def answer(
    key: str, *values: str, importance: ProfileImportance = ProfileImportance.PREFERENCE
) -> HunterProfileAnswer:
    return HunterProfileAnswer(key, values, importance)


def complete_profile() -> HunterProfile:
    return HunterProfile((
        answer("prey", "venado"),
        answer("modality", "rastreo"),
        answer("terrain", "monte_denso"),
        answer("experience", "principiante"),
        answer("daily_availability", "1_2h"),
    ))


def test_translator_preserves_original_answers_and_normalizes_dimensions() -> None:
    profile = complete_profile()
    translated = HunterProfileTranslator().translate(profile)
    assert translated.original is profile
    assert translated.completeness == ProfileCompleteness.COMPLETE
    assert translated.missing_fields == ()
    assert [item.key for item in translated.dimensions] == [
        "prey", "modality", "terrain", "experience", "daily_availability"
    ]
    assert translated.translator_version == "hunter-profile-v1"


def test_missing_and_ambiguous_answers_return_stable_errors() -> None:
    translated = HunterProfileTranslator().translate(HunterProfile((
        answer("prey", "venado"), answer("terrain", "bosque"),
    )))
    assert translated.completeness == ProfileCompleteness.INCOMPLETE
    assert translated.missing_fields == ("modality", "experience", "daily_availability")
    with pytest.raises(ValueError, match="profile_cardinality_invalid:experience"):
        HunterProfileTranslator().translate(HunterProfile((
            answer("experience", "principiante", "avanzada"),
        )))


def test_multiple_selection_and_required_constraint_are_deterministic() -> None:
    profile = HunterProfile((
        answer("prey", "venado", "jabalí"),
        answer("modality", "rastreo", "rastro_herido", importance=ProfileImportance.REQUIRED),
        answer("terrain", "monte_denso", "bosque"),
        answer("experience", "intermedia"),
        answer("daily_availability", "mas_2h"),
    ))
    translated = HunterProfileTranslator().translate(profile)
    assert translated.dimensions[0].values == ("venado", "jabalí")
    assert translated.constraints[0].dimension == "modality"


def test_hunting_frequency_does_not_replace_daily_availability() -> None:
    profile = HunterProfile((
        answer("prey", "venado"), answer("modality", "rastreo"),
        answer("terrain", "monte_denso"), answer("experience", "principiante"),
        answer("hunting_frequency", "ocasional"),
    ))
    translated = HunterProfileTranslator().translate(profile)
    assert translated.missing_fields == ("daily_availability",)


def test_profile_rejects_unknown_values_duplicates_and_schema() -> None:
    with pytest.raises(ValueError, match="profile_value_unsupported:prey"):
        HunterProfileTranslator().translate(HunterProfile((answer("prey", "dragon"),)))
    with pytest.raises(ValueError, match="profile_answer_duplicate"):
        HunterProfile((answer("prey", "venado"), answer("prey", "jabalí")))
    with pytest.raises(ValueError, match="profile_schema_unsupported"):
        HunterProfileTranslator().translate(
            HunterProfile((answer("prey", "venado"),), schema_version="3.0")
        )
