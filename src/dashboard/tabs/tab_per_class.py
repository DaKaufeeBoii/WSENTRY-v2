"""
Tab 5: Per-Class Metrics — Detailed Precision, Recall, F1, and Confusion Matrices.
Zero mock data: loads and parses real experimental evaluation results from Phase 1.
"""
import re
from typing import Dict, Any, List, Tuple
import streamlit as st
import plotly.graph_objects as go

from src.dashboard.components.charts import apply_dark_theme, CLASS_COLORS, CLASS_NAMES

DATASET_METADATA = [
    {
        "id": "WSN-DS",
        "name": "WSN-DS (Wireless Sensor Networks)",
        "rf_key": "RF_WSN-DS",
        "xgb_key": "XGB_WSN-DS",
        "class_order": [0, 1, 2, 3],
    },
    {
        "id": "CIC-IoT",
        "name": "CIC-IoT-2023 (Smart Home IoT)",
        "rf_key": "RF_CIC-IoT",
        "xgb_key": "XGB_CIC-IoT",
        "class_order": [0, 2, 3, 4],
    },
    {
        "id": "Edge-IIoT",
        "name": "Edge-IIoTset (Industrial IoT)",
        "rf_key": "RF_Edge-IIoT",
        "xgb_key": "XGB_Edge-IIoT",
        "class_order": [0, 2, 3, 4],
    },
]


def _parse_classification_report(report_str: str) -> Dict[int, Dict[str, float]]:
    """Parse sklearn classification_report string into structured class metrics."""
    metrics = {}
    if not report_str:
        return metrics

    for line in report_str.strip().split("\n"):
        parts = line.strip().split()
        if len(parts) == 5 and parts[0].isdigit():
            cls_id = int(parts[0])
            try:
                metrics[cls_id] = {
                    "precision": float(parts[1]),
                    "recall": float(parts[2]),
                    "f1": float(parts[3]),
                    "support": int(parts[4]),
                }
            except ValueError:
                pass
    return metrics


def render(phase1: Dict[str, Any], phase2: Dict[str, Any]) -> None:
    st.subheader("Per-Class Intrusion Metrics")
    st.caption("Granular class-level performance: Precision, Recall, F1-Score, Confusion Matrices, and Support Distributions from empirical test sets.")

    same_dataset = phase1.get("same_dataset", {})
    if not same_dataset:
        st.warning("No Phase 1 benchmark results found in results/phase1_results.json.")
        return

    model_family = st.radio(
        "Select Baseline Architecture:",
        ["Random Forest (RF)", "XGBoost (XGB)"],
        horizontal=True,
    )
    is_rf = "Random Forest" in model_family

    for meta in DATASET_METADATA:
        key = meta["rf_key"] if is_rf else meta["xgb_key"]
        result = same_dataset.get(key, {})
        if not result:
            continue

        raw_cm = result.get("confusion_matrix", [])
        report_str = result.get("report", "")
        metrics_by_class = _parse_classification_report(report_str)

        class_indices = meta["class_order"]
        class_labels = [CLASS_NAMES.get(c, f"Class {c}") for c in class_indices]

        # Extract values for the active classes
        prec_vals = [metrics_by_class.get(c, {}).get("precision", 0.0) * 100 for c in class_indices]
        rec_vals = [metrics_by_class.get(c, {}).get("recall", 0.0) * 100 for c in class_indices]
        f1_vals = [metrics_by_class.get(c, {}).get("f1", 0.0) * 100 for c in class_indices]
        support_vals = [metrics_by_class.get(c, {}).get("support", 0) for c in class_indices]

        acc = result.get("accuracy", 0.0)
        far = result.get("far", 0.0)
        train_time = result.get("train_time_s", 0.0)
        inf_time = result.get("inference_time_s", 0.0)

        with st.expander(f"📊 {meta['name']} — {key} (Acc: {acc:.2f}%, FAR: {far:.2f}%)", expanded=True):
            # Overview telemetry
            t_col1, t_col2, t_col3, t_col4 = st.columns(4)
            t_col1.metric("Overall Accuracy", f"{acc:.2f}%")
            t_col2.metric("False Alarm Rate (FAR)", f"{far:.2f}%")
            t_col3.metric("Training Time", f"{train_time:.1f}s")
            t_col4.metric("Inference Time", f"{inf_time:.3f}s")

            col_bar, col_cm, col_pie = st.columns([1.3, 1.2, 0.9])

            # 1. Horizontal Bar Chart for Precision, Recall, F1
            with col_bar:
                st.markdown("##### Precision / Recall / F1-Score")
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(
                    y=class_labels, x=prec_vals, name="Precision", orientation="h",
                    marker_color="#00d4ff", text=[f"{v:.1f}%" for v in prec_vals], textposition="auto"
                ))
                fig_bar.add_trace(go.Bar(
                    y=class_labels, x=rec_vals, name="Recall", orientation="h",
                    marker_color="#10b981", text=[f"{v:.1f}%" for v in rec_vals], textposition="auto"
                ))
                fig_bar.add_trace(go.Bar(
                    y=class_labels, x=f1_vals, name="F1-Score", orientation="h",
                    marker_color="#a855f7", text=[f"{v:.1f}%" for v in f1_vals], textposition="auto"
                ))
                fig_bar.update_layout(
                    barmode="group", height=320,
                    xaxis=dict(range=[0, 105], title="Score (%)"),
                    legend=dict(orientation="h", y=-0.25, x=0.1),
                    margin=dict(l=10, r=10, t=20, b=30),
                )
                apply_dark_theme(fig_bar)
                st.plotly_chart(fig_bar)

            # 2. Confusion Matrix Heatmap (Real Test Data)
            with col_cm:
                st.markdown("##### Real Confusion Matrix (Test Split)")
                if raw_cm:
                    annot_text = [[f"{val:,}" for val in row] for row in raw_cm]
                    fig_cm = go.Figure(
                        data=go.Heatmap(
                            z=raw_cm,
                            x=class_labels,
                            y=class_labels,
                            text=annot_text,
                            texttemplate="%{text}",
                            textfont=dict(size=11, color="#ffffff"),
                            colorscale="Blues",
                            showscale=False,
                        )
                    )
                    fig_cm.update_layout(
                        height=320,
                        xaxis_title="Predicted Label",
                        yaxis_title="True Label",
                        margin=dict(l=10, r=10, t=20, b=30),
                        yaxis=dict(autorange="reversed"),
                    )
                    apply_dark_theme(fig_cm)
                    st.plotly_chart(fig_cm)
                else:
                    st.info("Confusion matrix data unavailable.")

            # 3. Class Support Distribution Pie Chart
            with col_pie:
                st.markdown("##### Test Support Distribution")
                colors = [CLASS_COLORS.get(c, "#64748b") for c in class_indices]
                fig_pie = go.Figure(go.Pie(
                    labels=class_labels,
                    values=support_vals,
                    hole=0.45,
                    marker=dict(colors=colors),
                    textinfo="percent",
                    hoverinfo="label+value+percent",
                ))
                fig_pie.update_layout(
                    height=320,
                    showlegend=False,
                    margin=dict(l=10, r=10, t=20, b=30),
                )
                apply_dark_theme(fig_pie)
                st.plotly_chart(fig_pie)

