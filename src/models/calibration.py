"""
Temperature scaling for confidence calibration.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from torch.utils.data import DataLoader, TensorDataset


class TemperatureScaler(nn.Module):
    """Learns a single temperature parameter to calibrate softmax probabilities."""
    def __init__(self):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1) * 1.5)

    def forward(self, logits):
        return logits / self.temperature


def fit_temperature(model, X_val, y_val, batch_size=512, device="cpu", max_iter=100):
    """Fit temperature on validation set. Returns TemperatureScaler."""
    scaler = TemperatureScaler().to(device)
    optimizer = torch.optim.LBFGS([scaler.temperature], lr=0.01, max_iter=max_iter)
    criterion = nn.CrossEntropyLoss()

    # Collect logits
    model.eval()
    ds = TensorDataset(torch.tensor(X_val))
    dl = DataLoader(ds, batch_size=batch_size)
    all_logits = []
    with torch.no_grad():
        for (xb,) in dl:
            out = model(xb.to(device))
            all_logits.append(out.cpu())
    logits = torch.cat(all_logits).to(device)
    labels = torch.tensor(y_val, dtype=torch.long).to(device)

    def closure():
        optimizer.zero_grad()
        loss = criterion(scaler(logits), labels)
        loss.backward()
        return loss

    optimizer.step(closure)
    return scaler


def compute_ece(probs, labels, n_bins=15):
    """Expected Calibration Error."""
    confidences = np.max(probs, axis=1)
    predictions = np.argmax(probs, axis=1)
    accuracies = (predictions == labels).astype(float)

    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
        if mask.sum() == 0:
            continue
        bin_acc = accuracies[mask].mean()
        bin_conf = confidences[mask].mean()
        ece += mask.sum() / len(labels) * abs(bin_acc - bin_conf)
    return ece


def calibrated_predict(model, scaler, X_test, batch_size=512, device="cpu"):
    """Predict with temperature-scaled probabilities."""
    model.eval()
    ds = TensorDataset(torch.tensor(X_test))
    dl = DataLoader(ds, batch_size=batch_size)
    preds, probs = [], []
    with torch.no_grad():
        for (xb,) in dl:
            logits = model(xb.to(device))
            scaled = scaler(logits)
            p = F.softmax(scaled, dim=1)
            preds.append(scaled.argmax(1).cpu().numpy())
            probs.append(p.cpu().numpy())
    return np.concatenate(preds), np.concatenate(probs)
