from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from k9_expert.domain.models import (
    BreedAssertion,
    BreedAttributeProfile,
    SnapshotId,
    StructuredBreedProfile,
)
from k9_expert.infrastructure.sqlite import StructuredKnowledgeRepository


class StructuredBreedProfileService:
    def __init__(self, repository: StructuredKnowledgeRepository) -> None:
        self.repository = repository

    def profile(self, snapshot_id: str, breed: str) -> StructuredBreedProfile:
        assertions = self.repository.eligible(snapshot_id, breed)
        by_attribute: dict[str, list[BreedAssertion]] = defaultdict(list)
        for assertion in assertions:
            by_attribute[assertion.attribute_key].append(assertion)
        attributes = []
        for key, values in sorted(by_attribute.items()):
            positions = {(item.value, item.polarity) for item in values}
            conflicting = any(
                value == other_value and polarity != other_polarity
                for value, polarity in positions
                for other_value, other_polarity in positions
            )
            attributes.append(BreedAttributeProfile(
                key, tuple(values), "conflicting" if conflicting else "documented"
            ))
        policy = assertions[0].policy_version if assertions else "structured-knowledge-v2"
        return StructuredBreedProfile(
            breed, SnapshotId(UUID(snapshot_id)), tuple(attributes), policy
        )

    def attribute(
        self, snapshot_id: str, breed: str, key: str
    ) -> BreedAttributeProfile:
        profile = self.profile(snapshot_id, breed)
        return next(
            (item for item in profile.attributes if item.key == key),
            BreedAttributeProfile(key, (), "unknown"),
        )
