"""
Tab 4: ROC / AUC Curves — Multi-class Discrimination Analysis.
"""
import os
from typing import Optional, Dict, Any
import numpy as np
import streamlit as st
import plotly.graph_objects as go

from src.dashboard.components.charts import apply_dark_theme, CLASS_COLORS, CLASS_NAMES


def load_roc_data() -> Optional[Dict[str, Any]]:
    """Loads precomputed ROC data from results/roc_curves.npz or data/processed/roc_curves.npz."""
    paths = ["results/roc_curves.npz", "data/processed/roc_curves.npz"]
    for p in paths:
        if os.path.exists(p):
            try:
                npz = np.load(p)
                return dict(npz)
            except Exception:
                pass
    return None


def render(roc_data: Optional[Dict[str, Any]] = None) -> None:
    st.subheader("Receiver Operating Characteristic (ROC) & AUC")
    st.caption("One-vs-Rest (OvR) multi-class discrimination performance per dataset.")

    if roc_data is None:
        roc_data = load_roc_data()

    if roc_data is None:
        st.warning("Pre-computed ROC data not found. Run the precomputation script:")
        st.code("python -m src.dashboard.precompute_roc", language="bash")
        if st.button("Generate ROC Curves Now"):
            from src.dashboard.precompute_roc import generate_roc_curves_data
            generate_roc_curves_data()
            st.rerun()
        return

    datasets = ["WSN-DS", "CIC-IoT-2023", "Edge-IIoTset"]
    selected_ds = st.selectbox("Select Benchmark Dataset:", datasets)

    mean_fpr = roc_data.get(f"{selected_ds}_mean_fpr", np.linspace(0, 1, 100))

    fig = go.Figure()

    # Diagonal chance line
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1],
        mode="lines",
        line=dict(color="#64748b", dash="dash"),
        name="Random Chance (AUC = 0.50)",
    ))

    # Per-class curves
    for cls_idx, cls_name in CLASS_NAMES.items():
        tpr_key = f"{selected_ds}_{cls_name}_tpr"
        auc_key = f"{selected_ds}_{cls_name}_auc"
        if tpr_key in roc_data and auc_key in roc_data:
            tpr = roc_data[tpr_key]
            auc_val = float(roc_data[auc_key][0])
            color = CLASS_COLORS.get(cls_idx, "#00d4ff")

            fig.add_trace(go.Scatter(
                x=mean_fpr, y=tpr,
                mode="lines",
                name=f"{cls_name} (AUC = {auc_val:.3f})",
                line=dict(color=color, width=2.5),
            ))

    # Micro average
    micro_tpr_key = f"{selected_ds}_micro_tpr"
    micro_auc_key = f"{selected_ds}_micro_auc"
    if micro_tpr_key in roc_data and micro_auc_key in roc_data:
        tpr_micro = roc_data[micro_tpr_key]
        auc_micro = float(roc_data[micro_auc_key][0])
        fig.add_trace(go.Scatter(
            x=mean_fpr, y=tpr_micro,
            mode="lines",
            name=f"Micro-Average (AUC = {auc_micro:.3f})",
            line=dict(color="#38bdf8", dash="dot", width=2.5),
        ))

    # Macro average
    macro_tpr_key = f"{selected_ds}_macro_tpr"
    macro_auc_key = f"{selected_ds}_macro_auc"
    if macro_tpr_key in roc_data and macro_auc_key in roc_data:
        tpr_macro = roc_data[macro_tpr_key]
        auc_macro = float(roc_data[macro_auc_key][0])
        fig.add_trace(go.Scatter(
            x=mean_fpr, y=tpr_macro,
            mode="lines",
            name=f"Macro-Average (AUC = {auc_macro:.3f})",
            line=dict(color="#e2e8f0", dash="dashdot", width=2.5),
        ))

    fig.update_layout(
        xaxis_title="False Positive Rate (FPR)",
        yaxis_title="True Positive Rate (TPR)",
        xaxis=dict(range=[-0.01, 1.01]),
        yaxis=dict(range=[-0.01, 1.01]),
        height=520,
        legend=dict(x=0.55, y=0.08, bgcolor="rgba(26, 29, 35, 0.8)"),
    )
    apply_dark_theme(fig, title=f"Multi-Class ROC Curves: {selected_ds}")
    st.plotly_chart(fig)
