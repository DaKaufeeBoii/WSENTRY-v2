"""
Reusable metric card components for W-SENTRY Streamlit dashboard.
"""
from typing import Optional
import streamlit as st


def render_metric_card(
    label: str,
    value: float,
    suffix: str = "%",
    delta: Optional[float] = None,
    help_text: Optional[str] = None,
) -> None:
    """
    Renders a styled metric card.
    Args:
        label: Metric title.
        value: Numeric value.
        suffix: String suffix like "%" or " pkts/s".
        delta: Optional difference delta.
        help_text: Optional tooltip text.
    """
    val_str = f"{value:.2f}{suffix}" if isinstance(value, float) else f"{value}{suffix}"
    delta_str = f"{delta:+.2f}{suffix}" if delta is not None else None

    st.metric(
        label=label,
        value=val_str,
        delta=delta_str,
        help=help_text,
    )
