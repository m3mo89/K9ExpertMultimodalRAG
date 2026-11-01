from pathlib import Path

import fitz

from k9_expert.infrastructure.extraction import OcrPolicy, PdfExtractor


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
