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
    assert chunks[0].classification.breed is None
    assert chunks[0].content_hash != chunks[1].content_hash


def test_encyclopedia_golden_pages_preserve_direct_text_ocr_selection_and_page_links() -> None:
    source = Path("docs/references/enciclopedia-perros-caza.pdf")
    pages = PdfExtractor().extract(source)
    assert len(pages) == 243
    assert "Enciclopedia de los perros de caza" in pages[0].text
    assert OcrPolicy().decide(pages[1]).required is True
    structured = HeadingDetector().structure([pages[9]])
    chunks = PageAwareChunker(max_tokens=80, overlap_tokens=10).chunk(structured)
    assert chunks
    assert all(chunk.covered_pages == (10,) for chunk in chunks)


def test_typographic_headings_and_section_chunks_name_their_topic() -> None:
    def block(text: str, font: str = "Body-Regular", bold: bool = False) -> TextBlock:
        return TextBlock(text, 0, 0, 10, 10, font, bold, "Italic" in font)

    body = "Con un nacimiento alto y enroscada sobre el lomo, nunca ha de llevarse de lado."
    page = ExtractedPage(
        physical_page=29,
        width=100,
        height=100,
        text="",
        blocks=(
            block("PERROS DE CAZA NÓRDICOS", "Title-Bold", bold=True),
            block("Norsk elghund", "Title-Italic"),
            block("Cola"),
            block(body),
            block("2. Saltar con la piel de cobro."),
            block("Ejemplar de norsk elghund gris."),
        ),
        non_whitespace_characters=200,
        token_count=40,
    )
    structured = HeadingDetector().structure([page])
    assert [item.section_path for item in structured] == [
        ("Perros de caza nórdicos", "Norsk elghund", "Cola")
    ] * 3
    [chunk] = PageAwareChunker().chunk(structured)
    assert chunk.text.startswith("Perros de caza nórdicos › Norsk elghund › Cola\n")
    assert chunk.chunking_version == "page-section-v3-classified"
    assert chunk.classification.breed == "Norsk elghund"
    assert chunk.classification.breed_group is None
    assert chunk.classification.section == "morfologia:cola"


def test_encyclopedia_golden_structure_keeps_breed_context() -> None:
    pages = PdfExtractor().extract(Path("docs/references/enciclopedia-perros-caza.pdf"))
    chunks = PageAwareChunker().chunk(HeadingDetector().structure(pages))
    by_text = {chunk.text.split("\n", 1)[-1][:40]: chunk for chunk in chunks}
    tail = next(c for c in chunks if "enroscada sobre el lomo" in c.text)
    assert tail.covered_pages == (29,)
    assert tail.section_path == ("Perros de caza nórdicos", "Norsk elghund", "Cola")
    ear = next(c for c in chunks if "espigas dentro del oído" in c.text)
    assert ear.covered_pages == (236,) and ear.section_path[0] == "Indicaciones prácticas"
    assert not any(path.endswith(".") for c in chunks for path in c.section_path)
    assert len(by_text) > 600
