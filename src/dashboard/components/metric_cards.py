"""
Reusable metric cards for Streamlit dashboard.
"""
from typing import Optional
import streamlit as st


def render_metric_card(
    label: str,
    value: float,
    suffix: str = "%",
    delta: Optional[float] = None,
    help_text: Optional[str] = None
) -> None:
    """
    Renders a styled metric card in Streamlit.
    """
    if isinstance(value, (int, float)):
        val_str = f"{value:.2f}{suffix}"
    else:
        val_str = f"{value}{suffix}"

    delta_str = f"{delta:+.2f}{suffix}" if delta is not None else None
    st.metric(label=label, value=val_str, delta=delta_str, help=help_text)

