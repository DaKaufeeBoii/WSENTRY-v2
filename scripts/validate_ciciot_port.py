"""
Check the CICIoT2023 feature port against the official CSV: every official row of a class
is the mean of one 10-packet block of that class's capture, so an exact port reproduces
each official row among its own rows.

usage: python scripts/validate_ciciot_port.py LABEL PCAP [CSV_GLOB]
"""
import glob
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.features.ciciot_features import FEATURES, extract

label, pcap = sys.argv[1], sys.argv[2]
pattern = sys.argv[3] if len(sys.argv) > 3 else "data/raw/ciciot2023_kaggle_csv/wataiData/csv/CICIoT2023/part-*.csv"
official = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(pattern))])
official = official[official["label"] == label][FEATURES].to_numpy(float)
mine = extract(pcap, n_rows=10)[FEATURES].to_numpy(float)

scale = np.maximum(np.abs(official), 1e-9)
best = np.array([(np.abs(mine - row) / scale[i]).max(axis=1).min() for i, row in enumerate(official)])
worst_feature = [FEATURES[int(np.argmax(np.abs(mine[np.argmin((np.abs(mine - row) / scale[i]).max(axis=1))] - row)
                                        / scale[i]))] for i, row in enumerate(official)]
print(f"{label}: {len(official)} official rows, {len(mine)} extracted rows")
for tol in (1e-9, 1e-6, 1e-3):
    print(f"  official rows reproduced within relative {tol:g}: {np.mean(best <= tol):.1%}")
if (best > 1e-6).any():
    print("  features most often off:", pd.Series(worst_feature)[best > 1e-6].value_counts().head(5).to_dict())
