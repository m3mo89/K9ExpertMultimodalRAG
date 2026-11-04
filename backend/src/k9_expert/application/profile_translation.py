"""Deterministic translation from original hunter answers to recommendation dimensions."""

from __future__ import annotations

from k9_expert.domain.hunter_profile import (
    FIELD_BY_KEY,
    PROFILE_TRANSLATOR_VERSION,
    REQUIRED_FIELDS,
    validate_answer,
)
from k9_expert.domain.models import (
    HunterProfile,
    ProfileCompleteness,
    ProfileConstraint,
    ProfileImportance,
    RecommendationDimension,
    TranslatedHunterProfile,
)

DIMENSION_WEIGHTS = {
    "prey": 0.30,
    "modality": 0.30,
    "terrain": 0.25,
    "experience": 0.20,
    "daily_availability": 0.15,
    "hunting_frequency": 0.05,
    "climate": 0.10,
    "space": 0.05,
    "care_preference": 0.10,
}


class HunterProfileTranslator:
    version = PROFILE_TRANSLATOR_VERSION

    def translate(self, profile: HunterProfile) -> TranslatedHunterProfile:
        if profile.schema_version != "2.0":
            raise ValueError("profile_schema_unsupported")
        answers = {answer.key: answer for answer in profile.answers}
        for answer in profile.answers:
            validate_answer(answer.key, answer.values)
        missing = tuple(key for key in REQUIRED_FIELDS if key not in answers)
        dimensions = tuple(
            RecommendationDimension(
                key=answer.key,
                values=answer.values,
                weight=DIMENSION_WEIGHTS[answer.key],
                required=FIELD_BY_KEY[answer.key].required,
            )
            for answer in profile.answers
        )
        constraints = tuple(
            ProfileConstraint(answer.key, answer.values)
            for answer in profile.answers
            if answer.importance == ProfileImportance.REQUIRED
        )
        return TranslatedHunterProfile(
            original=profile,
            dimensions=dimensions,
            constraints=constraints,
            completeness=(
                ProfileCompleteness.COMPLETE if not missing else ProfileCompleteness.INCOMPLETE
            ),
            missing_fields=missing,
            translator_version=self.version,
        )
