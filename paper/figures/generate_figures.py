"""
Generate 4 publication-quality figures for the W-SENTRY IEEE paper.
All figures: 300 DPI, IEEE-compliant white background, Times New Roman fonts.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as path_effects
import numpy as np
import os

OUT = r"C:\Users\Riteesh\Programming\w-sentry\paper\figures"

# ── Global IEEE style ──────────────────────────────────────────────────
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif'],
    'font.size': 9,
    'axes.titlesize': 10,
    'axes.labelsize': 9,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.05,
    'axes.linewidth': 0.6,
    'lines.linewidth': 1.0,
    'patch.linewidth': 0.5,
})

# Color palette — professional, colorblind-safe
C_BG = '#FFFFFF'
C_TEXT = '#1a1a2e'
C_ACCENT1 = '#2563EB'   # blue
C_ACCENT2 = '#059669'   # emerald
C_ACCENT3 = '#DC2626'   # red
C_ACCENT4 = '#7C3AED'   # violet
C_ACCENT5 = '#D97706'   # amber
C_LIGHT = '#F1F5F9'
C_MID = '#94A3B8'
C_DARK = '#334155'

# ═══════════════════════════════════════════════════════════════════════
# FIGURE 1: System Architecture Diagram
# ═══════════════════════════════════════════════════════════════════════

def draw_box(ax, x, y, w, h, label, color, text_color='white', fontsize=7, bold=False, sublabel=None):
    """Draw a rounded box with centered text."""
    box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                         boxstyle="round,pad=0.02",
                         facecolor=color, edgecolor='#475569',
                         linewidth=0.6, zorder=3)
    ax.add_patch(box)
    weight = 'bold' if bold else 'normal'
    ax.text(x, y + (0.015 if sublabel else 0), label,
            ha='center', va='center', fontsize=fontsize,
            color=text_color, fontweight=weight, zorder=4)
    if sublabel:
        ax.text(x, y - 0.025, sublabel,
                ha='center', va='center', fontsize=5.5,
                color=text_color, alpha=0.85, zorder=4, style='italic')

def draw_arrow(ax, x1, y1, x2, y2, color='#475569', style='->', lw=0.8):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw),
                zorder=2)

def fig1_architecture():
    fig, ax = plt.subplots(1, 1, figsize=(7.16, 5.5))
    ax.set_xlim(0, 1.4)
    ax.set_ylim(0, 1)
    ax.set_aspect('auto')
    ax.axis('off')
    fig.patch.set_facecolor(C_BG)

    # Title
    ax.text(0.7, 0.97, 'W-SENTRY System Architecture',
            ha='center', va='top', fontsize=12, fontweight='bold', color=C_TEXT)

    cx = 0.5  # center x for main pipeline

    # ── Row 1: Datasets ──
    y_ds = 0.88
    datasets = [('WSN-DS', cx - 0.25), ('CIC-IoT-2023', cx), ('Edge-IIoTset', cx + 0.25)]
    for name, x in datasets:
        draw_box(ax, x, y_ds, 0.22, 0.055, name, '#1E3A5F', fontsize=7.5)

    ax.text(cx, 0.925, 'Multi-Source Datasets', ha='center', va='center',
            fontsize=7.5, color=C_DARK, fontweight='bold')

    for _, x in datasets:
        draw_arrow(ax, x, y_ds - 0.028, cx, 0.815)

    # ── Row 2: Feature Mapping ──
    y_feat = 0.785
    draw_box(ax, cx, y_feat, 0.42, 0.055, 'Behavioral Feature Mapping', '#2563EB', fontsize=8, sublabel='20 unified features')
    draw_arrow(ax, cx, y_feat - 0.028, cx, 0.725)

    # ── Row 3: Normalization ──
    y_norm = 0.695
    draw_box(ax, cx, y_norm, 0.42, 0.055, 'Log Normalization + RobustScaler', '#0369A1', fontsize=7.5)
    draw_arrow(ax, cx, y_norm - 0.028, cx, 0.635)

    # ── Row 4: Sliding Window ──
    y_sw = 0.605
    draw_box(ax, cx, y_sw, 0.35, 0.05, 'Sliding Window (T=5)', '#0E7490', fontsize=8)

    # ── Branching: two paths ──
    x_left = 0.3
    x_right = 0.7
    draw_arrow(ax, cx - 0.1, y_sw - 0.025, x_left, 0.525)
    draw_arrow(ax, cx + 0.1, y_sw - 0.025, x_right, 0.525)

    y_model = 0.495
    # Left: Baseline ML
    draw_box(ax, x_left, y_model, 0.28, 0.055, 'Baseline ML', '#059669', fontsize=8, sublabel='RF / XGBoost')

    # Right: Hybrid DL
    draw_box(ax, x_right, y_model, 0.34, 0.055, 'Hybrid CNN-BiLSTM-Attn', '#7C3AED', fontsize=7.5, sublabel='Temporal + Spatial features')

    # ── DANN branch (far right) ──
    x_dann = 1.12
    draw_box(ax, x_dann, y_model, 0.24, 0.055, 'DANN Module', '#DC2626', fontsize=7.5, sublabel='Gradient Reversal')
    draw_arrow(ax, x_right + 0.17, y_model, x_dann - 0.12, y_model, color='#DC2626', lw=0.8)

    # DANN to Domain Discriminator
    y_disc = 0.37
    draw_box(ax, x_dann, y_disc, 0.24, 0.05, 'Domain Discriminator', '#B91C1C', fontsize=7, sublabel='Adversarial alignment')
    draw_arrow(ax, x_dann, y_model - 0.028, x_dann, y_disc + 0.025, color='#DC2626', lw=0.7)

    # Dashed arrow back (gradient reversal)
    ax.annotate('', xy=(x_dann + 0.08, y_model - 0.028), xytext=(x_dann + 0.08, y_disc + 0.025),
                arrowprops=dict(arrowstyle='->', color='#DC2626', lw=0.6, linestyle='dashed'),
                zorder=2)
    ax.text(x_dann + 0.14, (y_model + y_disc) / 2, 'grad reversal',
            fontsize=6, color='#DC2626', ha='left', va='center', style='italic')

    # ── Merge arrows to classification ──
    y_class = 0.37
    draw_arrow(ax, x_left, y_model - 0.028, cx, y_class + 0.025)
    draw_arrow(ax, x_right, y_model - 0.028, cx, y_class + 0.025)

    # ── Row 6: Threat Classification ──
    draw_box(ax, cx, y_class, 0.42, 0.055, 'Threat Classification', '#B45309', fontsize=8, bold=True, sublabel='5 classes: Normal, DoS, Probe, R2L, U2R')
    draw_arrow(ax, cx, y_class - 0.028, cx, 0.29)

    # ── Row 7: Confidence Scoring ──
    y_conf = 0.26
    draw_box(ax, cx, y_conf, 0.32, 0.05, 'Confidence Scoring', '#92400E', fontsize=8)
    draw_arrow(ax, cx, y_conf - 0.025, cx, 0.19)

    # ── Row 8: Mitigation Engine ──
    y_mit = 0.16
    draw_box(ax, cx, y_mit, 0.36, 0.055, 'Mitigation Engine', '#1E3A5F', fontsize=8, bold=True, sublabel='Automated response actions')

    # ── Legend ──
    legend_items = [
        (mpatches.Patch(color='#2563EB'), 'Preprocessing'),
        (mpatches.Patch(color='#059669'), 'Baseline ML'),
        (mpatches.Patch(color='#7C3AED'), 'Deep Learning'),
        (mpatches.Patch(color='#DC2626'), 'Domain Adaptation'),
        (mpatches.Patch(color='#B45309'), 'Output'),
    ]
    ax.legend([i[0] for i in legend_items], [i[1] for i in legend_items],
              loc='lower center', framealpha=0.9, edgecolor='#CBD5E1',
              fontsize=6.5, ncol=5, bbox_to_anchor=(0.5, -0.01))

    fig.savefig(os.path.join(OUT, 'fig1_architecture.png'), facecolor=C_BG)
    plt.close(fig)
    print('[✓] Figure 1: System Architecture saved')


# ═══════════════════════════════════════════════════════════════════════
# FIGURE 2: Transfer Matrix Heatmaps
# ═══════════════════════════════════════════════════════════════════════

def fig2_transfer_matrix():
    datasets = ['WSN-DS', 'CIC-IoT', 'Edge-IIoT']

    rf_matrix = np.array([
        [99.60,  0.18, 11.94],
        [ 1.26, 99.42, 26.30],
        [ 1.90, 67.64, 92.06],
    ])

    dl_matrix = np.array([
        [97.79,  0.30, 80.70],
        [ 0.99, 97.79, 15.40],
        [26.96, 61.77, 97.42],
    ])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.16, 3.0))
    fig.patch.set_facecolor(C_BG)

    for idx, (ax, matrix, title) in enumerate([(ax1, rf_matrix, '(a) Random Forest'),
                               (ax2, dl_matrix, '(b) Hybrid CNN-BiLSTM-Attn')]):
        im = ax.imshow(matrix, cmap='YlOrRd', vmin=0, vmax=100, aspect='equal')

        ax.set_xticks(range(3))
        ax.set_yticks(range(3))
        ax.set_xticklabels(datasets, fontsize=7)
        ax.set_yticklabels(datasets, fontsize=7)
        ax.set_xlabel('Test Dataset', fontsize=8, labelpad=6)
        if idx == 0:
            ax.set_ylabel('Train Dataset', fontsize=8, labelpad=6)
        ax.set_title(title, fontsize=9, fontweight='bold', pad=8)

        # Annotate cells
        for i in range(3):
            for j in range(3):
                val = matrix[i, j]
                color = 'white' if val > 55 else '#1a1a2e'
                ax.text(j, i, f'{val:.1f}%',
                        ha='center', va='center', fontsize=8,
                        fontweight='bold', color=color)

        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)

    # Shared colorbar
    cbar = fig.colorbar(im, ax=[ax1, ax2], shrink=0.82, aspect=25, pad=0.03)
    cbar.set_label('Accuracy (%)', fontsize=8)
    cbar.ax.tick_params(labelsize=7)

    fig.suptitle('Cross-Dataset Transfer Accuracy (%)', fontsize=10,
                 fontweight='bold', y=1.02)

    fig.savefig(os.path.join(OUT, 'fig2_transfer_matrix.png'), facecolor=C_BG)
    plt.close(fig)
    print('[✓] Figure 2: Transfer Matrix Heatmaps saved')


# ═══════════════════════════════════════════════════════════════════════
# FIGURE 3: Same-Dataset Accuracy Bar Chart
# ═══════════════════════════════════════════════════════════════════════

def fig3_accuracy_bars():
    datasets = ['WSN-DS', 'CIC-IoT-2023', 'Edge-IIoTset']
    rf_vals   = [99.60, 99.42, 92.06]
    xgb_vals  = [99.56, 99.44, 91.92]
    dl_vals   = [98.06, 97.80, 94.39]

    x = np.arange(len(datasets))
    width = 0.22

    fig, ax = plt.subplots(figsize=(5.0, 3.2))
    fig.patch.set_facecolor(C_BG)
    ax.set_facecolor(C_BG)

    bars1 = ax.bar(x - width, rf_vals, width, label='Random Forest',
                   color=C_ACCENT1, edgecolor='white', linewidth=0.3, zorder=3)
    bars2 = ax.bar(x, xgb_vals, width, label='XGBoost',
                   color=C_ACCENT2, edgecolor='white', linewidth=0.3, zorder=3)
    bars3 = ax.bar(x + width, dl_vals, width, label='Hybrid DL',
                   color=C_ACCENT4, edgecolor='white', linewidth=0.3, zorder=3)

    # Value labels on bars
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, height + 0.3,
                    f'{height:.1f}',
                    ha='center', va='bottom', fontsize=6, color=C_DARK, fontweight='bold')

    ax.set_ylabel('Accuracy (%)', fontsize=9)
    ax.set_title('Same-Dataset Classification Accuracy', fontsize=10, fontweight='bold', pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(datasets, fontsize=8)
    ax.set_ylim(88, 101.5)
    ax.yaxis.grid(True, alpha=0.3, linestyle='--', zorder=0)
    ax.set_axisbelow(True)
    ax.legend(loc='lower left', framealpha=0.95, edgecolor='#CBD5E1', fontsize=7)

    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    ax.spines['left'].set_color('#CBD5E1')
    ax.spines['bottom'].set_color('#CBD5E1')

    fig.savefig(os.path.join(OUT, 'fig3_accuracy_comparison.png'), facecolor=C_BG)
    plt.close(fig)
    print('[✓] Figure 3: Accuracy Comparison saved')


# ═══════════════════════════════════════════════════════════════════════
# FIGURE 4: Log Normalization Ablation
# ═══════════════════════════════════════════════════════════════════════

def fig4_ablation():
    methods = ['Clip + RobustScaler\n(no log transform)', 'Log + Clip + RobustScaler\n(W-SENTRY)']
    values = [56.80, 94.39]
    colors = ['#94A3B8', C_ACCENT1]
    edge_colors = ['#64748B', '#1D4ED8']

    fig, ax = plt.subplots(figsize=(4.0, 3.2))
    fig.patch.set_facecolor(C_BG)
    ax.set_facecolor(C_BG)

    bars = ax.bar(methods, values, width=0.55, color=colors, edgecolor=edge_colors,
                  linewidth=0.8, zorder=3)

    # Value labels
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 1.5,
                f'{val:.1f}%',
                ha='center', va='bottom', fontsize=11, fontweight='bold',
                color=C_TEXT)

    # Improvement arrow
    ax.annotate('',
                xy=(1, values[1] - 2), xytext=(0, values[0] + 3),
                arrowprops=dict(arrowstyle='->', color=C_ACCENT2, lw=1.5,
                                connectionstyle='arc3,rad=0.3'))
    ax.text(0.5, 78, '+37.6 pp',
            ha='center', va='center', fontsize=9, fontweight='bold',
            color=C_ACCENT2,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#ECFDF5', edgecolor=C_ACCENT2, linewidth=0.6))

    ax.set_ylabel('Accuracy (%)', fontsize=9)
    ax.set_title('Impact of Log Normalization\non Edge-IIoTset', fontsize=10, fontweight='bold', pad=10)
    ax.set_ylim(0, 108)
    ax.yaxis.grid(True, alpha=0.3, linestyle='--', zorder=0)
    ax.set_axisbelow(True)

    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    ax.spines['left'].set_color('#CBD5E1')
    ax.spines['bottom'].set_color('#CBD5E1')

    fig.savefig(os.path.join(OUT, 'fig4_log_normalization_ablation.png'), facecolor=C_BG)
    plt.close(fig)
    print('[✓] Figure 4: Log Normalization Ablation saved')


# ═══════════════════════════════════════════════════════════════════════
# Run all
# ═══════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print(f'Output directory: {OUT}')
    fig1_architecture()
    fig2_transfer_matrix()
    fig3_accuracy_bars()
    fig4_ablation()
    print('\nAll 4 figures generated successfully.')
