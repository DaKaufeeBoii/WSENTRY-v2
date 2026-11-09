"""Run the deployed model on every artifact in attack_samples.json.

  --write  : save predictions to scripts/golden_predictions.json   (run on laptop A)
  default  : compare with that golden file, exit 1 on any mismatch  (run on the UNO Q)
Also prints latency and, per attack family, how many artifacts the model flags with
the family's own class at confidence >= 0.85 (the block threshold)."""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.live.inference import InferenceEngine  # noqa: E402

FAMILY_CLASS = {"jam": 1, "spoof": 2, "dos": 3, "scan": 4}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--samples", default=str(ROOT / "scripts" / "attack_samples.json"))
    ap.add_argument("--golden", default=str(ROOT / "scripts" / "golden_predictions.json"))
    a = ap.parse_args()
    if a.threads:
        import torch
        torch.set_num_threads(a.threads)
    pools = json.loads(Path(a.samples).read_text())["pools"]
    eng = InferenceEngine(model_dir=str(ROOT / "models" / "saved"))
    eng.predict_batch(np.zeros((1, 5, 20), dtype=np.float32))          # warm-up
    preds, t0 = {}, time.perf_counter()
    for fam, seqs in pools.items():
        out = eng.predict_batch(np.asarray(seqs, dtype=np.float32))
        preds[fam] = [[int(c), round(float(p), 4)] for c, p, _ in out]
    ms = (time.perf_counter() - t0) * 1000
    n = sum(len(v) for v in preds.values())
    print(f"[parity] {n} artifacts in {ms:.0f} ms ({ms / n:.2f} ms each)")
    for fam, rows in preds.items():
        hit = sum(1 for c, p in rows if c == FAMILY_CLASS[fam] and p >= 0.85)
        print(f"[parity] {fam:5s} {hit:3d}/{len(rows)} flagged as its own class with conf >= 0.85")
    if a.write:
        Path(a.golden).write_text(json.dumps(preds))
        print(f"[parity] wrote {a.golden}")
        return
    gold = json.loads(Path(a.golden).read_text())
    bad = [(f, i, g, p) for f in gold for i, (g, p) in enumerate(zip(gold[f], preds[f]))
           if g[0] != p[0] or abs(g[1] - p[1]) > 1e-3]
    if bad:
        print(f"[parity] FAIL: {len(bad)} mismatches, first: {bad[:5]}")
        sys.exit(1)
    print("[parity] PASS: same classes, confidences within 0.001")


if __name__ == "__main__":
    main()
