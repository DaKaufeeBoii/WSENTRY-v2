"""
Tab 1: Performance Overview
Visualizes baseline ML and deep learning results across WSN, CIC, and Edge datasets.
"""
from typing import Dict, Any
import streamlit as st
import pandas as pd
from src.dashboard.components.metric_cards import render_metric_card
from src.dashboard.components.charts import create_grouped_bar_chart


def render(phase1: Dict[str, Any], phase2: Dict[str, Any]) -> None:
    st.subheader("Model Performance Overview")
    st.markdown(
        "Comparison of baseline machine learning (Random Forest, XGBoost) and "
        "W-SENTRY Hybrid Deep Learning (CNN-BiLSTM-Attention) with DANN Domain Adaptation."
    )

    # Top row: 3 metric cards for Native Hybrid Deep Learning Accuracy
    native = phase2.get("native_same_dataset", {})
    wsn_acc = native.get("WSN", {}).get("accuracy", 98.06)
    cic_acc = native.get("CIC", {}).get("accuracy", 97.80)
    edge_acc = native.get("Edge", {}).get("accuracy", 94.39)

    col1, col2, col3 = st.columns(3)
    with col1:
        render_metric_card(
            label="WSN-DS Hybrid Accuracy",
            value=wsn_acc,
            help_text="Hybrid CNN-BiLSTM-Attention on WSN-DS routing dataset"
        )
    with col2:
        render_metric_card(
            label="CIC-IoT-2023 Hybrid Accuracy",
            value=cic_acc,
            help_text="Hybrid CNN-BiLSTM-Attention on CIC-IoT-2023 traffic flows"
        )
    with col3:
        render_metric_card(
            label="Edge-IIoTset Hybrid Accuracy",
            value=edge_acc,
            help_text="Hybrid CNN-BiLSTM-Attention on Edge-IIoTset (+37.6pp via log-norm)"
        )

    st.markdown("---")

    # Middle row: Grouped bar chart comparing RF, XGB, and CNN-BiLSTM-Attention
    datasets = ["WSN-DS", "CIC-IoT-2023", "Edge-IIoTset"]
    same_ds_p1 = phase1.get("same_dataset", {})

    rf_scores = [
        same_ds_p1.get("RF_WSN-DS", {}).get("accuracy", 99.60),
        same_ds_p1.get("RF_CIC-IoT", {}).get("accuracy", 99.42),
        same_ds_p1.get("RF_Edge-IIoT", {}).get("accuracy", 92.06),
    ]
    xgb_scores = [
        same_ds_p1.get("XGB_WSN-DS", {}).get("accuracy", 99.56),
        same_ds_p1.get("XGB_CIC-IoT", {}).get("accuracy", 99.44),
        same_ds_p1.get("XGB_Edge-IIoT", {}).get("accuracy", 91.92),
    ]
    hybrid_scores = [wsn_acc, cic_acc, edge_acc]

    model_scores = {
        "Random Forest": rf_scores,
        "XGBoost": xgb_scores,
        "Hybrid CNN-BiLSTM-Attn": hybrid_scores,
    }

    fig_comparison = create_grouped_bar_chart(datasets, model_scores, metric_name="Accuracy (%)")
    st.plotly_chart(fig_comparison, width="stretch")

    st.markdown("---")

    # Bottom row: DANN improvement & Temperature Calibration
    col_dann, col_calib = st.columns(2)

    with col_dann:
        st.subheader("DANN 2-Domain Adaptation (CIC + Edge)")
        st.markdown(
            "Unified model simultaneously trained on source and target domains "
            "with gradient reversal layer to extract domain-invariant features."
        )
        dann_2d = phase2.get("dann_2domain", {})
        cic_dann = dann_2d.get("CIC", {}).get("accuracy", 96.50)
        edge_dann = dann_2d.get("Edge", {}).get("accuracy", 96.29)

        dann_df = pd.DataFrame({
            "Dataset": ["CIC-IoT-2023", "Edge-IIoTset"],
            "Native Accuracy (%)": [cic_acc, edge_acc],
            "DANN Unified Accuracy (%)": [cic_dann, edge_dann],
            "Delta (pp)": [round(cic_dann - cic_acc, 2), round(edge_dann - edge_acc, 2)],
        })
        st.dataframe(dann_df, hide_index=True, width="stretch")

    with col_calib:
        st.subheader("Probability Calibration (ECE)")
        st.markdown(
            "Expected Calibration Error (ECE) before and after temperature scaling calibration."
        )
        calib_data = phase2.get("calibration", {})
        calib_rows = []
        for ds_name in ["WSN", "CIC", "Edge"]:
            c_info = calib_data.get(ds_name, {})
            calib_rows.append({
                "Dataset": ds_name,
                "Optimal Temp (T)": c_info.get("temperature", 1.0),
                "ECE Before (%)": c_info.get("ece_before", 0.0),
                "ECE After (%)": c_info.get("ece_after", 0.0),
            })
        st.dataframe(pd.DataFrame(calib_rows), hide_index=True, width="stretch")

