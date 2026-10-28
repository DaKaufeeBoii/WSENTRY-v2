"""
Model inference pipeline for real-time classification using Hybrid CNN-BiLSTM-Attention.
"""
import os
import json
from typing import Tuple, List, Optional
import numpy as np
import torch
import torch.nn.functional as F

from src.models.hybrid_dl import HybridCNNBiLSTMAttention
from src.models.calibration import TemperatureScaler


THREAT_LABELS = {
    0: "Normal",
    1: "Jamming",
    2: "Spoofing",
    3: "DoS_Flood",
    4: "Intrusion_Probe",
}


class InferenceEngine:
    """
    Loads Hybrid CNN-BiLSTM-Attention model checkpoint and TemperatureScaler,
    providing low-latency CPU batched inference.
    """

    def __init__(self, model_dir: str = "models/saved/", device: str = "cpu") -> None:
        self.device = torch.device(device)
        self.model_dir = model_dir
        self.config_path = os.path.join(model_dir, "model_config.json")
        self.model_path = os.path.join(model_dir, "hybrid_model.pt")
        self.scaler_path = os.path.join(model_dir, "temp_scaler.pt")

        # Load config or default
        n_features = 20
        n_classes = 5
        hidden_dim = 128
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    cfg = json.load(f)
                    n_features = cfg.get("n_features", n_features)
                    n_classes = cfg.get("n_classes", n_classes)
                    hidden_dim = cfg.get("hidden_dim", hidden_dim)
            except Exception as e:
                print(f"[InferenceEngine] Error loading config: {e}")

        # Instantiate model
        self.model = HybridCNNBiLSTMAttention(
            n_features=n_features,
            n_classes=n_classes,
            hidden_dim=hidden_dim,
            dropout=0.0
        ).to(self.device)

        if os.path.exists(self.model_path):
            try:
                state_dict = torch.load(self.model_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                print(f"[InferenceEngine] Loaded model checkpoint from {self.model_path}")
            except Exception as e:
                print(f"[InferenceEngine] Warning: Could not load state_dict ({e})")

        self.model.eval()

        # Instantiate temperature scaler
        self.temp_scaler = TemperatureScaler().to(self.device)
        if os.path.exists(self.scaler_path):
            try:
                scaler_dict = torch.load(self.scaler_path, map_location=self.device)
                self.temp_scaler.load_state_dict(scaler_dict)
            except Exception as e:
                print(f"[InferenceEngine] Warning: Could not load temp_scaler ({e})")
        self.temp_scaler.eval()

    @torch.no_grad()
    def get_probabilities(self, features: np.ndarray) -> np.ndarray:
        """
        Computes calibrated softmax probabilities for input tensor.
        Input shape: (batch_size, time_steps, n_features)
        Returns: (batch_size, n_classes) float numpy array.
        """
        if isinstance(features, list):
            features = np.array(features)
        if features.ndim == 2:
            features = np.expand_dims(features, axis=0)

        x_tensor = torch.tensor(features, dtype=torch.float32, device=self.device)
        logits = self.model(x_tensor)
        calibrated_logits = self.temp_scaler(logits)
        probs = F.softmax(calibrated_logits, dim=-1)
        return probs.cpu().numpy()

    def predict(self, features: np.ndarray) -> Tuple[int, float, str]:
        """
        Predicts single sample/window.
        Returns: (predicted_class, confidence, threat_label)
        """
        probs = self.get_probabilities(features)
        pred_class = int(np.argmax(probs[0]))
        confidence = float(probs[0][pred_class])
        label = THREAT_LABELS.get(pred_class, f"Class_{pred_class}")
        return pred_class, confidence, label

    def predict_batch(self, features: np.ndarray) -> List[Tuple[int, float, str]]:
        """
        Predicts batch of windows.
        Returns: list of (predicted_class, confidence, threat_label)
        """
        probs = self.get_probabilities(features)
        results = []
        for p_row in probs:
            pred_class = int(np.argmax(p_row))
            conf = float(p_row[pred_class])
            results.append((pred_class, conf, THREAT_LABELS.get(pred_class, f"Class_{pred_class}")))
        return results

