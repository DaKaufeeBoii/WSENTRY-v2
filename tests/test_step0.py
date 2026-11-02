"""
Tests for the Step 0 pipeline: scoring, padded windows, class weights.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.data.full_features import class_weights, prepare, split_indices, windows
from src.eval.metrics import score


def test_score_matches_hand_computed_values():
    m = score([0, 0, 0, 1], [0, 0, 1, 1])
    assert m["accuracy"] == 0.75
    assert m["majority_baseline"] == 0.75
    # class 0: P=1, R=2/3, F1=0.8; class 1: P=0.5, R=1, F1=2/3
    assert abs(m["macro_f1"] - (0.8 + 2 / 3) / 2) < 1e-9
    assert abs(m["far"] - 1 / 3) < 1e-9
    assert m["confusion_matrix"] == [[2, 1], [0, 1]]


def test_score_auc_uses_probability_columns_by_class():
    proba = np.array([[0.9, 0.1], [0.8, 0.2], [0.3, 0.7], [0.2, 0.8]])
    m = score([0, 0, 2, 2], [0, 0, 2, 2], proba, proba_classes=[0, 2])
    assert m["roc_auc"] == 1.0 and m["pr_auc"] == 1.0


def test_every_test_row_gets_a_window():
    rng = np.random.default_rng(0)
    X, y = rng.normal(size=(200, 3)), np.repeat([0, 1], 100)
    data = prepare(X, y, seed=1, time_steps=5)
    assert len(data["X_test_seq"]) == len(data["y_test"]) == 40
    assert np.allclose(data["X_test_seq"][7, -1], data["X_test"][7])
    assert not windows(np.ones((3, 2), np.float32), 5)[0, :4].any()  # padding is zeros


def test_split_matches_the_original_two_stage_split():
    from sklearn.model_selection import train_test_split
    rng = np.random.default_rng(0)
    X, y = rng.normal(size=(300, 2)), rng.integers(0, 3, 300)
    X_tv, X_te, y_tv, _ = train_test_split(X, y, test_size=0.2, stratify=y, random_state=4)
    X_tr, _, _, _ = train_test_split(X_tv, y_tv, test_size=0.125, stratify=y_tv, random_state=4)
    tr, _, te = split_indices(y, 4)
    assert np.array_equal(X[te], X_te) and np.array_equal(X[tr], X_tr)


def test_dropped_rows_stay_out_of_train_and_val_but_not_test():
    rng = np.random.default_rng(0)
    X, y = rng.normal(size=(400, 3)), np.repeat([0, 1, 2, 3], 100)
    drop = y == 3
    data = prepare(X, y, seed=0, strat=y, drop=drop)
    assert 3 not in data["y_train"] and 3 not in data["y_val"] and 3 in data["y_test"]
    assert len(data["X_train_seq"]) == len(data["y_train"])


def test_class_weights_are_inverse_frequency_and_clipped():
    w = class_weights(np.array([0] * 98 + [1] * 2))
    assert w[1] == 5.0 and abs(w[0] - 100 / (2 * 98)) < 1e-9
