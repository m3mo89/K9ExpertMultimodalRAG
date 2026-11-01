from pathlib import Path

import fitz
import pytest

from k9_expert.domain.errors import OcrUnavailableError
from k9_expert.infrastructure.extraction import (
    ExtractedPage,
    ExtractionCache,
    OcrPolicy,
    OcrResult,
    PdfExtractor,
    TesseractOcrAdapter,
    TextBlock,
)
from k9_expert.infrastructure.structuring import HeadingDetector, PageAwareChunker


def fixture_pdf(path: Path) -> None:
    document = fitz.open()
    text_page = document.new_page()
    text_page.insert_text(
        (72, 72), "El teckel tiene un tronco alargado y una cabeza bien cincelada."
    )
    document.new_page()
    document.save(path)
    document.close()


def test_extractor_preserves_page_geometry_blocks_and_quality(tmp_path: Path) -> None:
    path = tmp_path / "source.pdf"
    fixture_pdf(path)
    pages = PdfExtractor().extract(path)
    assert len(pages) == 2
    assert pages[0].physical_page == 1
    assert pages[0].width > 0 and pages[0].height > 0
    assert pages[0].blocks and "teckel" in pages[0].text
    assert pages[0].token_count > 8


def test_ocr_policy_only_flags_low_text_pages(tmp_path: Path) -> None:
    path = tmp_path / "source.pdf"
    fixture_pdf(path)
    text_page, blank_page = PdfExtractor().extract(path)
    policy = OcrPolicy()
    assert policy.decide(text_page).required is False
    blank_decision = policy.decide(blank_page)
    assert blank_decision.required is True
    assert blank_decision.reason == "low_text_characters"


def test_ocr_adapter_reports_missing_local_engine_with_typed_error(tmp_path: Path) -> None:
    path = tmp_path / "source.pdf"
    fixture_pdf(path)
    with pytest.raises(OcrUnavailableError) as error:
        TesseractOcrAdapter(executable="definitely-not-tesseract").extract_page(path, 1)
    assert error.value.code == "ocr_unavailable"


def test_ocr_adapter_rejects_pages_outside_the_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "source.pdf"
    fixture_pdf(path)
    monkeypatch.setattr(
        "k9_expert.infrastructure.extraction.shutil.which", lambda _: "/usr/bin/tesseract"
    )
    with pytest.raises(Exception, match="no existe"):
        TesseractOcrAdapter().extract_page(path, 99)


def test_extraction_cache_binds_keys_to_content_tool_and_configuration(tmp_path: Path) -> None:
    path = tmp_path / "source.pdf"
    fixture_pdf(path)
    pages = PdfExtractor().extract(path)
    cache = ExtractionCache(tmp_path / "cache")
    key = cache.key("content-hash", PdfExtractor.version, "min_tokens=8")
    assert key != cache.key("content-hash", PdfExtractor.version, "min_tokens=9")
    cache.set_pages(key, pages)
    assert cache.get_pages(key) == pages

    ocr_key = cache.key("content-hash", "tesseract 5.0", "spa:200")
    ocr = OcrResult("Teckel", "spa", "tesseract 5.0", 200, 1)
    cache.set_ocr(ocr_key, ocr)
    assert cache.get_ocr(ocr_key) == ocr


def test_heading_detection_and_page_aware_chunks_preserve_provenance() -> None:
    page = ExtractedPage(
        physical_page=7,
        width=100,
        height=100,
        text="",
        blocks=(
            TextBlock("2. Cuidados", 0, 0, 20, 10),
            TextBlock("El teckel requiere ejercicio moderado.", 0, 10, 80, 20),
        ),
        non_whitespace_characters=30,
        token_count=5,
    )
    structured = HeadingDetector().structure([page])
    assert structured[0].section_path == ("Cuidados",)
    chunks = PageAwareChunker(max_tokens=3, overlap_tokens=1).chunk(structured)
    assert chunks[0].covered_pages == (7,)
    assert chunks[0].section_path == ("Cuidados",)
    assert chunks[0].content_hash != chunks[1].content_hash
