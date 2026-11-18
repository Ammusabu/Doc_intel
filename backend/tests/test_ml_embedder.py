"""
Embedder tests — proves shape, L2 normalization, AND real semantic similarity.

The last test is the one that matters: same-meaning sentences must be close,
unrelated sentences must be far. That's the whole point of a bi-encoder.
"""
import numpy as np

from app.ml.embedder import Embedder, EMBED_DIM


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))  # both L2-normalized


def test_shape_and_normalization():
    emb = Embedder.load()
    texts = ["the quick brown fox", "a lazy dog sleeping in the sun", "python programming"]
    vecs = emb.encode(texts)
    assert vecs.shape == (3, EMBED_DIM)
    assert vecs.dtype == np.float32
    for v in vecs:
        norm = float(np.linalg.norm(v))
        assert abs(norm - 1.0) < 1e-4, f"expected L2-norm 1.0, got {norm}"


def test_batch_consistency():
    """Encoding the same text alone vs in a batch must give identical vectors."""
    emb = Embedder.load()
    single = emb.encode(["quantum computing uses qubits"])[0]
    batch = emb.encode(["padding text", "quantum computing uses qubits", "more padding"])[1]
    assert np.allclose(single, batch, atol=1e-5)


def test_semantic_similarity_paraphrase():
    """Paraphrases must have cosine > 0.5 — the whole point of a sentence encoder."""
    emb = Embedder.load()
    a = emb.encode(["The dog runs fast"])[0]
    b = emb.encode(["A dog is running quickly"])[0]
    assert _cos(a, b) > 0.5, f"paraphrase cosine too low: {_cos(a, b):.3f}"


def test_semantic_similarity_unrelated():
    """Unrelated sentences must have cosine < 0.3."""
    emb = Embedder.load()
    a = emb.encode(["The dog runs fast"])[0]
    b = emb.encode(["Quarterly tax filing deadline is April 15"])[0]
    assert _cos(a, b) < 0.3, f"unrelated cosine too high: {_cos(a, b):.3f}"


def test_empty_input_returns_empty_array():
    emb = Embedder.load()
    v = emb.encode([])
    assert v.shape == (0, EMBED_DIM)
