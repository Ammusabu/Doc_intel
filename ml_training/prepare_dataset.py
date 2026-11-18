"""
Build a labeled 7-category corpus from sklearn's bundled 20 Newsgroups.

Mapping (20 NG → our taxonomy):
  Technical : comp.graphics, comp.os.ms-windows.misc, comp.sys.ibm.pc.hardware,
              comp.sys.mac.hardware, comp.windows.x
  Research  : sci.electronics, sci.med, sci.space, sci.crypt
  Legal     : talk.politics.guns, talk.politics.mideast
  HR        : talk.politics.misc, soc.religion.christian
  Business  : misc.forsale, rec.autos, rec.motorcycles
  Finance   : alt.atheism, talk.religion.misc   # NOTE: weak mapping — see README
  General   : rec.sport.baseball, rec.sport.hockey

Rationale: 20 NG has no HR/Finance/Legal categories. The mapping is a known
limitation documented in the README. We are honest about it — macro-F1 will
land around 0.70–0.85 and that is the number we report.

Output: ml_training/data/{train,val,test}.jsonl
        each line: {"text": "...", "label": "Technical"}
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from sklearn.datasets import fetch_20newsgroups

CATEGORY_MAP: dict[str, list[str]] = {
    "Technical": [
        "comp.graphics",
        "comp.os.ms-windows.misc",
        "comp.sys.ibm.pc.hardware",
        "comp.sys.mac.hardware",
        "comp.windows.x",
    ],
    "Research": ["sci.electronics", "sci.med", "sci.space", "sci.crypt"],
    "Legal": ["talk.politics.guns", "talk.politics.mideast"],
    "HR": ["talk.politics.misc", "soc.religion.christian"],
    "Business": ["misc.forsale", "rec.autos", "rec.motorcycles"],
    "Finance": ["alt.atheism", "talk.religion.misc"],
    "General": ["rec.sport.baseball", "rec.sport.hockey"],
}

SEED = 42
MAX_PER_CLASS = 600          # cap for balance; 7 × 600 = 4200 max
MIN_TEXT_CHARS = 200         # drop very short docs

def build() -> list[dict]:
    all_ng_groups = sorted({g for groups in CATEGORY_MAP.values() for g in groups})
    ds = fetch_20newsgroups(
        subset="all",
        categories=all_ng_groups,
        remove=("headers", "footers", "quotes"),
        shuffle=True,
        random_state=SEED,
    )
    # reverse map: 20NG group → our label
    group_to_label = {g: label for label, groups in CATEGORY_MAP.items() for g in groups}
    label_names = ds.target_names

    per_class: dict[str, list[dict]] = {label: [] for label in CATEGORY_MAP}
    for text, tgt in zip(ds.data, ds.target):
        text = " ".join(text.split())  # collapse whitespace
        if len(text) < MIN_TEXT_CHARS:
            continue
        label = group_to_label[label_names[tgt]]
        if len(per_class[label]) >= MAX_PER_CLASS:
            continue
        per_class[label].append({"text": text, "label": label})

    rng = random.Random(SEED)
    for label in per_class:
        rng.shuffle(per_class[label])
    return [row for label in per_class for row in per_class[label]]

def split(rows: list[dict]) -> tuple[list, list, list]:
    rng = random.Random(SEED)
    by_class: dict[str, list[dict]] = {}
    for r in rows:
        by_class.setdefault(r["label"], []).append(r)
    train, val, test = [], [], []
    for label, items in by_class.items():
        rng.shuffle(items)
        n = len(items)
        n_val, n_test = int(n * 0.10), int(n * 0.10)
        val.extend(items[:n_val])
        test.extend(items[n_val:n_val + n_test])
        train.extend(items[n_val + n_test:])
    for coll in (train, val, test):
        rng.shuffle(coll)
    return train, val, test

def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def main() -> None:
    out = Path(__file__).parent / "data"
    rows = build()
    train, val, test = split(rows)
    write_jsonl(out / "train.jsonl", train)
    write_jsonl(out / "val.jsonl", val)
    write_jsonl(out / "test.jsonl", test)

    def counts(rs):
        c: dict[str, int] = {}
        for r in rs:
            c[r["label"]] = c.get(r["label"], 0) + 1
        return {k: c.get(k, 0) for k in sorted(CATEGORY_MAP)}

    print(f"train={len(train)} val={len(val)} test={len(test)} total={len(rows)}")
    print("train per class:", counts(train))
    print("val   per class:", counts(val))
    print("test  per class:", counts(test))
    print(f"wrote -> {out}")

if __name__ == "__main__":
    main()
