"""Real packets -> the model's (5, 20) windows, through the same CICIoT2023 extractor and
behavioral mapping the model was trained on (src/features/ciciot_features.py, load_cic)."""
import json
from collections import Counter

import numpy as np
import pandas as pd

from src.data.dataset_loader import FEATURE_COLS, cic_behavioral
from src.features.ciciot_features import FEATURES, _parse, chunk_rows

EMPTY = np.zeros((0, 5, len(FEATURE_COLS)), dtype=np.float32)


class CicLive:
    def __init__(self, scaler_json, block_packets=10):
        with open(scaler_json) as f:
            sc = json.load(f)
        self.center, self.scale = np.array(sc["center"]), np.array(sc["scale"])
        self.block = block_packets
        self.tail = np.zeros((0, len(FEATURE_COLS)))           # last 4 rows: windows span batches

    def windows(self, frames):
        """frames: list of (ts, bytes) Ethernet frames. Returns (n, 5, 20) float32 windows.
        ponytail: extractor state resets per batch, not per 10 MB chunk as in the dataset;
        make chunk_rows incremental if the P6 gate shows this matters."""
        rows = pd.DataFrame(chunk_rows(frames), columns=FEATURES)
        n = len(rows) // self.block * self.block
        if n == 0:
            return EMPTY
        cic = rows.iloc[:n].groupby(np.arange(n) // self.block).mean()
        x = cic_behavioral(cic)[FEATURE_COLS].to_numpy(np.float64)
        x = np.clip(np.sign(x) * np.log1p(np.abs(x)), -50, 50)
        x = (x - self.center) / self.scale
        seq = np.vstack([self.tail, x])
        self.tail = seq[-4:]
        if len(seq) < 5:
            return EMPTY
        return np.lib.stride_tricks.sliding_window_view(seq, (5, seq.shape[1])).reshape(-1, 5, seq.shape[1]).astype(np.float32)


def top_source(frames, exclude=()):
    """(ip, share) of the most common IPv4 source among the frames, ignoring `exclude`."""
    srcs = []
    for _, buf in frames:
        p = _parse(buf)
        if p and p[0] == "ip" and p[2]["src"] not in exclude:
            srcs.append(p[2]["src"])
    if not srcs:
        return None, 0.0
    ip, n = Counter(srcs).most_common(1)[0]
    return ip, n / len(frames)
