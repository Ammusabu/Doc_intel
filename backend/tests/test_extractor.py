"""Extractor tests — real TXT and DOCX round-trips."""
from pathlib import Path

from app.services.extractor import extract, extract_docx, extract_txt, mime_from_filename

FIX = Path(__file__).parent / "fixtures"


def test_mime_from_filename():
    assert mime_from_filename("a.pdf") == "application/pdf"
    assert mime_from_filename("b.DOCX") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert mime_from_filename("c.txt") == "text/plain"
    assert mime_from_filename("d.xyz") is None


def test_extract_txt_one_page():
    data = (FIX / "sample.txt").read_bytes()
    pages = extract_txt(data)
    assert len(pages) == 1
    assert pages[0][0] == 1
    assert "graphics card" in pages[0][1].lower()


def test_extract_docx_paragraphs_as_pages():
    data = (FIX / "sample.docx").read_bytes()
    pages = extract_docx(data)
    assert len(pages) >= 2
    assert all(pnum > 0 for pnum, _ in pages)
    joined = " ".join(t for _, t in pages)
    assert "legal contract" in joined.lower()


def test_extract_dispatches_by_mime():
    data = (FIX / "sample.txt").read_bytes()
    pages = extract(data, "text/plain")
    assert len(pages) == 1
