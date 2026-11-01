from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz  # type: ignore[import-untyped]


@dataclass(frozen=True, slots=True)
class TextBlock:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    physical_page: int
    width: float
    height: float
    text: str
    blocks: tuple[TextBlock, ...]
    non_whitespace_characters: int
    token_count: int
    extraction_method: str = "direct"


@dataclass(frozen=True, slots=True)
class OcrDecision:
    required: bool
    reason: str | None


class PdfExtractor:
    version = "pymupdf-direct-v1"

    def extract(self, path: Path) -> list[ExtractedPage]:
        document = fitz.open(path)
        try:
            pages: list[ExtractedPage] = []
            for index, page in enumerate(document):
                raw_blocks = page.get_text("blocks")
                blocks = tuple(
                    TextBlock(
                        text=block[4].strip(), x0=block[0], y0=block[1], x1=block[2], y1=block[3]
                    )
                    for block in raw_blocks
                    if block[4].strip()
                )
                text = "\n".join(block.text for block in blocks)
                compact = " ".join(text.split())
                pages.append(
                    ExtractedPage(
                        physical_page=index + 1,
                        width=page.rect.width,
                        height=page.rect.height,
                        text=text,
                        blocks=blocks,
                        non_whitespace_characters=len("".join(text.split())),
                        token_count=len(compact.split()),
                    )
                )
            return pages
        finally:
            document.close()


class OcrPolicy:
    def __init__(self, min_characters: int = 40, min_tokens: int = 8) -> None:
        self.min_characters = min_characters
        self.min_tokens = min_tokens

    def decide(self, page: ExtractedPage) -> OcrDecision:
        if page.non_whitespace_characters < self.min_characters:
            return OcrDecision(True, "low_text_characters")
        if page.token_count < self.min_tokens:
            return OcrDecision(True, "low_text_tokens")
        return OcrDecision(False, None)
