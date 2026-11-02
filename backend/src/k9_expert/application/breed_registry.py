from __future__ import annotations

from dataclasses import dataclass

from k9_expert.domain.breed_vocabulary import CAPTION_ALIASES, normalize
from k9_expert.infrastructure.sqlite import DocumentRepository, SnapshotRepository


@dataclass(frozen=True, slots=True)
class RegisteredBreed:
    name: str
    group: str | None
    fragment_count: int


class BreedRegistry:
    """Breeds of the active snapshot, derived from its classified fragments.

    The registry changes only through snapshot publication, so it is cached per snapshot id.
    """

    def __init__(self, documents: DocumentRepository, snapshots: SnapshotRepository) -> None:
        self.documents, self.snapshots = documents, snapshots
        self._cached: tuple[str, tuple[RegisteredBreed, ...]] | None = None

    def breeds(self) -> tuple[RegisteredBreed, ...]:
        snapshot = self.documents.active_snapshot_id()
        if snapshot is None:
            return ()
        if self._cached is None or self._cached[0] != snapshot:
            breeds = tuple(
                RegisteredBreed(str(row["breed"]), row["breed_group"], int(row["fragments"]))
                for row in self.snapshots.breed_registry(snapshot)
            )
            self._cached = (snapshot, breeds)
        return self._cached[1]

    def names(self) -> list[str]:
        return [breed.name for breed in self.breeds()]

    def resolve(self, name: str) -> str | None:
        """Registered canonical name for a user-supplied name: normalized match, or a curated
        alias ("labrador" → "Retriever del Labrador")."""
        key = normalize(name)
        known = {normalize(breed): breed for breed in self.names()}
        if key in known:
            return known[key]
        alias = CAPTION_ALIASES.get(key)
        return known.get(normalize(alias)) if alias else None
