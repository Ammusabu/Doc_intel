"""Classifier inference test: loads checkpoint, predicts 3 texts, checks shape."""
from pathlib import Path

import pytest

from app.ml.classifier import DocumentClassifier, DEFAULT_CKPT


@pytest.mark.skipif(
    not (DEFAULT_CKPT / "labels.json").exists(),
    reason="classifier not trained yet — run ml_training/train_classifier.py",
)
def test_classifier_predicts_three_labels():
    clf = DocumentClassifier.load()
    samples = [
        "The quarterly budget report shows a projected revenue increase of 12%.",
        "The patient presented with acute respiratory symptoms and elevated temperature.",
        "Kubernetes pods failing readiness probe due to misconfigured liveness check.",
    ]
    out = clf.predict(samples)
    assert len(out) == 3
    for r in out:
        assert r["label"] in clf.id2label.values()
        assert 0.0 <= r["confidence"] <= 1.0
        assert abs(sum(r["probabilities"].values()) - 1.0) < 1e-4
