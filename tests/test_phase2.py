"""Tests for Phase 2: hybrid model, DANN, calibration."""
import pytest
import torch
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.hybrid_dl import HybridCNNBiLSTMAttention, train_hybrid, predict_hybrid
from src.models.dann import DANN, GradientReversal
from src.models.calibration import TemperatureScaler, compute_ece


def test_hybrid_forward():
    model = HybridCNNBiLSTMAttention(n_features=20, n_classes=5)
    x = torch.randn(8, 5, 20)
    out = model(x)
    assert out.shape == (8, 5)


def test_hybrid_extract_features():
    model = HybridCNNBiLSTMAttention(n_features=20, n_classes=5)
    x = torch.randn(8, 5, 20)
    feat = model.extract_features(x)
    assert feat.shape == (8, 256)


def test_dann_forward():
    model = DANN(n_features=20, n_classes=5, n_domains=3)
    x = torch.randn(8, 5, 20)
    threat, domain = model(x, alpha=0.5)
    assert threat.shape == (8, 5)
    assert domain.shape == (8, 3)


def test_gradient_reversal():
    x = torch.randn(4, 8, requires_grad=True)
    y = GradientReversal.apply(x, 1.0)
    loss = y.sum()
    loss.backward()
    # Gradient should be -1 * ones (reversed)
    assert torch.allclose(x.grad, -torch.ones_like(x))


def test_temperature_scaler():
    scaler = TemperatureScaler()
    logits = torch.randn(16, 5)
    scaled = scaler(logits)
    assert scaled.shape == logits.shape
    # Temperature > 1 should reduce magnitude
    assert scaled.abs().mean() < logits.abs().mean()


def test_ece_perfect():
    # Perfect calibration: 100% confidence and 100% correct
    probs = np.eye(3)[np.array([0, 1, 2, 0, 1])]
    labels = np.array([0, 1, 2, 0, 1])
    ece = compute_ece(probs, labels)
    assert ece < 0.01


def test_train_hybrid_small():
    """Smoke test: train on tiny data, loss decreases."""
    np.random.seed(42)
    X = np.random.randn(100, 5, 20).astype(np.float32)
    y = np.random.randint(0, 5, 100)
    model, hist = train_hybrid(X, y, X, y, n_features=20, epochs=5, batch_size=32)
    assert hist["train_loss"][-1] < hist["train_loss"][0]
