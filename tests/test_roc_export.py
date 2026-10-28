"""Tests for the ROC export and the seeding helper."""
import json

import numpy as np
import pytest

from src.eval.roc_export import export_roc
from src.utils import set_seed

N = 600
CLASSES = [0, 2, 3, 4]  # mirrors CIC/Edge: no Jamming class present


@pytest.fixture
def synthetic():
    """Informative-but-imperfect probabilities over 4 classes."""
    rng = np.random.RandomState(0)
    y_true = rng.randint(0, len(CLASSES), N)
    probs = rng.rand(N, len(CLASSES)) * 0.3
    probs[np.arange(N), y_true] += 0.7
    probs = probs / probs.sum(axis=1, keepdims=True)
    return y_true, probs.astype(np.float32)


def _run(tmp_path, y_true, probs, name="CIC", **kw):
    return export_roc(
        {name: {"y_true": y_true, "probs": probs, "classes": CLASSES}},
        npz_path=str(tmp_path / "roc.npz"),
        json_path=str(tmp_path / "roc.json"),
        **kw,
    )[name]


def test_one_curve_per_class_with_sane_auc(tmp_path, synthetic):
    s = _run(tmp_path, *synthetic)
    assert s["classes"] == CLASSES
    assert len(s["curves"]) == len(CLASSES)
    assert 0.8 < s["macro_auc"] <= 1.0
    assert s["micro_auc"] is not None and 0.8 < s["micro_auc"] <= 1.0
    assert {c["class_id"] for c in s["curves"]} == set(CLASSES)


def test_curves_span_the_unit_square_and_are_monotone(tmp_path, synthetic):
    s = _run(tmp_path, *synthetic)
    for c in s["curves"]:
        assert c["fpr"][0] == 0.0 and c["tpr"][0] == 0.0
        assert c["fpr"][-1] == 1.0 and c["tpr"][-1] == 1.0
        assert all(b >= a for a, b in zip(c["fpr"], c["fpr"][1:]))
        assert all(b >= a for a, b in zip(c["tpr"], c["tpr"][1:]))


def test_downsampling_respects_max_points(tmp_path, synthetic):
    s = _run(tmp_path, *synthetic, max_points=25)
    for c in s["curves"]:
        assert len(c["fpr"]) == len(c["tpr"]) <= 25


def test_absent_class_is_skipped_not_fatal(tmp_path, synthetic):
    y_true, probs = synthetic
    y_missing = np.where(y_true == 3, 0, y_true)  # column index 3 (class 4) now unused
    s = _run(tmp_path, y_missing, probs, name="Edge")
    assert len(s["curves"]) == len(CLASSES) - 1
    assert CLASSES[3] not in {c["class_id"] for c in s["curves"]}


def test_npz_keeps_full_fidelity(tmp_path, synthetic):
    y_true, probs = synthetic
    _run(tmp_path, y_true, probs)
    z = np.load(tmp_path / "roc.npz")
    assert z["CIC__probs"].shape == (N, len(CLASSES))
    assert np.array_equal(z["CIC__y_true"], y_true)
    assert np.array_equal(z["CIC__classes"], np.asarray(CLASSES))
    # Probabilities survive the round-trip, so ROC can be recomputed later.
    assert np.allclose(z["CIC__probs"], probs, atol=1e-6)


def test_json_is_valid_and_matches_summary(tmp_path, synthetic):
    s = _run(tmp_path, *synthetic)
    with open(tmp_path / "roc.json") as f:
        loaded = json.load(f)
    assert loaded["CIC"]["macro_auc"] == s["macro_auc"]
    assert loaded["CIC"]["classes"] == CLASSES


def test_set_seed_makes_numpy_deterministic():
    set_seed(7)
    a = np.random.rand(5)
    set_seed(7)
    b = np.random.rand(5)
    assert np.array_equal(a, b)


def test_set_seed_makes_torch_deterministic():
    torch = pytest.importorskip("torch")
    set_seed(13)
    a = torch.rand(5)
    set_seed(13)
    b = torch.rand(5)
    assert torch.equal(a, b)
