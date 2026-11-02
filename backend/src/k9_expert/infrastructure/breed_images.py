"""Breed photos from the managed PDFs, identified by the caption printed under each photo."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import fitz  # type: ignore[import-untyped]

from k9_expert.domain.breed_vocabulary import breed_for_caption

# A caption starts at most this many points below its photo.
CAPTION_GAP = 40


@dataclass(frozen=True, slots=True)
class BreedPhoto:
    page: int
    caption: str
    bbox: tuple[float, float, float, float]


class PdfBreedImages:
    """Indexes each PDF once per process; rendered photos are cached on disk as PNG."""

    def __init__(self, cache_root: Path, dpi: int = 96) -> None:
        self.cache_root = cache_root
        self.dpi = dpi
        self._index: dict[str, dict[str, BreedPhoto]] = {}

    def find(self, pdf_path: str, breed: str) -> BreedPhoto | None:
        if pdf_path not in self._index:
            self._index[pdf_path] = self._scan(pdf_path)
        return self._index[pdf_path].get(breed)

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
    def _scan(pdf_path: str) -> dict[str, BreedPhoto]:
        """First captioned photo of each breed in page order."""
        found: dict[str, BreedPhoto] = {}
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
                    if not below:
                        continue
                    caption = " ".join(str(below[0][4]).split())
                    breed = breed_for_caption(caption)
                    if breed is not None and breed not in found:
                        found[breed] = BreedPhoto(number, caption, (x0, y0, x1, y1))
        return found
