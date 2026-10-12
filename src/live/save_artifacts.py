"""
Model and preprocessor artifact exporter for live inference.
"""
import argparse
import json
import os
import joblib
import numpy as np
import torch
from sklearn.preprocessing import RobustScaler

from src.models.hybrid_dl import HybridCNNBiLSTMAttention, train_hybrid
from src.models.calibration import TemperatureScaler, fit_temperature
from src.data.dataset_loader import FEATURE_COLS


def export_model_artifacts(
    dataset_name: str = "wsn",
    output_dir: str = "models/saved/",
    epochs: int = 5,
    device: str = "cpu",
) -> None:
    """
    Exports:
    - models/saved/scaler.pkl
    - models/saved/hybrid_model.pt
    - models/saved/temp_scaler.pt
    - models/saved/model_config.json
    """
    os.makedirs(output_dir, exist_ok=True)
    n_features = len(FEATURE_COLS)  # 20
    n_classes = 5
    hidden_dim = 128
    time_steps = 5

    print(f"[W-SENTRY] Exporting inference artifacts to {output_dir}...")

    # Load real dataset
    try:
        from src.data.dataset_loader import load_wsn, load_cic, load_edge
        from src.features.preprocessor import preprocess

        loader_map = {"wsn": load_wsn, "cic": load_cic, "edge": load_edge}
        if dataset_name.lower() not in loader_map:
            raise ValueError(f"Unknown dataset '{dataset_name}'. Choose from wsn, cic, edge.")

        df = loader_map[dataset_name.lower()](mode="behavioral")
        data = preprocess(df, feature_cols=FEATURE_COLS, smote=False, time_steps=time_steps)
        scaler = data["scaler"]
        X_train = data["X_train_seq"]
        y_train = data["y_train_seq"]
        X_val = data["X_val_seq"]
        y_val = data["y_val_seq"]
        print(f"  Loaded real dataset {dataset_name}: {len(df)} records")
    except Exception as e:
        raise FileNotFoundError(
            f"Cannot export artifacts: real dataset '{dataset_name}' could not be loaded ({e}). "
            "Mock data is disabled. Ensure the raw benchmark CSV files are in data/raw/ "
            "or use the pre-trained artifacts in models/saved/."
        )

    # Train model
    model, _ = train_hybrid(
        X_train, y_train, X_val, y_val,
        n_features=n_features, n_classes=n_classes,
        epochs=epochs, batch_size=128, device=device
    )

    # Fit temperature scaler
    temp_scaler = fit_temperature(model, X_val, y_val, device=device)

    # Save artifacts
    scaler_file = os.path.join(output_dir, "scaler.pkl")
    model_file = os.path.join(output_dir, "hybrid_model.pt")
    temp_file = os.path.join(output_dir, "temp_scaler.pt")
    config_file = os.path.join(output_dir, "model_config.json")

    joblib.dump(scaler, scaler_file)
    torch.save(model.state_dict(), model_file)
    torch.save(temp_scaler.state_dict(), temp_file)

    config_data = {
        "n_features": n_features,
        "n_classes": n_classes,
        "hidden_dim": hidden_dim,
        "time_steps": time_steps,
        "dataset_name": dataset_name,
        "classes": ["Normal", "Jamming", "Spoofing", "DoS_Flood", "Intrusion_Probe"],
    }
    with open(config_file, "w") as f:
        json.dump(config_data, f, indent=2)

    print(f"[W-SENTRY] Artifacts saved successfully:")
    print(f"  - {scaler_file}")
    print(f"  - {model_file}")
    print(f"  - {temp_file}")
    print(f"  - {config_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export W-SENTRY inference artifacts")
    parser.add_argument("--dataset", default="wsn", help="Dataset name (wsn, cic, edge)")
    parser.add_argument("--output-dir", default="models/saved/", help="Output directory")
    parser.add_argument("--epochs", type=int, default=5, help="Training epochs")
    args = parser.parse_args()

    export_model_artifacts(
        dataset_name=args.dataset,
        output_dir=args.output_dir,
        epochs=args.epochs,
    )
