"""
Tab 4: ROC / AUC Curves
Displays per-class one-vs-rest ROC curves and AUC performance.
"""
import os
import json
from typing import Optional, Dict, Any
import streamlit as st
import numpy as np
import pandas as pd
from src.dashboard.components.charts import create_roc_figure
from src.dashboard.precompute_roc import generate_roc_curves_from_results, CLASS_NAMES


def _load_roc_data() -> Dict[str, Any]:
    json_path = os.path.join("data", "processed", "roc_curves.json")
    if not os.path.exists(json_path):
        # Auto-generate if missing
        return generate_roc_curves_from_results()
    try:
        with open(json_path, "r") as f:
            return json.load(f)
    except Exception:
        return generate_roc_curves_from_results()


def render(roc_data: Optional[Dict[str, Any]] = None) -> None:
    st.subheader("Receiver Operating Characteristic (ROC) & AUC")
    st.markdown(
        "One-vs-Rest (OvR) ROC curves evaluating the discriminatory capability "
        "of the Hybrid CNN-BiLSTM-Attention model across threat categories."
    )

    if roc_data is None:
        roc_data = _load_roc_data()

    datasets = ["WSN", "CIC", "Edge"]
    selected_ds = st.selectbox("Select Dataset", datasets, index=0, format_func=lambda d: {
        "WSN": "WSN-DS (Wireless Sensor Networks)",
        "CIC": "CIC-IoT-2023 (IoT Traffic)",
        "Edge": "Edge-IIoTset (Industrial IoT)",
    }.get(d, d))

    ds_info = roc_data.get(selected_ds, {})
    curves = ds_info.get("curves", [])
    macro_auc = ds_info.get("macro_auc", 0.0)
    micro_auc = ds_info.get("micro_auc", 0.0)

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric("Macro-Average AUC", f"{macro_auc:.4f}")
    with col_m2:
        st.metric("Micro-Average AUC", f"{micro_auc:.4f}")

    if curves:
        chart_input = {}
        table_rows = []
        for c in curves:
            cid = c.get("class_id")
            cname = c.get("class_name", CLASS_NAMES.get(cid, f"Class {cid}"))
            auc_val = c.get("auc", 0.0)
            chart_input[cname] = {
                "fpr": np.array(c.get("fpr", [])),
                "tpr": np.array(c.get("tpr", [])),
                "auc": auc_val,
            }
            table_rows.append({
                "Class ID": cid,
                "Threat Category": cname,
                "Area Under Curve (AUC)": f"{auc_val:.4f}",
            })

        fig = create_roc_figure(chart_input, list(chart_input.keys()))
        st.plotly_chart(fig, width="stretch")

        st.subheader("Per-Class AUC Summary")
        st.dataframe(pd.DataFrame(table_rows), hide_index=True, width="stretch")
    else:
        st.info("No ROC curve data found. Run `python -m src.dashboard.precompute_roc`.")

