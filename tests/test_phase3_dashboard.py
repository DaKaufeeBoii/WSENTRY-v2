"""
Tests for dashboard static data loading, label mapping, and ROC structures.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.live.inference import THREAT_LABELS
from src.dashboard.precompute_roc import generate_roc_curves_from_results


def test_results_json_loadable():
    """phase1_results.json and phase2_results.json parse without error."""
    p1_path = os.path.join("data", "processed", "phase1_results.json")
    p2_path = os.path.join("data", "processed", "phase2_results.json")

    assert os.path.exists(p1_path), f"Missing {p1_path}"
    assert os.path.exists(p2_path), f"Missing {p2_path}"

    with open(p1_path, "r") as f:
        p1 = json.load(f)
    with open(p2_path, "r") as f:
        p2 = json.load(f)

    assert "same_dataset" in p1
    assert "transfer_matrix" in p1
    assert "native_same_dataset" in p2
    assert "behavioral_transfer_matrix" in p2


def test_transfer_matrix_keys():
    """All 9 source->target pairs exist in both matrices."""
    p1_path = os.path.join("data", "processed", "phase1_results.json")
    p2_path = os.path.join("data", "processed", "phase2_results.json")

    with open(p1_path, "r") as f:
        p1 = json.load(f)
    with open(p2_path, "r") as f:
        p2 = json.load(f)

    domains = ["WSN", "CIC", "Edge"]
    p1_tm = p1["transfer_matrix"]
    p2_tm = p2["behavioral_transfer_matrix"]

    for src in domains:
        for tgt in domains:
            key1 = f"{src}→{tgt}"
            key2 = f"{src}->{tgt}"
            assert key1 in p1_tm or key2 in p1_tm, f"Missing {key1} in phase 1 transfer matrix"
            assert key1 in p2_tm or key2 in p2_tm, f"Missing {key1} in phase 2 transfer matrix"


def test_threat_label_mapping():
    """THREAT_LABELS covers classes 0-4."""
    assert len(THREAT_LABELS) == 5
    for cid in range(5):
        assert cid in THREAT_LABELS
    assert THREAT_LABELS[0] == "Normal"
    assert THREAT_LABELS[1] == "Jamming"
    assert THREAT_LABELS[2] == "Spoofing"
    assert THREAT_LABELS[3] == "DoS_Flood"
    assert THREAT_LABELS[4] == "Intrusion_Probe"


def test_precompute_roc_output():
    """Precompute ROC function returns valid multi-class curves and saves files."""
    summary = generate_roc_curves_from_results(
        output_npz="data/processed/roc_curves.npz",
        output_json="data/processed/roc_curves.json",
    )
    for ds in ["WSN", "CIC", "Edge"]:
        assert ds in summary
        assert "curves" in summary[ds]
        assert len(summary[ds]["curves"]) > 0
        assert summary[ds]["macro_auc"] > 0.8

