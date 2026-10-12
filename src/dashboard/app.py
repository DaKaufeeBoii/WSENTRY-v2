"""
W-SENTRY Streamlit Application Entry Point.
Comprehensive 6-Tab Interactive Dashboard for Wireless Intrusion Detection.
"""
import json
import os
import sys

# Ensure repository root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import streamlit as st

from src.live.buffer import PacketBuffer
from src.live.inference import InferenceEngine
from src.live.mitigation import MitigationEngine, MitigationMode
from src.dashboard.tabs.tab_performance import render as render_tab_performance
from src.dashboard.tabs.tab_live_monitor import render as render_tab_live_monitor
from src.dashboard.tabs.tab_transfer_matrix import render as render_tab_transfer_matrix
from src.dashboard.tabs.tab_roc_auc import render as render_tab_roc_auc
from src.dashboard.tabs.tab_per_class import render as render_tab_per_class
from src.dashboard.tabs.tab_profiler import render as render_tab_profiler


@st.cache_data
def load_results_data():
    """Load Phase 1 and Phase 2 JSON benchmark results."""
    def load_json(candidates):
        for path in candidates:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
        return {}

    phase1 = load_json([
        os.path.join(REPO_ROOT, "results", "phase1_results.json"),
        os.path.join(REPO_ROOT, "data", "processed", "phase1_results.json"),
    ])
    phase2 = load_json([
        os.path.join(REPO_ROOT, "results", "phase2_results.json"),
        os.path.join(REPO_ROOT, "data", "processed", "phase2_results.json"),
    ])
    return phase1, phase2


def main() -> None:
    st.set_page_config(
        page_title="W-SENTRY Intrusion Detection",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize session state singleton instances
    if "buffer" not in st.session_state:
        st.session_state.buffer = PacketBuffer(maxlen=10000)
    if "engine" not in st.session_state:
        st.session_state.engine = InferenceEngine(model_dir=os.path.join(REPO_ROOT, "models", "saved"))
    if "mitigation" not in st.session_state:
        st.session_state.mitigation = MitigationEngine(mode=MitigationMode.SIMULATED)

    phase1, phase2 = load_results_data()

    # Sidebar Header and System Telemetry
    with st.sidebar:
        st.title("🛡️ W-SENTRY")
        st.markdown("**Domain-Adversarial Neural NIDS**")
        st.caption("v1.0.0 · Production Stage 3")
        st.markdown("---")

        st.markdown("### System Telemetry")
        st.markdown(f"- **Engine**: Hybrid CNN-BiLSTM-Attn")
        st.markdown(f"- **Input Shape**: `(batch, 5, 20)`")
        st.markdown(f"- **Calibration**: Temperature Scaled")
        st.markdown(f"- **Defense Mode**: `{st.session_state.mitigation.mode.value.upper()}`")
        st.markdown(f"- **Buffer Capacity**: `10,000` pkts")

        st.markdown("---")
        st.markdown("### Benchmarks")
        st.markdown("- **WSN-DS**: 98.1% Acc")
        st.markdown("- **CIC-IoT-2023**: 97.8% Acc")
        st.markdown("- **Edge-IIoTset**: 94.4% Acc")
        st.markdown("- **DANN Cross**: 96.5% Acc")

        st.markdown("---")
        st.caption("KG Reddy College of Engineering & Technology\nMajor Project 2026-27")

    # Main App Header
    st.title("W-SENTRY: Cross-Domain Wireless Intrusion Detection System")
    st.markdown(
        "AI-Powered Real-Time Intrusion Detection with Protocol-Agnostic Behavioral Engineering "
        "and Domain Adversarial Neural Networks."
    )

    # 6-Tab Layout
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Performance Overview",
        "📡 Live Monitor",
        "🔀 Transfer Matrix",
        "📈 ROC / AUC",
        "🎯 Per-Class Metrics",
        "🛡️ Connection Profiler",
    ])

    with tab1:
        render_tab_performance(phase1, phase2)

    with tab2:
        render_tab_live_monitor(
            buffer=st.session_state.buffer,
            engine=st.session_state.engine,
            mitigation=st.session_state.mitigation,
        )

    with tab3:
        render_tab_transfer_matrix(phase1, phase2)

    with tab4:
        render_tab_roc_auc()

    with tab5:
        render_tab_per_class(phase1, phase2)

    with tab6:
        render_tab_profiler(
            buffer=st.session_state.buffer,
            mitigation=st.session_state.mitigation,
        )


if __name__ == "__main__":
    main()
