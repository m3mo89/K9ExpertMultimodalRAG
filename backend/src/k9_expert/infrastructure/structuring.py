from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import groupby

from k9_expert.domain.breed_vocabulary import BreedClassification, classify_section
from k9_expert.infrastructure.extraction import ExtractedPage, TextBlock


@dataclass(frozen=True, slots=True)
class StructuredBlock:
    physical_page: int
    text: str
    section_path: tuple[str, ...]


CHUNKING_VERSION = "page-section-v3-classified"


@dataclass(frozen=True, slots=True)
class Chunk:
    content_hash: str
    ordinal: int
    text: str
    section_path: tuple[str, ...]
    covered_pages: tuple[int, ...]
    token_estimate: int
    classification: BreedClassification
    chunking_version: str = CHUNKING_VERSION


class HeadingDetector:
    """Recognises explicit headings only: numbered, typographic, or short subheadings.

    Typographic headings use a font family other than the document's dominant body font:
    bold ones open a level-1 section, others a level-2 topic. A short unpunctuated body-font
    line directly followed by a paragraph is a level-3 subheading. Nothing here claims
    breed metadata; section names are recorded as found.
    """

    _numbered = re.compile(r"^(\d+(?:\.\d+)*)[.)]?\s+(.+)$")

    def structure(self, pages: Iterable[ExtractedPage]) -> list[StructuredBlock]:
        page_list = list(pages)
        body = _body_family(page_list)
        path: list[tuple[int, str]] = []
        blocks: list[StructuredBlock] = []
        for page in page_list:
            for index, block in enumerate(page.blocks):
                following = page.blocks[index + 1] if index + 1 < len(page.blocks) else None
                heading = self._heading(block, body, following)
                if heading is not None:
                    level, text = heading
                    path = [entry for entry in path if entry[0] < level] + [(level, text)]
                    continue
                if block.text:
                    section = tuple(text for _, text in path)
                    blocks.append(StructuredBlock(page.physical_page, block.text, section))
        return blocks

    def _heading(
        self, block: TextBlock, body: str | None, following: TextBlock | None
    ) -> tuple[int, str] | None:
        normalized = " ".join(block.text.split())
        words = normalized.split()
        if not words or len(words) > 10:
            return None
        # Captions, list items and figure notes end like sentences; headings do not.
        if normalized[-1] in ".,;:)»!?":
            return None
        numbered = self._numbered.match(normalized)
        if numbered and len(words) <= 8 and numbered.group(2)[0].isupper():
            return numbered.group(1).count(".") + 1, numbered.group(2)
        if any(char.isdigit() for char in normalized):
            return None
        title = normalized.capitalize() if normalized.isupper() else normalized
        if body is not None and block.font and _family(block.font) != body:
            return (1 if block.bold else 2), title
        if normalized.isupper() and any(char.isalpha() for char in normalized):
            return 1, title
        is_subheading = (
            len(words) <= 4
            and normalized[0].isupper()
            and following is not None
            and len(following.text.split()) > 8
        )
        return (3, normalized) if is_subheading else None


class PageAwareChunker:
    """Groups consecutive blocks of one page and section; each chunk names its section.

    The section header makes a passage self-describing ("… › Norsk elghund › Cola"), which
    retrieval needs because body text rarely repeats the breed name.
    """

    def __init__(self, max_tokens: int = 180, overlap_tokens: int = 24) -> None:
        if max_tokens < 1 or not 0 <= overlap_tokens < max_tokens:
            raise ValueError("invalid_chunking_limits")
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, blocks: Iterable[StructuredBlock]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for (page, section), group in groupby(
            blocks, key=lambda block: (block.physical_page, block.section_path)
        ):
            words = " ".join(block.text for block in group).split()
            header = " › ".join(section)
            start = 0
            while start < len(words):
                end = min(start + self.max_tokens, len(words))
                body = " ".join(words[start:end])
                text = f"{header}\n{body}" if header else body
                digest = hashlib.sha256(
                    f"{CHUNKING_VERSION}:{page}:{'/'.join(section)}:{text}".encode()
                ).hexdigest()
                chunks.append(
                    Chunk(
                        content_hash=digest,
                        ordinal=len(chunks) + 1,
                        text=text,
                        section_path=section,
                        covered_pages=(page,),
                        token_estimate=len(text.split()),
                        classification=classify_section(section),
                    )
                )
                if end == len(words):
                    break
                start = end - self.overlap_tokens
        return chunks


def _family(font: str) -> str:
    return font.split("-")[0].split(",")[0].lower()


def _body_family(pages: list[ExtractedPage]) -> str | None:
    weight: Counter[str] = Counter()
    for page in pages:
        for block in page.blocks:
            if block.font:
                weight[_family(block.font)] += len(block.text)
    return weight.most_common(1)[0][0] if weight else None
