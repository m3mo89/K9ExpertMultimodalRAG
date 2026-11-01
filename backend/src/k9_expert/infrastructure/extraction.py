from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

import fitz  # type: ignore[import-untyped]

from k9_expert.domain.errors import OcrExecutionError, OcrTimeoutError, OcrUnavailableError


@dataclass(frozen=True, slots=True)
class TextBlock:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    # Dominant font of the block, used to recognise typographic headings.
    font: str = ""
    bold: bool = False
    italic: bool = False


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


@dataclass(frozen=True, slots=True)
class OcrResult:
    text: str
    language: str
    engine_version: str
    dpi: int
    physical_page: int
    extraction_method: str = "tesseract-ocr"


class ExtractionCache:
    """Small, rebuildable file cache; keys bind content, tool and configuration versions."""

    def __init__(self, root: Path) -> None:
        self.root = root

    @staticmethod
    def key(content_hash: str, tool_version: str, configuration: str = "") -> str:
        source = f"{content_hash}:{tool_version}:{configuration}".encode()
        return hashlib.sha256(source).hexdigest()

    def get_pages(self, key: str) -> list[ExtractedPage] | None:
        payload = self._read(key)
        if payload is None or payload.get("kind") != "pages":
            return None
        raw_pages = payload.get("pages")
        if not isinstance(raw_pages, list):
            return None
        return [_page_from_json(cast(dict[str, object], page)) for page in raw_pages]

    def set_pages(self, key: str, pages: list[ExtractedPage]) -> None:
        self._write(key, {"kind": "pages", "pages": [_page_to_json(page) for page in pages]})

    def get_ocr(self, key: str) -> OcrResult | None:
        payload = self._read(key)
        if payload is None or payload.get("kind") != "ocr":
            return None
        result = payload.get("result")
        if not isinstance(result, dict):
            return None
        return _ocr_from_json(cast(dict[str, object], result))

    def set_ocr(self, key: str, result: OcrResult) -> None:
        self._write(key, {"kind": "ocr", "result": _ocr_to_json(result)})

    def _read(self, key: str) -> dict[str, object] | None:
        path = self.root / f"{key}.json"
        try:
            with path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
                return cast(dict[str, object], payload) if isinstance(payload, dict) else None
        except FileNotFoundError:
            return None

    def _write(self, key: str, payload: dict[str, object]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        destination = self.root / f"{key}.json"
        temporary = destination.with_suffix(".partial")
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
        os.replace(temporary, destination)


def _page_to_json(page: ExtractedPage) -> dict[str, object]:
    return {
        "physical_page": page.physical_page,
        "width": page.width,
        "height": page.height,
        "text": page.text,
        "blocks": [asdict(block) for block in page.blocks],
        "non_whitespace_characters": page.non_whitespace_characters,
        "token_count": page.token_count,
        "extraction_method": page.extraction_method,
    }


def _page_from_json(data: dict[str, object]) -> ExtractedPage:
    raw_blocks = data["blocks"]
    if not isinstance(raw_blocks, list):
        raise ValueError("invalid_cached_pages")
    blocks = tuple(
        TextBlock(
            text=str(block["text"]),
            x0=float(block["x0"]),
            y0=float(block["y0"]),
            x1=float(block["x1"]),
            y1=float(block["y1"]),
            font=str(block.get("font", "")),
            bold=bool(block.get("bold", False)),
            italic=bool(block.get("italic", False)),
        )
        for block in cast(list[dict[str, Any]], raw_blocks)
        if isinstance(block, dict)
    )
    return ExtractedPage(
        physical_page=int(str(data["physical_page"])),
        width=float(str(data["width"])),
        height=float(str(data["height"])),
        text=str(data["text"]),
        blocks=blocks,
        non_whitespace_characters=int(str(data["non_whitespace_characters"])),
        token_count=int(str(data["token_count"])),
        extraction_method=str(data["extraction_method"]),
    )


def _ocr_to_json(result: OcrResult) -> dict[str, object]:
    return {
        "text": result.text,
        "language": result.language,
        "engine_version": result.engine_version,
        "dpi": result.dpi,
        "physical_page": result.physical_page,
        "extraction_method": result.extraction_method,
    }


def _ocr_from_json(data: dict[str, object]) -> OcrResult:
    return OcrResult(
        text=str(data["text"]),
        language=str(data["language"]),
        engine_version=str(data["engine_version"]),
        dpi=int(str(data["dpi"])),
        physical_page=int(str(data["physical_page"])),
        extraction_method=str(data["extraction_method"]),
    )


class PdfExtractor:
    version = "pymupdf-direct-v2"

    def extract(self, path: Path) -> list[ExtractedPage]:
        document = fitz.open(path)
        try:
            pages: list[ExtractedPage] = []
            for index, page in enumerate(document):
                raw = page.get_text("dict")["blocks"]
                blocks = tuple(
                    block for block in (_text_block(item) for item in raw) if block is not None
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

    def extract_path(self, path: str) -> list[ExtractedPage]:
        return self.extract(Path(path))


def _text_block(raw: dict[str, object]) -> TextBlock | None:
    """Text of one PyMuPDF dict block plus the font covering most of its characters."""
    if raw.get("type") != 0:
        return None
    lines: list[str] = []
    weight: dict[tuple[str, bool, bool], int] = {}
    for line in cast(list[dict[str, object]], raw.get("lines", [])):
        spans = cast(list[dict[str, object]], line.get("spans", []))
        lines.append("".join(str(span["text"]) for span in spans))
        for span in spans:
            font, flags = str(span["font"]), int(cast(int, span["flags"]))
            key = (font, bool(flags & 16) or "Bold" in font, bool(flags & 2) or "Italic" in font)
            weight[key] = weight.get(key, 0) + len(str(span["text"]).strip())
    text = "\n".join(lines).strip()
    if not text:
        return None
    font, bold, italic = max(weight, key=lambda key: weight[key]) if weight else ("", False, False)
    x0, y0, x1, y1 = cast(tuple[float, float, float, float], raw["bbox"])
    return TextBlock(text, x0, y0, x1, y1, font, bold, italic)


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


class TesseractOcrAdapter:
    """Local OCR adapter that bounds raster resources before invoking Tesseract."""

    extraction_version = "tesseract-ocr-v1"

    def __init__(
        self,
        executable: str = "tesseract",
        language: str = "spa",
        dpi: int = 200,
        timeout_seconds: float = 30.0,
        max_pixels: int = 16_000_000,
    ) -> None:
        self.executable = executable
        self.language = language
        self.dpi = dpi
        self.timeout_seconds = timeout_seconds
        self.max_pixels = max_pixels

    def extract_page(self, pdf_path: Path, physical_page: int) -> OcrResult:
        if shutil.which(self.executable) is None:
            raise OcrUnavailableError(f"No se encontró el ejecutable OCR: {self.executable}")
        if physical_page < 1:
            raise OcrExecutionError("La página física debe ser mayor que cero.")
        document = fitz.open(pdf_path)
        try:
            if physical_page > document.page_count:
                raise OcrExecutionError("La página física no existe en el PDF.")
            page = document[physical_page - 1]
            scale = self.dpi / 72
            matrix = fitz.Matrix(scale, scale)
            pixels = int(page.rect.width * scale) * int(page.rect.height * scale)
            if pixels > self.max_pixels:
                raise OcrExecutionError("La rasterización OCR excede el límite de píxeles.")
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            with tempfile.TemporaryDirectory(prefix="k9-ocr-") as temporary:
                image_path = Path(temporary) / "page.png"
                pixmap.save(image_path)
                return self._run(image_path, physical_page)
        finally:
            document.close()

    def _run(self, image_path: Path, physical_page: int) -> OcrResult:
        command = [self.executable, str(image_path), "stdout", "-l", self.language]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            raise OcrTimeoutError() from error
        except OSError as error:
            raise OcrUnavailableError(str(error)) from error
        if completed.returncode != 0:
            detail = completed.stderr.strip() or "Tesseract devolvió un error."
            raise OcrExecutionError(detail)
        text = completed.stdout.strip()
        if not text:
            raise OcrExecutionError("El OCR no devolvió texto utilizable.")
        return OcrResult(
            text=text,
            language=self.language,
            engine_version=self.engine_version(),
            dpi=self.dpi,
            physical_page=physical_page,
        )

    def engine_version(self) -> str:
        try:
            completed = subprocess.run(
                [self.executable, "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise OcrUnavailableError() from error
        if completed.returncode != 0:
            raise OcrUnavailableError(completed.stderr.strip() or "Tesseract no responde.")
        return completed.stdout.splitlines()[0]
