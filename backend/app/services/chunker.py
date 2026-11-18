"""
Token-aware chunker for document text.

Splits text into fixed-token chunks with overlap, respecting page boundaries.
Uses the distilbert-base-uncased tokenizer so no tokenizer boundary is crossed
between the classifier, the chunker, and the embedder.

API:
    chunk_document(pages: list[str], chunk_size=256, overlap=50) -> list[dict]

Each page is a plain string (no formatting). Page boundaries are hard breaks:
a chunk never spans two pages. Each returned chunk:
    {
        "chunk_index": int,       # monotonic across the whole document
        "page_number": int,       # 1-indexed
        "content": str,           # decoded chunk text
        "token_count": int,       # number of tokens in the chunk
    }
"""
from __future__ import annotations

from functools import lru_cache

from transformers import AutoTokenizer

TOKENIZER_NAME = "distilbert-base-uncased"


@lru_cache(maxsize=1)
def _get_tokenizer():
    return AutoTokenizer.from_pretrained(TOKENIZER_NAME)


def _chunk_one_page(
    text: str,
    page_number: int,
    start_index: int,
    chunk_size: int,
    overlap: int,
) -> list[dict]:
    """Chunk a single page's text, returning chunks with global indices."""
    if overlap >= chunk_size:
        raise ValueError(f"overlap ({overlap}) must be < chunk_size ({chunk_size})")

    tok = _get_tokenizer()
    ids = tok.encode(text, add_special_tokens=False)
    if not ids:
        return []

    step = chunk_size - overlap
    chunks: list[dict] = []
    i = 0
    idx = start_index
    while i < len(ids):
        window = ids[i : i + chunk_size]
        decoded = tok.decode(window, skip_special_tokens=True).strip()
        if decoded:  # don't emit empty/whitespace-only chunks
            chunks.append({
                "chunk_index": idx,
                "page_number": page_number,
                "content": decoded,
                "token_count": len(window),
            })
            idx += 1
        if i + chunk_size >= len(ids):
            break
        i += step
    return chunks


def chunk_document(
    pages: list[str],
    chunk_size: int = 256,
    overlap: int = 50,
) -> list[dict]:
    """
    Chunk a document given its pages in order.
    Returns list of dicts (see module docstring).
    """
    if not pages:
        return []
    all_chunks: list[dict] = []
    for page_idx, page_text in enumerate(pages, start=1):
        page_chunks = _chunk_one_page(
            page_text,
            page_number=page_idx,
            start_index=len(all_chunks),
            chunk_size=chunk_size,
            overlap=overlap,
        )
        all_chunks.extend(page_chunks)
    return all_chunks


def count_tokens(text: str) -> int:
    """Public helper — useful for tests and validation."""
    return len(_get_tokenizer().encode(text, add_special_tokens=False))
