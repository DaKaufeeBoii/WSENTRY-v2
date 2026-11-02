"""
W-SENTRY SOC Dashboard: Streamlit main entry point.
Visualizes Phase 1/2 results and runs real-time network capture, classification, and mitigation.
"""
import os
import sys
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

from src.dashboard.tabs import (
    tab_performance,
    tab_live_monitor,
    tab_transfer_matrix,
    tab_roc_auc,
    tab_per_class,
    tab_profiler,
)
from src.live.buffer import PacketBuffer
from src.live.inference import InferenceEngine
from src.live.mitigation import MitigationEngine
from src.live.inference_thread import InferenceThread


@st.cache_data
def load_results():
    """Load Phase 1 and Phase 2 JSON results."""
    p1_path = os.path.join(PROJECT_ROOT, "data", "processed", "phase1_results.json")
    p2_path = os.path.join(PROJECT_ROOT, "data", "processed", "phase2_results.json")

    phase1, phase2 = {}, {}
    if os.path.exists(p1_path):
        with open(p1_path, "r") as f:
            phase1 = json.load(f)
    if os.path.exists(p2_path):
        with open(p2_path, "r") as f:
            phase2 = json.load(f)

    return phase1, phase2


def init_session_state():
    """Initialize persistent background engines and buffers."""
    if "buffer" not in st.session_state:
        st.session_state.buffer = PacketBuffer(maxlen=10000)

    if "engine" not in st.session_state:
        model_dir = os.path.join(PROJECT_ROOT, "models", "saved")
        st.session_state.engine = InferenceEngine(model_dir=model_dir)

    if "mitigation" not in st.session_state:
        st.session_state.mitigation = MitigationEngine()

    if "capture" not in st.session_state:
        st.session_state.capture = None

    if "is_capturing" not in st.session_state:
        st.session_state.is_capturing = False

    if "inference_thread" not in st.session_state or not st.session_state.inference_thread.is_alive():
        inf_thread = InferenceThread(
            buffer=st.session_state.buffer,
            engine=st.session_state.engine,
            mitigation=st.session_state.mitigation,
            poll_interval=0.1,
        )
        inf_thread.start()
        st.session_state.inference_thread = inf_thread


def main():
    st.set_page_config(
        page_title="W-SENTRY SOC Dashboard",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    init_session_state()
    phase1, phase2 = load_results()

    # Title Banner
    col_t1, col_t2 = st.columns([4, 1])
    with col_t1:
        st.title("🛡️ W-SENTRY Security Operations Center")
        st.caption(
            "Cross-Domain Wireless Network Intrusion Detection & Autonomous Prevention System | "
            "Hybrid CNN-BiLSTM-Attention with DANN Adaptation"
        )
    with col_t2:
        st.markdown(
            "<div style='text-align: right; padding-top: 15px;'>"
            "<span style='color: #00d4ff; font-weight: bold;'>SYSTEM ONLINE</span><br>"
            "<small style='color: #94a3b8;'>v3.0.0 Live</small></div>",
            unsafe_allow_html=True
        )

    # Auto-refresh when live capture is running
    if st.session_state.get("is_capturing", False) and HAS_AUTOREFRESH:
        st_autorefresh(interval=2000, key="live_refresh")

    # 6-Tab Layout
    tabs = st.tabs([
        "📊 Performance Overview",
        "📡 Live Monitor",
        "🔄 Transfer Matrix",
        "📈 ROC / AUC Curves",
        "🎯 Per-Class Metrics",
        "🔒 Connection Profiler & Mitigation",
    ])

    with tabs[0]:
        tab_performance.render(phase1, phase2)

    with tabs[1]:
        tab_live_monitor.render(
            st.session_state.buffer,
            st.session_state.engine,
            st.session_state.capture,
        )

    with tabs[2]:
        tab_transfer_matrix.render(phase1, phase2)

    with tabs[3]:
        tab_roc_auc.render()

    with tabs[4]:
        tab_per_class.render(phase1, phase2)

    with tabs[5]:
        tab_profiler.render(
            st.session_state.buffer,
            st.session_state.mitigation,
        )


if __name__ == "__main__":
    main()

