from __future__ import annotations

from typing import cast
from uuid import uuid4

from k9_expert.infrastructure.sqlite import (
    RecommendationContextRepository,
    RecommendationRepository,
)


class RecommendationContextService:
    """Creates immutable, evidence-bounded contexts from a persisted deterministic result."""

    def __init__(
        self, recommendations: RecommendationRepository, contexts: RecommendationContextRepository
    ) -> None:
        self.recommendations = recommendations
        self.contexts = contexts

    def create(self, recommendation_id: str, selected_breeds: list[str]) -> dict[str, object]:
        if not 1 <= len(selected_breeds) <= 3 or len(set(selected_breeds)) != len(selected_breeds):
            raise ValueError("context_breed_selection_invalid")
        result = self.recommendations.get(recommendation_id)
        candidates = result.get("candidates", [])
        if not isinstance(candidates, list):
            raise ValueError("recommendation_record_invalid")
        allowed_breeds = {
            str(candidate.get("breed")) for candidate in candidates if isinstance(candidate, dict)
        }
        if not set(selected_breeds).issubset(allowed_breeds):
            raise ValueError("context_breed_not_in_recommendation")
        evidence = [
            str(evidence_id)
            for candidate in candidates if isinstance(candidate, dict)
            and str(candidate.get("breed")) in selected_breeds
            for dimension in candidate.get("dimensions", []) if isinstance(dimension, dict)
            for evidence_id in dimension.get("evidence_ids", [])
        ]
        context_id = uuid4()
        self.contexts.save(
            context_id, recommendation_id, selected_breeds, list(dict.fromkeys(evidence))
        )
        return self.contexts.get(str(context_id))

    def answer(self, context_id: str, question: str) -> dict[str, object]:
        """Deterministic contextual explanation. It never invokes a model or recalculates rank."""
        context = self.contexts.get(context_id)
        if not question.strip():
            raise ValueError("context_question_required")
        lowered = question.lower()
        if any(term in lowered for term in ("cambiar", "prefiero", "más tiempo", "menos tiempo")):
            return {
                "status": "new_recommendation_required",
                "answer": "El cambio de preferencias requiere crear una nueva recomendación.",
                "bibliographic_evidence": [],
                "policy_inference": [],
                "generated_explanation": None,
            }
        record = self.recommendations.get(str(context["recommendation_id"]))
        selected = cast(list[object], context["selected_breeds"])
        candidates = [
            item for item in cast(list[object], record.get("candidates", []))
            if isinstance(item, dict) and item.get("breed") in selected
        ]
        inference = [
            {
                "breed": item.get("breed"),
                "band": item.get("band"),
                "coverage": item.get("coverage"),
                "penalties": item.get("penalties", []),
            }
            for item in candidates
        ]
        evidence = list(cast(list[object], context["allowed_evidence"]))
        names = ", ".join(str(item.get("breed")) for item in candidates)
        return {
            "status": "grounded",
            "answer": (
                f"Resultado determinista para {names}. Consulte el desglose y las fuentes citadas."
            ),
            "bibliographic_evidence": evidence,
            "policy_inference": inference,
            "generated_explanation": None,
        }
