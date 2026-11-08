"""Render the audited Markdown report to a styled DOCX.

The Markdown remains the reviewable source of truth.  The renderer intentionally
supports only the constructs used by that source: headings, paragraphs, block
quotes, pipe tables, lists, fenced code and local images.
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/deliverables/final/K9-BreedMatch-Informe-Tecnico.md"
OUTPUT = ROOT / "docs/deliverables/final/K9-BreedMatch-Informe-Tecnico.docx"
NAVY = "17324D"
BLUE = "1E6A78"


def shade(cell, color: str) -> None:
    props = cell._tc.get_or_add_tcPr()
    node = OxmlElement("w:shd")
    node.set(qn("w:fill"), color)
    props.append(node)


def repeat_header(row) -> None:
    props = row._tr.get_or_add_trPr()
    node = OxmlElement("w:tblHeader")
    node.set(qn("w:val"), "true")
    props.append(node)


def page_field(paragraph) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, end])


def toc(paragraph) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = ' TOC \\o "1-3" \\h \\z \\u '
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "Actualice el índice en Word (clic derecho → Actualizar campo)."
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, separate, text, end])


def add_inline(paragraph, text: str) -> None:
    # Minimal inline rendering for bold and code.
    for part in re.split(r"(`[^`]+`|\*\*[^*]+\*\*)", text):
        if not part:
            continue
        if part.startswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Aptos Mono"
            run.font.size = Pt(8)
            run.font.color.rgb = RGBColor.from_string("7A3030")
        elif part.startswith("**"):
            paragraph.add_run(part[2:-2]).bold = True
        else:
            paragraph.add_run(part)


def split_row(line: str) -> list[str]:
    return [item.strip() for item in line.strip().strip("|").split("|")]


def render() -> None:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin, sec.bottom_margin = Inches(.78), Inches(.72)
    sec.left_margin, sec.right_margin = Inches(.82), Inches(.78)
    styles = doc.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(10)
    styles["Normal"].paragraph_format.space_after = Pt(6)
    styles["Normal"].paragraph_format.line_spacing = 1.12
    for name, size, color in (("Title", 27, NAVY), ("Heading 1", 17, NAVY),
                              ("Heading 2", 13, BLUE), ("Heading 3", 11, "2A7B69")):
        styles[name].font.name = "Aptos Display"
        styles[name].font.size = Pt(size)
        styles[name].font.color.rgb = RGBColor.from_string(color)
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("K9 BreedMatch · Informe técnico · ")
    page_field(footer)

    # Cover is authored from the first metadata block for predictable layout.
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("K9 BREEDMATCH").bold = True
    p.runs[0].font.size = Pt(15)
    doc.add_paragraph("\n")
    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run("Arquitectura local en capas para la recomendación explicable de razas de perros de caza mediante embeddings y RAG")
    doc.add_paragraph("\n")
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run("Guillermo Tinoco Ramos\nUniversidad Politécnica de Chiapas\nTópicos Selectos de Arquitectura de Software\n7 de noviembre de 2026\n\nCommit auditado: ec5fe0bf5fce63067175816d05697643de3f1e6f")
    note = doc.add_paragraph("No se consigna docente porque el dato no está disponible en las fuentes.")
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    note.runs[0].italic = True
    doc.add_page_break()
    doc.add_heading("Índice", 1)
    toc(doc.add_paragraph())
    doc.add_page_break()

    # Skip the source cover through the first Summary heading.
    i = next(idx for idx, value in enumerate(lines) if value == "## Resumen")
    in_code = False
    code_lines: list[str] = []
    figure_number = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            if not in_code:
                in_code = True
                code_lines = []
            else:
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Inches(.25)
                r = p.add_run("\n".join(code_lines))
                r.font.name = "Aptos Mono"
                r.font.size = Pt(7.5)
                shade_dummy = OxmlElement("w:shd")
                shade_dummy.set(qn("w:fill"), "F2F4F6")
                p._p.get_or_add_pPr().append(shade_dummy)
                in_code = False
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue
        if not line.strip():
            i += 1
            continue
        image = re.fullmatch(r"!\[(.+)]\((.+)\)", line)
        if image:
            image_path = (SOURCE.parent / image.group(2)).resolve()
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            with Image.open(image_path) as bitmap:
                ratio = bitmap.width / bitmap.height
            max_width, max_height = 6.45, 7.25
            width = min(max_width, max_height * ratio)
            p.add_run().add_picture(str(image_path), width=Inches(width))
            figure_number += 1
            cap = doc.add_paragraph(image.group(1), style="Caption")
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            i += 1
            continue
        if line.startswith("#"):
            marks, text = line.split(" ", 1)
            level = min(len(marks) - 1, 3)
            if level == 1 and text.startswith(("5.", "7.", "9.", "12.")):
                doc.add_page_break()
            if text.startswith("12.5 "):
                doc.add_page_break()
            doc.add_heading(text, level=max(1, level))
            i += 1
            continue
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?\s*:?-+", lines[i + 1]):
            headers = split_row(line)
            i += 2
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            table = doc.add_table(rows=1, cols=len(headers))
            table.style = "Light Shading Accent 1"
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = True
            for col, value in enumerate(headers):
                table.cell(0, col).text = value
                shade(table.cell(0, col), NAVY)
                for run in table.cell(0, col).paragraphs[0].runs:
                    run.font.color.rgb = RGBColor(255, 255, 255)
                    run.bold = True
                    run.font.size = Pt(7.5)
            repeat_header(table.rows[0])
            for row in rows:
                cells = table.add_row().cells
                for col in range(len(headers)):
                    value = row[col] if col < len(row) else ""
                    cells[col].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                    cells[col].text = value.replace("**", "").replace("`", "")
                    for paragraph in cells[col].paragraphs:
                        for run in paragraph.runs:
                            run.font.size = Pt(7.2)
            doc.add_paragraph()
            continue
        if line.startswith("- ") or re.match(r"^\d+\. ", line):
            style = "List Bullet" if line.startswith("- ") else "List Number"
            text = re.sub(r"^(?:- |\d+\. )", "", line)
            p = doc.add_paragraph(style=style)
            add_inline(p, text)
            i += 1
            continue
        if line.startswith("> "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(.3)
            p.paragraph_format.right_indent = Inches(.2)
            r = p.add_run(line[2:])
            r.italic = True
            i += 1
            continue
        p = doc.add_paragraph()
        add_inline(p, line)
        i += 1

    settings = doc.settings._element
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    settings.append(update)
    core = doc.core_properties
    core.title = "K9 BreedMatch — Informe técnico conforme a rúbrica"
    core.author = "Guillermo Tinoco Ramos"
    core.subject = "Arquitectura de software, RAG y recomendación explicable"
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    render()
