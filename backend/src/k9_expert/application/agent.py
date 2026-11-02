from __future__ import annotations

from k9_expert.domain.models import Evidence


class DomainPreservingReformulator:
    """Clarifies documentary domain without changing immutable request filters."""

    version = "domain-reformulation-v1"

    def __call__(self, text: str, _evidence: list[Evidence]) -> str:
        normalized = " ".join(text.split())
        prefix = "Información documental sobre razas y perros de caza: "
        return normalized if normalized.lower().startswith(prefix.lower()) else prefix + normalized
