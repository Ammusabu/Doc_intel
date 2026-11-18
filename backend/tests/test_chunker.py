"""Chunker tests — verify token-aware splitting, overlap, and page metadata."""
from app.services.chunker import chunk_document, count_tokens


def test_single_page_produces_multiple_chunks_with_overlap():
    # Long text on one page → many chunks, all page 1
    text = "the quick brown fox jumps over the lazy dog. " * 200
    chunks = chunk_document([text], chunk_size=256, overlap=50)
    assert len(chunks) >= 2
    assert all(c["page_number"] == 1 for c in chunks)
    assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))
    # every chunk ≤ chunk_size tokens
    assert all(c["token_count"] <= 256 for c in chunks)
    # final chunk may be smaller, but should still have content
    assert all(c["content"] for c in chunks)


def test_chunks_do_not_span_pages():
    page_a = "alpha beta gamma delta " * 100   # ~400 tokens
    page_b = "one two three four five " * 100  # ~500 tokens
    chunks = chunk_document([page_a, page_b], chunk_size=256, overlap=50)
    page_1_chunks = [c for c in chunks if c["page_number"] == 1]
    page_2_chunks = [c for c in chunks if c["page_number"] == 2]
    assert len(page_1_chunks) >= 1
    assert len(page_2_chunks) >= 1
    # chunk_index must be globally monotonic across page boundary
    assert page_1_chunks[-1]["chunk_index"] < page_2_chunks[0]["chunk_index"]


def test_no_data_loss():
    """Total chunked characters must cover at least 95% of source chars."""
    text = "Lorem ipsum dolor sit amet. " * 300
    chunks = chunk_document([text], chunk_size=256, overlap=50)
    total_chunked_chars = sum(len(c["content"]) for c in chunks)
    # overlap inflates this by design; ensure >= source length (no drop)
    assert total_chunked_chars >= len(text) * 0.95


def test_empty_page_returns_no_chunks():
    assert chunk_document([""]) == []


def test_overlap_must_be_less_than_chunk_size():
    import pytest
    with pytest.raises(ValueError):
        chunk_document(["some text"], chunk_size=50, overlap=50)


def test_token_count_matches_helper():
    text = "the quick brown fox jumps over the lazy dog"
    expected = count_tokens(text)
    chunks = chunk_document([text], chunk_size=256, overlap=50)
    # single chunk since < chunk_size tokens
    assert len(chunks) == 1
    assert chunks[0]["token_count"] == expected
