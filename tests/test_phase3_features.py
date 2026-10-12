"""
Tests for live behavioral feature extraction (Task 3.2.3, 3.9).
"""
import time
import numpy as np
import pytest
from scapy.all import IP, TCP

from src.live.feature_extractor import LiveFeatureExtractor
from src.data.dataset_loader import FEATURE_COLS


def test_feature_extractor_output_shape():
    """5-packet window produces (1, 5, 20) array."""
    extractor = LiveFeatureExtractor()
    packets = [
        IP(src="192.168.1.10", dst="192.168.1.1") / TCP(sport=1000 + i, dport=80, flags="S")
        for i in range(5)
    ]
    out = extractor.extract(packets, window_size=5)
    assert isinstance(out, np.ndarray)
    assert out.shape == (1, 5, 20)
    assert len(FEATURE_COLS) == 20


def test_feature_extractor_known_syn_flood():
    """Synthetic SYN packets produce high f_syn_ratio, f_rate."""
    extractor = LiveFeatureExtractor()
    now = time.time()
    packets = []
    for i in range(5):
        pkt = IP(src="192.168.1.50", dst="192.168.1.1") / TCP(sport=5000 + i, dport=80, flags="S")
        pkt.time = now + (i * 0.001)  # High burst rate
        packets.append(pkt)

    parsed = [extractor._parse_packet(p) for p in packets]
    vec = extractor._extract_vector_for_subwindow(parsed)
    feature_dict = dict(zip(FEATURE_COLS, vec))

    assert feature_dict["f_syn_ratio"] == 1.0
    assert feature_dict["f_rate"] > 1000.0  # Fast transmission rate
    assert feature_dict["f_control_ratio"] == 1.0


def test_feature_extractor_known_normal():
    """Synthetic HTTP ACK packets produce normal feature distribution."""
    extractor = LiveFeatureExtractor()
    now = time.time()
    packets = []
    for i in range(5):
        pkt = IP(src="192.168.1.100", dst="192.168.1.1") / TCP(sport=54321, dport=443, flags="A")
        pkt.time = now + (i * 0.1)  # Normal pacing
        packets.append(pkt)

    parsed = [extractor._parse_packet(p) for p in packets]
    vec = extractor._extract_vector_for_subwindow(parsed)
    feature_dict = dict(zip(FEATURE_COLS, vec))

    assert feature_dict["f_syn_ratio"] == 0.0
    assert feature_dict["f_ack_ratio"] == 1.0
    assert feature_dict["f_rate"] < 100000.0


def test_feature_extractor_scaler_consistency():
    """Output range matches normalized finite array."""
    extractor = LiveFeatureExtractor()
    packets = [
        IP(src="10.0.0.1", dst="10.0.0.2") / TCP(sport=80, dport=1234, flags="PA")
        for _ in range(5)
    ]
    out = extractor.extract(packets, window_size=5)
    assert not np.isnan(out).any()
    assert not np.isinf(out).any()
    assert out.dtype == np.float32
