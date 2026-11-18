"""
Inference wrapper for the fine-tuned DistilBERT classifier.

Usage:
    clf = DocumentClassifier.load()
    result = clf.predict(["some document text"])
"""
from __future__ import annotations

import json
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MAX_LEN = 256
DEFAULT_CKPT = Path(__file__).resolve().parents[2] / "ml_models" / "classifier"


def _pick_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


class DocumentClassifier:
    def __init__(self, model, tokenizer, id2label, device):
        self.model = model
        self.tokenizer = tokenizer
        self.id2label = id2label
        self.device = device

    @classmethod
    def load(cls, ckpt: Path | str = DEFAULT_CKPT) -> "DocumentClassifier":
        ckpt = Path(ckpt)
        if not (ckpt / "model.safetensors").exists() and not (ckpt / "pytorch_model.bin").exists():
            raise FileNotFoundError(
                f"No classifier checkpoint at {ckpt}. Run ml_training/train_classifier.py first."
            )
        device = _pick_device()
        tokenizer = AutoTokenizer.from_pretrained(ckpt)
        model = AutoModelForSequenceClassification.from_pretrained(ckpt).to(device).eval()
        id2label = {int(k): v for k, v in json.loads((ckpt / "labels.json").read_text()).items()}
        return cls(model, tokenizer, id2label, device)

    @torch.no_grad()
    def predict(self, texts: list[str] | str, batch_size: int = 16) -> list[dict]:
        if isinstance(texts, str):
            texts = [texts]
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            enc = self.tokenizer(
                batch, truncation=True, max_length=MAX_LEN,
                padding=True, return_tensors="pt",
            ).to(self.device)
            logits = self.model(**enc).logits
            probs = torch.softmax(logits, dim=-1).cpu().numpy()
            for p in probs:
                idx = int(p.argmax())
                results.append({
                    "label": self.id2label[idx],
                    "confidence": float(p[idx]),
                    "probabilities": {
                        self.id2label[j]: float(p[j]) for j in range(len(p))
                    },
                })
        return results
