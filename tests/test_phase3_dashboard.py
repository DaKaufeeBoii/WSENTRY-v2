"""
Tests for dashboard data sources and contracts (Task 3.1, 3.9).
"""
import json
import os
import pytest

from src.live.inference import THREAT_LABELS


def test_results_json_loadable():
    """phase1_results.json and phase2_results.json parse without error."""
    p1_path = os.path.join("results", "phase1_results.json")
    p2_path = os.path.join("results", "phase2_results.json")

    assert os.path.exists(p1_path), f"{p1_path} missing"
    assert os.path.exists(p2_path), f"{p2_path} missing"

    with open(p1_path, "r", encoding="utf-8") as f:
        p1 = json.load(f)
    with open(p2_path, "r", encoding="utf-8") as f:
        p2 = json.load(f)

    assert "same_dataset" in p1
    assert "native_same_dataset" in p2
    assert "behavioral_transfer_matrix" in p2


def test_transfer_matrix_keys():
    """All 9 source->target pairs exist in both transfer matrices."""
    p1_path = os.path.join("results", "phase1_results.json")
    p2_path = os.path.join("results", "phase2_results.json")

    with open(p1_path, "r", encoding="utf-8") as f:
        p1 = json.load(f)
    with open(p2_path, "r", encoding="utf-8") as f:
        p2 = json.load(f)

    expected_pairs = [
        "WSN→WSN", "WSN→CIC", "WSN→Edge",
        "CIC→WSN", "CIC→CIC", "CIC→Edge",
        "Edge→WSN", "Edge→CIC", "Edge→Edge",
    ]

    p1_matrix = p1["transfer_matrix"]
    p2_matrix = p2["behavioral_transfer_matrix"]

    for pair in expected_pairs:
        # Check standard unicode or ascii arrow
        ascii_pair = pair.replace("→", "->")
        found1 = pair in p1_matrix or ascii_pair in p1_matrix
        found2 = pair in p2_matrix or ascii_pair in p2_matrix
        assert found1, f"Missing pair {pair} in Phase 1 matrix"
        assert found2, f"Missing pair {pair} in Phase 2 matrix"


def test_threat_label_mapping():
    """THREAT_LABELS covers classes 0-4 correctly."""
    assert len(THREAT_LABELS) == 5
    for c in range(5):
        assert c in THREAT_LABELS
    assert THREAT_LABELS[0] == "Normal"
    assert THREAT_LABELS[1] == "Jamming"
    assert THREAT_LABELS[2] == "Spoofing"
    assert THREAT_LABELS[3] == "DoS_Flood"
    assert THREAT_LABELS[4] == "Intrusion_Probe"


def test_classification_report_parsing():
    """Verify that real report strings from phase1_results.json are accurately parsed."""
    from src.dashboard.tabs.tab_per_class import _parse_classification_report

    p1_path = os.path.join("results", "phase1_results.json")
    with open(p1_path, "r", encoding="utf-8") as f:
        p1 = json.load(f)

    for model_name in ["RF_WSN-DS", "RF_CIC-IoT", "RF_Edge-IIoT"]:
        report_str = p1["same_dataset"][model_name]["report"]
        parsed = _parse_classification_report(report_str)
        assert len(parsed) >= 4
        for cls_id, metrics in parsed.items():
            assert 0.0 <= metrics["precision"] <= 1.0
            assert 0.0 <= metrics["recall"] <= 1.0
            assert 0.0 <= metrics["f1"] <= 1.0
            assert metrics["support"] > 0


def test_real_confusion_matrices_shape():
    """Verify that confusion matrices in phase1_results.json are real 2D matrices."""
    p1_path = os.path.join("results", "phase1_results.json")
    with open(p1_path, "r", encoding="utf-8") as f:
        p1 = json.load(f)

    for model_name in ["RF_WSN-DS", "RF_CIC-IoT", "RF_Edge-IIoT"]:
        cm = p1["same_dataset"][model_name]["confusion_matrix"]
        assert isinstance(cm, list)
        n_rows = len(cm)
        assert n_rows >= 4
        for row in cm:
            assert len(row) == n_rows
            assert all(isinstance(val, int) and val >= 0 for val in row)

