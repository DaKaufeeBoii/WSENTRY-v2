"""
Tab 5: Per-Class Metrics
Displays detailed precision, recall, F1, and confusion matrices per dataset.
"""
from typing import Dict, Any, List
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from src.dashboard.components.charts import create_annotated_matrix_heatmap, DARK_LAYOUT


THREAT_NAMES = {
    0: "Normal",
    1: "Jamming",
    2: "Spoofing",
    3: "DoS_Flood",
    4: "Intrusion_Probe",
}


def _extract_report_df(report_str: str) -> pd.DataFrame:
    """Parses standard scikit-learn classification_report string into a DataFrame."""
    lines = [line.strip() for line in report_str.split("\n") if line.strip()]
    data = []
    for line in lines[1:]:
        tokens = line.split()
        if not tokens:
            continue
        if tokens[0] in ["accuracy", "macro", "weighted"]:
            continue
        try:
            cid = int(tokens[0])
            prec = float(tokens[1])
            rec = float(tokens[2])
            f1 = float(tokens[3])
            support = int(tokens[4])
            data.append({
                "Class ID": cid,
                "Threat Label": THREAT_NAMES.get(cid, f"Class {cid}"),
                "Precision": round(prec * 100, 2),
                "Recall (%)": round(rec * 100, 2),
                "F1-Score (%)": round(f1 * 100, 2),
                "Support (Samples)": support,
            })
        except Exception:
            continue
    return pd.DataFrame(data)


def render(phase1: Dict[str, Any], phase2: Dict[str, Any]) -> None:
    st.subheader("Per-Class Evaluation & Confusion Matrices")
    st.markdown(
        "Granular performance assessment across distinct threat vectors: "
        "Normal (0), Jamming (1), Spoofing (2), DoS Flood (3), and Intrusion Probe (4)."
    )

    same_ds = phase1.get("same_dataset", {})
    dataset_keys = [
        ("WSN-DS (Wireless Sensor Networks)", "RF_WSN-DS", [0, 1, 2, 3]),
        ("CIC-IoT-2023 (IoT Network Traffic)", "RF_CIC-IoT", [0, 2, 3, 4]),
        ("Edge-IIoTset (Industrial IoT Protocol)", "RF_Edge-IIoT", [0, 2, 3, 4]),
    ]

    for title, model_key, class_ids in dataset_keys:
        model_data = same_ds.get(model_key, {})
        with st.expander(title, expanded=(model_key == "RF_WSN-DS")):
            col_left, col_right = st.columns([1, 1])

            # Left column: Classification metrics
            with col_left:
                st.markdown("##### Classification Report")
                report_text = model_data.get("report", "")
                if report_text:
                    df_metrics = _extract_report_df(report_text)
                    st.dataframe(df_metrics, hide_index=True, width="stretch")

                    # Horizontal bar chart of F1-scores
                    fig_bars = go.Figure(
                        go.Bar(
                            x=df_metrics["F1-Score (%)"],
                            y=df_metrics["Threat Label"],
                            orientation="h",
                            marker_color="#00d4ff",
                            text=[f"{v:.1f}%" for v in df_metrics["F1-Score (%)"]],
                            textposition="auto",
                        )
                    )
                    fig_bars.update_layout(
                        title=f"Per-Class F1-Scores ({model_key})",
                        xaxis=dict(range=[0, 105], title="F1-Score (%)"),
                        height=250,
                        **DARK_LAYOUT,
                    )
                    st.plotly_chart(fig_bars, width="stretch")

            # Right column: Confusion matrix
            with col_right:
                st.markdown("##### Confusion Matrix")
                cm = model_data.get("confusion_matrix")
                if cm:
                    cm_arr = np.array(cm)
                    labels = [THREAT_NAMES.get(c, f"C{c}") for c in class_ids[:len(cm_arr)]]
                    fig_cm = create_annotated_matrix_heatmap(
                        z=cm_arr,
                        x_labels=labels,
                        y_labels=labels,
                        title="Confusion Matrix (Counts)",
                        colorscale="Blues",
                        is_percentage=False,
                    )
                    st.plotly_chart(fig_cm, width="stretch")

