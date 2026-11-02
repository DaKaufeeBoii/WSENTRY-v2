"""
Step 0 runner: every model on the same features, split, class weighting and scoring,
repeated over several seeds.

usage: python run_step0.py [--datasets wsn cic edge] [--models rf xgb hybrid]
                           [--seeds 0 1 2 3 4] [--max-rows N] [--out data/processed/step0]

Each run writes <out>/runs/<dataset>__<model>__seed<k>.json (config, seed, metrics,
confusion matrix); finished runs are skipped, so an interrupted sweep resumes.
<out>/summary.json and summary.md hold mean and standard deviation over seeds.
"""
import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np
import sklearn
import torch
import xgboost

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.full_features import DATASETS, class_weights, load, prepare
from src.eval.metrics import score
from src.models.baseline_ml import train_rf, train_xgb
from src.models.hybrid_dl import predict_hybrid, train_hybrid
from src.utils import set_seed

CONFIG = {
    # rows per dataset (None = all); CIC is capped for run time, sampled once with sample_seed
    "max_rows": {"wsn": None, "cic": 300_000, "edge": None},
    "sample_seed": 0,
    "split": {"train": 0.7, "val": 0.1, "test": 0.2},
    "transform": "sign(x)*log1p(|x|), clip [-50, 50], robust scaler fit on train",
    "class_weight": "N/(C*n_c) clipped to [0.5, 5], same for all models; no SMOTE",
    "time_steps": 5,  # hybrid only; windows of shuffled rows, zero-padded so every test row is scored
    "rf": {"n_estimators": 100},
    "xgb": {"n_estimators": 100, "max_depth": 6, "learning_rate": 0.1},  # depth and rate are fixed in train_xgb
    "hybrid": {"epochs": 20, "batch_size": 256, "lr": 1e-3},
}
METRICS = ["accuracy", "macro_f1", "weighted_f1", "balanced_accuracy", "roc_auc", "pr_auc", "far",
           "majority_baseline"]
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def fit_predict(model, data, seed):
    """Train one model; return (y_pred, proba, proba_classes)."""
    w = class_weights(data["y_train"])
    if model == "rf":
        clf = train_rf(data["X_train"], data["y_train"], random_state=seed, class_weight=w,
                       **CONFIG["rf"])
        return clf.predict(data["X_test"]), clf.predict_proba(data["X_test"]), clf.classes_
    if model == "xgb":
        clf = train_xgb(data["X_train"], data["y_train"], random_state=seed,
                        sample_weight=np.array([w[int(c)] for c in data["y_train"]]),
                        n_estimators=CONFIG["xgb"]["n_estimators"])
        proba = clf.predict_proba(data["X_test"])
        return clf._wsentry_le.classes_[proba.argmax(1)], proba, clf._wsentry_le.classes_
    # hybrid: contiguous labels inside the network; train_hybrid applies the same weight formula
    classes = np.unique(data["y_train"])
    to_idx = {int(c): i for i, c in enumerate(classes)}
    idx = lambda ys: np.array([to_idx[int(v)] for v in ys])
    net, _ = train_hybrid(data["X_train_seq"], idx(data["y_train"]), data["X_val_seq"], idx(data["y_val"]),
                          n_features=data["X_train"].shape[1], n_classes=len(classes), device=DEVICE,
                          seed=seed, **CONFIG["hybrid"])
    pred, proba = predict_hybrid(net, data["X_test_seq"], device=DEVICE)
    return classes[pred], proba, classes


def summarize(out_dir):
    runs = [json.load(open(os.path.join(out_dir, "runs", f))) for f in sorted(os.listdir(os.path.join(out_dir, "runs")))]
    groups = {}
    for r in runs:
        groups.setdefault((r["dataset"], r["model"]), []).append(r)
    summary = {}
    for (ds, model), rs in sorted(groups.items()):
        row = {"seeds": [r["seed"] for r in rs]}
        for m in METRICS:
            vals = [r["metrics"][m] for r in rs if r["metrics"].get(m) is not None]
            if vals:
                row[m] = {"mean": float(np.mean(vals)), "std": float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0}
        summary[f"{ds}/{model}"] = row
    json.dump(summary, open(os.path.join(out_dir, "summary.json"), "w"), indent=2)
    cols = ["accuracy", "macro_f1", "balanced_accuracy", "roc_auc", "far", "majority_baseline"]
    lines = ["| dataset/model | seeds | " + " | ".join(cols) + " |", "|" + " --- |" * (len(cols) + 2)]
    for key, row in summary.items():
        cells = [f"{100 * row[c]['mean']:.2f} ± {100 * row[c]['std']:.2f}" if c in row else "" for c in cols]
        lines.append(f"| {key} | {len(row['seeds'])} | " + " | ".join(cells) + " |")
    open(os.path.join(out_dir, "summary.md"), "w", encoding="utf-8").write(
        "Step 0 results, percent, mean ± sample std over seeds.\n\n" + "\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", nargs="+", default=list(DATASETS))
    ap.add_argument("--models", nargs="+", default=["rf", "xgb", "hybrid"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    ap.add_argument("--max-rows", type=int, help="override every dataset's row cap (smoke tests)")
    ap.add_argument("--out", default="data/processed/step0")
    args = ap.parse_args()
    os.makedirs(os.path.join(args.out, "runs"), exist_ok=True)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    versions = {"sklearn": sklearn.__version__, "xgboost": xgboost.__version__, "torch": torch.__version__,
                "numpy": np.__version__}

    for ds in args.datasets:
        cap = args.max_rows or CONFIG["max_rows"][ds]
        X, y, feats = load(ds, max_rows=cap, sample_seed=CONFIG["sample_seed"])
        print(f"=== {ds}: {len(y)} rows, {len(feats)} features, classes {np.bincount(y).tolist()}")
        for seed in args.seeds:
            data = None
            for model in args.models:
                path = os.path.join(args.out, "runs", f"{ds}__{model}__seed{seed}.json")
                if os.path.exists(path):
                    continue
                if data is None:
                    data = prepare(X, y, seed, time_steps=CONFIG["time_steps"])
                set_seed(seed)
                t0 = time.time()
                pred, proba, pcls = fit_predict(model, data, seed)
                m = score(data["y_test"], pred, proba, pcls)
                rec = {"dataset": ds, "model": model, "seed": seed, "metrics": m,
                       "seconds": round(time.time() - t0, 1), "n_rows": int(len(y)), "row_cap": cap,
                       "data": DATASETS[ds]["path"],
                       "features": feats, "config": CONFIG, "device": DEVICE, "git_commit": commit,
                       "versions": versions}
                json.dump(rec, open(path, "w"), indent=1)
                print(f"  {ds} {model} seed {seed}: acc {100 * m['accuracy']:.2f}  macro-F1 "
                      f"{100 * m['macro_f1']:.2f}  ({rec['seconds']}s)")
    summarize(args.out)


if __name__ == "__main__":
    main()
