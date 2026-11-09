"""Feed a pcap through the live chain (CicLive -> model) in 10*block-frame batches, like the board.
   python scripts/unoq/check_live_chain.py <pcap> --expect <class id>"""
import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.features.ciciot_features import read_pcap  # noqa: E402
from src.live.cic_live import CicLive  # noqa: E402
from src.live.inference import InferenceEngine  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("pcap")
ap.add_argument("--expect", type=int, required=True)
ap.add_argument("--block-packets", type=int, default=100)
ap.add_argument("--max-frames", type=int, default=20000)
a = ap.parse_args()
live = CicLive(ROOT / "models" / "saved" / "scaler.json", a.block_packets)
eng = InferenceEngine(model_dir=str(ROOT / "models" / "saved"))
batch, preds = [], []
for i, fr in enumerate(read_pcap(a.pcap)):
    if i >= a.max_frames:
        break
    batch.append(fr)
    if len(batch) == 10 * a.block_packets:
        w, batch = live.windows(batch), []
        if len(w):
            preds += [(c, p) for c, p, _ in eng.predict_batch(w)]
counts = Counter(c for c, _ in preds)
hit = sum(1 for c, p in preds if c == a.expect and p >= 0.85)
print(f"{len(preds)} windows  classes {dict(counts)}  most common {counts.most_common(1)}  "
      f"hit(class {a.expect}, conf >= 0.85) {hit / max(1, len(preds)):.0%}")
