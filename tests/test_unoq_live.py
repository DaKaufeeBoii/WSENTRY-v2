"""Live-packet chain: shared CIC mapping, scaler export, packets -> windows."""
import json
import os
import struct
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.data.dataset_loader import FEATURE_COLS, cic_behavioral  # noqa: E402
from src.features.ciciot_features import FEATURES  # noqa: E402

FIN, PSH, ACK = 0x01, 0x08, 0x10


def tcp_frame(payload_len, flags, sport=40000, dport=80, ttl=64):
    """Same builder as tests/test_ciciot_features.py: 10.0.0.1 -> 10.0.0.2 over Ethernet."""
    total = 20 + 20 + payload_len
    ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, total, 1, 0, ttl, 6, 0, bytes([10, 0, 0, 1]), bytes([10, 0, 0, 2]))
    tcp = struct.pack("!HHIIBBHHH", sport, dport, 0, 0, 0x50, flags, 1024, 0, 0)
    return b"\xaa" * 6 + b"\xbb" * 6 + b"\x08\x00" + ip + tcp + b"x" * payload_len


def test_cic_behavioral_is_the_training_mapping():
    rng = np.random.RandomState(0)
    df = pd.DataFrame(rng.rand(4, len(FEATURES)) * 10 + 1, columns=FEATURES)
    out = cic_behavioral(df)
    assert list(out.columns) == FEATURE_COLS
    np.testing.assert_allclose(out["f_rate"], df["Rate"])
    np.testing.assert_allclose(out["f_send_recv_ratio"], df["Srate"] / (df["Drate"] + 1))
    np.testing.assert_allclose(out["f_control_ratio"],
                               (df["syn_count"] + df["fin_count"] + df["rst_count"]) / df["Number"])
    np.testing.assert_allclose(out["f_timing"], df["IAT"])


def test_scaler_json_matches_pickle():
    root = Path(__file__).resolve().parents[1] / "models" / "saved"
    sk, js = joblib.load(root / "scaler.pkl"), json.loads((root / "scaler.json").read_text())
    x = np.random.RandomState(1).randn(7, 20)
    np.testing.assert_allclose((x - js["center"]) / np.array(js["scale"]), sk.transform(x), rtol=1e-6)


def test_live_windows_and_top_source(tmp_path):
    from src.live.cic_live import CicLive, top_source
    sj = tmp_path / "s.json"
    sj.write_text(json.dumps({"center": [0.0] * 20, "scale": [1.0] * 20}))
    live = CicLive(sj, block_packets=10)
    frames = [(1.7e9 + 0.001 * i, tcp_frame(i % 50, ACK | PSH)) for i in range(100)]
    w = live.windows(frames)
    assert w.shape == (6, 5, 20) and np.isfinite(w).all()      # 100 frames -> 10 rows -> 6 windows
    assert live.windows(frames[:30]).shape == (3, 5, 20)       # 3 new rows + 4 carried-over rows
    assert top_source(frames) == ("10.0.0.1", 1.0)
    assert top_source(frames, exclude={"10.0.0.1"}) == (None, 0.0)
