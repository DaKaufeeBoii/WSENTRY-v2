"""
Dashboard tabs package.
"""
from .tab_performance import render as render_tab_performance
from .tab_live_monitor import render as render_tab_live_monitor
from .tab_transfer_matrix import render as render_tab_transfer_matrix
from .tab_roc_auc import render as render_tab_roc_auc
from .tab_per_class import render as render_tab_per_class
from .tab_profiler import render as render_tab_profiler

__all__ = [
    "render_tab_performance",
    "render_tab_live_monitor",
    "render_tab_transfer_matrix",
    "render_tab_roc_auc",
    "render_tab_per_class",
    "render_tab_profiler",
]
