"""
Tab 2: Live Monitor
Interactive real-time packet capture, throughput gauges, threat stream, and confidence histograms.
"""
from datetime import datetime, timezone
from typing import Optional
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.live.buffer import PacketBuffer
from src.live.capture import LiveCapture
from src.live.inference import InferenceEngine
from src.dashboard.components.charts import create_gauge_chart, DARK_LAYOUT


THREAT_COLORS = {
    0: "#10b981",  # Normal: Green
    1: "#a855f7",  # Jamming: Purple
    2: "#f97316",  # Spoofing: Orange
    3: "#ef4444",  # DoS Flood: Red
    4: "#eab308",  # Intrusion Probe: Yellow
    -1: "#64748b", # Pending: Gray
}


def render(buffer: PacketBuffer, engine: InferenceEngine, capture: Optional[LiveCapture] = None) -> None:
    st.subheader("Live Intrusion Detection Monitor")

    # Header controls
    c_nic, c_btn, c_stat = st.columns([3, 1, 1])

    with c_nic:
        ifaces = LiveCapture.list_interfaces()
        label_to_id = {iface.get("label", iface.get("name")): iface.get("id", iface.get("name")) for iface in ifaces}
        selected_label = st.selectbox(
            "Network Interface (NIC)",
            options=list(label_to_id.keys()),
            index=0,
            help="Select network adapter for promiscuous sniffing (Npcap / scapy)"
        )
        selected_nic = label_to_id[selected_label]

    with c_btn:
        st.write("") # spacer
        st.write("")
        is_capturing = st.session_state.get("is_capturing", False)
        if is_capturing:
            if st.button("⏹ Stop Capture", type="secondary", width="stretch"):
                if st.session_state.get("capture") is not None:
                    st.session_state.capture.stop()
                st.session_state.is_capturing = False
                st.rerun()
        else:
            if st.button("▶ Start Capture", type="primary", width="stretch"):
                # Start capture
                cap = LiveCapture(iface=selected_nic, buffer=buffer)
                cap.start()
                st.session_state.capture = cap
                st.session_state.is_capturing = True
                st.rerun()

    with c_stat:
        st.write("")
        st.write("")
        if st.session_state.get("is_capturing", False):
            st.success("● CAPTURING")
        else:
            st.warning("○ IDLE")

    st.markdown("---")

    # Metrics Row
    stats = buffer.get_stats()
    threat_rate = buffer.get_threat_rate(window_seconds=60.0)
    pkt_rate = buffer.get_packet_rate(window_seconds=5.0)

    m1, m2, m3 = st.columns([1, 1, 1])
    with m1:
        fig_threat = create_gauge_chart(value=threat_rate, max_val=100.0, title="Threat Rate (60s %)")
        st.plotly_chart(fig_threat, width="stretch")
    with m2:
        fig_rate = create_gauge_chart(value=pkt_rate, max_val=500.0, title="Throughput (Pkts/sec)")
        st.plotly_chart(fig_rate, width="stretch")
    with m3:
        st.metric(label="Total Processed Packets", value=f"{stats['total_packets']:,}")
        st.metric(label="Threats Detected", value=f"{stats['threats_detected']:,}")
        st.metric(label="Buffer Occupancy", value=f"{stats['buffer_size']} / {buffer.maxlen}")

    st.markdown("---")

    # Real-time Packet Stream Table
    st.subheader("Live Packet Stream (Recent 50 Packets)")
    recent_records = buffer.get_recent(n=50)

    if recent_records:
        rows = []
        for r in recent_records:
            time_str = datetime.fromtimestamp(r.timestamp, timezone.utc).strftime("%H:%M:%S.%f")[:-3]
            rows.append({
                "Time": time_str,
                "Source IP": r.src_ip,
                "Dest IP": r.dst_ip,
                "Protocol": r.protocol,
                "Length": r.length,
                "Flags": r.flags,
                "Classification": r.label,
                "Confidence": f"{r.confidence * 100:.1f}%" if r.prediction >= 0 else "—",
            })
        df_packets = pd.DataFrame(rows)
        st.dataframe(df_packets, hide_index=True, width="stretch")
    else:
        st.info("No packets captured yet. Click 'Start Capture' or run simulation.")

    # Bottom Charts: Threat distribution + Confidence histogram
    st.markdown("---")
    c_pie, c_hist = st.columns(2)

    with c_pie:
        st.subheader("Threat Category Distribution")
        by_class = stats.get("by_class", {})
        labels = ["Normal", "Jamming", "Spoofing", "DoS Flood", "Intrusion Probe"]
        counts = [by_class.get(i, 0) for i in range(5)]
        if sum(counts) > 0:
            fig_pie = go.Figure(
                go.Pie(
                    labels=labels,
                    values=counts,
                    hole=0.45,
                    marker=dict(colors=[THREAT_COLORS[i] for i in range(5)]),
                )
            )
            fig_pie.update_layout(height=280, **DARK_LAYOUT)
            st.plotly_chart(fig_pie, width="stretch")
        else:
            st.caption("Awaiting packet traffic to display threat distribution.")

    with c_hist:
        st.subheader("Prediction Confidence Distribution")
        recent_200 = buffer.get_recent(n=200)
        confs = [r.confidence for r in recent_200 if r.prediction >= 0]
        if confs:
            fig_hist = go.Figure(
                go.Histogram(
                    x=confs,
                    nbinsx=20,
                    marker_color="#00d4ff",
                )
            )
            fig_hist.update_layout(
                xaxis=dict(title="Calibrated Softmax Probability", range=[0, 1.05]),
                yaxis=dict(title="Count"),
                height=280,
                **DARK_LAYOUT,
            )
            st.plotly_chart(fig_hist, width="stretch")
        else:
            st.caption("Awaiting classified predictions for confidence histogram.")

