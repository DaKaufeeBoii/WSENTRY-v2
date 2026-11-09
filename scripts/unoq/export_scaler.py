"""Export the RobustScaler as JSON so the board needs no scikit-learn: x' = (x - center) / scale."""
import json
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parents[2]
s = joblib.load(ROOT / "models" / "saved" / "scaler.pkl")
(ROOT / "models" / "saved" / "scaler.json").write_text(
    json.dumps({"center": s.center_.tolist(), "scale": s.scale_.tolist()}))
print("wrote models/saved/scaler.json")
