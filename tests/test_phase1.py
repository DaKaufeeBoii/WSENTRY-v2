"""
Tests for Phase 1: data loading, preprocessing, baselines.
"""
import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.data.dataset_loader import load_wsn, load_cic, load_edge, FEATURE_COLS
from src.features.preprocessor import preprocess


def test_wsn_loads():
    df = load_wsn(max_rows=1000)
    assert len(df) > 0
    for col in FEATURE_COLS:
        assert col in df.columns, f"Missing {col}"
    assert "threat_class" in df.columns
    assert df["threat_class"].isin([0, 1, 2, 3, 4]).all()


def test_cic_loads():
    df = load_cic(max_rows=1000)
    assert len(df) > 0
    for col in FEATURE_COLS:
        assert col in df.columns
    assert df["threat_class"].isin([0, 1, 2, 3, 4]).all()


def test_edge_loads():
    df = load_edge(max_rows=5000)
    assert len(df) > 0
    for col in FEATURE_COLS:
        assert col in df.columns
    assert df["threat_class"].isin([0, 1, 2, 3, 4]).all()


def test_no_nan_inf():
    for loader in [load_wsn, load_cic]:
        df = loader(max_rows=500)
        vals = df[FEATURE_COLS].values
        assert not np.isnan(vals).any(), f"NaN in {loader.__name__}"
        assert not np.isinf(vals).any(), f"Inf in {loader.__name__}"
    # ponytail: Edge loads full 2.2M first, skip in unit tests


def test_preprocess_shapes():
    df = load_wsn(max_rows=500)
    result = preprocess(df, smote=False, time_steps=5)
    n_features = len(FEATURE_COLS)
    # Sequences should be (N, 5, 20)
    assert result["X_train_seq"].shape[1] == 5
    assert result["X_train_seq"].shape[2] == n_features
    assert len(result["y_train_seq"]) == result["X_train_seq"].shape[0]
