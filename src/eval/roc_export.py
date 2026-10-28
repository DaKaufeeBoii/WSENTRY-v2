"""
Export true threshold-swept ROC curves from model probabilities.

The models already return calibratable probabilities (predict_hybrid /
predict_dann); this turns them into per-class one-vs-rest ROC curves so the
paper figure and the dashboard use measured curves instead of a single
operating point.

Writes two artifacts:
  * .npz  — full-fidelity probabilities + labels, for re-analysis
  * .json — downsampled curves + AUCs, small enough for the dashboard to read
"""
import json

import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve


def _downsample(x, y, max_points):
    """Thin a curve to at most max_points, keeping the endpoints."""
    if len(x) <= max_points:
        return x, y
    idx = np.unique(np.linspace(0, len(x) - 1, max_points).astype(int))
    return x[idx], y[idx]


def export_roc(per_dataset, npz_path, json_path, max_points=120):
    """
    per_dataset: {name: {"y_true": (N,) ints indexing the probs columns,
                         "probs":  (N, n_classes) float,
                         "classes": [original class id for each column]}}

    Returns the JSON summary that was written.
    """
    npz = {}
    summary = {}

    for name, d in per_dataset.items():
        y_true = np.asarray(d["y_true"]).astype(int)
        probs = np.asarray(d["probs"], dtype=np.float32)
        classes = [int(c) for c in d["classes"]]

        npz[f"{name}__y_true"] = y_true
        npz[f"{name}__probs"] = probs
        npz[f"{name}__classes"] = np.asarray(classes)

        curves, aucs = [], []
        for col, cid in enumerate(classes):
            y_bin = (y_true == col).astype(int)
            # A class absent from this test split has no ROC.
            if y_bin.min() == y_bin.max():
                continue
            fpr, tpr, _ = roc_curve(y_bin, probs[:, col])
            auc = float(roc_auc_score(y_bin, probs[:, col]))
            aucs.append(auc)
            f_ds, t_ds = _downsample(fpr, tpr, max_points)
            curves.append({
                "class_id": cid,
                "auc": round(auc, 4),
                "fpr": [round(float(v), 5) for v in f_ds],
                "tpr": [round(float(v), 5) for v in t_ds],
            })

        # Micro-average: pool every one-vs-rest decision into one curve.
        micro = None
        try:
            onehot = np.zeros_like(probs, dtype=np.int8)
            onehot[np.arange(len(y_true)), y_true] = 1
            micro = round(float(roc_auc_score(onehot.ravel(), probs.ravel())), 4)
        except ValueError:
            pass

        summary[name] = {
            "classes": classes,
            "curves": curves,
            "macro_auc": round(float(np.mean(aucs)), 4) if aucs else None,
            "micro_auc": micro,
        }
        print(f"  ROC {name}: macro_auc={summary[name]['macro_auc']}, "
              f"micro_auc={micro}, curves={len(curves)}")

    np.savez_compressed(npz_path, **npz)
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Saved {npz_path} and {json_path}")
    return summary
