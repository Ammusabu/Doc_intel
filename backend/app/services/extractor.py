"""
Text extraction from PDF/DOCX/TXT.

Returns `list[tuple[page_number, text]]` — page-level metadata preserved.
- PDF: pypdf, one tuple per page.
- DOCX: python-docx, one tuple per paragraph — page boundary = paragraph boundary
  (DOCX has no reliable page concept without rendering; we treat paragraphs as pages).
- TXT: one page.
"""
from __future__ import annotations

import io
from pathlib import Path

import docx  # python-docx
from pypdf import PdfReader

SUPPORTED_MIMES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}

MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}


def mime_from_filename(filename: str) -> str | None:
    return MIME_BY_EXT.get(Path(filename).suffix.lower())


def extract_pdf(data: bytes) -> list[tuple[int, str]]:
    reader = PdfReader(io.BytesIO(data))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((i, text))
    return pages


def extract_docx(data: bytes) -> list[tuple[int, str]]:
    document = docx.Document(io.BytesIO(data))
    pages = []
    for i, para in enumerate(document.paragraphs, start=1):
        text = para.text
        if text.strip():
            pages.append((i, text))
    return pages


def extract_txt(data: bytes) -> list[tuple[int, str]]:
    text = data.decode("utf-8", errors="replace")
    return [(1, text)] if text.strip() else []


def extract(data: bytes, mime_type: str) -> list[tuple[int, str]]:
    kind = SUPPORTED_MIMES.get(mime_type)
    if kind == "pdf":
        return extract_pdf(data)
    if kind == "docx":
        return extract_docx(data)
    if kind == "txt":
        return extract_txt(data)
    raise ValueError(f"unsupported MIME type: {mime_type}")
