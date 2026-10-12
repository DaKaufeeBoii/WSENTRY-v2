"""
Baseline ML models: Random Forest, XGBoost.
"""
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
)
import xgboost as xgb


def train_rf(X_train, y_train, n_estimators=100, random_state=42):
    clf = RandomForestClassifier(n_estimators=n_estimators, random_state=random_state, n_jobs=-1)
    clf.fit(X_train, y_train)
    return clf


def train_xgb(X_train, y_train, n_estimators=100, random_state=42):
    # ponytail: XGBoost needs contiguous 0..N labels
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    y_enc = le.fit_transform(y_train)
    n_classes = len(le.classes_)
    clf = xgb.XGBClassifier(
        n_estimators=n_estimators,
        max_depth=6,
        learning_rate=0.1,
        objective="multi:softprob",
        num_class=n_classes,
        random_state=random_state,
        n_jobs=-1,
        eval_metric="mlogloss",
    )
    clf.fit(X_train, y_enc)
    clf._wsentry_le = le  # stash for inverse transform
    return clf


def evaluate(model, X_test, y_test, model_name="Model"):
    """Returns dict of metrics."""
    y_pred = model.predict(X_test)
    # ponytail: inverse-transform XGBoost's encoded labels
    if hasattr(model, "_wsentry_le"):
        y_pred = model._wsentry_le.inverse_transform(y_pred)
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    rec = recall_score(y_test, y_pred, average="weighted", zero_division=0)
    f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)
    cm = confusion_matrix(y_test, y_pred)
    # False alarm rate: benign classified as attack / total benign
    benign_mask = y_test == 0
    if benign_mask.sum() > 0:
        far = (y_pred[benign_mask] != 0).sum() / benign_mask.sum()
    else:
        far = 0.0

    report = classification_report(y_test, y_pred, zero_division=0)

    return {
        "model_name": model_name,
        "accuracy": round(acc * 100, 2),
        "precision": round(prec * 100, 2),
        "recall": round(rec * 100, 2),
        "f1": round(f1 * 100, 2),
        "far": round(far * 100, 2),
        "confusion_matrix": cm,
        "report": report,
    }
