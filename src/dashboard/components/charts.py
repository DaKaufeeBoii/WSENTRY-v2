"""
Shared Plotly chart builders and styling for W-SENTRY dashboard.
"""
from typing import Dict, List, Any, Optional
import plotly.graph_objects as go
import plotly.express as px
import plotly.figure_factory as ff

# Consistent threat color mapping across all tabs
CLASS_COLORS: Dict[int, str] = {
    0: "#10b981",  # Normal: Emerald Green
    1: "#a855f7",  # Jamming: Purple
    2: "#f97316",  # Spoofing: Orange
    3: "#ef4444",  # DoS_Flood: Crimson Red
    4: "#eab308",  # Intrusion_Probe: Amber Yellow
}

CLASS_NAMES: Dict[int, str] = {
    0: "Normal",
    1: "Jamming",
    2: "Spoofing",
    3: "DoS_Flood",
    4: "Intrusion_Probe",
}

COLOR_MAP = {CLASS_NAMES[k]: v for k, v in CLASS_COLORS.items()}


def apply_dark_theme(fig: go.Figure, title: Optional[str] = None) -> go.Figure:
    """Apply unified dark cyber aesthetic to a Plotly figure."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1a1d23",
        plot_bgcolor="#0e1117",
        font=dict(color="#fafafa", family="sans-serif", size=12),
        margin=dict(l=40, r=40, t=50 if title else 30, b=40),
        title=dict(text=title, font=dict(size=16, color="#00d4ff")) if title else None,
        hoverlabel=dict(bgcolor="#1a1d23", font_size=12, font_color="#ffffff"),
    )
    fig.update_xaxes(gridcolor="#282d37", zerolinecolor="#3b4252")
    fig.update_yaxes(gridcolor="#282d37", zerolinecolor="#3b4252")
    return fig


def create_dark_figure(title: Optional[str] = None) -> go.Figure:
    """Instantiate an empty Figure with the dark theme applied."""
    fig = go.Figure()
    return apply_dark_theme(fig, title=title)


def create_annotated_heatmap(
    z_matrix: List[List[float]],
    x_labels: List[str],
    y_labels: List[str],
    title: str = "",
    colorscale: str = "RdYlGn",
    value_format: str = ".1f",
    suffix: str = "%",
    showscale: bool = True,
) -> go.Figure:
    """Create an annotated heatmap compatible with all Plotly versions including 7+."""
    annot_text = [[f"{val:{value_format}}{suffix}" for val in row] for row in z_matrix]
    fig = go.Figure(
        data=go.Heatmap(
            z=z_matrix,
            x=x_labels,
            y=y_labels,
            text=annot_text,
            texttemplate="%{text}",
            textfont=dict(size=12, color="#ffffff"),
            colorscale=colorscale,
            showscale=showscale,
            hoverongaps=False,
        )
    )
    apply_dark_theme(fig, title=title)
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return fig


def create_gauge(value: float, title: str = "Threat Level", max_val: float = 100.0) -> go.Figure:
    """Create a real-time dial / gauge chart for threat rate."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": "%", "font": {"color": "#fafafa", "size": 28}},
            title={"text": title, "font": {"color": "#00d4ff", "size": 14}},
            gauge={
                "axis": {"range": [0, max_val], "tickcolor": "#888"},
                "bar": {"color": "#00d4ff"},
                "bgcolor": "#1a1d23",
                "steps": [
                    {"range": [0, 20], "color": "rgba(16, 185, 129, 0.3)"},
                    {"range": [20, 50], "color": "rgba(234, 179, 8, 0.3)"},
                    {"range": [50, 100], "color": "rgba(239, 68, 68, 0.4)"},
                ],
                "threshold": {
                    "line": {"color": "#ef4444", "width": 4},
                    "thickness": 0.75,
                    "value": 50,
                },
            },
        )
    )
    apply_dark_theme(fig)
    fig.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=220)
    return fig
