from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from uuid import UUID

from k9_expert.domain.models import Citation, DocumentId, DocumentVersionId, FragmentId, SourceRef
from k9_expert.infrastructure.breed_images import BreedPhoto, PdfBreedImages
from k9_expert.infrastructure.sqlite import DocumentRepository, SnapshotRepository

# Sections shown first; any other documented section follows in reading order.
PREFERRED_SECTIONS = ("Historia", "Aspecto general", "El trabajo y las cualidades")
SECTION_CHARACTERS = 900
# Shorter bodies are stray headings or photo captions, not prose.
MINIMUM_SECTION_CHARACTERS = 40


@dataclass(frozen=True, slots=True)
class ProfileSection:
    heading: str
    text: str
    citation: Citation


@dataclass(frozen=True, slots=True)
class BreedProfile:
    breed: str
    sections: tuple[ProfileSection, ...]
    photo_caption: str | None = None
    photo_page: int | None = None


class BreedProfileService:
    """Breed sheet built only from the active corpus: book text per section and its photo.

    No model is involved; every paragraph carries the page it was taken from.
    """

    def __init__(
        self, documents: DocumentRepository, snapshots: SnapshotRepository, images: PdfBreedImages
    ) -> None:
        self.documents, self.snapshots, self.images = documents, snapshots, images

    def profile(self, breed: str) -> BreedProfile:
        rows = self._rows(breed)
        grouped: dict[str, list[sqlite3.Row]] = {}
        for row in rows:
            path = [part for part in str(row["section_path"]).split("/") if part]
            heading = path[-1] if path and path[-1] != breed else "Presentación"
            grouped.setdefault(heading, []).append(row)
        ordered = sorted(
            grouped,
            key=lambda name: (
                PREFERRED_SECTIONS.index(name) if name in PREFERRED_SECTIONS else 99
            ),
        )
        sections = tuple(
            section for section in (self._section(name, grouped[name]) for name in ordered)
            if len(section.text) >= MINIMUM_SECTION_CHARACTERS
        )
        photo = self._photo(breed, rows)
        return BreedProfile(
            breed, sections,
            photo[1].caption if photo else None, photo[1].page if photo else None,
        )

    def photo(self, breed: str) -> bytes | None:
        found = self._photo(breed, self._rows(breed))
        return self.images.render(found[0], found[1]) if found else None

    def _rows(self, breed: str) -> list[sqlite3.Row]:
        snapshot = self.documents.active_snapshot_id()
        rows = self.snapshots.breed_fragments(snapshot, breed) if snapshot else []
        if not rows:
            raise KeyError("breed_not_found")
        return rows

    def _photo(
        self, breed: str, rows: list[sqlite3.Row]
    ) -> tuple[str, BreedPhoto] | None:
        for path in dict.fromkeys(str(row["file_path"]) for row in rows):
            found = self.images.find(path, breed)
            if found is not None:
                return path, found
        return None

    @staticmethod
    def _section(heading: str, rows: list[sqlite3.Row]) -> ProfileSection:
        # Fragment text starts with its section path; the body follows the first line.
        body = " ".join(str(row["text"]).partition("\n")[2].strip() for row in rows).strip()
        if len(body) > SECTION_CHARACTERS:
            body = body[:SECTION_CHARACTERS].rsplit(" ", 1)[0] + "…"
        first = rows[0]
        return ProfileSection(heading, body, Citation(
            FragmentId(UUID(str(first["id"]))),
            SourceRef(
                DocumentId(UUID(str(first["document_id"]))),
                DocumentVersionId(UUID(str(first["version_id"]))),
                str(first["title"]), first["author"], first["edition"],
                int(first["page_start"]), first["printed_page_label"],
            ),
        ))
