"""
Experiment 4: does a model flag an attack family it never saw in training?

For each dataset and attack family, train on everything except that family (same
features, weighting and models as run_step0.py), then score how well the unknown score
1 - max class probability separates the family's test rows from the known test rows.

usage: python run_exp4_unknown.py [--datasets wsn cic edge] [--models rf xgb hybrid]
                                  [--seeds 0 1 2 3 4] [--max-rows N] [--out data/processed/exp4]
"""
import argparse
import json
import os
import sys
import time

import numpy as np
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_step0 import CONFIG as STEP0, DEVICE, fit_predict
from src.data.full_features import DATASETS, load, prepare
from src.eval.metrics import score
from src.utils import set_seed

# raw label -> attack family. CICIoT2023 follows its paper's seven categories and
# Edge-IIoTset its five; membership is read from the label names (check against both papers).
FAMILIES = {
    "wsn": {"Blackhole": "Blackhole", "Grayhole": "Grayhole", "Flooding": "Flooding", "TDMA": "TDMA"},
    "cic": {
        **{l: "DDoS" for l in ["DDoS-ICMP_Flood", "DDoS-UDP_Flood", "DDoS-TCP_Flood", "DDoS-PSHACK_Flood",
                               "DDoS-SYN_Flood", "DDoS-RSTFINFlood", "DDoS-SynonymousIP_Flood",
                               "DDoS-ICMP_Fragmentation", "DDoS-UDP_Fragmentation", "DDoS-ACK_Fragmentation",
                               "DDoS-HTTP_Flood", "DDoS-SlowLoris"]},
        **{l: "DoS" for l in ["DoS-UDP_Flood", "DoS-TCP_Flood", "DoS-SYN_Flood", "DoS-HTTP_Flood"]},
        **{l: "Mirai" for l in ["Mirai-greeth_flood", "Mirai-udpplain", "Mirai-greip_flood"]},
        **{l: "Recon" for l in ["Recon-HostDiscovery", "Recon-OSScan", "Recon-PortScan", "Recon-PingSweep",
                                "VulnerabilityScan"]},
        **{l: "Web" for l in ["SqlInjection", "CommandInjection", "XSS", "BrowserHijacking",
                              "Backdoor_Malware", "Uploading_Attack"]},
        "DictionaryBruteForce": "BruteForce",
        "MITM-ArpSpoofing": "Spoofing", "DNS_Spoofing": "Spoofing",
    },
    "edge": {
        **{l: "DDoS" for l in ["DDoS_UDP", "DDoS_ICMP", "DDoS_TCP", "DDoS_HTTP"]},
        **{l: "Scanning" for l in ["Port_Scanning", "Vulnerability_scanner", "Fingerprinting"]},
        **{l: "Injection" for l in ["SQL_injection", "XSS", "Uploading"]},
        **{l: "Malware" for l in ["Backdoor", "Password", "Ransomware"]},
        "MITM": "MITM",
    },
}
FPR = 0.05  # detection rate is reported at the threshold that flags 5% of known test rows


def unknown_metrics(unknown, pred, proba):
    s = 1 - proba.max(1)
    thr = np.quantile(s[~unknown], 1 - FPR)
    return {
        "auroc_unknown": float(roc_auc_score(unknown, s)),
        "detect_at_5pct_fpr": float(np.mean(s[unknown] > thr)),
        # an unseen attack labelled as any attack class still raises an alert
        "alerted_as_attack": float(np.mean(pred[unknown] != 0)),
        "n_unknown_test": int(unknown.sum()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", nargs="+", default=list(FAMILIES))
    ap.add_argument("--models", nargs="+", default=["rf", "xgb", "hybrid"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    ap.add_argument("--max-rows", type=int)
    ap.add_argument("--out", default="data/processed/exp4")
    args = ap.parse_args()
    os.makedirs(os.path.join(args.out, "runs"), exist_ok=True)

    for ds in args.datasets:
        X, y, feats, raw = load(ds, max_rows=args.max_rows or STEP0["max_rows"][ds],
                                sample_seed=STEP0["sample_seed"], with_raw=True)
        fam = np.array([FAMILIES[ds].get(r, "Normal") for r in raw])
        assert (fam[y == 0] == "Normal").all() and (fam[y != 0] != "Normal").all(), "family map missed a label"
        codes = np.unique(fam, return_inverse=True)[1]
        for held in sorted(set(fam) - {"Normal"}):
            for seed in args.seeds:
                for model in args.models:
                    path = os.path.join(args.out, "runs", f"{ds}__{held}__{model}__seed{seed}.json")
                    if os.path.exists(path):
                        continue
                    data = prepare(X, y, seed, time_steps=STEP0["time_steps"], strat=codes, drop=fam == held)
                    set_seed(seed)
                    t0 = time.time()
                    pred, proba, _ = fit_predict(model, data, seed)
                    unknown = fam[data["idx_test"]] == held
                    rec = {"dataset": ds, "held_out": held, "model": model, "seed": seed,
                           **unknown_metrics(unknown, pred, proba),
                           "known": score(data["y_test"][~unknown], pred[~unknown]),
                           "seconds": round(time.time() - t0, 1), "device": DEVICE, "fpr": FPR,
                           "data": DATASETS[ds]["path"]}
                    json.dump(rec, open(path, "w"), indent=1)
                    print(f"  {ds} hold-out {held} {model} seed {seed}: AUROC {rec['auroc_unknown']:.3f}  "
                          f"detect@5%FPR {rec['detect_at_5pct_fpr']:.3f}  alerted {rec['alerted_as_attack']:.3f}")
    summarize(args.out)


def summarize(out_dir):
    runs = [json.load(open(os.path.join(out_dir, "runs", f))) for f in sorted(os.listdir(os.path.join(out_dir, "runs")))]
    groups = {}
    for r in runs:
        groups.setdefault((r["dataset"], r["held_out"], r["model"]), []).append(r)
    keys = ["auroc_unknown", "detect_at_5pct_fpr", "alerted_as_attack"]
    summary, lines = {}, ["| dataset | held-out family | model | seeds | AUROC | detected at 5% FPR | alerted as attack |",
                          "| --- | --- | --- | --- | --- | --- | --- |"]
    for (ds, held, model), rs in sorted(groups.items()):
        row = {k: {"mean": float(np.mean([r[k] for r in rs])),
                   "std": float(np.std([r[k] for r in rs], ddof=1)) if len(rs) > 1 else 0.0} for k in keys}
        row["seeds"] = [r["seed"] for r in rs]
        summary[f"{ds}/{held}/{model}"] = row
        lines.append(f"| {ds} | {held} | {model} | {len(rs)} | " + " | ".join(
            f"{row[k]['mean']:.3f} ± {row[k]['std']:.3f}" for k in keys) + " |")
    json.dump(summary, open(os.path.join(out_dir, "summary.json"), "w"), indent=2)
    open(os.path.join(out_dir, "summary.md"), "w", encoding="utf-8").write(
        "Experiment 4: unknown-family detection, mean ± sample std over seeds.\n\n" + "\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
