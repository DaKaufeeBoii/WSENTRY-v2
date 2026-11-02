"""
Step 0 data: every numeric column of each dataset, minus identifiers, timestamps,
capture-order indexes and label copies, mapped to the five-class taxonomy. One
seeded split and transform is shared by all models, so every model is scored on
exactly the same test rows.
"""
import glob

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import RobustScaler

from src.data.dataset_loader import WSN_LABEL_MAP, CIC_LABEL_MAP, EDGE_LABEL_MAP

DATASETS = {
    "wsn": {
        "path": "data/raw/WSN-DS.csv", "label": "Attack type", "map": WSN_LABEL_MAP,
        # node identifiers: a model could learn which nodes attack instead of how
        "exclude": ["id", "who CH"],
    },
    "cic": {
        # official CSV export (Kaggle mirror madhavmalhotra/unb-cic-iot-dataset); each part is a
        # random slice of all 34 classes. The older IoT_Intrusion.csv stops at Excel's row limit.
        "path": "data/raw/ciciot2023_kaggle_csv/wataiData/csv/CICIoT2023/part-0000[0-9]-*.csv",
        "label": "label", "map": CIC_LABEL_MAP,
        # IAT holds the absolute capture timestamp at every 20th packet (see
        # src/features/ciciot_features.py); alone it predicts the class at 98.9% accuracy
        "exclude": ["IAT"],
    },
    "edge": {
        "path": "data/raw/ML-EdgeIIoT-dataset.csv", "label": "Attack_type", "map": EDGE_LABEL_MAP,
        # Attack_label copies the label; the other two encode capture time or order
        "exclude": ["Attack_label", "icmp.transmit_timestamp", "udp.stream"],
        # stored as text in the CSV but numeric in meaning
        "coerce": ["dns.qry.name.len"],
    },
}


def load(name, max_rows=None, sample_seed=0, with_raw=False):
    """Return (X float64 array, y int array, feature names[, raw label strings]) for one dataset."""
    spec = DATASETS[name]
    files = sorted(glob.glob(spec["path"]))
    assert files, f"no data at {spec['path']}"
    df = pd.concat([pd.read_csv(f, low_memory=False) for f in files], ignore_index=True)
    df.columns = [c.strip() for c in df.columns]
    raw = df[spec["label"]].astype(str).str.strip()
    y = raw.map(spec["map"])
    keep = y.notna().to_numpy()
    df, raw, y = df[keep], raw[keep].to_numpy(), y[keep].astype(int).to_numpy()
    for col in spec.get("coerce", []):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    feats = [c for c in df.select_dtypes("number").columns if c not in spec["exclude"]]
    X = df[feats].fillna(0).to_numpy(np.float64)
    if max_rows and len(y) > max_rows:
        # proportional stratified sample; the subset stays fixed across seeds
        idx, _ = train_test_split(np.arange(len(y)), train_size=max_rows, stratify=y, random_state=sample_seed)
        X, y, raw = X[idx], y[idx], raw[idx]
    return (X, y, feats, raw) if with_raw else (X, y, feats)


def split_indices(strat, seed, val_size=0.1, test_size=0.2):
    """Stratified 70/10/20 split of row indices."""
    idx = np.arange(len(strat))
    tv, te = train_test_split(idx, test_size=test_size, stratify=strat, random_state=seed)
    tr, va = train_test_split(tv, test_size=val_size / (1 - test_size), stratify=strat[tv], random_state=seed)
    return tr, va, te


def prepare(X, y, seed, time_steps=5, strat=None, drop=None):
    """
    Signed log, clip, stratified split, train-fit robust scaler, padded windows.
    strat: labels to stratify on (default y). drop: bool mask of rows kept out of train and
    val (still in test); windows are built after dropping, so dropped rows never leak in.
    """
    tr, va, te = split_indices(y if strat is None else strat, seed)
    if drop is not None:
        tr, va = tr[~drop[tr]], va[~drop[va]]
    X = np.clip(np.sign(X) * np.log1p(np.abs(X)), -50, 50)
    scaler = RobustScaler().fit(X[tr])
    out = {"idx_test": te}
    for part, rows in (("train", tr), ("val", va), ("test", te)):
        arr = scaler.transform(X[rows]).astype(np.float32)
        out[f"X_{part}"], out[f"y_{part}"] = arr, y[rows]
        out[f"X_{part}_seq"] = windows(arr, time_steps)
    return out


def windows(X, time_steps):
    """One window per row, ending at that row; the first rows are zero-padded so none is dropped."""
    padded = np.vstack([np.zeros((time_steps - 1, X.shape[1]), np.float32), X])
    seqs = np.lib.stride_tricks.sliding_window_view(padded, (time_steps, X.shape[1]))
    return np.ascontiguousarray(seqs.reshape(-1, time_steps, X.shape[1]))


def class_weights(y):
    """Inverse-frequency weights N / (C * n_c), clipped to [0.5, 5]; the hybrid model's formula."""
    classes, counts = np.unique(y, return_counts=True)
    w = np.clip(len(y) / (len(classes) * counts), 0.5, 5.0)
    return {int(c): float(v) for c, v in zip(classes, w)}
