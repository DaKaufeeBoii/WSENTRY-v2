"""
One scoring function for every model: accuracy, macro and weighted F1, balanced
accuracy, per-class metrics, false alarm rate, majority-class baseline and, when
probabilities are given, one-vs-rest ROC-AUC and PR-AUC.
"""
import numpy as np
from sklearn.metrics import (
    accuracy_score, average_precision_score, balanced_accuracy_score, confusion_matrix,
    f1_score, precision_recall_fscore_support, roc_auc_score,
)


def score(y_true, y_pred, proba=None, proba_classes=None):
    """Metrics as fractions. `proba` columns follow `proba_classes`."""
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    classes = np.unique(y_true)  # macro averages run over the classes present in the test set
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=classes, zero_division=0)
    out = {
        "n_test": int(len(y_true)),
        "accuracy": accuracy_score(y_true, y_pred),
        "macro_f1": f1_score(y_true, y_pred, labels=classes, average="macro", zero_division=0),
        "weighted_f1": f1_score(y_true, y_pred, labels=classes, average="weighted", zero_division=0),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "majority_baseline": np.bincount(y_true).max() / len(y_true),
        "far": float(np.mean(y_pred[y_true == 0] != 0)) if (y_true == 0).any() else None,
        "per_class": {int(c): {"precision": p[i], "recall": r[i], "f1": f[i], "support": int(s[i])}
                      for i, c in enumerate(classes)},
        "classes": [int(c) for c in classes],
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=classes).tolist(),
    }
    if proba is not None:
        col = {int(c): i for i, c in enumerate(proba_classes)}
        aucs, aps = [], []
        for c in classes:
            hit = (y_true == c).astype(int)
            s_c = proba[:, col[int(c)]] if int(c) in col else np.zeros(len(y_true))
            aucs.append(roc_auc_score(hit, s_c))
            aps.append(average_precision_score(hit, s_c))
        out["roc_auc"], out["pr_auc"] = float(np.mean(aucs)), float(np.mean(aps))
    return {k: (float(v) if isinstance(v, np.floating) else v) for k, v in out.items()}
