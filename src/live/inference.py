"""
Live inference engine with temperature scaling and calibrated softmax.
"""
import json
import os
from typing import List, Tuple, Dict, Any, Optional

import numpy as np
import torch
import torch.nn.functional as F

from src.models.hybrid_dl import HybridCNNBiLSTMAttention
from src.models.calibration import TemperatureScaler

THREAT_LABELS: Dict[int, str] = {
    0: "Normal",
    1: "Jamming",
    2: "Spoofing",
    3: "DoS_Flood",
    4: "Intrusion_Probe",
}


class InferenceEngine:
    """
    Loads trained Hybrid CNN-BiLSTM-Attention model + temperature scaler.
    Provides fast, calibrated single-window and batched inference on CPU or GPU.
    """

    def __init__(self, model_dir: str = "models/saved/", device: str = "cpu") -> None:
        self.model_dir = model_dir
        self.device = torch.device(device if (device == "cpu" or torch.cuda.is_available()) else "cpu")

        # Load config or default
        config_path = os.path.join(model_dir, "model_config.json")
        model_path = os.path.join(model_dir, "hybrid_model.pt")
        temp_path = os.path.join(model_dir, "temp_scaler.pt")

        n_features = 20
        n_classes = 5
        hidden_dim = 128

        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    cfg = json.load(f)
                    n_features = cfg.get("n_features", 20)
                    n_classes = cfg.get("n_classes", 5)
                    hidden_dim = cfg.get("hidden_dim", 128)
            except Exception:
                pass

        self.n_features = n_features
        self.n_classes = n_classes
        self.hidden_dim = hidden_dim

        # Initialize network
        self.model = HybridCNNBiLSTMAttention(
            n_features=n_features,
            n_classes=n_classes,
            hidden_dim=hidden_dim,
        ).to(self.device)

        # Initialize temperature scaler
        self.temp_scaler = TemperatureScaler().to(self.device)

        # Load weights if available
        if os.path.exists(model_path):
            try:
                state_dict = torch.load(model_path, map_location=self.device, weights_only=True)
                self.model.load_state_dict(state_dict)
            except Exception:
                pass

        if os.path.exists(temp_path):
            try:
                temp_state = torch.load(temp_path, map_location=self.device, weights_only=True)
                self.temp_scaler.load_state_dict(temp_state)
            except Exception:
                pass

        self.model.eval()
        self.temp_scaler.eval()

    def predict(self, features: np.ndarray) -> Tuple[int, float, str]:
        """
        Run inference on a single sequence window.
        Args:
            features: np.ndarray of shape (1, time_steps, n_features) or (time_steps, n_features).
        Returns:
            (predicted_class, confidence, label)
        """
        if features.ndim == 2:
            features = np.expand_dims(features, axis=0)

        probs = self.get_probabilities(features)
        pred_cls = int(np.argmax(probs[0]))
        confidence = float(probs[0][pred_cls])
        label = THREAT_LABELS.get(pred_cls, "Unknown")
        return pred_cls, confidence, label

    def predict_batch(self, features: np.ndarray) -> List[Tuple[int, float, str]]:
        """
        Batch inference for multiple windows.
        Args:
            features: np.ndarray of shape (batch, time_steps, n_features).
        Returns:
            List of (predicted_class, confidence, label)
        """
        if len(features) == 0:
            return []
        if features.ndim == 2:
            features = np.expand_dims(features, axis=0)

        probs = self.get_probabilities(features)
        results = []
        for p in probs:
            pred_cls = int(np.argmax(p))
            confidence = float(p[pred_cls])
            label = THREAT_LABELS.get(pred_cls, "Unknown")
            results.append((pred_cls, confidence, label))
        return results

    def get_probabilities(self, features: np.ndarray) -> np.ndarray:
        """
        Compute full calibrated probability distribution.
        Args:
            features: np.ndarray of shape (batch, time_steps, n_features).
        Returns:
            np.ndarray of shape (batch, n_classes).
        """
        if features.ndim == 2:
            features = np.expand_dims(features, axis=0)

        with torch.no_grad():
            tensor_x = torch.tensor(features, dtype=torch.float32, device=self.device)
            # Ensure feature dimension matches model expectation
            if tensor_x.shape[-1] != self.n_features:
                if tensor_x.shape[-1] < self.n_features:
                    pad = torch.zeros(
                        (tensor_x.shape[0], tensor_x.shape[1], self.n_features - tensor_x.shape[-1]),
                        dtype=torch.float32,
                        device=self.device,
                    )
                    tensor_x = torch.cat([tensor_x, pad], dim=-1)
                else:
                    tensor_x = tensor_x[:, :, :self.n_features]

            logits = self.model(tensor_x)
            scaled_logits = self.temp_scaler(logits)
            probs = F.softmax(scaled_logits, dim=-1).cpu().numpy()
            return probs
