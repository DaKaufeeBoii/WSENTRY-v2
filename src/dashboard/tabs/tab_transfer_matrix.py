"""
Tab 3: Transfer Matrix Heatmap — Cross-Dataset Generalization Analysis.
"""
from typing import Dict, Any, List
import streamlit as st

from src.dashboard.components.charts import create_annotated_heatmap


def _extract_3x3_matrix(matrix_dict: Dict[str, float]) -> List[List[float]]:
    """Convert dict with 'SRC->DST' keys to 3x3 float matrix."""
    datasets = ["WSN", "CIC", "Edge"]
    z = []
    for src in datasets:
        row = []
        for dst in datasets:
            key1 = f"{src}→{dst}"
            key2 = f"{src}->{dst}"
            val = matrix_dict.get(key1, matrix_dict.get(key2, 0.0))
            row.append(float(val))
        z.append(row)
    return z


def render(phase1: Dict[str, Any], phase2: Dict[str, Any]) -> None:
    st.subheader("Cross-Dataset Transfer Matrix")
    st.caption("Evaluating feature generalization when training on one dataset and testing directly on another without retraining.")

    labels = ["WSN-DS", "CIC-IoT-2023", "Edge-IIoTset"]

    # Matrices from phase1 and phase2
    p1_dict = phase1.get("transfer_matrix", {})
    p2_dict = phase2.get("behavioral_transfer_matrix", {})

    z_p1 = _extract_3x3_matrix(p1_dict)
    z_p2 = _extract_3x3_matrix(p2_dict)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Phase 1: Native Baseline Transfer (RF)")
        st.caption("Native protocol-specific features collapse on foreign architectures.")
        fig1 = create_annotated_heatmap(
            z_matrix=z_p1,
            x_labels=labels,
            y_labels=labels,
            title="Phase 1: Baseline Transfer Accuracy (%)",
            colorscale="RdYlGn",
        )
        st.plotly_chart(fig1)

    with col2:
        st.markdown("#### Phase 2: Behavioral Feature Transfer")
        st.caption("Protocol-agnostic behavioral features significantly bridge the domain gap.")
        fig2 = create_annotated_heatmap(
            z_matrix=z_p2,
            x_labels=labels,
            y_labels=labels,
            title="Phase 2: Behavioral Transfer Accuracy (%)",
            colorscale="RdYlGn",
        )
        st.plotly_chart(fig2)

    st.markdown("---")
    st.markdown("### Key Scientific Insights")

    info1, info2, info3 = st.columns(3)
    with info1:
        st.info(
            "**WSN-DS → Edge-IIoTset: +68.8 pp Gain**\n\n"
            "Baseline RF transfer was just **11.94%** (worse than random guessing). "
            "With behavioral feature engineering, transfer accuracy jumps to **80.70%**."
        )
    with info2:
        st.info(
            "**Edge-IIoTset → WSN-DS: +25.1 pp Gain**\n\n"
            "Transfer from Edge to WSN increased from **1.90%** to **26.96%**, "
            "confirming that traffic flow dynamics generalize across sensor topologies."
        )
    with info3:
        st.info(
            "**Stable In-Domain Retention**\n\n"
            "Same-dataset accuracies remain virtually uncompromised (**97.4% - 97.8%**), "
            "proving behavioral abstractions preserve high discriminative resolution."
        )
