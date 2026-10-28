"""
Tests for Phase 1: data loading, preprocessing, baselines.
"""
import pytest
import numpy as np
import pandas as pd
import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data.dataset_loader import load_wsn, load_cic, load_edge, FEATURE_COLS
from src.features.preprocessor import preprocess

WSN_PATH = REPO_ROOT / "data" / "raw" / "WSN-DS.csv"
CIC_PATH = REPO_ROOT / "data" / "raw" / "IoT_Intrusion.csv"
EDGE_PATH = REPO_ROOT / "data" / "raw" / "ML-EdgeIIoT-dataset.csv"

WSN_EXISTS = WSN_PATH.exists()
CIC_EXISTS = CIC_PATH.exists()
EDGE_EXISTS = EDGE_PATH.exists()


@pytest.mark.skipif(not WSN_EXISTS, reason="Raw WSN-DS.csv dataset not found in data/raw/")
def test_wsn_loads():
    df = load_wsn(path=str(WSN_PATH), max_rows=1000)
    assert len(df) > 0
    for col in FEATURE_COLS:
        assert col in df.columns, f"Missing {col}"
    assert "threat_class" in df.columns
    assert df["threat_class"].isin([0, 1, 2, 3, 4]).all()


@pytest.mark.skipif(not CIC_EXISTS, reason="Raw IoT_Intrusion.csv dataset not found in data/raw/")
def test_cic_loads():
    df = load_cic(path=str(CIC_PATH), max_rows=1000)
    assert len(df) > 0
    for col in FEATURE_COLS:
        assert col in df.columns
    assert df["threat_class"].isin([0, 1, 2, 3, 4]).all()


@pytest.mark.skipif(not EDGE_EXISTS, reason="Raw Edge-IIoTset dataset not found in data/raw/")
def test_edge_loads():
    df = load_edge(path=str(EDGE_PATH), max_rows=5000)
    assert len(df) > 0
    for col in FEATURE_COLS:
        assert col in df.columns
    assert df["threat_class"].isin([0, 1, 2, 3, 4]).all()


@pytest.mark.skipif(not (WSN_EXISTS and CIC_EXISTS), reason="Raw datasets not found")
def test_no_nan_inf():
    for loader, p in [(load_wsn, str(WSN_PATH)), (load_cic, str(CIC_PATH))]:
        df = loader(path=p, max_rows=500)
        vals = df[FEATURE_COLS].values
        assert not np.isnan(vals).any(), f"NaN in {loader.__name__}"
        assert not np.isinf(vals).any(), f"Inf in {loader.__name__}"


def test_preprocess_shapes():
    if WSN_EXISTS:
        df = load_wsn(path=str(WSN_PATH), max_rows=500)
    else:
        # Synthetic DataFrame matching FEATURE_COLS + threat_class
        np.random.seed(42)
        n_samples = 300
        data = {col: np.random.randn(n_samples) for col in FEATURE_COLS}
        data["threat_class"] = np.random.choice([0, 1, 2, 3, 4], size=n_samples)
        df = pd.DataFrame(data)

    result = preprocess(df, smote=False, time_steps=5)
    n_features = len(FEATURE_COLS)
    # Sequences should be (N, 5, 20)
    assert result["X_train_seq"].shape[1] == 5
    assert result["X_train_seq"].shape[2] == n_features
    assert len(result["y_train_seq"]) == result["X_train_seq"].shape[0]
