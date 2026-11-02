# W-SENTRY: setting up laptop A and laptop B

Laptop A is the detector: it runs the trained model server (port 8000) and the
dashboard (port 5173). Laptop B is the attacker: it only needs the `laptop-b`
folder and plain Python. Put both laptops on the same Wi-Fi or hotspot.

## Laptop A (detector)

### Install first

| Tool | Version used on the original laptop | Get it |
|------|-------------------------------------|--------|
| Python | 3.11 (3.11.16) | python.org, tick "Add python.exe to PATH" |
| Node.js | 24 LTS (v24.19.0, npm 11) | nodejs.org |
| NVIDIA driver | any driver with CUDA 12.8 support (570+) | only needed for training; the demo runs the model on CPU |

Original specs: Windows 11, NVIDIA RTX 3050 6 GB laptop GPU, torch 2.11.0+cu128.

### Set up (once)

Unzip, then in the `w-sentry` folder double-click `setup_laptopA.cmd`, or run
the same steps by hand in PowerShell:

```powershell
cd w-sentry
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci --prefix frontend
.venv\Scripts\python.exe -c "from src.live.inference import InferenceEngine; InferenceEngine(); print('model OK')"
```

`requirements.txt` has the exact versions from the working `.venv`.

No NVIDIA GPU? Change the first line of `requirements.txt` to
`--extra-index-url https://download.pytorch.org/whl/cpu` and the torch line to
`torch==2.11.0+cpu`. The demo works the same; training will be slow.

### Run the demo

Run once as Administrator, so it can open the firewall ports:

```powershell
scripts\run_laptopA.cmd
```

That opens two windows: the model server on port 8000 and the dashboard at
http://localhost:5173. If you'd rather start them separately:

```powershell
.venv\Scripts\python.exe scripts\detector_server.py
```

```powershell
npm --prefix frontend run dev
```

Firewall rules (admin PowerShell, once; `run_laptopA.cmd` tries these for you):

```powershell
netsh advfirewall firewall add rule name="W-SENTRY model" dir=in action=allow protocol=TCP localport=8000
```

```powershell
netsh advfirewall firewall add rule name="W-SENTRY discovery" dir=in action=allow protocol=UDP localport=50505
```

### Tests

```powershell
.venv\Scripts\python.exe -m pytest tests/test_roc_export.py -v
```

## Laptop B (attacker)

Only Python 3 is needed (standard library only, no pip installs).

1. Copy just the `laptop-b` folder from this zip to laptop B.
2. Make sure laptop A is running `scripts\run_laptopA.cmd`.
3. Double-click `laptop-b\run.cmd`, or run `python menu.py`. It finds laptop A
   on the network and shows the attack menu.

If discovery fails, pass laptop A's IP (shown in the dashboard's Network link panel):

```powershell
python menu.py 192.168.x.x
```

See `laptop-b/README.md` for the direct commands and `docs/DEMO_NETWORK.md` for
how the two laptops talk and how to diagnose problems.

## Trained checkpoints (included)

`models/saved/` holds the trained model the detector loads, so laptop A does not
need to retrain:

- `hybrid_model.pt`: CNN-BiLSTM-Attention weights
- `scaler.pkl`: the feature scaler
- `temp_scaler.pt`: temperature-scaling calibration
- `model_config.json`: model settings

These are the only checkpoints in the project. The Phase 2 DANN weights
(`models/weights/*.pth`, written by `scripts/save_weights.py`) were never saved
on the original laptop. To retrain the detector model: `python scripts/train_model.py`
(needs `data/raw`).

## Not in this zip

- `.venv` and `frontend/node_modules`: rebuilt by the setup steps above.
- `data/raw` (4.5 GB of datasets): only needed to retrain. Get it with
  `python scripts/download_datasets.py` (needs `KAGGLE_USERNAME` and `KAGGLE_KEY`).
- The old Streamlit dashboard and Scapy attack scripts (`src/dashboard`,
  `src/attack`) need extra packages the live demo doesn't use:
  `.venv\Scripts\python.exe -m pip install -r requirements_phase3.txt`.
