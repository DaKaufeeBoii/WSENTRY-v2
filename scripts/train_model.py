"""
Train and persist a deployable W-SENTRY checkpoint for the Phase 3 live dashboard.

`src/live/save_artifacts.py` only writes an *untrained* scaffold checkpoint, so the
Streamlit SOC dashboard and live inference engine have no real model to run. This
script trains the actual Hybrid CNN-BiLSTM-Attention model on the combined
behavioral feature space (WSN-DS + CIC-IoT-2023 + Edge-IIoTset), so a single
checkpoint covers all five threat classes (Normal / Jamming / Spoofing /
DoS_Flood / Intrusion_Probe), then saves the artifacts the live pipeline loads:

    models/saved/hybrid_model.pt     trained model weights
    models/saved/scaler.pkl          RobustScaler fitted on the training split
    models/saved/temp_scaler.pt      temperature-scaling calibration
    models/saved/model_config.json   architecture / feature metadata

It also writes an honest held-out evaluation report to:

    data/processed/showcase_eval.json

Usage:
    python scripts/train_model.py                      # defaults below
    python scripts/train_model.py --max-rows 100000 --epochs 30
    python scripts/train_model.py --datasets WSN CIC Edge
"""
import os
import sys
import json
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import torch
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    confusion_matrix, roc_auc_score,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.dataset_loader import load_wsn, load_cic, load_edge, FEATURE_COLS
from src.features.preprocessor import preprocess
from src.models.hybrid_dl import train_hybrid, predict_hybrid
from src.models.calibration import fit_temperature, compute_ece
from src.utils import set_seed

THREAT_LABELS = {
    0: "Normal", 1: "Jamming", 2: "Spoofing",
    3: "DoS_Flood", 4: "Intrusion_Probe",
}
LOADERS = {"WSN": load_wsn, "CIC": load_cic, "Edge": load_edge}


def load_combined(dataset_names, max_rows):
    """Load the behavioral feature frames and concatenate into one 5-class set."""
    frames = []
    for name in dataset_names:
        print(f"[train] loading {name} (behavioral, max_rows={max_rows}) ...")
        df = LOADERS[name](mode="behavioral", max_rows=max_rows)
        slim = df[FEATURE_COLS + ["threat_class"]].copy()
        slim["source"] = name
        frames.append(slim)
        counts = slim["threat_class"].value_counts().sort_index().to_dict()
        print(f"        {len(slim):>7,} rows  class counts={counts}")
        del df
    combined = pd.concat(frames, ignore_index=True)
    # Shuffle so the pseudo-sequence windows mix sources rather than blocking by dataset.
    combined = combined.sample(frac=1.0, random_state=42).reset_index(drop=True)
    print(f"[train] combined: {len(combined):,} rows across {len(dataset_names)} datasets")
    return combined


def evaluate(model, data, device="cpu"):
    """Held-out metrics on the test split."""
    X_test, y_test = data["X_test_seq"], data["y_test_seq"]
    preds, probs = predict_hybrid(model, X_test, device=device)

    acc = float(accuracy_score(y_test, preds))
    present = sorted(set(y_test.tolist()))
    p, r, f1, support = precision_recall_fscore_support(
        y_test, preds, labels=present, zero_division=0
    )
    per_class = {}
    for i, cid in enumerate(present):
        per_class[THREAT_LABELS.get(cid, str(cid))] = {
            "class_id": int(cid),
            "precision": round(float(p[i]), 4),
            "recall": round(float(r[i]), 4),
            "f1": round(float(f1[i]), 4),
            "support": int(support[i]),
        }

    cm = confusion_matrix(y_test, preds, labels=present).tolist()

    # One-vs-rest macro AUC over the classes present in the test split.
    try:
        onehot = np.zeros((len(y_test), probs.shape[1]), dtype=np.int8)
        onehot[np.arange(len(y_test)), y_test] = 1
        aucs = []
        for cid in present:
            col = onehot[:, cid]
            if col.min() != col.max():
                aucs.append(roc_auc_score(col, probs[:, cid]))
        macro_auc = round(float(np.mean(aucs)), 4) if aucs else None
    except Exception:
        macro_auc = None

    ece = round(float(compute_ece(probs, y_test)), 4)
    return {
        "accuracy": round(acc, 4),
        "macro_auc": macro_auc,
        "ece": ece,
        "per_class": per_class,
        "confusion_matrix": {"labels": present, "matrix": cm},
        "test_samples": int(len(y_test)),
    }


