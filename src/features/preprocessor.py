"""
Preprocessor: RobustScaler, stratified split, SMOTE, sliding window.
"""
import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import SMOTE

from src.data.dataset_loader import FEATURE_COLS


def preprocess(df, feature_cols=None, test_size=0.2, val_size=0.1,
               smote=True, time_steps=5, random_state=42):
    """
    Full preprocessing pipeline.
    feature_cols: which columns to use (defaults to FEATURE_COLS).
    """
    if feature_cols is None:
        feature_cols = FEATURE_COLS

    X = df[feature_cols].values.astype(np.float64)
    # Log-transform then clip: handles columns like tcp.ack_raw (billions range)
    X = np.sign(X) * np.log1p(np.abs(X))
    X = np.clip(X, -50, 50).astype(np.float32)
    y = df["threat_class"].values.astype(int)

    # Stratified split: train (70%) / val (10%) / test (20%)
    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=random_state
    )
    relative_val = val_size / (1 - test_size)
    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval, test_size=relative_val, stratify=y_trainval,
        random_state=random_state
    )

    # SMOTE on train only
    if smote:
        min_count = pd.Series(y_train).value_counts().min()
        if min_count >= 6:
            sm = SMOTE(random_state=random_state, k_neighbors=min(5, min_count - 1))
            X_train, y_train = sm.fit_resample(X_train, y_train)

    # Fit scaler on train only
    scaler = RobustScaler()
    X_train = scaler.fit_transform(X_train).astype(np.float32)
    X_val = scaler.transform(X_val).astype(np.float32)
    X_test = scaler.transform(X_test).astype(np.float32)

    # Sliding window sequences
    X_train_seq = _make_sequences(X_train, time_steps)
    X_val_seq = _make_sequences(X_val, time_steps)
    X_test_seq = _make_sequences(X_test, time_steps)

    y_train_seq = y_train[time_steps - 1:]
    y_val_seq = y_val[time_steps - 1:]
    y_test_seq = y_test[time_steps - 1:]

    return {
        "X_train": X_train, "X_val": X_val, "X_test": X_test,
        "y_train": y_train, "y_val": y_val, "y_test": y_test,
        "X_train_seq": X_train_seq, "X_val_seq": X_val_seq, "X_test_seq": X_test_seq,
        "y_train_seq": y_train_seq, "y_val_seq": y_val_seq, "y_test_seq": y_test_seq,
        "scaler": scaler, "n_features": len(feature_cols),
    }


def _make_sequences(X, time_steps):
    if len(X) < time_steps:
        pad = np.zeros((time_steps - len(X), X.shape[1]), dtype=np.float32)
        X = np.vstack([pad, X])
    seqs = np.lib.stride_tricks.sliding_window_view(X, (time_steps, X.shape[1]))
    return seqs.reshape(-1, time_steps, X.shape[1]).astype(np.float32)
