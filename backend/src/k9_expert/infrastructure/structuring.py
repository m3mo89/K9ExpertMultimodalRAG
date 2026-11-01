from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass

from k9_expert.infrastructure.extraction import ExtractedPage


@dataclass(frozen=True, slots=True)
class StructuredBlock:
    physical_page: int
    text: str
    section_path: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Chunk:
    content_hash: str
    ordinal: int
    text: str
    section_path: tuple[str, ...]
    covered_pages: tuple[int, ...]
    token_estimate: int
    chunking_version: str = "page-aware-v1"


class HeadingDetector:
    """Conservatively recognises explicit numbered or typographic headings only."""

    _numbered = re.compile(r"^(\d+(?:\.\d+)*)[.)]?\s+(.+)$")

    def structure(self, pages: Iterable[ExtractedPage]) -> list[StructuredBlock]:
        path: list[str] = []
        blocks: list[StructuredBlock] = []
        for page in pages:
            for block in page.blocks:
                heading = self._heading(block.text)
                if heading is not None:
                    level, text = heading
                    path[level - 1 :] = [text]
                    continue
                if block.text:
                    blocks.append(StructuredBlock(page.physical_page, block.text, tuple(path)))
        return blocks

    def _heading(self, text: str) -> tuple[int, str] | None:
        normalized = " ".join(text.split())
        numbered = self._numbered.match(normalized)
        if numbered:
            return numbered.group(1).count(".") + 1, numbered.group(2)
        words = normalized.split()
        is_short_uppercase = 1 <= len(words) <= 10 and normalized.isupper()
        if is_short_uppercase and any(char.isalpha() for char in normalized):
            return 1, normalized.title()
        return None


class PageAwareChunker:
    def __init__(self, max_tokens: int = 180, overlap_tokens: int = 24) -> None:
        if max_tokens < 1 or not 0 <= overlap_tokens < max_tokens:
            raise ValueError("invalid_chunking_limits")
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, blocks: Iterable[StructuredBlock]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for block in blocks:
            words = block.text.split()
            start = 0
            while start < len(words):
                end = min(start + self.max_tokens, len(words))
                text = " ".join(words[start:end])
                ordinal = len(chunks) + 1
                digest = hashlib.sha256(
                    f"page-aware-v1:{block.physical_page}:{'/'.join(block.section_path)}:{text}".encode()
                ).hexdigest()
                chunks.append(
                    Chunk(
                        content_hash=digest,
                        ordinal=ordinal,
                        text=text,
                        section_path=block.section_path,
                        covered_pages=(block.physical_page,),
                        token_estimate=len(words[start:end]),
                    )
                )
                if end == len(words):
                    break
                start = end - self.overlap_tokens
        return chunks