def main():
    ap = argparse.ArgumentParser(description="Train a deployable W-SENTRY checkpoint")
    ap.add_argument("--datasets", nargs="+", default=["WSN", "CIC", "Edge"],
                    choices=list(LOADERS.keys()))
    ap.add_argument("--max-rows", type=int, default=60000,
                    help="max rows sampled per dataset before combining")
    ap.add_argument("--epochs", type=int, default=25)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-dir", default=str(PROJECT_ROOT / "models" / "saved"))
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    set_seed(args.seed)
    print(f"[train] device={device}  datasets={args.datasets}  epochs={args.epochs}")

    combined = load_combined(args.datasets, args.max_rows)

    # SMOTE balances the rarer classes (Jamming only appears in WSN).
    data = preprocess(combined, feature_cols=FEATURE_COLS, smote=True,
                      time_steps=5, random_state=args.seed)
    n_classes = int(max(5, combined["threat_class"].max() + 1))
    print(f"[train] train_seq={data['X_train_seq'].shape}  "
          f"val_seq={data['X_val_seq'].shape}  test_seq={data['X_test_seq'].shape}")

    model, hist = train_hybrid(
        data["X_train_seq"], data["y_train_seq"],
        data["X_val_seq"], data["y_val_seq"],
        n_features=len(FEATURE_COLS), n_classes=n_classes,
        epochs=args.epochs, batch_size=args.batch_size, device=device, seed=args.seed,
    )

    print("[train] fitting temperature scaler ...")
    temp_scaler = fit_temperature(model, data["X_val_seq"], data["y_val_seq"], device=device)

    print("[train] evaluating on held-out test split ...")
    report = evaluate(model, data, device=device)

    # ---- persist artifacts ----
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), out_dir / "hybrid_model.pt")
    torch.save(temp_scaler.state_dict(), out_dir / "temp_scaler.pt")
    joblib.dump(data["scaler"], out_dir / "scaler.pkl")
    config = {
        "n_features": len(FEATURE_COLS),
        "n_classes": n_classes,
        "hidden_dim": 128,
        "feature_names": FEATURE_COLS,
        "model_architecture": "HybridCNNBiLSTMAttention",
        "trained_on": args.datasets,
        "threat_labels": THREAT_LABELS,
    }
    with open(out_dir / "model_config.json", "w") as f:
        json.dump(config, f, indent=2)

    # Persist a small stratified slice of the held-out test windows so the
    # showcase can demonstrate the deployed engine without re-reading the CSVs.
    y_test = data["y_test_seq"]
    sample_idx = []
    rng = np.random.RandomState(args.seed)
    for cid in sorted(set(y_test.tolist())):
        idx = np.where(y_test == cid)[0]
        take = min(60, len(idx))
        sample_idx.extend(rng.choice(idx, size=take, replace=False).tolist())
    sample_idx = np.array(sorted(sample_idx))
    samples_path = PROJECT_ROOT / "data" / "processed" / "showcase_samples.npz"
    samples_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        samples_path,
        X=data["X_test_seq"][sample_idx].astype(np.float32),
        y=y_test[sample_idx].astype(np.int64),
    )
    print(f"[train] showcase samples saved to {samples_path} ({len(sample_idx)} windows)")

    eval_path = PROJECT_ROOT / "data" / "processed" / "showcase_eval.json"
    eval_path.parent.mkdir(parents=True, exist_ok=True)
    report_out = {
        "datasets": args.datasets,
        "max_rows_per_dataset": args.max_rows,
        "epochs_ran": len(hist["train_loss"]),
        "final_val_acc": round(float(hist["val_acc"][-1]), 4),
        **report,
    }
    with open(eval_path, "w") as f:
        json.dump(report_out, f, indent=2)

    print("\n" + "=" * 60)
    print(" W-SENTRY MODEL — HELD-OUT EVALUATION")
    print("=" * 60)
    print(f"  Test accuracy : {report['accuracy'] * 100:.2f}%")
    print(f"  Macro AUC     : {report['macro_auc']}")
    print(f"  ECE           : {report['ece']}")
    print(f"  Test samples  : {report['test_samples']:,}")
    print("  Per-class F1:")
    for label, m in report["per_class"].items():
        print(f"    {label:16s} P={m['precision']:.3f} R={m['recall']:.3f} "
              f"F1={m['f1']:.3f}  (n={m['support']})")
    print("=" * 60)
    print(f"[train] artifacts saved to {out_dir}")
    print(f"[train] eval report saved to {eval_path}")


if __name__ == "__main__":
    main()
