"""
Tests for live behavioral feature extraction and scaling.
"""
import time
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.live.feature_extractor import LiveFeatureExtractor
from src.data.dataset_loader import FEATURE_COLS


def test_feature_extractor_output_shape():
    """5-packet window produces (1, 5, 20) array."""
    extractor = LiveFeatureExtractor(scaler_path=None, window_size=5)
    packets = []
    now = time.time()
    for i in range(5):
        pkt = {
            "timestamp": now + i * 0.01,
            "length": 100,
            "payload_length": 60,
            "protocol": "TCP",
            "src_ip": "192.168.1.10",
            "dst_ip": "192.168.1.100",
            "src_port": 10000 + i,
            "dst_port": 80,
            "flags": "A",
        }
        packets.append(pkt)

    out = extractor.extract(packets)
    assert isinstance(out, np.ndarray)
    assert out.shape == (1, 5, 20)
    assert not np.isnan(out).any()
    assert not np.isinf(out).any()


def test_feature_extractor_known_syn_flood():
    """Synthetic SYN packets produce high f_syn_ratio and f_rate."""
    extractor = LiveFeatureExtractor(scaler_path=None, window_size=5)
    packets = []
    now = time.time()
    for i in range(5):
        pkt = {
            "timestamp": now + i * 0.001,  # very rapid bursts
            "length": 64,
            "payload_length": 0,
            "protocol": "TCP",
            "src_ip": "192.168.1.50",
            "dst_ip": "192.168.1.100",
            "src_port": 20000 + i,
            "dst_port": 80,
            "flags": "S",  # SYN flag
        }
        packets.append(pkt)

    feats = extractor.extract_features_dict(packets)
    assert feats["f_syn_ratio"] == 1.0
    assert feats["f_control_ratio"] == 1.0
    assert feats["f_rate"] > 1000.0


def test_feature_extractor_known_normal():
    """Synthetic HTTP traffic produces low control ratio and non-zero payload ratio."""
    extractor = LiveFeatureExtractor(scaler_path=None, window_size=5)
    packets = []
    now = time.time()
    for i in range(5):
        pkt = {
            "timestamp": now + i * 0.1,  # normal pacing
            "length": 800,
            "payload_length": 760,
            "protocol": "TCP",
            "src_ip": "192.168.1.20",
            "dst_ip": "192.168.1.100",
            "src_port": 45000 + i,
            "dst_port": 443,
            "flags": "PA",  # PSH+ACK data
        }
        packets.append(pkt)

    feats = extractor.extract_features_dict(packets)
    assert feats["f_syn_ratio"] == 0.0
    assert feats["f_payload_ratio"] > 1.0


def test_feature_extractor_scaler_consistency():
    """Output remains bounded within reasonable scaling bounds."""
    extractor = LiveFeatureExtractor(scaler_path="models/saved/scaler.pkl", window_size=5)
    packets = []
    now = time.time()
    for i in range(5):
        pkt = {
            "timestamp": now + i * 0.05,
            "length": 128,
            "payload_length": 80,
            "protocol": "TCP",
            "src_ip": "10.0.0.1",
            "dst_ip": "10.0.0.2",
            "src_port": 1234,
            "dst_port": 80,
            "flags": "A",
        }
        packets.append(pkt)

    out = extractor.extract(packets)
    assert out.shape == (1, 5, 20)
    assert (out >= -50.0).all() and (out <= 50.0).all()

