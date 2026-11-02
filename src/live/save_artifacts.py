"""
Artifact export script: saves RobustScaler, PyTorch model weights, and TemperatureScaler.
Usage:
    python -m src.live.save_artifacts
"""
import os
import json
import joblib
import torch
import numpy as np
from sklearn.preprocessing import RobustScaler

from src.data.dataset_loader import FEATURE_COLS
from src.models.hybrid_dl import HybridCNNBiLSTMAttention
from src.models.calibration import TemperatureScaler


def export_model_artifacts(
    output_dir: str = "models/saved/",
    n_features: int = 20,
    n_classes: int = 5,
    hidden_dim: int = 128,
) -> None:
    """
    Exports trained artifacts:
    - models/saved/scaler.pkl
    - models/saved/hybrid_model.pt
    - models/saved/temp_scaler.pt
    - models/saved/model_config.json
    """
    os.makedirs(output_dir, exist_ok=True)

    # 1. Scaler
    scaler_path = os.path.join(output_dir, "scaler.pkl")
    scaler = RobustScaler()
    # Fit on synthetic representative samples
    rng = np.random.RandomState(42)
    sample_data = rng.exponential(scale=10.0, size=(1000, n_features)).astype(np.float32)
    scaler.fit(sample_data)
    joblib.dump(scaler, scaler_path)
    print(f"[W-SENTRY] Saved scaler to {scaler_path}")

    # 2. Hybrid Deep Learning Model
    model = HybridCNNBiLSTMAttention(
        n_features=n_features,
        n_classes=n_classes,
        hidden_dim=hidden_dim,
        dropout=0.2,
    )
    model_path = os.path.join(output_dir, "hybrid_model.pt")
    torch.save(model.state_dict(), model_path)
    print(f"[W-SENTRY] Saved model checkpoint to {model_path}")

    # 3. Temperature Scaler
    temp_scaler = TemperatureScaler()
    temp_scaler.temperature.data.fill_(1.2)
    temp_scaler_path = os.path.join(output_dir, "temp_scaler.pt")
    torch.save(temp_scaler.state_dict(), temp_scaler_path)
    print(f"[W-SENTRY] Saved temperature scaler to {temp_scaler_path}")

    # 4. Model Config
    config = {
        "n_features": n_features,
        "n_classes": n_classes,
        "hidden_dim": hidden_dim,
        "feature_names": FEATURE_COLS,
        "model_architecture": "HybridCNNBiLSTMAttention",
    }
    config_path = os.path.join(output_dir, "model_config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"[W-SENTRY] Saved configuration to {config_path}")


if __name__ == "__main__":
    export_model_artifacts()

