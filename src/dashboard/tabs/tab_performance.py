"""
Tab 1: Performance Overview — Hybrid DL, Baselines, DANN, and Calibration.
"""
from typing import Dict, Any
import streamlit as st
import plotly.graph_objects as go

from src.dashboard.components.metric_cards import render_metric_card
from src.dashboard.components.charts import apply_dark_theme


def render(phase1: Dict[str, Any], phase2: Dict[str, Any]) -> None:
    st.subheader("Performance Overview")
    st.caption("Benchmark evaluation across heterogeneous datasets: WSN-DS, CIC-IoT-2023, and Edge-IIoTset.")

    # 1. Top row: 3 metric cards
    native_res = phase2.get("native_same_dataset", {})
    wsn_acc = native_res.get("WSN", {}).get("accuracy", 98.06)
    cic_acc = native_res.get("CIC", {}).get("accuracy", 97.80)
    edge_acc = native_res.get("Edge", {}).get("accuracy", 94.39)

    col1, col2, col3 = st.columns(3)
    with col1:
        render_metric_card("WSN-DS Hybrid Accuracy", wsn_acc, suffix="%", delta=+17.36, help_text="Wireless Sensor Network benchmark")
    with col2:
        render_metric_card("CIC-IoT-2023 Hybrid Accuracy", cic_acc, suffix="%", delta=+3.40, help_text="Multi-protocol IoT benchmark")
    with col3:
        render_metric_card("Edge-IIoTset Hybrid Accuracy", edge_acc, suffix="%", delta=+37.60, help_text="Industrial IoT benchmark with log-normalization")

    st.markdown("---")

    # 2. Middle row: Grouped bar chart comparing RF, XGBoost, CNN-BiLSTM-Attention
    st.markdown("### Model Comparison: Baselines vs. Hybrid Deep Learning")
    metric_choice = st.radio("Select Metric:", ["Accuracy", "F1-Score", "False Alarm Rate (FAR)"], horizontal=True)

    same_p1 = phase1.get("same_dataset", {})
    rf_wsn = same_p1.get("RF_WSN-DS", {})
    rf_cic = same_p1.get("RF_CIC-IoT", {})
    rf_edge = same_p1.get("RF_Edge-IIoT", {})

    xgb_wsn = same_p1.get("XGB_WSN-DS", {})
    xgb_cic = same_p1.get("XGB_CIC-IoT", {})
    xgb_edge = same_p1.get("XGB_Edge-IIoT", {})

    datasets = ["WSN-DS", "CIC-IoT-2023", "Edge-IIoTset"]
    if metric_choice == "Accuracy":
        rf_vals = [rf_wsn.get("accuracy", 99.60), rf_cic.get("accuracy", 99.42), rf_edge.get("accuracy", 92.06)]
        xgb_vals = [xgb_wsn.get("accuracy", 99.56), xgb_cic.get("accuracy", 99.44), xgb_edge.get("accuracy", 91.92)]
        dl_vals = [wsn_acc, cic_acc, edge_acc]
        unit = "%"
    elif metric_choice == "F1-Score":
        rf_vals = [rf_wsn.get("f1", 99.60), rf_cic.get("f1", 99.42), rf_edge.get("f1", 94.25)]
        xgb_vals = [xgb_wsn.get("f1", 99.57), xgb_cic.get("f1", 99.44), xgb_edge.get("f1", 94.01)]
        dl_vals = [
            native_res.get("WSN", {}).get("f1", 98.15),
            native_res.get("CIC", {}).get("f1", 97.59),
            native_res.get("Edge", {}).get("f1", 94.65),
        ]
        unit = "%"
    else:
        # False Alarm Rate (lower is better)
        rf_vals = [rf_wsn.get("far", 0.29), rf_cic.get("far", 8.24), rf_edge.get("far", 0.59)]
        xgb_vals = [xgb_wsn.get("far", 0.33), xgb_cic.get("far", 9.31), xgb_edge.get("far", 0.58)]
        dl_vals = [0.22, 1.85, 1.42]
        unit = "%"

    fig_cmp = go.Figure()
    fig_cmp.add_trace(go.Bar(
        x=datasets, y=rf_vals, name="Random Forest Baseline",
        marker_color="#64748b", text=[f"{v}{unit}" for v in rf_vals], textposition="auto"
    ))
    fig_cmp.add_trace(go.Bar(
        x=datasets, y=xgb_vals, name="XGBoost Baseline",
        marker_color="#38bdf8", text=[f"{v}{unit}" for v in xgb_vals], textposition="auto"
    ))
    fig_cmp.add_trace(go.Bar(
        x=datasets, y=dl_vals, name="Hybrid CNN-BiLSTM-Attention",
        marker_color="#00d4ff", text=[f"{v}{unit}" for v in dl_vals], textposition="auto"
    ))

    fig_cmp.update_layout(barmode="group", height=380, yaxis_title=f"{metric_choice} ({unit})")
    apply_dark_theme(fig_cmp)
    st.plotly_chart(fig_cmp)

    st.markdown("---")

    # 3. Bottom row: DANN improvement comparison & Calibration ECE
    col_dann, col_calib = st.columns(2)

    with col_dann:
        st.markdown("### Domain Adversarial Generalization (DANN)")
        dann_data = phase2.get("dann_2domain", {})
        cic_dann = dann_data.get("CIC", {}).get("accuracy", 96.50)
        edge_dann = dann_data.get("Edge", {}).get("accuracy", 96.29)

        dann_domains = ["CIC-IoT Domain", "Edge-IIoT Domain"]
        native_transfer_unadapted = [61.77, 80.70]  # Baseline unadapted cross-transfer
        dann_unified = [cic_dann, edge_dann]

        fig_dann = go.Figure()
        fig_dann.add_trace(go.Bar(
            x=dann_domains, y=native_transfer_unadapted, name="Unadapted Cross-Domain",
            marker_color="#f97316", text=[f"{v:.1f}%" for v in native_transfer_unadapted], textposition="auto"
        ))
        fig_dann.add_trace(go.Bar(
            x=dann_domains, y=dann_unified, name="DANN Unified Model",
            marker_color="#10b981", text=[f"{v:.1f}%" for v in dann_unified], textposition="auto"
        ))
        fig_dann.update_layout(
            barmode="group", height=320,
            yaxis_title="Target Domain Accuracy (%)",
            title=dict(text="Closing the Cross-Domain Distribution Gap", font=dict(size=14, color="#00d4ff"))
        )
        apply_dark_theme(fig_dann)
        st.plotly_chart(fig_dann)
        st.caption("DANN aligns latent feature distributions using gradient reversal, closing over 85% of the domain transfer gap.")

    with col_calib:
        st.markdown("### Confidence Calibration (Temperature Scaling)")
        calib_data = phase2.get("calibration", {})
        ece_wsn = calib_data.get("WSN", {}).get("ece_before", 1.70)
        ece_cic = calib_data.get("CIC", {}).get("ece_before", 0.23)
        ece_edge = calib_data.get("Edge", {}).get("ece_before", 1.78)

        t_wsn = calib_data.get("WSN", {}).get("temperature", 1.04)
        t_cic = calib_data.get("CIC", {}).get("temperature", 1.495)
        t_edge = calib_data.get("Edge", {}).get("temperature", 1.077)

        fig_ece = go.Figure()
        fig_ece.add_trace(go.Bar(
            x=["WSN-DS", "CIC-IoT-2023", "Edge-IIoTset"],
            y=[ece_wsn, ece_cic, ece_edge],
            marker_color="#a855f7",
            text=[f"ECE: {v}%\n(T={t})" for v, t in zip([ece_wsn, ece_cic, ece_edge], [t_wsn, t_cic, t_edge])],
            textposition="auto"
        ))
        fig_ece.update_layout(
            height=320,
            yaxis_title="Expected Calibration Error (ECE %)",
            title=dict(text="Post-Hoc Probability Calibration", font=dict(size=14, color="#00d4ff"))
        )
        apply_dark_theme(fig_ece)
        st.plotly_chart(fig_ece)
        st.caption("Temperature scaling ensures that predicted softmax probabilities correspond to true empirical accuracy.")
