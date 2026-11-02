"""
Export the deployed model's predictions on its held-out test windows for the
dashboard's Live Monitor replay (frontend/public/replay.json).

Rebuilds the exact test split used by scripts/train_model.py (same loaders,
max_rows, seed and stratified split), applies the saved scaler, runs the saved
checkpoint through InferenceEngine, and checks the accuracy against
data/processed/showcase_eval.json before writing anything.
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
from src.live.inference import InferenceEngine  # noqa: E402
from train_model import load_combined  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-rows", type=int, default=None,
                    help="defaults to max_rows_per_dataset in showcase_eval.json")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(PROJECT_ROOT / "frontend" / "public" / "replay.json"))
    args = ap.parse_args()

    eval_report = json.loads((PROJECT_ROOT / "data" / "processed" / "showcase_eval.json").read_text())
    max_rows = args.max_rows or eval_report["max_rows_per_dataset"]
    datasets = eval_report["datasets"]

    combined = load_combined(datasets, max_rows)

    # Same transform and split as preprocess(); the split depends only on
    # n_samples, y, test_size and the seed, so splitting row indices matches it.
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
    src_seq = combined["source"].values[idx_test][4:]

    engine = InferenceEngine(model_dir=str(PROJECT_ROOT / "models" / "saved"))
    probs = np.concatenate([engine.get_probabilities(X_seq[i:i + 2048])
                            for i in range(0, len(X_seq), 2048)])
    pred = probs.argmax(axis=1)
    conf = probs.max(axis=1)
    acc = float((pred == y_seq).mean())

    print(f"[replay] windows={len(y_seq)} accuracy={acc:.4f} "
          f"(showcase_eval: {eval_report['accuracy']} on {eval_report['test_samples']})")
    if len(y_seq) != eval_report["test_samples"] or abs(acc - eval_report["accuracy"]) > 0.005:
        sys.exit("[replay] split does not reproduce showcase_eval.json; not writing replay")

    out = {
        "source": "held-out test windows, scripts/train_model.py split",
        "datasets": datasets,
        "accuracy": round(acc, 4),
        "n": int(len(y_seq)),
        "truth": y_seq.tolist(),
        "pred": pred.tolist(),
        "conf": [round(float(c), 3) for c in conf],
        "origin": src_seq.tolist(),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, separators=(",", ":")))
    print(f"[replay] wrote {args.out}")


if __name__ == "__main__":
    main()
