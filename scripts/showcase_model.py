"""
W-SENTRY model showcase — prove the deployed checkpoint actually detects threats.

Loads the trained model through the SAME serving path the live dashboard uses
(`src.live.inference.InferenceEngine`), runs held-out behavioral windows for every
threat class through it, and shows predicted label + calibrated confidence + the
mitigation action the firewall engine would take. Also prints the honest held-out
benchmark written by scripts/train_model.py.

Usage:
    python scripts/showcase_model.py
"""
import os
import sys
import json
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.live.inference import InferenceEngine, THREAT_LABELS
from src.live.buffer import PacketRecord
from src.live.mitigation import MitigationEngine, MitigationMode

SAMPLES = PROJECT_ROOT / "data" / "processed" / "showcase_samples.npz"
EVAL = PROJECT_ROOT / "data" / "processed" / "showcase_eval.json"


def load_or_make_samples():
    """Return (X, y) held-out windows. Regenerate a small set if none saved."""
    if SAMPLES.exists():
        d = np.load(SAMPLES)
        return d["X"], d["y"]

    print("[showcase] No saved samples; regenerating a small deterministic set ...")
    from src.data.dataset_loader import load_wsn, load_cic, load_edge, FEATURE_COLS
    from src.features.preprocessor import preprocess
    import pandas as pd

    frames = []
    for name, loader in [("WSN", load_wsn), ("CIC", load_cic), ("Edge", load_edge)]:
        df = loader(mode="behavioral", max_rows=8000)
        frames.append(df[FEATURE_COLS + ["threat_class"]].copy())
    combined = pd.concat(frames, ignore_index=True).sample(frac=1.0, random_state=42)
    data = preprocess(combined, feature_cols=FEATURE_COLS, smote=False,
                      time_steps=5, random_state=42)
    X, y = data["X_test_seq"], data["y_test_seq"]
    idx = []
    rng = np.random.RandomState(42)
    for cid in sorted(set(y.tolist())):
        ci = np.where(y == cid)[0]
        idx.extend(rng.choice(ci, size=min(60, len(ci)), replace=False).tolist())
    idx = np.array(sorted(idx))
    X, y = X[idx].astype(np.float32), y[idx].astype(np.int64)
    np.savez_compressed(SAMPLES, X=X, y=y)
    return X, y


def main():
    print("=" * 66)
    print(" 🛡  W-SENTRY MODEL SHOWCASE")
    print("=" * 66)

    engine = InferenceEngine(model_dir=str(PROJECT_ROOT / "models" / "saved"))
    mit = MitigationEngine(mode=MitigationMode.SIMULATED, cooldown_seconds=0.0)

    X, y = load_or_make_samples()
    probs = engine.get_probabilities(X)
    preds = probs.argmax(axis=1)
    conf = probs.max(axis=1)

    overall = float((preds == y).mean())

    # Per-class live-serving summary.
    print("\n Deployed engine on held-out behavioral windows "
          f"({len(y)} samples, serving path = InferenceEngine):\n")
    print(f"  {'True class':18s} {'n':>4s} {'correct':>8s} {'avg conf':>9s}")
    print("  " + "-" * 44)
    for cid in sorted(set(y.tolist())):
        m = y == cid
        acc = float((preds[m] == cid).mean())
        print(f"  {THREAT_LABELS.get(cid, str(cid)):18s} {int(m.sum()):>4d} "
              f"{acc*100:>7.1f}% {conf[m].mean()*100:>8.1f}%")
    print("  " + "-" * 44)
    print(f"  {'OVERALL':18s} {len(y):>4d} {overall*100:>7.1f}%")

    # Walk a few representative detections through the mitigation engine.
    print("\n Example detections → autonomous mitigation:\n")
    shown = set()
    for i in range(len(y)):
        cid = int(preds[i])
        if cid in shown or cid == 0:
            continue
        shown.add(cid)
        rec = PacketRecord(
            timestamp=0.0, src_ip=f"192.168.1.{50 + cid}", dst_ip="192.168.1.100",
            src_port=4444, dst_port=80, protocol="TCP", length=64, flags="S",
            prediction=cid, confidence=float(conf[i]),
            label=THREAT_LABELS.get(cid, str(cid)),
        )
        action = mit.respond(rec)
        act = f"{action.action} ({action.rule_command.split('name=')[0].strip() or 'alert'})" \
            if action else "no action"
        true_lbl = THREAT_LABELS.get(int(y[i]), str(int(y[i])))
        flag = "✓" if cid == int(y[i]) else "≈"
        print(f"  {flag} predicted {THREAT_LABELS.get(cid, str(cid)):16s} "
              f"conf={conf[i]*100:5.1f}%  true={true_lbl:16s} → {action.action if action else 'ALERT_ONLY'}")

    # Honest benchmark from training.
    if EVAL.exists():
        rep = json.loads(EVAL.read_text())
        print("\n" + "=" * 66)
        print(" HELD-OUT BENCHMARK (from scripts/train_model.py)")
        print("=" * 66)
        print(f"  datasets      : {rep.get('datasets')}")
        print(f"  test accuracy : {rep['accuracy']*100:.2f}%")
        print(f"  macro AUC     : {rep.get('macro_auc')}")
        print(f"  ECE (calib.)  : {rep.get('ece')}")
        print("  per-class F1  :")
        for lbl, m in rep.get("per_class", {}).items():
            print(f"     {lbl:16s} P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f}")
    else:
        print("\n[showcase] No benchmark file yet — run: python scripts/train_model.py")

    print("\n" + "=" * 66)
    print(" Launch the full interactive SOC:  scripts/run_dashboard.sh")
    print("=" * 66)


if __name__ == "__main__":
    main()
