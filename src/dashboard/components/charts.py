"""
Shared chart builders using Plotly for W-SENTRY dashboard.
"""
from typing import Dict, List, Optional
import numpy as np
import plotly.graph_objects as go


DARK_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(26,29,35,0.7)",
    font=dict(color="#fafafa", family="sans-serif"),
    margin=dict(l=40, r=40, t=50, b=40),
)


def create_grouped_bar_chart(
    datasets: List[str],
    model_scores: Dict[str, List[float]],
    metric_name: str = "Accuracy (%)"
) -> go.Figure:
    """
    Creates a grouped bar chart comparing models across datasets.
    """
    fig = go.Figure()
    colors = ["#3b82f6", "#10b981", "#00d4ff", "#f59e0b", "#ec4899"]

    for idx, (model_name, scores) in enumerate(model_scores.items()):
        color = colors[idx % len(colors)]
        fig.add_trace(
            go.Bar(
                name=model_name,
                x=datasets,
                y=scores,
                text=[f"{s:.2f}%" for s in scores],
                textposition="auto",
                marker_color=color,
            )
        )

    fig.update_layout(
        barmode="group",
        title=f"Model Comparison across Datasets ({metric_name})",
        yaxis=dict(title=metric_name, range=[0, 105]),
        xaxis=dict(title="Dataset"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        **DARK_LAYOUT,
    )
    return fig


def create_annotated_matrix_heatmap(
    z: np.ndarray | List[List[float]],
    x_labels: List[str],
    y_labels: List[str],
    title: str = "Transfer Matrix",
    colorscale: str = "RdYlGn",
    is_percentage: bool = True
) -> go.Figure:
    """
    Creates an annotated heatmap for transfer matrix or confusion matrix.
    """
    z_arr = np.array(z)
    text_annotations = []
    for row in z_arr:
        text_row = []
        for val in row:
            if is_percentage:
                text_row.append(f"{val:.2f}%")
            else:
                text_row.append(f"{val:.3f}" if isinstance(val, float) else f"{val}")
        text_annotations.append(text_row)

    fig = go.Figure(
        go.Heatmap(
            z=z_arr,
            x=x_labels,
            y=y_labels,
            text=text_annotations,
            texttemplate="%{text}",
            textfont=dict(size=14, color="white"),
            colorscale=colorscale,
            showscale=True,
        )
    )

    fig.update_layout(
        title=title,
        xaxis=dict(title="Target Domain / Predicted Class"),
        yaxis=dict(title="Source Domain / True Class", autorange="reversed"),
        **DARK_LAYOUT,
    )
    return fig


def create_roc_figure(
    roc_data: Dict[str, Dict[str, np.ndarray]],
    class_names: List[str]
) -> go.Figure:
    """
    Creates a multi-class ROC curve plot.
    roc_data: mapping class_label -> {'fpr': array, 'tpr': array, 'auc': float}
    """
    fig = go.Figure()

    # Diagonal random baseline
    fig.add_trace(
        go.Scatter(
            x=[0, 1],
            y=[0, 1],
            mode="lines",
            line=dict(color="#64748b", dash="dash"),
            name="Chance (AUC = 0.50)",
        )
    )

    colors = ["#10b981", "#ef4444", "#f59e0b", "#00d4ff", "#a855f7", "#ec4899"]
    for i, (name, d) in enumerate(roc_data.items()):
        fpr = d["fpr"]
        tpr = d["tpr"]
        auc = d.get("auc", 0.0)
        color = colors[i % len(colors)]
        fig.add_trace(
            go.Scatter(
                x=fpr,
                y=tpr,
                mode="lines",
                line=dict(color=color, width=2),
                name=f"{name} (AUC = {auc:.3f})",
            )
        )

    fig.update_layout(
        title="Receiver Operating Characteristic (ROC) Curves",
        xaxis=dict(title="False Positive Rate (FPR)", range=[-0.02, 1.02]),
        yaxis=dict(title="True Positive Rate (TPR)", range=[-0.02, 1.05]),
        legend=dict(orientation="v", yanchor="bottom", y=0.05, xanchor="right", x=0.98),
        **DARK_LAYOUT,
    )
    return fig


def create_gauge_chart(value: float, max_val: float = 100.0, title: str = "Threat Rate") -> go.Figure:
    """Creates a gauge for threat rate or packet rate."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            title={"text": title, "font": {"color": "#fafafa"}},
            gauge={
                "axis": {"range": [0, max_val], "tickcolor": "#fafafa"},
                "bar": {"color": "#ef4444" if value > (max_val * 0.4) else "#00d4ff"},
                "steps": [
                    {"range": [0, max_val * 0.3], "color": "rgba(16, 185, 129, 0.2)"},
                    {"range": [max_val * 0.3, max_val * 0.7], "color": "rgba(245, 158, 11, 0.2)"},
                    {"range": [max_val * 0.7, max_val], "color": "rgba(239, 68, 68, 0.2)"},
                ],
            },
        )
    )
    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#fafafa"),
    )
    return fig

