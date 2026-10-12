"""
Tab 2: Live Monitor — Real-time packet capture, inference streaming, and threat analytics.
"""
from datetime import datetime
import time
from typing import Optional
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

from src.live.buffer import PacketBuffer, PacketRecord
from src.live.inference import InferenceEngine, THREAT_LABELS
from src.live.capture import LiveCapture
from src.live.feature_extractor import LiveFeatureExtractor
from src.live.inference_thread import InferenceThread
from src.live.mitigation import MitigationEngine
from src.dashboard.components.charts import create_gauge, apply_dark_theme, CLASS_COLORS, CLASS_NAMES


def render(
    buffer: PacketBuffer,
    engine: InferenceEngine,
    mitigation: MitigationEngine,
) -> None:
    st.subheader("Live Packet Monitor & Threat Classification")
    st.caption("Real-time network traffic sniffing, 20-feature extraction, and calibrated neural inference.")

    # 1. Interface Selection and Control Toolbar
    if "capture_instance" not in st.session_state:
        st.session_state.capture_instance = None
    if "inference_thread_instance" not in st.session_state:
        st.session_state.inference_thread_instance = None

    ifaces = LiveCapture.list_interfaces()
    iface_options = [f"{i['name']} ({i['description']}) — {i['ip']}" for i in ifaces]
    iface_names = [i["name"] for i in ifaces]

    source_mode = st.radio("Capture Source:", ["Live Network Interface (NIC)", "Real PCAP File Replay"], horizontal=True)

    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([2.5, 1.2, 1.2, 1.5])

    pcap_file = None
    selected_iface = iface_names[0] if ifaces else "Default NIC"

    with ctrl_col1:
        if source_mode == "Live Network Interface (NIC)":
            selected_idx = st.selectbox(
                "Network Interface (NIC):",
                range(len(ifaces)),
                format_func=lambda idx: iface_options[idx],
                index=0,
            )
            selected_iface = iface_names[selected_idx] if ifaces else "Default NIC"
        else:
            pcap_file = st.text_input("PCAP Capture File Path:", value="", placeholder="e.g. data/captures/traffic.pcap")

    is_active = (
        st.session_state.capture_instance is not None
        and st.session_state.capture_instance.is_running
    )

    with ctrl_col2:
        st.write("")
        st.write("")
        if not is_active:
            btn_label = "▶ Start Sniffing" if source_mode == "Live Network Interface (NIC)" else "▶ Replay PCAP"
            if st.button(btn_label, type="primary", use_container_width=True):
                feat_extractor = LiveFeatureExtractor()
                cap = LiveCapture(
                    iface=selected_iface,
                    buffer=buffer,
                    feature_extractor=feat_extractor,
                    pcap_path=pcap_file if source_mode != "Live Network Interface (NIC)" else None,
                )
                cap.start()
                st.session_state.capture_instance = cap

                # Start background inference thread with real RobustScaler
                inf_thread = InferenceThread(
                    buffer=buffer,
                    engine=engine,
                    mitigation=mitigation,
                    scaler=feat_extractor.scaler,
                )
                inf_thread.start()
                st.session_state.inference_thread_instance = inf_thread
                st.rerun()
        else:
            if st.button("⏹ Stop Capture", type="secondary", use_container_width=True):
                if st.session_state.capture_instance:
                    st.session_state.capture_instance.stop()
                    st.session_state.capture_instance = None
                if st.session_state.inference_thread_instance:
                    st.session_state.inference_thread_instance.stop()
                    st.session_state.inference_thread_instance = None
                st.rerun()

    with ctrl_col3:
        st.write("")
        st.write("")
        if st.button("🧹 Clear Buffer", use_container_width=True):
            buffer.clear()
            st.rerun()

    with ctrl_col4:
        st.write("")
        st.write("")
        if is_active:
            if source_mode == "Real PCAP File Replay":
                st.success("● REPLAYING PCAP")
            else:
                st.success("● LIVE SNIFFING ACTIVE")
        else:
            st.info("○ CAPTURE IDLE")

    # Display capture error if any
    if st.session_state.capture_instance and getattr(st.session_state.capture_instance, "error_message", None):
        st.error(f"⚠️ {st.session_state.capture_instance.error_message}")
        st.caption("Tip: On Windows, live raw socket capture requires Administrator privileges or Npcap installed with WinPcap API compatible mode.")

    # Autorefresh when active
    auto_refresh_enabled = st.checkbox("Enable Auto-Refresh (2s interval)", value=is_active)
    if auto_refresh_enabled and HAS_AUTOREFRESH:
        st_autorefresh(interval=2000, key="live_monitor_refresh")

    # 2. Key Metrics Row
    stats = buffer.get_stats()
    threat_rate = buffer.get_threat_rate(window_seconds=60.0)
    pps = buffer.get_packets_per_second(window_seconds=5.0)

    g_col1, g_col2, g_col3, g_col4 = st.columns([1.5, 1, 1, 1])

    with g_col1:
        gauge_fig = create_gauge(threat_rate, title="Rolling Threat Rate (60s)")
        st.plotly_chart(gauge_fig)

    with g_col2:
        st.metric("Capture Rate", f"{pps:.1f} pkts/s")
        st.metric("Total Packets", f"{stats['total_packets']:,}")

    with g_col3:
        st.metric("Threats Detected", f"{stats['threats_detected']:,}")
        st.metric("Buffer Depth", f"{stats['current_buffer_size']:,} / {buffer.maxlen:,}")

    with g_col4:
        st.markdown("**Threat Breakdown:**")
        by_class = stats["by_class"]
        st.markdown(f"- 🟣 Jamming: `{by_class.get(1, 0)}`")
        st.markdown(f"- 🟠 Spoofing: `{by_class.get(2, 0)}`")
        st.markdown(f"- 🔴 DoS Flood: `{by_class.get(3, 0)}`")
        st.markdown(f"- 🟡 Probe Scan: `{by_class.get(4, 0)}`")

    st.markdown("---")

    # 3. Real-Time Packet Stream Table
    st.markdown("### Real-Time Ingested Packets (Last 50)")

    recent_records = buffer.get_recent(50)
    if recent_records:
        table_rows = []
        for r in reversed(recent_records):
            time_str = datetime.fromtimestamp(r.timestamp).strftime("%H:%M:%S.%f")[:-3]
            pred_badge = {
                0: "🟢 Normal",
                1: "🟣 Jamming",
                2: "🟠 Spoofing",
                3: "🔴 DoS Flood",
                4: "🟡 Probe",
            }.get(r.prediction, "⚪ Pending")

            action_status = "None"
            if r.prediction in (2, 3, 4):
                action_status = "Blocked IP"
            elif r.prediction == 1:
                action_status = "Alert Sent"

            table_rows.append({
                "Time": time_str,
                "Source IP": r.src_ip,
                "Destination IP": r.dst_ip,
                "Proto": r.protocol,
                "Length": r.length,
                "Flags": r.flags or "-",
                "Classification": pred_badge,
                "Confidence": f"{r.confidence * 100:.1f}%" if r.confidence > 0 else "-",
                "Action Taken": action_status,
            })

        df_packets = pd.DataFrame(table_rows)
        st.dataframe(
            df_packets,
            height=300,
            column_config={
                "Confidence": st.column_config.TextColumn("Confidence"),
                "Classification": st.column_config.TextColumn("Classification"),
            },
        )
    else:
        st.info(
            f"Buffer is currently empty. Click 'Start Sniffing' above to capture live packets on '{selected_iface}', "
            "or generate real network traffic (e.g. ping, web requests, or attack scripts from the attacker laptop)."
        )

    st.markdown("---")

    # 4. Analytics Row: Threat Distribution Pie & Confidence Histogram
    pie_col, hist_col = st.columns(2)

    with pie_col:
        st.markdown("### Threat Distribution (Rolling Window)")
        recent_all = buffer.get_recent(200)
        class_counts = {name: 0 for name in CLASS_NAMES.values()}
        for r in recent_all:
            if r.prediction in CLASS_NAMES:
                class_counts[CLASS_NAMES[r.prediction]] += 1

        labels = list(class_counts.keys())
        values = list(class_counts.values())

        if sum(values) > 0:
            pie_fig = go.Figure(go.Pie(
                labels=labels,
                values=values,
                hole=0.45,
                marker=dict(colors=[CLASS_COLORS[i] for i in range(5)]),
                textinfo="percent+label",
            ))
            pie_fig.update_layout(height=280, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
            apply_dark_theme(pie_fig)
            st.plotly_chart(pie_fig)
        else:
            st.caption("No classified packets to display distribution.")

    with hist_col:
        st.markdown("### Model Confidence Distribution")
        confs = [r.confidence for r in recent_all if r.prediction >= 0 and r.confidence > 0]
        if confs:
            hist_fig = px.histogram(
                x=confs, nbins=15,
                labels={"x": "Calibrated Softmax Probability"},
                color_discrete_sequence=["#00d4ff"],
            )
            hist_fig.update_layout(height=280, yaxis_title="Packet Count", margin=dict(l=10, r=10, t=10, b=10))
            apply_dark_theme(hist_fig)
            st.plotly_chart(hist_fig)
        else:
            st.caption("No confidence samples collected yet.")

