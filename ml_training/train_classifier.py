"""
Fine-tune distilbert-base-uncased for 7-class document classification.

Run from repo root with backend venv active:
    python ml_training/train_classifier.py

Outputs (to MODEL_DIR/classifier/):
    config.json, model.safetensors, tokenizer.*, labels.json, train_history.json
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import f1_score
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "ml_training" / "data"
MODEL_NAME = "distilbert-base-uncased"
MAX_LEN = 256
BATCH_SIZE = 16
EPOCHS = 5
LR = 2e-5
WARMUP_RATIO = 0.1
WEIGHT_DECAY = 0.01
PATIENCE = 2
SEED = 42

OUT_DIR = ROOT / "backend" / "ml_models" / "classifier"

import sys
FORCE = "--force" in sys.argv
if (OUT_DIR / "model.safetensors").exists() and not FORCE:
    print(f"[skip] checkpoint already exists at {OUT_DIR}. Pass --force to retrain.")
    sys.exit(0)
torch.manual_seed(SEED)
np.random.seed(SEED)

def pick_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")

class JsonlDataset(Dataset):
    def __init__(self, path: Path, tokenizer, label2id: dict[str, int]):
        self.rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.tok = tokenizer
        self.label2id = label2id

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, i: int) -> dict:
        r = self.rows[i]
        enc = self.tok(
            r["text"],
            truncation=True,
            max_length=MAX_LEN,
            padding="max_length",
            return_tensors="pt",
        )
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "labels": torch.tensor(self.label2id[r["label"]], dtype=torch.long),
        }

@torch.no_grad()
def evaluate(model, loader, device) -> tuple[float, float, np.ndarray, np.ndarray]:
    model.eval()
    losses, preds, golds = [], [], []
    ce = torch.nn.CrossEntropyLoss()
    for batch in loader:
        input_ids = batch["input_ids"].to(device)
        attn = batch["attention_mask"].to(device)
        labels = batch["labels"].to(device)
        out = model(input_ids=input_ids, attention_mask=attn)
        loss = ce(out.logits, labels)
        losses.append(loss.item())
        preds.extend(out.logits.argmax(dim=-1).cpu().numpy().tolist())
        golds.extend(labels.cpu().numpy().tolist())
    macro_f1 = f1_score(golds, preds, average="macro")
    acc = float(np.mean(np.array(preds) == np.array(golds)))
    return float(np.mean(losses)), acc, np.array(preds), np.array(golds), macro_f1

def main() -> None:
    device = pick_device()
    print(f"[device] {device}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=7
    ).to(device)

    # Build label set from training data so ordering is deterministic & reproducible
    train_rows = [json.loads(l) for l in (DATA / "train.jsonl").read_text().splitlines() if l.strip()]
    labels_sorted = sorted({r["label"] for r in train_rows})
    label2id = {lab: i for i, lab in enumerate(labels_sorted)}
    id2label = {i: lab for lab, i in label2id.items()}
    (OUT_DIR / "labels.json").write_text(json.dumps(id2label, indent=2))
    print(f"[labels] {label2id}")

    train_ds = JsonlDataset(DATA / "train.jsonl", tokenizer, label2id)
    val_ds = JsonlDataset(DATA / "val.jsonl", tokenizer, label2id)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    optim = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    total_steps = len(train_loader) * EPOCHS
    sched = get_linear_schedule_with_warmup(
        optim,
        num_warmup_steps=int(WARMUP_RATIO * total_steps),
        num_training_steps=total_steps,
    )
    ce = torch.nn.CrossEntropyLoss()

    best_f1 = -1.0
    epochs_without_improve = 0
    history = []

    for epoch in range(1, EPOCHS + 1):
        model.train()
        t0 = time.time()
        running = 0.0
        for step, batch in enumerate(train_loader, 1):
            input_ids = batch["input_ids"].to(device)
            attn = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            optim.zero_grad()
            out = model(input_ids=input_ids, attention_mask=attn)
            loss = ce(out.logits, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optim.step()
            sched.step()
            running += loss.item()
            if step % 50 == 0:
                print(f"  epoch {epoch} step {step}/{len(train_loader)} loss={running/step:.4f}")

        val_loss, val_acc, _, _, val_f1 = evaluate(model, val_loader, device)
        dur = time.time() - t0
        print(
            f"[epoch {epoch}] train_loss={running/len(train_loader):.4f} "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.4f} val_f1={val_f1:.4f} ({dur:.1f}s)"
        )
        history.append({
            "epoch": epoch,
            "train_loss": running / len(train_loader),
            "val_loss": val_loss,
            "val_acc": val_acc,
            "val_macro_f1": val_f1,
            "duration_s": round(dur, 2),
        })

        if val_f1 > best_f1 + 1e-4:
            best_f1 = val_f1
            epochs_without_improve = 0
            model.save_pretrained(OUT_DIR)
            tokenizer.save_pretrained(OUT_DIR)
            print(f"  ✓ new best val_f1={val_f1:.4f} → saved to {OUT_DIR}")
        else:
            epochs_without_improve += 1
            print(f"  no improvement ({epochs_without_improve}/{PATIENCE})")
            if epochs_without_improve >= PATIENCE:
                print(f"[early stop] at epoch {epoch}, best val_f1={best_f1:.4f}")
                break

    (OUT_DIR / "train_history.json").write_text(json.dumps(history, indent=2))
    print(f"[done] best val_macro_f1={best_f1:.4f}  checkpoint → {OUT_DIR}")

if __name__ == "__main__":
    main()
