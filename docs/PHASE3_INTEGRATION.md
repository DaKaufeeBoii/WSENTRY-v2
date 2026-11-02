# Phase 3 Integration Notes

This document records how the Phase 3 live-dashboard code (from the
`DaKaufeeBoii/WSENTRY-v2` repository) was merged into this project, what was
reconciled, how it was diagnosed, and how to run the live demo and the model
showcase.

---

## 1. What was merged in

The following Phase 3 components were brought in from the upstream repo (they did
not exist here before):

| Area | Files |
|------|-------|
| Live capture + inference | `src/live/` (buffer, capture, feature_extractor, inference, inference_thread, mitigation, save_artifacts) |
| Streamlit SOC dashboard | `src/dashboard/` (app, precompute_roc, `components/`, `tabs/` — 6 tabs) |
| Attack simulation toolkit | `src/attack/` (flood, scan, arp_spoof, runner) |
| Model artifacts | `models/saved/` (checkpoint, scaler, temp scaler, config) |
| Tests | `tests/test_phase3_{capture,features,mitigation,dashboard}.py` |
| Ops / docs | `scripts/demo_launcher.py`, `scripts/setup_wsl_attack.sh`, `docs/DEMO_RUNBOOK.md`, `GUIDE.md`, `changes.md`, `MANIFEST.json`, `.streamlit/config.toml`, `requirements_phase3.txt`, `data/processed/roc_curves.{json,npz}` |

All existing Phase 1 / Phase 2 / CICIoT / step0 / exp4 work in this repo was kept
untouched.

## 2. Conflicts reconciled

Four files existed in both repos with real differences. Resolution:

| File | Kept | Why |
|------|------|-----|
| `src/data/dataset_loader.py` | **upstream** | Superset — adds `_resolve_data_path()` so loaders work from any CWD (needed by the dashboard). Otherwise identical to ours. |
| `src/models/baseline_ml.py` | **ours** | Superset — adds `class_weight` / `sample_weight` params our Phase 2 / exp4 runs use. Backward compatible, so the upstream code is unaffected. |
| `tests/test_roc_export.py` | **upstream** | Fixes a real bug in our copy: it asserted `3 not in curves` where the dropped class id is `CLASSES[3] == 4`. |
| `tests/test_phase1.py` | **upstream** (then patched) | Upstream adds `skipif` guards + synthetic fallback so the suite runs with or without raw data. See the fix below. |
| `README.md` | **upstream** | Phase 3 section updated from "TODO" to the launch instructions. |
| `.gitignore` | **merged** | Upstream base (tracks `models/saved/*.pt,*.pkl`) + our extra ignores (`*.h5`, `logs/`, `*.tmp`, `temp/`). |

## 3. Bug found during diagnosis

`tests/test_phase1.py::test_edge_loads` called `load_edge(..., max_rows=5000)`,
which defaults to `mode="native"`. Edge *native* mode intentionally returns raw
protocol columns (`tcp.flags.ack`, …), not the 20 behavioral `FEATURE_COLS` the
test asserts. This never surfaced upstream because that repo ships no raw data, so
the test was always skipped. **Fix:** the test now loads Edge in `mode="behavioral"`
(the shared 20-feature schema used by Phase 2/3). WSN and CIC already return the
behavioral schema in both modes, so they were unaffected.

## 4. The shipped checkpoint was an untrained scaffold

`src/live/save_artifacts.py` saves a **freshly-initialised** model with no
training, and that scaffold was what shipped in `models/saved/hybrid_model.pt`.
Fed three very different traffic windows (normal / SYN-flood / port-scan) it
returned identical near-uniform probabilities — it could not detect anything.

To make the dashboard and live pipeline actually demonstrate detection, a new
training script was added:

- **`scripts/train_model.py`** — trains the real Hybrid CNN-BiLSTM-Attention model
  on the combined behavioral feature space (WSN + CIC + Edge, all five threat
  classes) using the project's own `preprocess()` + `train_hybrid()` + temperature
  calibration, then saves `hybrid_model.pt`, `scaler.pkl`, `temp_scaler.pt`,
  `model_config.json`, plus an honest held-out report to
  `data/processed/showcase_eval.json`.

Re-run it on your machine for a stronger model (more rows / epochs):

```bash
python scripts/train_model.py --max-rows 150000 --epochs 40
```

## 5. New shell scripts (what you asked for)

All live in `scripts/` and are POSIX bash (run from WSL/Linux/macOS; on Windows
run the attacker side from WSL per `docs/DEMO_RUNBOOK.md`):

| Script | Role | Example |
|--------|------|---------|
| `run_dashboard.sh` | Launch the Streamlit SOC (detector) | `scripts/run_dashboard.sh` |
| `run_attack.sh` | Launch one simulated attack (attacker) | `scripts/run_attack.sh syn-flood --target 192.168.1.100 --duration 30` |
| `run_demo.sh` | Scripted attack sequence for a live demo | `scripts/run_demo.sh --target 192.168.1.100 --gateway 192.168.1.1` |
| `showcase_model.sh` | Quantitative model showcase (trains if needed) | `scripts/showcase_model.sh` |
| `setup_wsl_attack.sh` | One-time attacker tooling install (upstream) | `wsl -e bash scripts/setup_wsl_attack.sh` |

**Safety:** the attack wrappers refuse any target that is not a private/loopback
address (10.x, 172.16–31.x, 192.168.x, 127.x) and prompt before aggressive floods
(set `WSENTRY_YES=1` to skip the prompt in scripted demos). These are for
authorized lab use against your own detector only.

## 6. How to show it off

Single machine (no second laptop needed):

```bash
# 1. Train a real checkpoint + print held-out metrics + live detection table
scripts/showcase_model.sh

# 2. Launch the interactive SOC dashboard
scripts/run_dashboard.sh           # http://localhost:8501
#    -> Live Monitor tab -> Start Capture (uses the Loopback/simulation fallback)
```

Two machines (full LAN demo): follow `docs/DEMO_RUNBOOK.md`; run
`scripts/run_dashboard.sh` on the detector and `scripts/run_demo.sh --target <detector-ip>`
on the attacker.

## 7. Test status

Full suite green after the merge: **44 passed** (Phase 1/2/3 + CICIoT + step0 +
ROC export), verified on Python 3.14 / torch 2.15 CPU and consistent with the
upstream Windows/py3.12 run.
