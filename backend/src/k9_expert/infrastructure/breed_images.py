"""Breed photos from the managed PDFs, identified by the caption printed under each photo."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import fitz  # type: ignore[import-untyped]

from k9_expert.domain.breed_vocabulary import caption_breed

# A caption starts at most this many points below its photo.
CAPTION_GAP = 40


@dataclass(frozen=True, slots=True)
class BreedPhoto:
    page: int
    caption: str
    bbox: tuple[float, float, float, float]


class PdfBreedImages:
    """Indexes each PDF's captioned photos once per process; rendered photos are cached on disk
    as PNG. Captions are matched against the breed registry at lookup, so breeds discovered
    later need no rescan."""

    def __init__(self, cache_root: Path, dpi: int = 96) -> None:
        self.cache_root = cache_root
        self.dpi = dpi
        self._index: dict[str, list[BreedPhoto]] = {}

    def find(self, pdf_path: str, breed: str, breeds: Iterable[str]) -> BreedPhoto | None:
        """First photo, in page order, whose caption names `breed` rather than a longer
        registered name (a "Basset hound" caption is not a photo of "Basset")."""
        if pdf_path not in self._index:
            self._index[pdf_path] = self._scan(pdf_path)
        names = {*breeds, breed}
        return next(
            (photo for photo in self._index[pdf_path]
             if caption_breed(photo.caption, names) == breed),
            None,
        )

    def render(self, pdf_path: str, photo: BreedPhoto) -> bytes:
        key = hashlib.sha256(f"{pdf_path}:{photo.page}:{photo.bbox}:{self.dpi}".encode())
        cached = self.cache_root / f"{key.hexdigest()}.png"
        if cached.is_file():
            return cached.read_bytes()
        with fitz.open(pdf_path) as document:
            pixmap = document[photo.page - 1].get_pixmap(
                clip=fitz.Rect(photo.bbox), dpi=self.dpi
            )
            data: bytes = pixmap.tobytes("png")
        self.cache_root.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(data)
        return data

    @staticmethod
    def _scan(pdf_path: str) -> list[BreedPhoto]:
        """Every photo with a caption printed just below it, in page order."""
        found: list[BreedPhoto] = []
        with fitz.open(pdf_path) as document:
            for number, page in enumerate(document, start=1):
                images = page.get_image_info()
                if not images:
                    continue
                blocks = page.get_text("blocks")
                for image in images:
                    x0, y0, x1, y1 = image["bbox"]
                    below = sorted(
                        (block for block in blocks if y1 - 2 <= block[1] <= y1 + CAPTION_GAP),
                        key=lambda block: block[1],
                    )
                    if below:
                        caption = " ".join(str(below[0][4]).split())
                        found.append(BreedPhoto(number, caption, (x0, y0, x1, y1)))
        return found
