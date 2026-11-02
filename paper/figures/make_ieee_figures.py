"""Paper figures drawn only from the saved results in data/processed/.

Run from the repo root:  python paper/figures/make_ieee_figures.py
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
P1 = json.loads((ROOT / "data/processed/phase1_results.json").read_text(encoding="utf-8"))

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "STIXGeneral", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "pdf.fonttype": 42,
})

# Classes present in each test set (order of the saved confusion matrices).
CLASSES = {"WSN-DS": [0, 1, 2, 3], "CIC-IoT": [0, 2, 3, 4], "Edge-IIoT": [0, 2, 3, 4]}
TITLES = {"WSN-DS": "(a) WSN-DS", "CIC-IoT": "(b) CICIoT2023", "Edge-IIoT": "(c) Edge-IIoTset"}


def rf_confusion():
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.35), constrained_layout=True)
    for ax, (key, cls) in zip(axes, CLASSES.items()):
        cm = np.array(P1["same_dataset"][f"RF_{key}"]["confusion_matrix"], dtype=float)
        pct = 100 * cm / cm.sum(axis=1, keepdims=True)
        im = ax.imshow(pct, cmap="Greys", vmin=0, vmax=100)
        for i in range(len(cls)):
            for j in range(len(cls)):
                ax.text(j, i, f"{pct[i, j]:.1f}\n({int(cm[i, j]):,})", ha="center", va="center",
                        fontsize=6, color="white" if pct[i, j] > 55 else "black")
        ax.set_xticks(range(len(cls)), cls)
        ax.set_yticks(range(len(cls)), cls)
        ax.set_xlabel("Predicted class")
        ax.set_ylabel("True class")
        ax.set_title(TITLES[key])
    fig.colorbar(im, ax=axes, shrink=0.85, label="Row percentage")
    fig.savefig(OUT / "fig_rf_cm.pdf")
    plt.close(fig)


if __name__ == "__main__":
    rf_confusion()
    # Self-check: row percentages of the Edge-IIoTset class-3 row match the paper's 37.7% figure.
    cm = np.array(P1["same_dataset"]["RF_Edge-IIoT"]["confusion_matrix"], dtype=float)
    assert round(100 * cm[2, 1] / cm[2].sum(), 1) == 37.7
    print("wrote", OUT / "fig_rf_cm.pdf")
