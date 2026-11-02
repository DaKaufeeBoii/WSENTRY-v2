"""
Export real held-out feature artifacts for the networked demo.

The attacker laptop sends these to the detector, which runs the REAL model on
them and decides whether to block. Each artifact is a (5, 20) behavioral-feature
sequence from the model's held-out test split (records it never trained on),
grouped by the attack family it belongs to. The detector is NOT told the family;
it classifies each artifact itself.

Writes scripts/attack_samples.json: { "meta": {...}, "pools": { "<family>": [[[20]x5], ...] } }
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.model_selection import train_test_split
import joblib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from src.data.dataset_loader import FEATURE_COLS  # noqa: E402
from src.features.preprocessor import _make_sequences  # noqa: E402
from train_model import load_combined  # noqa: E402

# class id -> attacker-facing family handle
FAMILY = {1: "jam", 2: "spoof", 3: "dos", 4: "scan"}
PER_FAMILY = 80


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(PROJECT_ROOT / "scripts" / "attack_samples.json"))
    args = ap.parse_args()

    eval_report = json.loads((PROJECT_ROOT / "data" / "processed" / "showcase_eval.json").read_text())
    combined = load_combined(eval_report["datasets"], eval_report["max_rows_per_dataset"])

    X = combined[FEATURE_COLS].values.astype(np.float64)
    X = np.sign(X) * np.log1p(np.abs(X))
    X = np.clip(X, -50, 50).astype(np.float32)
    y = combined["threat_class"].values.astype(int)
    idx = np.arange(len(y))
    _, idx_test = train_test_split(idx, test_size=0.2, stratify=y, random_state=args.seed)

    scaler = joblib.load(PROJECT_ROOT / "models" / "saved" / "scaler.pkl")
    X_test = scaler.transform(X[idx_test]).astype(np.float32)
    X_seq = _make_sequences(X_test, 5)
    y_seq = y[idx_test][4:]

    rng = np.random.RandomState(args.seed)
    pools = {}
    for cid, fam in FAMILY.items():
        where = np.where(y_seq == cid)[0]
        take = rng.choice(where, size=min(PER_FAMILY, len(where)), replace=False)
        pools[fam] = [X_seq[i].round(5).tolist() for i in take]

    out = {
        "meta": {
            "note": "real held-out test sequences; features only, no labels",
            "features": FEATURE_COLS,
            "shape": "[n][5][20]",
        },
        "pools": pools,
    }
    Path(args.out).write_text(json.dumps(out, separators=(",", ":")))
    print(f"[samples] wrote {args.out}")
    for fam, seqs in pools.items():
        print(f"          {fam:6s} {len(seqs)} artifacts")


if __name__ == "__main__":
    main()
