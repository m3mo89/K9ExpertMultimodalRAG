from __future__ import annotations

from collections.abc import Mapping

from k9_expert.domain.models import RouteDecision


class ComplexityRouter:
    def __init__(self, policy_version: str = "router-v1") -> None:
        self.policy_version = policy_version

    def route(self, features: Mapping[str, object]) -> RouteDecision:
        def count(name: str) -> int:
            value = features.get(name, 0)
            return value if isinstance(value, int) and not isinstance(value, bool) else 0

        complex_reasons = (
            (bool(features.get("reformulated")), "agent_reformulation"),
            (count("candidate_count") > 2, "multiple_candidates"),
            (count("criterion_count") > 3, "multiple_criteria"),
            (count("evidence_count") > 6, "large_evidence_set"),
        )
        reason = next((name for matched, name in complex_reasons if matched), None)
        return RouteDecision(
            "complex" if reason else "simple",
            reason or "bounded_request",
            self.policy_version,
        )
