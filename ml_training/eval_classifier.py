"""
Evaluate the fine-tuned classifier on the held-out test split.
Writes backend/ml_models/classifier/eval.json — this is the file to quote in the README.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import classification_report, confusion_matrix
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "ml_training" / "data"
CKPT = ROOT / "backend" / "ml_models" / "classifier"
MAX_LEN = 256
BATCH_SIZE = 32


def pick_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


class TestDataset(Dataset):
    def __init__(self, path: Path, tokenizer, label2id: dict[str, int]):
        self.rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        self.tok = tokenizer
        self.label2id = label2id

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        r = self.rows[i]
        enc = self.tok(
            r["text"], truncation=True, max_length=MAX_LEN,
            padding="max_length", return_tensors="pt",
        )
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "label": self.label2id[r["label"]],
        }


def main() -> None:
    device = pick_device()
    print(f"[device] {device}")
    id2label = {int(k): v for k, v in json.loads((CKPT / "labels.json").read_text()).items()}
    label2id = {v: k for k, v in id2label.items()}
    label_order = [id2label[i] for i in sorted(id2label)]

    tokenizer = AutoTokenizer.from_pretrained(CKPT)
    model = AutoModelForSequenceClassification.from_pretrained(CKPT).to(device).eval()

    ds = TestDataset(DATA / "test.jsonl", tokenizer, label2id)
    loader = DataLoader(ds, batch_size=BATCH_SIZE, shuffle=False)

    golds, preds = [], []
    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attn = batch["attention_mask"].to(device)
            logits = model(input_ids=input_ids, attention_mask=attn).logits
            preds.extend(logits.argmax(-1).cpu().numpy().tolist())
            golds.extend(batch["label"].numpy().tolist())

    labels_idx = list(range(len(label_order)))
    report = classification_report(
        golds, preds, labels=labels_idx, target_names=label_order,
        digits=4, zero_division=0,
    )
    cm = confusion_matrix(golds, preds, labels=labels_idx)
    acc = float(np.mean(np.array(golds) == np.array(preds)))

    print("\n=== Classification Report (test split) ===")
    print(report)
    print("Confusion matrix (rows=true, cols=pred):")
    print("labels:", label_order)
    print(cm)

    out = {
        "checkpoint": str(CKPT),
        "n_test": len(golds),
        "accuracy": acc,
        "labels": label_order,
        "report_text": report,
        "confusion_matrix": cm.tolist(),
    }
    (CKPT / "eval.json").write_text(json.dumps(out, indent=2))
    print(f"\n[saved] {CKPT / 'eval.json'}")


if __name__ == "__main__":
    main()
