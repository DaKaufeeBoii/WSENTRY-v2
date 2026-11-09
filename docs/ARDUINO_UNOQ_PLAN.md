# W-SENTRY on the Arduino UNO Q: implementation plan (coding-agent handoff)

Audience: a coding agent (Antigravity or similar) working in this repo, plus the human who
has the board. Read sections 0 to 5 in full before touching anything. Then execute the
phases in order. Every step has an ID, exact commands, and a "Done when" check.

Base: branch `master` at commit `a6fda3c` ("Make the demo scripts portable across laptops")
or later. Work on branch `feat/arduino-unoq`. If it doesn't exist where you are:
`git switch -c feat/arduino-unoq origin/master`.

---

## 0. Operating rules for the agent

### 0.1 Execution protocol

1. Run the phases in order: P0, P1, P2, P3, P4, P5, P6, then P7. P5 (proof on the device)
   is required for the faculty demo. P6 (live packets) is recommended, and its gate
   (P6.7) decides whether live mode is used in the demo. If time runs out during P6,
   finish P7 with replay mode. P2 is hardware setup and can be done by the human while
   you do P1.
2. Keep a progress log at the repo root: `ARDUINO_PROGRESS.md`, one line per step ID:
   `- [x] P1.2 tests written, 8 failing as expected` or `- [ ] P3.2`. Write facts you
   discover there too (board IP, Python version, torch version, latency numbers).
3. After each step, run its "Done when" check. If it passes, tick it and move on.
4. If a check fails, you may make up to 2 targeted fix attempts within the step's scope,
   using the troubleshooting table (section 11). If it still fails, STOP. Write
   `ARDUINO_ERROR_REPORT.md` using the template in section 12, tell the human, and end
   your turn. Don't skip ahead, don't redesign, and don't "temporarily" disable a check.
5. To resume after an error report is resolved: read `ARDUINO_PROGRESS.md`, then restart
   from the first unticked step.
6. Steps marked **[HUMAN]** need a person: a physical action, a password prompt, a GUI
   (Arduino App Lab), or looking at a screen. Print exactly what the human must do, then
   wait for confirmation. Your shell can't answer password prompts. After P2.5 you can
   SSH to the board without a password, but `sudo` always needs the human. To check
   kernel rules without sudo, use the detector's `/api/status` (its `rules` field lists
   the live `iptables -S WSENTRY` output).

### 0.2 Hard rules (do not break them, even to get unblocked)

- Don't retrain or modify `models/saved/*`, `scripts/attack_samples.json` or
  `laptop-b/attack_samples.json`. The demo uses the existing trained checkpoint.
- Default behaviour on Windows laptops must stay exactly as it is today: the detector
  defaults to `--enforce dryrun`. Don't change any existing file in `laptop-b/`; P5.7
  only adds the new `laptop-b/real_traffic.py`.
- Never write a Wi-Fi password, the board's `arduino` password, or any token into a file,
  a script, a commit, the progress log or an error report. The human types `sudo`
  passwords and Wi-Fi passwords themselves.
- Generate network traffic only toward the UNO Q, only on the private demo hotspot.
- Don't commit or push unless the human asks. Never use `git push --no-verify`.
- Don't add packages to `requirements.txt` (laptop A). Board packages live only in
  `scripts/unoq/setup_board.sh`.
- Don't modify `paper/`, `data/`, `src/dashboard/` (old Streamlit UI), `src/attack/` or
  `notebooks/`.
- Write tests first for the P1 code changes (section 7, P1.2), then make them pass.

---

## 1. Goal and the demo story

**Goal:** show that W-SENTRY defends an Arduino. The trained W-SENTRY model runs on the
Arduino itself, classifies incoming attack traffic, and the Arduino blocks the attacker
with a real kernel firewall rule. The Arduino's LED matrix shows its state.

**What the audience sees (about 90 seconds):**

1. The Arduino UNO Q sits on the table with its own monitor (SBC mode) showing the
   W-SENTRY board console: board identity, `FIREWALL: ON`, live packet counters. Its LED
   matrix shows a live packets/s graph alternating with `ON`. Laptop A shows the
   W-SENTRY dashboard, whose Network link panel reads
   `live model on <board> (aarch64)`. The model runs on the Arduino, not the laptop.
2. Laptop B (the attacker) has two windows. One is the attack menu, which found the
   Arduino by itself on the network. The other is a `ping -t <BOARD_IP>` that replies.
3. The presenter picks "DoS flood". Laptop B's menu shows the first batches delivered and
   classified ("model saw DoS_Flood 97%").
4. Within about a second, the Arduino blocks laptop B:
   - laptop B's menu switches to `X BLOCKED by W-SENTRY - target refused (403)`
   - laptop B's ping switches to `Request timed out` (a real kernel DROP on the Arduino)
   - the LED matrix scrolls `DDOS BLOCKED` with a blinking top bar
   - the board console turns red ("ATTACKER BLOCKED BY THE KERNEL FIREWALL"). With the
     real UDP flood (P5.7) running alongside, its "dropped by W-SENTRY" counter climbs
     while "reached the OS" falls
   - the dashboard shows the detection, the mitigation step and the `iptables` rule text
5. After 45 seconds the block expires: the ping replies again and the matrix returns to the graph.
6. Optional extras: "Before vs after W-SENTRY" (protection OFF, then ON), and the
   multi-stage combo (scan, OS probe, spoofing, DoS), both already in laptop B's menu.

**Proof moments for a skeptical audience (P5.8):**
- **Firewall switch:** a faculty member presses the button on the board to turn the
  firewall OFF and then ON.
- **The laptop isn't doing it:** laptop A is switched off mid-attack and the board keeps
  defending.
- **The board is doing it:** the board's Wi-Fi is switched off from its own keyboard and
  defense stops.
- **Identity:** `cat /proc/device-tree/model; lscpu` is typed on the board's own keyboard.
- **Real packets:** a real UDP flood from laptop B shows up in the board's kernel
  counters and is dropped there.

**Honest framing (say it this way in the demo and the report):** in the primary mode, laptop B
sends real held-out attack records (feature windows from the test split) over HTTP. That
part is unchanged from the two-laptop demo. The model inference on the Arduino is real.
The firewall block on the Arduino is real. A real UDP flood can run alongside, and its
packets are really dropped by the Arduino's kernel. In **live mode** (P6, used only if
its gate passes), the model classifies the real packets the board itself captures,
through the same CICIoT2023 feature extractor the training data was built with.

---

## 2. Hardware: Arduino UNO Q (4 GB variant)

| Item | Value | Source / confidence |
|------|-------|---------------------|
| MPU | Qualcomm Dragonwing QRB2210, quad-core Arm Cortex-A53, runs Debian Linux | user (box); Linux side confirmed |
| OS | Debian 13 "Trixie", arm64, default user `arduino` | Arduino docs/community, verify in P2.3 |
| MCU | STM32U585 (Cortex-M33). Runs the Arduino sketch (Zephyr-based core) | user (box) |
| RAM / storage | 4 GB LPDDR4 / 32 GB eMMC | user (box) |
| Radio | Wi-Fi + Bluetooth LE | user (box) |
| Display on board | 8 x 13 LED matrix driven by the MCU (`Arduino_LED_Matrix`) | Arduino examples, verify in P5 |
| Expansion | Qwiic connector for Modulino nodes (optional buzzer/pixels); UNO headers (D2 used for the firewall button) | user (box) |
| Standalone use | Monitor, keyboard and mouse through a USB-C hub (SBC mode) | user (box) |
| Shell access | `ssh arduino@<BOARD_IP>`, `adb shell` over USB-C, or App Lab's terminal | Arduino docs |
| MPU to MCU link | "Bridge" RPC via the `arduino-router` service, socket `/var/run/arduino-router.sock` | Arduino docs/community, verify in P5 |

**Why this board changes the design:** a classic Arduino (2 KB RAM) could never run this
model. The UNO Q's Linux side has 4 GB RAM and a quad-core A53. The W-SENTRY model is
small: CNN-BiLSTM-Attention, about 0.83 M parameters, a 3.3 MB fp32 checkpoint, and one
inference is a (5 x 20) window. So the existing PyTorch model runs on the board unchanged,
and the MCU handles the LED matrix.

---

## 3. What exists today (read these files)

| File | What it does | Relevant detail |
|------|--------------|-----------------|
| `scripts/detector_server.py` | Live detector: stdlib HTTP server on :8000, UDP discovery on :50505, runs the real model per attack, SSE to the dashboard | Blocks are in-memory only; the firewall rule is a `[dry run] netsh ...` string (lines 89-90). `self.blocks` is mutated in 5 places (lines 70, 88, 244, 251, 256-258). |
| `src/live/inference.py` | `InferenceEngine`: loads `models/saved/{hybrid_model.pt,temp_scaler.pt,model_config.json}`, CPU inference, `predict_batch((n,5,20))` | Needs only `torch` + `numpy`. |
| `src/models/hybrid_dl.py`, `src/models/calibration.py`, `src/utils.py` | Model class, temperature scaler, seeding | Imports: torch, numpy, os, random. No pandas or sklearn needed at inference time. |
| `scripts/attack_samples.json` (= `laptop-b/attack_samples.json`, identical) | 320 held-out (5,20) windows, 80 per family: `jam`, `spoof`, `dos`, `scan` | Already log-normalised and RobustScaled, so feed them to the model as-is. |
| `laptop-b/attacker.py`, `laptop-b/menu.py`, `laptop-b/run.cmd` | Attacker console, stdlib only. Finds the detector by UDP broadcast, saved IP, then subnet scan. Sends `/api/attack`, heartbeat every 2 s, prints 403 as BLOCKED | `combo` and `--before-after` also call `/api/unblock` and `/api/protection` from laptop B. They must keep working while laptop B is blocked. |
| `frontend/src/lib/mockFeed.js` | Dashboard feed; subscribes to `${location.hostname}:8000` (line 35-36) | Hard-wired to "detector = same host as the dashboard". Must become configurable. |
| `frontend/src/views/AttackDemo.jsx` | Attack Demo page; Network link panel text at line 71 | Shows "live model server on port 8000". |
| `docs/DEMO_NETWORK.md` | Current two-laptop architecture (laptop A = detector, laptop B = attacker) | Use it as the API reference. `docs/DEMO_RUNBOOK.md` is the older Streamlit/Scapy flow with reversed laptop names, so ignore it. |
| `data/processed/showcase_eval.json` | Held-out metrics of the deployed checkpoint | Accuracy 94.6%. Recall: DoS 0.97, Normal 0.98, Jamming 0.81, Spoofing 0.81, Probe 0.64. **Lead the demo with DoS.** |

Model input contract: float32 array `(batch, 5, 20)` in the column order of
`models/saved/model_config.json` `feature_names`. Classes: 0 Normal, 1 Jamming,
2 Spoofing, 3 DoS_Flood, 4 Intrusion_Probe. Block policy: class > 0 and calibrated
confidence >= 0.85, so Jamming is alert-only and DoS, Spoofing and Probe get blocked.

---

## 4. Target architecture

```
  LAPTOP B (attacker)                ARDUINO UNO Q  (the defended device)                 LAPTOP A (SOC screen)
  ┌──────────────────────┐           ┌─────────────────────────────────────────────┐      ┌────────────────────────┐
  │ laptop-b/menu.py      │ UDP 50505 │ Linux side (QRB2210, Debian 13)              │ SSE  │ dashboard (Vite :5173) │
  │  (unchanged)          │──────────▶│  scripts/detector_server.py                  │─────▶│ VITE_DETECTOR_URL =    │
  │                       │ HTTP 8000 │   --enforce iptables --threads 4             │ HTTP │ http://<BOARD_IP>:8000 │
  │                       │──────────▶│   InferenceEngine -> hybrid_model.pt (REAL)  │◀─────│                        │
  │ ping -t <BOARD_IP>    │◀── 403 ───│   Firewall -> iptables chain WSENTRY (REAL)  │      └────────────────────────┘
  │  (proof of kernel     │  ICMP     │   lights thread --(Bridge RPC)--┐            │
  │   DROP while blocked) │──── X ───▶│                                 ▼            │
  └──────────────────────┘           │ MCU side (STM32U585): sketch draws status on │
                                     │ the 8x13 LED matrix: check / ! / X / -        │
                                     └─────────────────────────────────────────────┘
```

All three devices join the same phone hotspot (or Windows Mobile Hotspot). Only the UNO
Q runs `detector_server.py`. Laptop A runs only the dashboard.

| Part | Real or prop |
|------|--------------|
| Model inference | **Real, on the Arduino** (same checkpoint as laptop A, proven bit-for-bit by the parity check in P3) |
| Block decision | **Real** (the model's class and confidence feed the existing policy) |
| Firewall | **Real kernel rule on the Arduino** (`iptables`), auto-removed after 45 s and on shutdown |
| Attack traffic, replay mode | Replayed held-out records over HTTP (prop, same as today) |
| Attack traffic, live mode (P6, only if its gate passes) | **Real** floods and scans from laptop B, captured and classified on the board |
| Packets in / reached the OS / dropped | **Real kernel counters on the board** (`/proc/net/dev`, `/proc/net/snmp`, iptables rule counters) |
| Board identity on the console | **Real**, read from the board's own `/proc` and `/sys` |
| LED matrix, console, firewall button | Real board state, mirrored from the detector (P5) |

### 4.1 The firewall rule design (important)

When the model blocks source `S`, the board adds two rules to its own chain `WSENTRY`,
which is jumped to from the top of `INPUT`:

```
-A WSENTRY -s S -p tcp --dport 8000 -j RETURN   # API port stays reachable: laptop B gets HTTP 403s,
                                                 # and its menu's unblock/protection calls keep working
-A WSENTRY -s S -j DROP                          # everything else from S is dropped by the kernel
```

Why the exemption: laptop B's `combo` and `--before-after` modes call `/api/unblock` and
`/api/protection` from laptop B itself. A full DROP would break them, and the 403 lines
are the clearest on-screen proof. The kernel DROP is proven by laptop B's ping and by
`sudo iptables -S WSENTRY`.

**Lock-out warning:** never SSH into the board from laptop B during the demo, because a
block drops laptop B's SSH. Use laptop A or `adb shell` over USB for board access.
`adb` over USB is not affected by iptables.

---

## 5. Decisions already made (don't re-litigate)

1. Run the existing PyTorch model on the board unchanged (Plan A). Use ONNX Runtime
   (Plan B, section 7.8) only if torch fails the P2/P3 gates.
2. All firewall code goes in `scripts/detector_server.py` (a `Firewall` class), not a new
   module. Default `--enforce dryrun` keeps Windows behaviour identical.
3. iptables mode requires root, so the detector is started with `sudo` by
   `scripts/unoq/run_detector.sh` and the human types the password. No sudoers changes.
4. The dashboard stays on laptop A and points at the board through `VITE_DETECTOR_URL`.
5. Laptop B is unchanged and keeps using the existing `laptop-b/` folder.
6. On-device proof (P5) is required. The board console reads only the detector's HTTP
   status and kernel counters. The LED matrix and the button go through the Bridge in a
   separate thread, and a failure there must never affect detection or blocking.
7. Real-packet mode (P6) uses the repo's validated CICIoT2023 extractor
   (`src/features/ciciot_features.py`) plus the exact `load_cic` mapping, so the live
   features match how the model was trained. Do **not** use `src/live/feature_extractor.py`:
   its formulas differ from training (for example, `f_port_entropy` is Shannon entropy
   there but Rank/Covariance/port-difference in training). Live mode is used in the demo
   only if the P6.7 gate passes.

---

## 6. Placeholders used below

| Placeholder | Meaning | How to get it |
|-------------|---------|---------------|
| `<BOARD_IP>` | UNO Q's IPv4 on the hotspot | on the board: `hostname -I` (first address) |
| `<LAPTOP_A_IP>` / `<LAPTOP_B_IP>` | laptops' IPv4 on the hotspot | Windows: `ipconfig`, the Wi-Fi adapter's IPv4 |
| `REPO` | the repo root on laptop A | the folder containing `README.md` |
| `~/w-sentry` | the repo copy on the board | created in P3 |

Record the real values in `ARDUINO_PROGRESS.md`. Phone hotspots can change IPs between
sessions, so re-check on demo day.

---

## 7. Phases

### P0. Laptop A pre-flight (agent, about 15 min)

**P0.1 Branch.** `git status -sb` must show `feat/arduino-unoq` and a clean tree, apart
from this plan file and the progress log.
Done when: the branch is checked out.

**P0.2 Python env.** From REPO:
```powershell
.venv\Scripts\python.exe -c "import torch, numpy; print(torch.__version__, numpy.__version__)"
```
If it fails with `No Python at '...'`, the venv's base interpreter is gone. Delete `.venv`
and rebuild it with any installed CPython 3.11 or 3.12. Run `py -0p` to list them, then
use the matching selector: `py -3.11 -m venv .venv`, `py -3.12 -m venv .venv`, or a
listed tag such as `py -V:Astral/CPython3.12.11 -m venv .venv`. If `uv` is installed,
`uv venv -p 3.12 .venv` also works. Then
`.venv\Scripts\python.exe -m pip install -r requirements.txt`. Note that `requirements.txt`
pins `torch==2.11.0+cu128`, a multi-GB download. On a laptop without an NVIDIA GPU, or to
save time, first switch to CPU torch as described in `SETUP_NEW_LAPTOPS.md` ("No NVIDIA
GPU?"). If none of these work, write an error report; the human must install Python 3.12.
Done when: torch and numpy versions print.

**P0.3 Model smoke test.**
```powershell
.venv\Scripts\python.exe -c "from src.live.inference import InferenceEngine; InferenceEngine(); print('model OK')"
```
Done when: `Loaded model checkpoint from ...` and `model OK` print with no "Warning: Could not load".

**P0.4 Baseline regression (today's behaviour).** Terminal 1:
`.venv\Scripts\python.exe scripts\detector_server.py`. Terminal 2:
`python laptop-b\attacker.py 127.0.0.1 dos --duration 5`.
Done when terminal 2 matches this **pattern**. The exact text varies run to run
(timestamps, random batch sizes), so don't compare it literally:
(1) at least one line containing `model saw DoS_Flood`, (2) then at least one line
containing `X BLOCKED by W-SENTRY`, (3) a summary box containing `was BLOCKED by W-SENTRY`.
Stop the server with Ctrl+C. Save the last 10 lines in the progress log as the baseline.
Every later "P0.4 regression" means re-running this step and checking the same pattern.

**P0.5 Baseline tests.** `.venv\Scripts\python.exe -m pytest tests/test_roc_export.py -q`.
Done when: the tests pass. (Don't run the whole `tests/` folder; some suites need `data/raw`.)

---

### P1. Code changes in the repo (agent, about 2 to 3 h)

Files created or changed in P1 (nothing else):

| File | Change |
|------|--------|
| `tests/test_unoq_firewall.py` | new: tests first (P1.2) |
| `scripts/detector_server.py` | `Firewall` class, `Detector.block/unblock/expire`, sweeper, `/api/status`, `--enforce/--threads/--lights`, cleanup on exit, arch in hello |
| `scripts/check_parity.py` | new: golden-prediction parity check and per-family hit rates |
| `scripts/unoq/setup_board.sh` | new: one-time board setup |
| `scripts/unoq/run_detector.sh` | new: start the detector on the board |
| `scripts/unoq/push_to_board.ps1` | new: copy the needed files from laptop A to the board |
| `frontend/src/lib/mockFeed.js` | `VITE_DETECTOR_URL` support; keep `arch` from hello |
| `frontend/src/views/AttackDemo.jsx` | Network link text shows host and arch |

**P1.1 Read first:** `scripts/detector_server.py` (whole file), `laptop-b/attacker.py`
(`post`, `attack`, `combo`, `before_after`), `frontend/src/lib/mockFeed.js` lines 30-131
and 545-560.

**P1.2 Write the tests first: `tests/test_unoq_firewall.py`.**

The tests must run on Windows laptop A without root and without iptables, so inject a
fake runner. Load the server module from its file path, because `scripts/` is not a package.

```python
"""Firewall + block bookkeeping for the UNO Q detector. Runs anywhere: iptables is faked."""
import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("detector_server", ROOT / "scripts" / "detector_server.py")
ds = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ds)


class FakeRun:
    """Records iptables calls (without the leading 'iptables -w'). '-C' answers 'rule absent'."""
    def __init__(self):
        self.calls = []

    def __call__(self, cmd, **kw):
        args = cmd[2:]
        self.calls.append(" ".join(args))
        return subprocess.CompletedProcess(cmd, 1 if args[0] == "-C" else 0, "", "")


def make_fw():
    run = FakeRun()
    fw = ds.Firewall("iptables", port=8000, run=run, which=lambda _: "/usr/sbin/iptables")
    return fw, run


def test_setup_creates_chain_and_jump():
    _, run = make_fw()
    assert run.calls == ["-N WSENTRY", "-F WSENTRY", "-C INPUT -j WSENTRY", "-I INPUT 1 -j WSENTRY"]


def test_block_keeps_api_port_open_and_drops_the_rest():
    fw, run = make_fw()
    run.calls.clear()
    fw.block("192.168.1.50")
    assert run.calls == [
        "-A WSENTRY -s 192.168.1.50 -p tcp --dport 8000 -j RETURN",
        "-A WSENTRY -s 192.168.1.50 -j DROP",
    ]


def test_unblock_deletes_both_rules_and_teardown_removes_chain():
    fw, run = make_fw()
    run.calls.clear()
    fw.unblock("192.168.1.50")
    fw.teardown()
    assert run.calls == [
        "-D WSENTRY -s 192.168.1.50 -p tcp --dport 8000 -j RETURN",
        "-D WSENTRY -s 192.168.1.50 -j DROP",
        "-F WSENTRY", "-D INPUT -j WSENTRY", "-X WSENTRY",
    ]


def test_dryrun_never_runs_iptables():
    run = FakeRun()
    fw = ds.Firewall("dryrun", run=run)
    fw.block("1.2.3.4"); fw.unblock("1.2.3.4"); fw.clear(); fw.teardown()
    assert run.calls == []
    assert fw.describe("1.2.3.4", 7).startswith("[dry run] netsh")


class RecFw:
    mode = "iptables"
    def __init__(self):
        self.log = []
    def block(self, ip): self.log.append("block " + ip)
    def unblock(self, ip): self.log.append("unblock " + ip)
    def clear(self): self.log.append("clear")
    def describe(self, ip, rid): return f"rule {rid} {ip}"


def test_detector_adds_rule_once_and_expires_it():
    fw = RecFw()
    det = ds.Detector(fw=fw, engine=object())       # engine unused here: no model load
    assert det.block("10.0.0.5") and det.block("10.0.0.5")
    assert fw.log == ["block 10.0.0.5"]             # second block only extends the expiry
    det.blocks["10.0.0.5"] = 0                       # force expiry
    assert det.expire() == ["10.0.0.5"]
    assert fw.log == ["block 10.0.0.5", "unblock 10.0.0.5"] and not det.blocks


def test_detector_rejects_bad_or_self_addresses_when_enforcing():
    det = ds.Detector(fw=RecFw(), engine=object())
    for bad in ["", "0.0.0.0/0", "not-an-ip", "127.0.0.1", "0.0.0.0"]:
        assert det.block(bad) is False
    assert det.blocks == {}


def test_unblock_all_clears_chain():
    fw = RecFw()
    det = ds.Detector(fw=fw, engine=object())
    det.block("10.0.0.5"); det.block("10.0.0.6")
    det.unblock()
    assert det.blocks == {} and fw.log[-1] == "clear"


def test_manual_block_only_firewalls_connected_devices_when_enforcing():
    # The dashboard's idle simulation POSTs /api/block for made-up IPs (mockFeed.js:394).
    # A real kernel rule must only ever hit a device that actually connected (laptop B).
    det = ds.Detector(fw=RecFw(), engine=object())
    det.devices["192.168.1.77"] = {"ip": "192.168.1.77"}
    assert det.manual_block("192.168.1.50") is False
    assert det.manual_block("192.168.1.77") is True
    assert list(det.blocks) == ["192.168.1.77"]
    dry = ds.Detector(fw=ds.Firewall("dryrun"), engine=object())
    assert dry.manual_block("192.168.1.50") is True     # dry run: today's behaviour
```

Run `.venv\Scripts\python.exe -m pytest tests/test_unoq_firewall.py -q`.
Done when: 8 tests are collected and all FAIL (no `Firewall`, `expire`, etc. yet). Record
the failure count in the progress log.

**P1.3 Implement the changes in `scripts/detector_server.py`.** Make these edits exactly;
keep everything else as it is.

(a) Imports: add `ipaddress`, `os`, `platform`, `shutil`, `signal`, `subprocess` to the
stdlib imports.

(b) Add this class above `class Detector` (after the `POLICY` dict):

```python
CHAIN = "WSENTRY"


class Firewall:
    """Kernel firewall on Linux (iptables), or a dry run that only describes the rule.

    In iptables mode a blocked source keeps access to the W-SENTRY API port, so laptop B
    still gets HTTP 403 and its menu (combo, before/after) keeps working. Every other
    packet from that source is dropped by the kernel (ping, real scans, real floods)."""

    def __init__(self, mode="dryrun", port=8000, run=subprocess.run, which=shutil.which):
        self.mode, self.port, self.run = mode, port, run
        if mode != "iptables":
            return
        if not which("iptables"):
            raise SystemExit("[firewall] iptables not found. On the board: sudo apt-get install -y iptables")
        self._ipt("-N", CHAIN)                               # create; harmless error if it exists
        self._ipt("-F", CHAIN)                               # start empty: no stale blocks
        if self._ipt("-C", "INPUT", "-j", CHAIN).returncode != 0:
            self._ipt("-I", "INPUT", "1", "-j", CHAIN)       # our chain is checked first

    def _ipt(self, *args):
        return self.run(["iptables", "-w", *args], capture_output=True, text=True)

    def _rules(self, ip):
        return [["-s", ip, "-p", "tcp", "--dport", str(self.port), "-j", "RETURN"],
                ["-s", ip, "-j", "DROP"]]

    def describe(self, ip, rid):
        if self.mode == "iptables":
            return f"iptables -A {CHAIN} -s {ip} -j DROP   (W-SENTRY_{rid}, enforced on {platform.node()})"
        return (f'[dry run] netsh advfirewall firewall add rule '
                f'name="W-SENTRY_{rid}" dir=in action=block remoteip={ip}')

    def block(self, ip):
        if self.mode != "iptables":
            return
        for r in self._rules(ip):
            res = self._ipt("-A", CHAIN, *r)
            if res.returncode != 0:
                print(f"[firewall] could not block {ip}: {res.stderr.strip()}")

    def unblock(self, ip):
        if self.mode == "iptables":
            for r in self._rules(ip):
                self._ipt("-D", CHAIN, *r)

    def clear(self):
        if self.mode == "iptables":
            self._ipt("-F", CHAIN)

    def listing(self):
        """Live rules in our chain (iptables -S WSENTRY). Served by /api/status, so checks need no sudo."""
        if self.mode != "iptables":
            return []
        return self._ipt("-S", CHAIN).stdout.splitlines()

    def teardown(self):
        if self.mode == "iptables":
            self._ipt("-F", CHAIN)
            self._ipt("-D", "INPUT", "-j", CHAIN)
            self._ipt("-X", CHAIN)
```

(c) `Detector.__init__`: change the signature to `def __init__(self, fw=None, engine=None):`.
Set `self.engine = engine or InferenceEngine(model_dir=...)` (print the "loading" and
"ready" lines only when it actually loads the model), `self.fw = fw or Firewall("dryrun")`,
change `self.lock = threading.Lock()` to `threading.RLock()` (re-entrant: `mitigate` and
`expire` call `block`/`unblock` while holding it), add `self.last = None` for the last
threat verdict, and add `self.own_ips = set(lan_ips())`. Compute the board's own
addresses once here, because `lan_ips()` does a DNS lookup that must never run while
`mitigate` holds the lock.

(d) Add these methods to `Detector` and route every write to `self.blocks` through them:

```python
    def block(self, ip):
        """Block ip for BLOCK_SECONDS. The kernel rule is added only on the first block."""
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return False                                  # trust boundary: /api/block takes any string
        if self.fw.mode == "iptables" and (addr.is_loopback or addr.is_unspecified or ip in self.own_ips):
            return False                                  # never firewall the board itself
        with self.lock:
            if ip not in self.blocks:
                self.fw.block(ip)
            self.blocks[ip] = time.time() + BLOCK_SECONDS
        return True

    def manual_block(self, ip):
        """/api/block. When enforcing, only devices that really connected can be firewalled:
        the dashboard's idle simulation posts made-up attacker IPs here."""
        if self.fw.mode == "iptables" and ip not in self.devices:
            return False
        return self.block(ip)

    def unblock(self, ip=None):
        """Unblock one ip, or everything when ip is None."""
        with self.lock:
            if ip is None:
                self.blocks.clear()
                self.fw.clear()
            elif self.blocks.pop(ip, None) is not None:
                self.fw.unblock(ip)

    def expire(self):
        """Release every block whose time ran out. Returns the released IPs."""
        now = time.time()
        with self.lock:
            gone = [ip for ip, t in self.blocks.items() if t < now]
            for ip in gone:
                self.unblock(ip)
        return gone

    def board_state(self):
        """One word for the board's lights: off | blocked | alert | safe."""
        with self.lock:
            if not self.protection:
                return "off"
            if self.blocks:
                return "blocked"
            if self.last and time.time() - self.last["ts"] < 3:
                return "alert"
            return "safe"
```

Notes:
- The loopback/self check and the connected-device check apply only in iptables mode. In
  dryrun mode, P0.4's local self-test (attacker on 127.0.0.1) and the dashboard's
  simulated blocks must behave exactly as today.
- `lan_ips()` is the existing module-level function and is resolved at call time, so the
  definition order is fine.
- `self.devices` is filled by the existing `Detector.seen()` on `/api/connect`,
  `/api/heartbeat` and `/api/attack`, so laptop B is in it as soon as its menu connects.

(e) Replace the bodies that touch `self.blocks` directly:
- `is_blocked(ip)`: becomes `with self.lock: return ip in self.blocks`. Expiry moves to the
  sweeper thread (f), because a kernel-blocked source may never send another request.
- `mitigate`: replace `self.blocks[ip] = now + BLOCK_SECONDS` and the hand-built `rule`
  string with `self.block(ip)` and `rule = self.fw.describe(ip, rid)`. Keep the jamming
  (alert-only) branch as it is.
- `/api/protection` with `on=false`: replace `with DET.lock: DET.blocks.clear()` with `DET.unblock()`.
- `/api/block`: `ok = DET.manual_block(str(body["ip"])) if body.get("ip") else False`, then
  `return self._json(200, {"ok": ok})`.
- `/api/unblock`: `DET.unblock(body.get("ip") or None)`.
- `/api/attack`: after the classification loop, record the strongest threat:
  ```python
            threats = [r for r in results if r["cls"] > 0]
            if threats:
                top = max(threats, key=lambda r: r["conf"])
                DET.last = {**top, "ip": ip, "ts": time.time()}
  ```

Afterwards, `grep -n "blocks\[" scripts/detector_server.py` must show writes only inside
`Detector.block`, `unblock` and `expire`, and test code.

(f) Module-level sweeper:

```python
def sweeper():
    """Expire blocks every second, even when the blocked source has gone silent."""
    while True:
        time.sleep(1)
        for ip in DET.expire():
            DET.broadcast({"type": "unblock", "ip": ip})
```

(g) New `GET /api/status` in `do_GET`, next to `/api/hello`:

```python
        if path == "/api/status":
            with DET.lock:
                blocked = sorted(DET.blocks)
            return self._json(200, {"wsentry": True, "host": socket.gethostname(),
                                    "arch": platform.machine(), "enforce": DET.fw.mode,
                                    "protection": DET.protection, "blocked": blocked,
                                    "last": DET.last, "state": DET.board_state(),
                                    "rules": DET.fw.listing()})
```

Also add `"arch": platform.machine()` and `"enforce": DET.fw.mode` to the `/api/hello`
JSON and to the SSE `hello` message.

(h) Lights thread. It is used in P5, but write it now; it stays off unless `--lights bridge`:

```python
LIGHT_CODES = {"safe": 0, "alert": 1, "blocked": 2, "off": 3}


def lights_loop():
    """Mirror board_state() onto the UNO Q LED matrix via the Bridge. Never raises."""
    sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "unoq"))
    last = None
    while True:
        s = DET.board_state()
        if s != last:
            try:
                from bridge_ping import bridge_call    # the one Bridge client (P5.4); inside try: may not exist yet
                bridge_call("wsentry_show", LIGHT_CODES[s])
                last = s
                print(f"[lights] {s}")
            except Exception as e:                  # lights must never break detection
                print(f"[lights] bridge call failed: {e}")
                time.sleep(2)
        time.sleep(0.25)
```

(i) `main()`:

```python
def _stop(*_):
    raise KeyboardInterrupt                           # SIGTERM (systemd) -> same cleanup as Ctrl+C


def main():
    global DET
    ap = argparse.ArgumentParser(description="W-SENTRY live detector server")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--enforce", choices=["dryrun", "iptables"], default="dryrun",
                    help="iptables: real kernel rule on Linux (needs root). dryrun: only show the rule (default).")
    ap.add_argument("--threads", type=int, default=0, help="torch CPU threads (0 = torch default; use 4 on the UNO Q)")
    ap.add_argument("--lights", choices=["none", "bridge"], default="none",
                    help="bridge: mirror state onto the UNO Q LED matrix")
    args = ap.parse_args()
    if args.enforce == "iptables" and hasattr(os, "geteuid") and os.geteuid() != 0:
        raise SystemExit("[detector] --enforce iptables needs root. On the board run: bash scripts/unoq/run_detector.sh")
    if args.threads:
        import torch
        torch.set_num_threads(args.threads)
    fw = Firewall(args.enforce, port=args.port)
    DET = Detector(fw=fw)
    signal.signal(signal.SIGTERM, _stop)
    threading.Thread(target=discovery_responder, args=(args.port,), daemon=True).start()
    threading.Thread(target=sweeper, daemon=True).start()
    if args.lights == "bridge":
        threading.Thread(target=lights_loop, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    ips = ", ".join(f"{i}:{args.port}" for i in lan_ips()) or f"localhost:{args.port}"
    print(f"[detector] listening on {ips}  (discovery UDP {DISCOVERY_PORT})  "
          f"enforce={args.enforce}  arch={platform.machine()}")
    print("[detector] the dashboard and attacker connect here; the real model runs on every attack.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[detector] stopped.")
    finally:
        fw.teardown()
        if args.enforce == "iptables":
            print("[detector] firewall chain WSENTRY removed.")
```

(j) **SSE must never stall the detector.** Today `broadcast` writes to SSE sockets with no
timeout (`detector_server.py:96-107`). If the dashboard laptop vanishes without closing
its connection (Wi-Fi off, lid shut), the send buffer fills and every caller of
`broadcast` hangs: the 403 path, the sweeper, `set_protection` and live mode. Two changes:
- In `do_GET` `/api/events`, call `self.connection.settimeout(2)` right before
  `DET.clients.append(self.wfile)`. A stuck write then raises after 2 s, and `broadcast`
  already drops a client that raises.
- Add `self.sse_lock = threading.Lock()` in `Detector.__init__`. Wrap the write loop in
  `broadcast`, and the `: ping` write in the `/api/events` loop, in `with DET.sse_lock:`
  (`self.sse_lock` inside the class), so two threads never interleave half-written
  events on one socket.

Done when: `.venv\Scripts\python.exe -m pytest tests/test_unoq_firewall.py -q` passes
(8 tests), and the P0.4 regression still matches its pattern (dryrun unchanged).

**P1.4 `scripts/check_parity.py` (new).** It proves the board runs the same model and
reports which attack families are demo-safe.

```python
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
```

Run on laptop A: `.venv\Scripts\python.exe scripts\check_parity.py --write`.
Done when: it writes `scripts/golden_predictions.json` and prints 4 family lines. Copy the
output into the progress log. The `dos` hit count should be high; it is the demo lead.
Then run it once without `--write`. Done when: `PASS`.

**P1.5 `scripts/unoq/setup_board.sh` (new).** Write it with LF line endings.
`.gitattributes` only fixes line endings at commit and checkout, and the push script
tars files as they are on disk. A CRLF file breaks bash on the board, so the push script
(P1.7) refuses to send any `.sh` that contains `\r`.

```bash
#!/usr/bin/env bash
# One-time setup ON the UNO Q (Linux side). Run in an interactive shell: it asks for the
# arduino password (sudo).   bash ~/w-sentry/scripts/unoq/setup_board.sh
set -euo pipefail
cd "$HOME/w-sentry"
echo "== system packages"
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip iptables
echo "== python venv"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install numpy msgpack
# CPU-only wheel. The plain PyPI torch for aarch64 may pull GBs of CUDA packages.
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
echo "== versions"
uname -m
python3 -V
.venv/bin/python -c "import torch, numpy; print('torch', torch.__version__, 'numpy', numpy.__version__, 'threads', torch.get_num_threads())"
echo "== model smoke test"
.venv/bin/python -c "import sys; sys.path.insert(0, '.'); from src.live.inference import InferenceEngine; InferenceEngine(); print('model OK')"
```

**P1.6 `scripts/unoq/run_detector.sh` (new, LF).**

```bash
#!/usr/bin/env bash
# Start W-SENTRY on the UNO Q with the real kernel firewall. Ctrl+C stops it and removes its rules.
#   bash ~/w-sentry/scripts/unoq/run_detector.sh                  (P4)
#   bash ~/w-sentry/scripts/unoq/run_detector.sh --lights bridge  (after P5)
cd "$HOME/w-sentry"
exec sudo "$HOME/w-sentry/.venv/bin/python" scripts/detector_server.py --enforce iptables --threads 4 "$@"
```

**P1.7 `scripts/unoq/push_to_board.ps1` (new).** Copies only what the board needs, using
the Windows built-in `tar`, `scp` and `ssh`. The push itself needs no internet, only the
hotspot. Needs P2.5 (key login) first, or the human must type the password twice.

```powershell
# Run on laptop A from the repo root:
#   powershell -ExecutionPolicy Bypass -File scripts\unoq\push_to_board.ps1 -Board <BOARD_IP>
param([Parameter(Mandatory = $true)][string]$Board)
Set-Location (Join-Path $PSScriptRoot "..\..")
$crlf = Get-ChildItem scripts\unoq\*.sh | Where-Object { (Get-Content -Raw $_.FullName) -match "`r" }
if ($crlf) { throw "CRLF line endings in: $($crlf.Name -join ', '). Convert them to LF first." }
$files = @(
  "scripts/detector_server.py", "scripts/check_parity.py",
  "scripts/attack_samples.json", "scripts/golden_predictions.json", "scripts/unoq",
  "src/__init__.py", "src/utils.py", "src/live/__init__.py", "src/live/inference.py",
  "src/models/__init__.py", "src/models/hybrid_dl.py", "src/models/calibration.py",
  "models/saved/hybrid_model.pt", "models/saved/temp_scaler.pt",
  "models/saved/model_config.json", "models/saved/scaler.pkl"
)
tar -czf wsentry-unoq.tgz @files
if ($LASTEXITCODE) { throw "tar failed (is scripts/golden_predictions.json there? run P1.4)" }
scp wsentry-unoq.tgz "arduino@${Board}:~/"
if ($LASTEXITCODE) { throw "scp failed: check the board IP and that SSH works (P2.4)" }
ssh "arduino@$Board" "mkdir -p ~/w-sentry && tar -xzf ~/wsentry-unoq.tgz -C ~/w-sentry && rm ~/wsentry-unoq.tgz && ls ~/w-sentry"
if ($LASTEXITCODE) { throw "remote unpack failed" }
Remove-Item wsentry-unoq.tgz
Write-Host "pushed to arduino@${Board}:~/w-sentry"
```

**P1.8 Dashboard: point it at the board.**
- `frontend/src/lib/mockFeed.js` lines 35-36 become:
  ```js
  const DETECTOR =
    import.meta.env.VITE_DETECTOR_URL ||
    (typeof location !== "undefined" ? `${location.protocol}//${location.hostname}:8000` : "http://localhost:8000");
  ```
- In `onBridge`, for `msg.type === "hello"`, keep the new fields:
  `this.bridgeInfo = { up: true, host: msg.host, ips: msg.ips, arch: msg.arch, enforce: msg.enforce };`
- `frontend/src/views/AttackDemo.jsx` line 71: replace the "live model server on port 8000" text with
  ``{b.up ? `live model on ${b.host || "detector"}${b.arch ? ` (${b.arch})` : ""} · ${b.enforce === "iptables" ? "kernel firewall" : "dry-run firewall"}` : "model server offline — start detector_server.py"}``
- Run `npm --prefix frontend run build`.
Done when: the build succeeds, and with laptop A's own detector running (P0.4 terminal 1),
`curl.exe -s http://localhost:8000/api/hello` returns JSON with `"arch": "AMD64"` and
`"enforce": "dryrun"`. Then a **[HUMAN]** check: run `npm --prefix frontend run dev` with no
env var, open http://localhost:5173, Attack Demo page. The human confirms the panel shows
`live model on <laptop hostname> (AMD64) · dry-run firewall`.

**P1.9 Sanity on laptop A.** Run the new tests, `tests/test_roc_export.py`, the P0.4
regression (pattern check) and `check_parity.py`. Done when: all four pass. Write a P1
summary in the progress log (`git diff --stat`).

---

### P2. Board bring-up ([HUMAN] with agent guidance, about 45 min, can run during P1)

**P2.1 [HUMAN] First boot.** If the board has never been set up, connect it to a laptop
by USB-C and finish Arduino App Lab's first-run setup: board name, `arduino` password,
Wi-Fi. Keep the password private.

**P2.2 [HUMAN] Network.** Start one hotspot **with internet access**: P3.2 downloads
system packages and torch, several hundred MB. A phone hotspot on mobile data works.
Windows "Mobile hotspot" on laptop A works only if laptop A has its own upstream
connection. After setup, the demo itself needs no internet. Join the UNO Q, laptop A and
laptop B to it. To join the board from its
shell instead of App Lab: `sudo nmcli dev wifi connect "<SSID>" password "<PASSWORD>"`
(the human types it). Some campus and enterprise networks isolate clients from each
other, so never use those.

**P2.3 [HUMAN] Board facts.** The human runs this in App Lab's terminal (or `adb shell` if
Android platform-tools are installed) and pastes the output to the agent. The `sudo`
line asks for the password:
```bash
hostname; hostname -I; uname -m; cat /etc/os-release | head -3; python3 -V; free -h; df -h /; command -v iptables nft || true; sudo iptables -S | head -20
```
Done when: `uname -m` = `aarch64`, Python >= 3.11, at least 2 GB free RAM and at least
3 GB free disk. Record everything in the progress log. Note any pre-existing INPUT rules.

**P2.4 [HUMAN] SSH from laptop A.** `ssh arduino@<BOARD_IP> "echo ok"`. The human types
the password. SSH is normally enabled automatically when Wi-Fi was set during first
setup. If it's off, enable it from the board's terminal. Arduino's docs mention both
`arduino-app-cli system network-mode enable` and `arduino-app-cli system network enable`,
so check `arduino-app-cli system --help` for the right one first.
Done when: `ok` prints. From laptop B, run `ping <BOARD_IP>`. Done when: replies come back
(peer traffic is allowed on this hotspot).

**P2.5 [HUMAN] Key login, so the agent can use SSH without a password.** On laptop A, in
PowerShell. Skip `ssh-keygen` if `~\.ssh\id_ed25519.pub` already exists; press Enter at
its prompts:
```powershell
ssh-keygen -t ed25519
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh arduino@<BOARD_IP> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```
Done when: the agent's `ssh -o BatchMode=yes arduino@<BOARD_IP> "echo ok"` prints `ok`
without a prompt. `sudo` on the board still needs the human; that's intended.

---

### P3. Deploy and prove the model on the Arduino (agent + [HUMAN] for sudo, about 30 min)

**P3.1 Push.** On laptop A: `powershell -ExecutionPolicy Bypass -File scripts\unoq\push_to_board.ps1 -Board <BOARD_IP>`.
Done when: it ends with `pushed to ...` and the listing shows `models scripts src`.

**P3.2 [HUMAN] Setup.** In an interactive SSH session from laptop A:
`bash ~/w-sentry/scripts/unoq/setup_board.sh`. Torch download and install can take 10 to 20
minutes. Done when: it ends with `model OK`, and the progress log has the torch version
and `uname -m`.
Gate: if torch fails to install or import, or the import takes more than 60 s, go to
Plan B (7.8) and log the reason.

**P3.3 Parity on the board.**
```bash
cd ~/w-sentry && .venv/bin/python scripts/check_parity.py --threads 4
```
Done when: `PASS`, and the per-family hit counts equal laptop A's. Record `ms each` (expect
under 50 ms per artifact; anything under 200 ms is fine for the demo).
If FAIL: don't loosen the 0.001 tolerance. Write an error report with both outputs.

**P3.4 Detector smoke test on the board.** **[HUMAN]** session 1 (interactive SSH from
laptop A): `bash ~/w-sentry/scripts/unoq/run_detector.sh` (types the sudo password).
Expect `listening on <BOARD_IP>:8000 ... enforce=iptables arch=aarch64`.
Agent, from laptop A:
```powershell
curl.exe -s http://<BOARD_IP>:8000/api/status
```
Done when: the JSON shows `"enforce": "iptables"`, `"state": "safe"` and `"rules": ["-N WSENTRY"]`
(an empty chain exists). **[HUMAN]** in a second board session:
`sudo iptables -S INPUT | head -3`. Done when: the first rule is `-A INPUT -j WSENTRY`.
Then **[HUMAN]** Ctrl+C in session 1 and run `sudo iptables -S | grep -c WSENTRY`. Done
when: it prints `0` (cleanup works).

---

### P4. Three-device rehearsal (agent drives laptop A + the board, [HUMAN] drives laptop B, about 30 min)

**P4.1 Board.** `bash ~/w-sentry/scripts/unoq/run_detector.sh`. Wait for `model ready`.

**P4.2 Laptop A (dashboard only, NOT `run_laptopA.cmd`).** A second detector anywhere on
the network would confuse laptop B's discovery.
```powershell
$env:VITE_DETECTOR_URL = "http://<BOARD_IP>:8000"; npm --prefix frontend run dev
```
Agent check: `curl.exe -s http://<BOARD_IP>:8000/api/hello` shows `"arch": "aarch64"` and
`"enforce": "iptables"`. **[HUMAN]** opens http://localhost:5173, goes to the Attack Demo
page, and confirms the Network link panel shows
`live model on <board hostname> (aarch64) · kernel firewall`.

**P4.3 [HUMAN] Laptop B.** Window 1: double-click `laptop-b\run.cmd`. Done when: it shows
`Connected to <board hostname> - handshake OK (RTT N ms). This machine is <LAPTOP_B_IP>.`
The menu doesn't print how it found the board. If discovery fails, it asks for the IP;
type `<BOARD_IP>`. Window 2: `ping -t <BOARD_IP>` (replies).

**P4.4 DoS run.** On laptop B pick 1 (DoS flood), duration 15. Expected within about 2 s:
- laptop B window 1: a few `delivered ... model saw DoS_Flood NN%` lines, then `X BLOCKED by W-SENTRY - target refused (403)`
- laptop B window 2: `Request timed out.`
- agent, from laptop A: `curl.exe -s http://<BOARD_IP>:8000/api/status` shows `"state": "blocked"`,
  `"blocked": ["<LAPTOP_B_IP>"]`, and `rules` containing
  `-A WSENTRY -s <LAPTOP_B_IP>/32 -p tcp -m tcp --dport 8000 -j RETURN` and `-A WSENTRY -s <LAPTOP_B_IP>/32 -j DROP`.
  No other IPs appear, even while the dashboard's idle simulation runs.
- dashboard: the attack, the detection, and a mitigation entry with the `iptables -A WSENTRY ...` rule
- about 45 s after the block: rules gone, ping replies again, dashboard shows the IP unblocked
Done when: all five hold. Paste the outputs into the progress log.

**P4.5 Menu regressions.** Run "Before vs after W-SENTRY" (DoS) and "Multi-stage combo".
Done when: both complete without a Python traceback on laptop B. Before shows "Attack ran
unblocked"; after shows BLOCKED. The combo shows each stage on the dashboard.

**P4.6 [HUMAN] Shutdown.** Ctrl+C on the board's detector. Done when:
`sudo iptables -S | grep -c WSENTRY` prints `0`, and laptop B's ping replies.

P0 to P4 is the minimum working demo. P5 is what convinces a skeptical audience, and if
its Bridge parts (matrix, button) fail, the console and kernel counters still work.

---

### P5. Proof on the device itself (required for the faculty demo, about 3 h)

Purpose: someone watching only the Arduino, with no laptop, can see four things:
(1) the code runs on this board, (2) whether the firewall is ON or OFF, (3) packets
arriving and being dropped, and (4) what kind of attack it is. Everything shown comes
from the board's own kernel and the model running on the board.

What the board will show:

| Proof | Where | Data source (on the board) |
|-------|-------|----------------------------|
| "This is the Arduino" | console header | `/proc/device-tree/model`, `/sys/devices/soc0/machine`, `/proc/cpuinfo`, `/etc/os-release`, `uname -m` |
| "The model runs here" | console line 2 | number of inferences done on this board, ms per inference measured here, sha256 of the model file on this board |
| Firewall ON / OFF | LED matrix (`ON` with a live graph, or `OFF`), console, physical button on the board | `DET.protection`, iptables chain `WSENTRY` |
| Packets arriving | LED matrix bar graph (packets/s, log scale), console bars | `/proc/net/dev` rx packet counter of the Wi-Fi interface |
| Packets the OS received vs dropped | console: "reached the OS" vs "dropped by W-SENTRY" | `/proc/net/snmp` `Ip InDelivers` (counted after the firewall) and the iptables DROP-rule packet counters |
| Attack type | LED matrix scrolls `DDOS BLOCKED` / `SCAN !` / `SPOOF` / `JAM`; console shows label and confidence | the model's verdict (`DET.last`) |

Hardware for P5 **[HUMAN]**:
- A monitor, a USB keyboard, and a **USB-C hub with HDMI out and power-delivery input**.
  This is the board's "SBC mode", which the box lists. The team's H15F9 portable monitor
  is confirmed to accept USB-C video; P5.6 has the hookup. Without a monitor, show the
  console over SSH on laptop A, which is weaker proof.
- One **pushbutton** (or a jumper wire) between header pin **D2** and **GND**. This is the
  physical firewall switch.
- Optional: a Modulino Buzzer on the Qwiic connector.

**P5.1 Status additions to `scripts/detector_server.py` (tests first).**

Write `tests/test_unoq_status.py` first. Run it and confirm it fails, then implement.

```python
"""Board status helpers: kernel counter parsers, lights frame, protection toggle, identity."""
import importlib.util
import platform
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("detector_server", ROOT / "scripts" / "detector_server.py")
ds = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ds)

NET_DEV = """Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo:    1200      12    0    0    0     0          0         0     1200      12    0    0    0     0       0          0
 wlan0: 9876543   54321    0    0    0     0          0        10   123456     789    0    0    0     0       0          0
"""
SNMP = """Ip: Forwarding DefaultTTL InReceives InHdrErrors InAddrErrors ForwDatagrams InUnknownProtos InDiscards InDelivers OutRequests
Ip: 2 64 5000 0 0 0 0 0 4900 3000
Icmp: InMsgs InErrors
Icmp: 3 0
"""
IPT = """Chain WSENTRY (1 references)
    pkts      bytes target     prot opt in     out     source               destination
      14      840 RETURN     6    --  *      *       192.168.1.50         0.0.0.0/0            tcp dpt:8000
    2500  1300000 DROP       0    --  *      *       192.168.1.50         0.0.0.0/0
       7      420 DROP       0    --  *      *       192.168.1.51         0.0.0.0/0
"""


def test_kernel_counter_parsers():
    assert ds.parse_net_dev(NET_DEV, "wlan0") == 54321
    assert ds.parse_net_dev(NET_DEV, "eth9") == 0
    assert ds.parse_in_delivers(SNMP) == 4900
    assert ds.parse_drops(IPT) == 2507


def new_det():
    return ds.Detector(fw=ds.Firewall("dryrun"), engine=object())


def test_lights_frame():
    det = new_det()
    det.traffic = {"rx_pps": 0}
    assert det.lights_frame() == [0, 0, 0]                 # safe, no attack, empty graph
    det.traffic = {"rx_pps": 1000}
    assert det.lights_frame()[2] == 8                      # 1000 packets/s fills the graph
    det.traffic = {"rx_pps": 10}
    assert det.lights_frame()[2] == 2
    det.last = {"label": "DoS_Flood", "ts": time.time()}
    assert det.lights_frame()[:2] == [1, 3]                # alert, DDoS
    det.block("10.0.0.9")
    assert det.lights_frame()[0] == 2                      # blocked
    det.set_protection(False)
    assert det.lights_frame()[0] == 3 and det.blocks == {} # off, and every block released


def test_device_info_fields():
    info = ds.device_info()
    assert {"board", "soc", "cpu", "arch", "os", "host", "model_sha"} <= set(info)
    assert info["arch"] == platform.machine() and len(info["model_sha"]) == 16
```

Implementation, all in `scripts/detector_server.py`:

(a) Imports: add `hashlib`, `math`, `struct`, and `from collections import Counter`.

(b) Module-level helpers. Put them near `lan_ips()`:

```python
ATTACK_CODES = {"Jamming": 1, "Spoofing": 2, "DoS_Flood": 3, "Intrusion_Probe": 4}


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip().strip("\x00")
    except OSError:
        return ""


def parse_net_dev(text, iface):
    """rx packet counter of iface from /proc/net/dev."""
    for line in text.splitlines():
        name, sep, rest = line.partition(":")
        if sep and name.strip() == iface:
            return int(rest.split()[1])
    return 0


def parse_in_delivers(text):
    """Ip InDelivers from /proc/net/snmp: packets handed to TCP/UDP/ICMP, i.e. after the firewall."""
    rows = [l.split() for l in text.splitlines() if l.startswith("Ip:")]
    return int(rows[1][rows[0].index("InDelivers")]) if len(rows) >= 2 else 0


def parse_drops(text):
    """Sum of the packet counters of DROP rules in `iptables -L WSENTRY -v -x -n` output."""
    total = 0
    for line in text.splitlines():
        f = line.split()
        if len(f) > 2 and f[0].isdigit() and f[2] == "DROP":
            total += int(f[0])
    return total


def _default_route():
    """(iface, gateway) of the IPv4 default route from /proc/net/route, or (None, None)."""
    for line in _read("/proc/net/route").splitlines()[1:]:
        f = line.split()
        if len(f) > 2 and f[1] == "00000000":
            return f[0], socket.inet_ntoa(struct.pack("<I", int(f[2], 16)))
    return None, None


def device_info():
    """Identity of the machine this detector runs on, read from its own kernel."""
    parts = [l.split(":", 1)[1].strip() for l in _read("/proc/cpuinfo").splitlines() if l.startswith("CPU part")]
    core = {"0xd03": "Cortex-A53", "0xd05": "Cortex-A55"}.get(parts[0], parts[0]) if parts else platform.processor()
    os_name = next((l.split("=", 1)[1].strip('"') for l in _read("/etc/os-release").splitlines()
                    if l.startswith("PRETTY_NAME=")), platform.platform())
    sha = hashlib.sha256((PROJECT_ROOT / "models" / "saved" / "hybrid_model.pt").read_bytes()).hexdigest()
    return {"board": _read("/proc/device-tree/model") or platform.node(),
            "soc": _read("/sys/devices/soc0/machine"),
            "cpu": f"{len(parts) or os.cpu_count()} x {core}",
            "arch": platform.machine(), "os": os_name, "host": socket.gethostname(),
            "model_sha": sha[:16]}
```

(c) `Firewall.dropped()`:

```python
    def dropped(self):
        """Packets dropped so far by our DROP rules (kernel counters). Resets when rules are removed."""
        if self.mode != "iptables":
            return 0
        return parse_drops(self._ipt("-L", CHAIN, "-v", "-x", "-n").stdout)
```

(d) `Detector`:
- In `__init__`, add `self.infer = {"count": 0, "last_ms": 0.0, "avg_ms": 0.0}`,
  `self.traffic = {}` and `self.device = {}`.
- In `classify`, time the model call:
  ```python
        t0 = time.perf_counter()
        out = self.engine.predict_batch(arr)
        ms = (time.perf_counter() - t0) * 1000 / len(arr)
        i = self.infer
        i["count"] += len(arr)
        i["last_ms"] = round(ms, 2)
        i["avg_ms"] = round(ms if i["count"] == len(arr) else 0.9 * i["avg_ms"] + 0.1 * ms, 2)
  ```
- New methods:
  ```python
    def set_protection(self, on):
        """One path for the dashboard toggle, laptop B's before/after and the board's button."""
        self.protection = bool(on)
        if not self.protection:
            self.unblock()
            self.broadcast({"type": "unblock"})
        self.broadcast({"type": "protection", "on": self.protection})

    def lights_frame(self):
        """[state, attack, level] for the LED matrix. level = packets/s into the board, 0-8, log scale."""
        attack = ATTACK_CODES.get((self.last or {}).get("label"), 0)
        level = min(8, int(math.log10(self.traffic.get("rx_pps", 0) + 1) * 8 / 3))
        return [LIGHT_CODES[self.board_state()], attack, level]
  ```
- `/api/protection` handler body becomes `DET.set_protection(body.get("on", True))` followed by
  the existing `return self._json(...)`.

(e) Traffic sampler thread:

```python
def traffic_loop(iface):
    """Once a second: packets into the board, packets that reached the OS, packets the firewall dropped."""
    prev, dropped_total = None, 0
    while True:
        try:
            now = (parse_net_dev(_read("/proc/net/dev"), iface),
                   parse_in_delivers(_read("/proc/net/snmp")), DET.fw.dropped())
        except Exception as e:                       # never let stats kill the detector
            print(f"[traffic] {e}")
            now = prev
        if prev and now:
            rx, dl, dr = (max(0, a - b) for a, b in zip(now, prev))
            dropped_total += dr
            DET.traffic = {"iface": iface, "rx_pps": rx, "delivered_pps": dl,
                           "dropped_pps": dr, "dropped_total": dropped_total}
        prev = now
        time.sleep(1)
```

On Windows the `/proc` files don't exist, so the counters stay 0. That's harmless; start
the thread everywhere.

(f) `main()`: add `ap.add_argument("--iface", default=None, help="interface to count packets on (default: the default route's)")`.
After `DET = Detector(fw=fw)`: `DET.device = device_info()`, then
`iface = args.iface or _default_route()[0] or "wlan0"` and
`threading.Thread(target=traffic_loop, args=(iface,), daemon=True).start()`.
Add `iface={iface}` and `board={DET.device['board']}` to the startup print.

(g) `/api/status` gains `"device": DET.device, "inference": DET.infer, "traffic": DET.traffic,
"lights": DET.lights_frame()`. `/api/hello` and the SSE `hello` gain `"board": DET.device.get("board")`.
In `AttackDemo.jsx` (P1.8 text), show `b.board || b.host` instead of `b.host`, and keep
`board: msg.board` in `mockFeed.js` `onBridge` hello.

Done when: `pytest tests/test_unoq_status.py tests/test_unoq_firewall.py -q` passes
(3 + 8 tests), and the P0.4 regression pattern still matches. Then re-push (P3.1), and
**[HUMAN]** restarts the board's detector (Ctrl+C, then `run_detector.sh`). Agent check:
`curl.exe -s http://<BOARD_IP>:8000/api/status` shows a non-empty `device.board`, a
`traffic.iface`, and `inference.count` rising after a replay attack from laptop B.

**P5.2 Board console: `scripts/unoq/console.py` (new, stdlib only).** It runs on the
board's own monitor and reads only `http://127.0.0.1:8000/api/status`, so it is
on-device by construction.

```python
"""Full-screen W-SENTRY status on the UNO Q's own monitor (SBC mode). Stdlib only.
   python3 ~/w-sentry/scripts/unoq/console.py        (q quits)"""
import curses
import json
import math
import time
import urllib.request

URL = "http://127.0.0.1:8000/api/status"
STATE = {"safe": ("PROTECTED - inspecting traffic, no attack", 1), "alert": ("ATTACK DETECTED", 3),
         "blocked": ("ATTACKER BLOCKED BY THE KERNEL FIREWALL", 2), "off": ("FIREWALL OFF - traffic is NOT inspected", 4)}
NAMES = {"DoS_Flood": "DDoS / DoS flood", "Intrusion_Probe": "port scan / probe",
         "Spoofing": "spoofing / MITM", "Jamming": "RF jamming"}


def fetch():
    try:
        with urllib.request.urlopen(URL, timeout=1) as r:
            return json.loads(r.read())
    except Exception:
        return None


def bar(v, width):
    return "#" * int(min(1.0, math.log10(v + 1) / 3.5) * width)    # log scale: ~3000/s fills it


def draw(scr, s):
    scr.erase()
    h, w = scr.getmaxyx()

    def put(y, x, text, attr=0):
        if 0 <= y < h and x < w - 1:
            scr.addnstr(y, x, text, w - x - 1, attr)

    if not s:
        put(1, 2, "W-SENTRY detector not reachable on 127.0.0.1:8000 - start scripts/unoq/run_detector.sh",
            curses.color_pair(3) | curses.A_BOLD)
        scr.refresh()
        return
    d, inf, t = s.get("device") or {}, s.get("inference") or {}, s.get("traffic") or {}
    put(0, 2, f"W-SENTRY on {d.get('board', '?')}  |  SoC {d.get('soc') or '?'}  |  {d.get('cpu', '?')}  |  "
              f"{d.get('arch', '?')}  |  {d.get('os', '?')}  |  host {d.get('host', '?')}", curses.A_BOLD)
    put(1, 2, f"model sha256 {d.get('model_sha', '?')}  |  inferences on this board: {inf.get('count', 0):,}  |  "
              f"{inf.get('last_ms', 0):.1f} ms last, {inf.get('avg_ms', 0):.1f} ms avg")
    on = s.get("protection")
    put(3, 2, f"FIREWALL: {'ON ' if on else 'OFF'}   ({s.get('enforce')}, chain WSENTRY)   - press the button on the board to toggle",
        curses.color_pair(1 if on else 4) | curses.A_BOLD)
    text, col = STATE.get(s.get("state"), ("?", 4))
    put(5, 2, f"  {text}  ", curses.color_pair(col) | curses.A_BOLD | curses.A_REVERSE)
    last = s.get("last")
    if last:
        put(6, 2, f"ATTACK: {NAMES.get(last.get('label'), last.get('label'))} ({last.get('label')})  "
                  f"confidence {last.get('conf', 0) * 100:.0f}%  from {last.get('ip')}  "
                  f"{time.time() - last.get('ts', time.time()):.0f} s ago")
    bw = max(10, w - 48)
    put(8, 2, f"packets in ({t.get('iface', '?')})  {t.get('rx_pps', 0):>9,} /s  {bar(t.get('rx_pps', 0), bw)}")
    put(9, 2, f"reached the OS       {t.get('delivered_pps', 0):>9,} /s  {bar(t.get('delivered_pps', 0), bw)}",
        curses.color_pair(3))
    put(10, 2, f"dropped by W-SENTRY  {t.get('dropped_pps', 0):>9,} /s  {bar(t.get('dropped_pps', 0), bw)}"
               f"   total {t.get('dropped_total', 0):,}", curses.color_pair(2))
    put(12, 2, "kernel rules right now (iptables -S WSENTRY):", curses.A_BOLD)
    for i, r in enumerate((s.get("rules") or ["(firewall not enforcing)"])[:6]):
        put(13 + i, 4, r)
    put(h - 1, 2, "q quits  |  every number here is read from this board's kernel and the model running on this board")
    scr.refresh()


def main(scr):
    curses.curs_set(0)
    scr.nodelay(True)
    curses.start_color()
    curses.use_default_colors()
    for i, c in enumerate([curses.COLOR_GREEN, curses.COLOR_RED, curses.COLOR_YELLOW, curses.COLOR_WHITE], 1):
        curses.init_pair(i, c, -1)
    while scr.getch() not in (ord("q"), ord("Q")):
        draw(scr, fetch())
        time.sleep(0.5)


if __name__ == "__main__":
    curses.wrapper(main)
```

Re-push (P3.1). The agent can't check a curses screen, because its shell has no
terminal: check `python3 -m py_compile ~/w-sentry/scripts/unoq/console.py` over SSH
instead. **[HUMAN]** check: in an interactive PowerShell on laptop A, run
`ssh -t arduino@<BOARD_IP> "python3 ~/w-sentry/scripts/unoq/console.py"`. Done when it
shows the board identity, `FIREWALL: ON` and live numbers, and during a P4.4 DoS run the
state changes to ATTACKER BLOCKED and the kernel rules appear.

**P5.3 Sketch for the MCU.** Save it as
`scripts/unoq/wsentry_lights/sketch.ino` and use it in an Arduino App Lab app named
`wsentry-lights`. Its Python `main.py` is just `from arduino.app_utils import App` then
`App.run()` for Route A, or the Route B poller below. Before writing it, open App Lab's
bundled `Arduino_LED_Matrix` and Bridge examples, and adapt the calls if their API differs
(`matrix.begin`, `setGrayscaleBits`, `draw(uint8_t[104])`, `Bridge.provide` with 3 int
arguments, a provided function returning `int`). Record any difference in the progress log.

```cpp
#include <Arduino_RouterBridge.h>
#include <Arduino_LED_Matrix.h>

Arduino_LED_Matrix matrix;
const int BUTTON_PIN = 2;            // pushbutton (or jumper wire) from D2 to GND = firewall switch

volatile int state = 0;              // 0 safe, 1 alert, 2 blocked, 3 firewall off
volatile int attack = 0;             // 0 none, 1 jam, 2 spoof, 3 ddos, 4 scan
volatile int level = 0;              // packets/s into the board, 0..8 (log scale), sent by Linux
volatile int presses = 0;            // button presses since boot, read by Linux
volatile uint32_t lastMsg = 0;       // millis() of the last wsentry_show call (watchdog)

uint8_t frame[104];                  // 8 rows x 13 columns, row-major
uint8_t hist[13];                    // bar-graph history, one column per 250 ms

struct Glyph { char c; uint8_t rows[5]; };   // 3x5 font, bit 2 = left column
const Glyph FONT[] = {
  {'A', {2, 5, 7, 5, 5}}, {'B', {6, 5, 6, 5, 6}}, {'C', {3, 4, 4, 4, 3}}, {'D', {6, 5, 5, 5, 6}},
  {'E', {7, 4, 6, 4, 7}}, {'F', {7, 4, 6, 4, 4}}, {'J', {1, 1, 1, 5, 2}}, {'K', {5, 5, 6, 5, 5}},
  {'L', {4, 4, 4, 4, 7}}, {'M', {5, 7, 7, 5, 5}}, {'N', {6, 5, 5, 5, 5}}, {'O', {2, 5, 5, 5, 2}},
  {'P', {6, 5, 6, 4, 4}}, {'S', {3, 4, 2, 1, 6}}, {'!', {2, 2, 2, 0, 2}}, {' ', {0, 0, 0, 0, 0}},
};
const int FONT_N = sizeof(FONT) / sizeof(FONT[0]);
const char* ATTACK_NAME[] = {"", "JAM", "SPOOF", "DDOS", "SCAN"};

const uint8_t* glyph(char c) {
  for (int i = 0; i < FONT_N; i++) if (FONT[i].c == c) return FONT[i].rows;
  return FONT[FONT_N - 1].rows;                        // unknown -> space
}
void px(int r, int c) { if (r >= 0 && r < 8 && c >= 0 && c < 13) frame[r * 13 + c] = 1; }
void text(const char* s, int x) {                      // rows 1..5, 4 columns per character
  for (int i = 0; s[i]; i++, x += 4) {
    const uint8_t* g = glyph(s[i]);
    for (int r = 0; r < 5; r++)
      for (int c = 0; c < 3; c++)
        if (g[r] & (4 >> c)) px(r + 1, x + c);
  }
}
int textWidth(const char* s) { return (int)strlen(s) * 4 - 1; }
void bars() { for (int c = 0; c < 13; c++) for (int r = 0; r < hist[c]; r++) px(7 - r, c); }

void wsentry_show(int s, int a, int lv) {
  state = s; attack = (a >= 0 && a <= 4) ? a : 0; level = lv; lastMsg = millis();
}
int wsentry_presses() { return presses; }

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  matrix.begin();
  matrix.setGrayscaleBits(1);                          // on/off pixels
  Bridge.begin();
  Bridge.provide("wsentry_show", wsentry_show);
  Bridge.provide("wsentry_presses", wsentry_presses);
}

void loop() {
  static uint32_t lastShift = 0, lastScroll = 0;
  static int lowCount = 0, scroll = 13, prevKey = -1;
  static bool latched = false;
  uint32_t now = millis();

  if (digitalRead(BUTTON_PIN) == LOW) {                // pressed = LOW; count once per press,
    if (++lowCount >= 2 && !latched) { presses++; latched = true; }   // after 2 stable samples
  } else {
    lowCount = 0;
    latched = false;
  }

  // Watchdog: no update from Linux for 3 s means the detector is not running -> show OFF.
  int st = (now - lastMsg > 3000) ? 3 : state;
  int key = st * 8 + attack;                           // restart the scroll when the message changes
  if (key != prevKey) { scroll = 13; prevKey = key; }

  if (now - lastShift >= 250) {                        // advance the packets/s graph
    lastShift = now;
    memmove(hist, hist + 1, 12);
    hist[12] = level > 8 ? 8 : level;
  }

  memset(frame, 0, sizeof(frame));
  if (st == 3) {
    text("OFF", 1);                                    // firewall off (or detector down): static OFF
  } else if (st == 0) {
    if ((now / 1000) % 4 == 0) text("ON", 3);          // firewall on: flash ON every 4 s,
    else bars();                                       // otherwise the live packet graph
  } else {                                             // alert / blocked: scroll the attack name
    char msg[24];
    snprintf(msg, sizeof msg, st == 2 ? "%s BLOCKED" : "%s !", ATTACK_NAME[attack]);
    text(msg, scroll);
    if (now - lastScroll >= 110) { lastScroll = now; scroll--; }
    if (scroll < -textWidth(msg)) scroll = 13;
    if (st == 2 && (now / 300) % 2) for (int c = 0; c < 13; c++) px(0, c);   // blinking top bar
  }
  matrix.draw(frame);
  delay(30);
}
```

Done when: App Lab compiles and runs it, and the matrix shows `OFF`. That's the watchdog:
nothing has called `wsentry_show` yet. P5.4 brings it to life.

**P5.4 Bridge client and lights loop (Route A).** New `scripts/unoq/bridge_ping.py`.
It's the only Bridge client; `lights_loop` imports `bridge_call` from it. The router
speaks MessagePack-RPC on a Unix socket: a request is `[0, msgid, method, params]` and a
response is `[1, msgid, error, result]`. If the router rejects this framing, check the
`arduino-router` project's README for the exact protocol and adjust only this file.

```python
"""Call functions the UNO Q sketch registered with Bridge.provide, from plain Linux Python.
   Test: sudo ~/w-sentry/.venv/bin/python ~/w-sentry/scripts/unoq/bridge_ping.py"""
import socket
import time

import msgpack

SOCK = "/var/run/arduino-router.sock"


def bridge_call(method, *params, path=SOCK, timeout=2.0):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as c:
        c.settimeout(timeout)
        c.connect(path)
        c.sendall(msgpack.packb([0, 1, method, list(params)]))
        unpacker = msgpack.Unpacker(raw=False)
        while True:
            data = c.recv(4096)
            if not data:
                raise ConnectionError("router closed the connection without a reply")
            unpacker.feed(data)
            for msg in unpacker:
                if isinstance(msg, list) and len(msg) == 4 and msg[0] == 1:
                    if msg[2]:
                        raise RuntimeError(f"bridge error: {msg[2]}")
                    return msg[3]


if __name__ == "__main__":
    before = bridge_call("wsentry_presses")
    for name, args in [("safe, small graph", (0, 0, 3)), ("alert DDOS", (1, 3, 6)),
                       ("blocked DDOS", (2, 3, 8)), ("firewall off", (3, 0, 0)), ("safe", (0, 0, 0))]:
        end = time.time() + 4
        while time.time() < end:                    # keep feeding it: the sketch's watchdog wants
            bridge_call("wsentry_show", *args)      # an update at least every 3 s
            time.sleep(0.5)
        print(name)
    print("button presses during this run:", bridge_call("wsentry_presses") - before)
```

Replace `lights_loop` from P1.3(h) in `detector_server.py` with:

```python
def lights_loop():
    """Mirror the detector onto the LED matrix and read the board's firewall button. Never raises."""
    sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "unoq"))
    presses = None
    while True:
        try:
            from bridge_ping import bridge_call
            bridge_call("wsentry_show", *DET.lights_frame())
            n = bridge_call("wsentry_presses")
            if presses is not None and n > presses:     # '>' not '!=': a sketch restart resets the count
                DET.set_protection(not DET.protection)
                print(f"[lights] board button -> firewall {'ON' if DET.protection else 'OFF'}")
            presses = n
        except Exception as e:                       # lights must never break detection
            print(f"[lights] bridge call failed: {e}")
            time.sleep(2)
        time.sleep(0.25)
```

First re-push (P3.1) so `bridge_ping.py` and the new `lights_loop` are on the board.
**[HUMAN]** runs `sudo ~/w-sentry/.venv/bin/python ~/w-sentry/scripts/unoq/bridge_ping.py`
on the board, watches the matrix, and presses the button exactly once during the run.
Done when: the matrix shows graph/ON, scrolling `DDOS !`, scrolling `DDOS BLOCKED` with a
blinking top bar, `OFF`, then graph/ON. The last line prints
`button presses during this run: 1`, and about 3 s after the script ends the matrix falls
back to `OFF` (the watchdog).

**Route B** (if Route A fails twice): the App Lab app's `main.py` does the same work
over HTTP. Run the detector without `--lights`.

```python
import json, time, urllib.request
from arduino.app_utils import App, Bridge

BASES = ["http://127.0.0.1:8000", "http://172.17.0.1:8000"]   # host, then docker gateway; add <BOARD_IP> if needed
presses = None


def api(path, body=None):
    for b in BASES:
        try:
            req = urllib.request.Request(b + path, json.dumps(body).encode() if body is not None else None,
                                         {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=1) as r:
                return json.loads(r.read())
        except Exception:
            continue
    return None


def loop():
    global presses
    s = api("/api/status")
    Bridge.call("wsentry_show", *(s["lights"] if s else [3, 0, 0]))
    n = Bridge.call("wsentry_presses")
    if s and presses is not None and n > presses:
        api("/api/protection", {"on": not s["protection"]})
    presses = n
    time.sleep(0.25)


App.run(user_loop=loop)
```

**P5.5 [HUMAN] Wire it in.** Board: `bash ~/w-sentry/scripts/unoq/run_detector.sh --lights bridge`
for Route A. With Route B, leave out `--lights bridge`: two button readers would each
toggle on one press and cancel out. Repeat P4.4. Done when: the human confirms the matrix shows the graph while
idle, `DDOS BLOCKED` scrolling during the block, and the graph again after expiry. One
button press shows `OFF` and `/api/status` reports `"protection": false`. A second press
restores ON.

**P5.6 [HUMAN] Board as a standalone screen.**

The team's portable monitor is checked. On 2026-11-08, Windows on laptop A identified the
**H15F9** portable monitor (EDID maker code SKG) on a USB-C to USB-C cable as
"DisplayPort (external)", with no USB Billboard device. That means it accepts
DisplayPort Alt Mode, which is what the UNO Q outputs on its USB-C port. The same cable
carries video. The board's single USB-C port is also its power input, and the board can't
power the monitor, so use one of these:
- **A (recommended):** board USB-C to a USB-C hub with power passthrough. Phone charger
  into the hub's power-in; the board asks for only 5 V / 3 A. Hub HDMI to the monitor's
  mini-HDMI, or the hub's video-capable USB-C to the monitor. Monitor powered from its
  second USB-C port with its own charger or a power bank. Keyboard into the hub. Don't use
  Apple's USB-C adapter (Arduino lists it as not working).
- **B (only if the monitor passes power through):** charger into the monitor's power
  USB-C port, then board to the monitor's video USB-C port with the cable used above. If
  the board's LEDs light and the desktop appears, no hub is needed. Use a Bluetooth
  keyboard, or start the console over SSH from laptop A.

If the screen stays black, check in order: a full-featured (not charge-only) cable, the
monitor's input selection, the monitor's own power, and the hub's charger.

Then connect everything and boot to the board's desktop. Open a terminal, enlarge the font
(Ctrl+Shift+Plus), and run `python3 ~/w-sentry/scripts/unoq/console.py`. Start the
detector in a second terminal or via SSH from laptop A.
Done when: the board's own monitor shows the console with live numbers.

**P5.7 `laptop-b/real_traffic.py` (new, stdlib only, no admin rights): real packets at the board.**
P5.8 needs real packets: the replay traffic uses the firewall-exempt API port, so on its
own it never shows drops. This file is new; no existing `laptop-b/` file changes.

```python
#!/usr/bin/env python3
"""Real attack traffic at the W-SENTRY demo board (laptop B). Stdlib only, no admin rights.
Only targets a private-network address whose W-SENTRY detector enforces a real firewall,
and stops after at most 60 seconds.

  py real_traffic.py udpflood [--duration 20] [--pps 2000] [--target IP]
  py real_traffic.py synflood [--duration 20] [--pps 1000] [--target IP]
  py real_traffic.py scan     [--pps 200] [--target IP]"""
import argparse
import ipaddress
import json
import os
import random
import socket
import sys
import threading
import time
import urllib.request

import attacker  # same folder: find_target() discovery


def demo_board(ip):
    """True only for a W-SENTRY detector that enforces a real firewall (the UNO Q), not a dry-run laptop."""
    try:
        with urllib.request.urlopen(f"http://{ip}:8000/api/hello", timeout=2) as r:
            js = json.loads(r.read() or b"{}")
        return js.get("wsentry") is True and js.get("enforce") == "iptables"
    except Exception:
        return False


def syn(ip, port):
    """One real TCP SYN: a non-blocking connect, abandoned at once (never waits for the reply)."""
    c = socket.socket()
    c.setblocking(False)
    try:
        c.connect_ex((ip, port))
    finally:
        c.close()


def paced(end, pps, send_one, sent):
    """Call send_one about pps times per second until end, or until it returns False."""
    while time.time() < end:
        t = time.time()
        for _ in range(25):
            try:
                if send_one() is False:
                    return
            except OSError:
                pass
            sent[0] += 1
        time.sleep(max(0.0, 25 / pps - (time.time() - t)))


def main():
    p = argparse.ArgumentParser(description="Real traffic at the W-SENTRY demo board")
    p.add_argument("mode", choices=["udpflood", "synflood", "scan"])
    p.add_argument("--target")
    p.add_argument("--duration", type=int, default=20)
    p.add_argument("--pps", type=int, default=0)
    a = p.parse_args()
    target = a.target or attacker.find_target(8000)[0]
    addr = ipaddress.ip_address(target)
    if not addr.is_private or addr.is_loopback or not demo_board(target):
        sys.exit(f"Refusing: {target} is not a private-network W-SENTRY board with its firewall enforcing.")
    duration = min(max(a.duration, 1), 60)
    end, sent = time.time() + duration, [0]
    if a.mode == "udpflood":
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        payload = os.urandom(512)

        def send_one():
            s.sendto(payload, (target, random.randint(1024, 65535)))
        pps = a.pps or 2000
    elif a.mode == "synflood":
        def send_one():
            syn(target, random.choice([80, 443, 23, 1883, 8080]))
        pps = a.pps or 1000
    else:
        ports = iter(random.sample(range(1, 1025), 1024))

        def send_one():
            port = next(ports, None)
            return False if port is None else syn(target, port)
        pps = a.pps or 200
    worker = threading.Thread(target=paced, args=(end, pps, send_one, sent), daemon=True)
    print(f"{a.mode} -> {target}, about {pps}/s for up to {duration}s (real packets: watch the board)")
    worker.start()
    last = 0
    while worker.is_alive():
        worker.join(1)
        print(f"  {time.strftime('%H:%M:%S')}  sent {sent[0]:,}  ({sent[0] - last:,}/s)")
        last = sent[0]
    print(f"done: {sent[0]:,} packets sent")


if __name__ == "__main__":
    main()
```

Then **[HUMAN]** copies `laptop-b/real_traffic.py` into laptop B's `laptop-b` folder,
next to `attacker.py`, which it imports. Run it with `py real_traffic.py ...`, or
`python real_traffic.py ...` if `py` is missing, as `run.cmd` does.
Done when:
- on laptop B, `py real_traffic.py udpflood --duration 10 --target <BOARD_IP>` prints
  about 2,000/s and the board's "packets in" (console or `/api/status` `traffic.rx_pps`)
  rises to match;
- `synflood` prints roughly its `--pps`;
- `py real_traffic.py udpflood --target 8.8.8.8` prints `Refusing`, and so does any
  target running the dry-run detector (laptop A's fallback).

**P5.8 Faculty proof rehearsal (run all of it once before demo day).** Each item is
something a skeptical viewer can check themselves. Use a **phone hotspot** for this.
Item 2 switches laptop A off, which would take down a hotspot hosted on laptop A.

1. **Identity:** on the board's own keyboard, type
   `cat /proc/device-tree/model; echo; uname -m; lscpu | head -15`. It shows the
   Arduino/Qualcomm board, aarch64 and Cortex-A53 cores. The console header shows the same.
2. **The laptop is not doing it:** start a DoS from laptop B, then **turn laptop A's
   Wi-Fi off, or shut its lid**. Laptop B still prints 403 BLOCKED and its ping still
   times out, the matrix still scrolls `DDOS BLOCKED`, and the board console keeps
   counting. Only the dashboard stops. This relies on P1.3(j): with the SSE timeout, a
   vanished dashboard costs at most one 2 s stall.
3. **The board is doing it:** during an attack, switch the board's Wi-Fi off from its
   own keyboard: `sudo nmcli radio wifi off`. Laptop B's requests start failing within a
   few seconds (network errors: nobody answers). The dashboard shows "model server
   offline" within about a minute (its event stream has no fast timeout). Then
   `sudo nmcli radio wifi on`; laptop B reconnects and defense resumes. Don't pull the
   power: abruptly powering off risks the board's storage. If you must, run `sync` first.
4. **Firewall OFF vs ON, by hand:** with `py real_traffic.py udpflood --duration 60`
   running on laptop B, a viewer presses the board's button, and the matrix shows `OFF`.
   Run the menu's DoS: nothing is blocked, laptop B says "Attack ran unblocked", "reached
   the OS" climbs with the flood, and "dropped" stays 0. Press again for `ON`: the next
   DoS is blocked, "dropped by W-SENTRY" takes over the flood rate, and "reached the OS"
   falls to background level.
5. **Packets are real:** during item 4, the matrix graph and "packets in" show thousands
   per second. Once blocked, they show in "dropped by W-SENTRY", and the console's rule
   list shows the DROP rule that is dropping them. Optional, second terminal on the
   board: `sudo tcpdump -n -i wlan0 host <LAPTOP_B_IP> -c 30` prints the raw packets.
6. **Attack type:** the matrix scrolls the class name (`DDOS`, `SCAN`, `SPOOF`, `JAM`), and
   the console prints the label and confidence. To show the label change, first wait for
   the DoS block to expire (45 s) or press Reset on the dashboard; a blocked source gets
   403 with no new classification. Then run "Port scan" from the menu.

Done when: all six are performed and noted in the progress log, with photos if possible.

Honest wording for items 4 and 5 in **replay mode**: "The flood packets are real and are
dropped by the Arduino's kernel. The model's verdict comes from the replayed attack
records laptop B sends alongside them." In **live mode** (P6, if its gate passes), the
verdict comes from the real packets themselves.

---

### P6. Live mode: classify the real packets captured on the board (recommended, gated, 4 to 6 h)

Why this is now feasible: `src/features/ciciot_features.py` is a standard-library port
of CICIoT2023's own packet-to-feature extractor, validated against the official CSV
(`scripts/validate_ciciot_port.py`, `tests/test_ciciot_features.py`). The model's CIC
training rows came from exactly that feature definition, followed by the `load_cic`
mapping (`src/data/dataset_loader.py:146-182`). If the board captures packets and runs
the same extractor and the same mapping, the live features match how the model was
trained. `src/live/feature_extractor.py` does not: its formulas differ from training, so
don't use it here.

Known residual risks, which the gate measures:
- **(a) IAT.** CICIoT2023 IAT carries the absolute capture time, a known dataset quirk;
  live captures are from a different date.
- **(b) Extractor state.** It resets per batch here, not per 10 MB chunk.
- **(c) Block size.** The dataset averages floods over 100-packet blocks.
  `--block-packets` (default 100) is the knob for that.

Evidence so far (P6.5): on a real CICIoT2023 ping-sweep capture, this chain makes Probe
the top prediction (61% of windows at confidence >= 0.85). Floods haven't been checked
on a capture yet; that is P6.5b.

**P6.1** Done in P5.7 (`laptop-b/real_traffic.py`).

**P6.2 Share the CIC mapping (refactor, laptop A).** In `src/data/dataset_loader.py`,
move the body that builds `features` in `load_cic` (lines 155-179, from `duration = ...`
through the `pd.DataFrame({...})`) into
`def cic_behavioral(df): ... return features.replace([np.inf, -np.inf], 0).fillna(0)`.
It returns only the 20 `FEATURE_COLS`. `load_cic` then does
`features = cic_behavioral(df)`, adds `threat_class` and `dataset`, and returns as
before. No formula changes.

Tests first: write the whole of `tests/test_unoq_live.py` now. Its three tests cover
P6.2, P6.3 and P6.4, and fail until each step is done.

```python
"""Live-packet chain: shared CIC mapping, scaler export, packets -> windows."""
import json
import os
import struct
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.data.dataset_loader import FEATURE_COLS, cic_behavioral  # noqa: E402
from src.features.ciciot_features import FEATURES  # noqa: E402

FIN, PSH, ACK = 0x01, 0x08, 0x10


def tcp_frame(payload_len, flags, sport=40000, dport=80, ttl=64):
    """Same builder as tests/test_ciciot_features.py: 10.0.0.1 -> 10.0.0.2 over Ethernet."""
    total = 20 + 20 + payload_len
    ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, total, 1, 0, ttl, 6, 0, bytes([10, 0, 0, 1]), bytes([10, 0, 0, 2]))
    tcp = struct.pack("!HHIIBBHHH", sport, dport, 0, 0, 0x50, flags, 1024, 0, 0)
    return b"\xaa" * 6 + b"\xbb" * 6 + b"\x08\x00" + ip + tcp + b"x" * payload_len


def test_cic_behavioral_is_the_training_mapping():
    rng = np.random.RandomState(0)
    df = pd.DataFrame(rng.rand(4, len(FEATURES)) * 10 + 1, columns=FEATURES)
    out = cic_behavioral(df)
    assert list(out.columns) == FEATURE_COLS
    np.testing.assert_allclose(out["f_rate"], df["Rate"])
    np.testing.assert_allclose(out["f_send_recv_ratio"], df["Srate"] / (df["Drate"] + 1))
    np.testing.assert_allclose(out["f_control_ratio"],
                               (df["syn_count"] + df["fin_count"] + df["rst_count"]) / df["Number"])
    np.testing.assert_allclose(out["f_timing"], df["IAT"])


def test_scaler_json_matches_pickle():
    root = Path(__file__).resolve().parents[1] / "models" / "saved"
    sk, js = joblib.load(root / "scaler.pkl"), json.loads((root / "scaler.json").read_text())
    x = np.random.RandomState(1).randn(7, 20)
    np.testing.assert_allclose((x - js["center"]) / np.array(js["scale"]), sk.transform(x), rtol=1e-6)


def test_live_windows_and_top_source(tmp_path):
    from src.live.cic_live import CicLive, top_source
    sj = tmp_path / "s.json"
    sj.write_text(json.dumps({"center": [0.0] * 20, "scale": [1.0] * 20}))
    live = CicLive(sj, block_packets=10)
    frames = [(1.7e9 + 0.001 * i, tcp_frame(i % 50, ACK | PSH)) for i in range(100)]
    w = live.windows(frames)
    assert w.shape == (6, 5, 20) and np.isfinite(w).all()      # 100 frames -> 10 rows -> 6 windows
    assert live.windows(frames[:30]).shape == (3, 5, 20)       # 3 new rows + 4 carried-over rows
    assert top_source(frames) == ("10.0.0.1", 1.0)
    assert top_source(frames, exclude={"10.0.0.1"}) == (None, 0.0)
```

Done when: `test_cic_behavioral_is_the_training_mapping` and `tests/test_ciciot_features.py`
pass. The other two still fail at this point.

**P6.3 Scaler without scikit-learn on the board.** New `scripts/unoq/export_scaler.py`:

```python
"""Export the RobustScaler as JSON so the board needs no scikit-learn: x' = (x - center) / scale."""
import json
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parents[2]
s = joblib.load(ROOT / "models" / "saved" / "scaler.pkl")
(ROOT / "models" / "saved" / "scaler.json").write_text(
    json.dumps({"center": s.center_.tolist(), "scale": s.scale_.tolist()}))
print("wrote models/saved/scaler.json")
```

Run it: `.venv\Scripts\python.exe scripts\unoq\export_scaler.py`. Done when:
`test_scaler_json_matches_pickle` passes. `scaler.json` is a new derived file; it doesn't
modify the checkpoint, so it's allowed under section 0.2.

**P6.4 Live chain module: `src/live/cic_live.py` (new).**

```python
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
```

Done when: `pytest tests/test_unoq_live.py -q` passes (3 tests).

**P6.5 Check the whole chain on a real CIC pcap, on laptop A, before the board.** New
`scripts/unoq/check_live_chain.py`:

```python
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
```

Run it on the local CIC pcaps (both are class 4, Intrusion_Probe, in `CIC_LABEL_MAP`):
```powershell
.venv\Scripts\python.exe scripts\unoq\check_live_chain.py data\raw\ciciot2023_kaggle_pcap\pcap\Recon-PingSweep\Recon-PingSweep\Recon-PingSweep.pcap --expect 4
.venv\Scripts\python.exe scripts\unoq\check_live_chain.py data\raw\ciciot2023_kaggle_pcap\pcap\Uploading_Attack\Uploading_Attack\Uploading_Attack.pcap --expect 4
```
**Reference results.** Measured on 2026-11-08 with exactly the code in this plan
(torch 2.7.1, pandas 2.3.3, the committed checkpoint):

| pcap (true class 4) | `--block-packets 100` (default) | `--block-packets 10` |
|---------------------|----------------------------------|----------------------|
| Recon-PingSweep | 176 windows, class 4 most common (127), **hit 61%** | 1873 windows, class 4 most common (787), hit 29% |
| Uploading_Attack | 104 windows, mostly class 3 (61), hit 29% | 1162 windows, mostly class 2 (901), hit 9% |

Uploading_Attack is a web-upload attack that per-packet flow features barely separate, so
treat it as informational only.

Done when: Recon-PingSweep at the default block size shows class 4 as the most common
prediction with a hit rate of at least 50%. Small differences from library versions are
fine. If it's clearly worse, your implementation differs from this plan: write an error
report with the outputs before continuing. The likely suspects are the `cic_behavioral`
refactor and the scaler JSON. If `data/raw` is missing on this laptop, write "skipped, no
pcaps" and continue.

**P6.5b [HUMAN + agent] Check a real flood capture, the case the demo depends on.** No
DDoS pcap is in the repo. The human runs these (they need their own Kaggle API token,
which the agent must not handle):
```powershell
kaggle datasets files congyuanxu/ciciot2023 --page-size 200
```
The slug is the one the repo's existing pcaps came from: see
`data/raw/ciciot2023_kaggle_pcap/download.log`. The listing is paginated; if the flood
files aren't on the first page, pass the `--page-token` it prints. Pick the **smallest**
file whose path contains `UDP_Flood`, for example under
`pcap/DDoS-UDP_Flood/` or `pcap/DoS-UDP_Flood/`. Then download it:
```powershell
kaggle datasets download congyuanxu/ciciot2023 -f "<that file path>" -p data\raw\ciciot2023_kaggle_pcap\flood
```
Unzip it if Kaggle delivers a `.zip`. Then the agent runs
`.venv\Scripts\python.exe scripts\unoq\check_live_chain.py <flood pcap> --expect 3`.
Done when: the result is in the progress log. If class 3 is the most common prediction
with a hit rate of at least 50%, live floods are likely to work on the board. If not,
say so in the log: the P6.7 gate will probably fail for floods, and replay mode stays the
verdict source.

**P6.6 Live sniffer in the detector.** Add to `scripts/detector_server.py`:

```python
LIVE_SKIP_PORTS = {8000, 22}                  # control channel (dashboard, attacker API) and SSH
FAMILY = {1: "jam", 2: "spoof", 3: "dos", 4: "scan"}


def live_loop(iface, block_packets, never_block):
    """--mode live: sniff real frames on iface, classify them with the same model, block the top source."""
    from src.features.ciciot_features import _parse
    from src.live.cic_live import CicLive, top_source
    live = CicLive(PROJECT_ROOT / "models" / "saved" / "scaler.json", block_packets)
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
    s.bind((iface, 0))
    print(f"[live] sniffing {iface}, {block_packets}-packet blocks; never blocking {sorted(never_block)}")
    batch, incoming, start, last_emit = [], [], time.time(), 0.0
    while True:
        buf, addr = s.recvfrom(65535)
        p = _parse(buf)
        if p and p[0] == "ip" and p[2]["l4"] and p[2]["l4"][0] == "tcp" \
                and {p[2]["l4"][1], p[2]["l4"][2]} & LIVE_SKIP_PORTS:
            continue
        frame = (time.time(), buf)
        batch.append(frame)                        # features: both directions, like the dataset capture
        if addr[2] != socket.PACKET_OUTGOING:
            incoming.append(frame)                 # attribution: only what arrived from outside; the board's
        if len(batch) < 10 * block_packets and time.time() - start < 1.0:   # own RST replies would halve shares
            continue
        frames, inc, batch, incoming, start = batch, incoming, [], [], time.time()
        try:
            ip, share = top_source(inc, exclude=DET.own_ips | never_block)
            attributed = ip is not None and share >= 0.5
            if attributed and DET.protection and DET.is_blocked(ip):
                # AF_PACKET sees packets before netfilter: the kernel is already dropping these.
                if time.time() - last_emit >= 1.0:
                    last_emit = time.time()
                    DET.broadcast({"type": "refused", "ip": ip, "device": DET.seen(ip),
                                   "packets": min(len(inc), 50)})
                continue
            wins = live.windows(frames)
            if not len(wins):
                continue
            results = DET.classify(wins)
            threats = [(c, q) for c, q in results if c > 0]
            if not threats:
                continue
            action = rule = None
            if attributed:
                c, conf = max(threats, key=lambda t: t[1])
                DET.last = {"cls": c, "conf": round(conf, 3), "label": THREAT_LABELS.get(c, "?"),
                            "ip": ip, "ts": time.time()}
                m = DET.mitigate(ip, c, conf)
                if m:
                    action, rule, _ = m
            print(f"[live] {time.strftime('%H:%M:%S')} frames={len(frames)} in={len(inc)} top={ip} "
                  f"share={share:.2f} classes={dict(Counter(c for c, _ in results))} action={action}")
            if attributed and (action or time.time() - last_emit >= 1.0):   # at most ~1 event/s
                last_emit = time.time()
                fam = FAMILY[Counter(c for c, _ in threats).most_common(1)[0][0]]
                DET.broadcast({"type": "attack", "ip": ip, "device": DET.seen(ip), "kind": fam,
                               "source": "live", "action": action, "rule": rule,
                               "results": [{"cls": c, "conf": round(q, 3), "label": THREAT_LABELS.get(c, "?")}
                                           for c, q in results]})
        except Exception as e:                    # one bad batch must not stop the sniffer
            print(f"[live] batch skipped: {e}")
```

In `main()`, add `--mode {replay,live}` (default `replay`), `--block-packets` (default 100;
P6.5 measured 100 to be much better than 10, and the dataset itself averages 100-packet
blocks for floods) and `--never-block` (comma-separated IPs, default empty). If `--mode live`, it requires
root (same check as iptables) and starts:
```python
        gw = _default_route()[1]
        never = {ip.strip() for ip in args.never_block.split(",") if ip.strip()} | ({gw} if gw else set())
        threading.Thread(target=live_loop, args=(iface, args.block_packets, never), daemon=True).start()
```
The replay path (`/api/attack`) keeps working in live mode.

Dashboard: live events carry the model's own class as `kind`. Scoring them against
themselves would fake the "Model accuracy" tile (`LiveMonitor.jsx:124`). In
`frontend/src/lib/mockFeed.js` `ingest()` (line 170), set
`truth: msg.source === "live" ? undefined : cls`. This needs the `source` field, so pass it
through from `onBridge` (`this.ingest(msg)` already passes the whole message). In
`_track()` (lines 431-437), count `inspected` and `correct` only when `pkt.truth !== undefined`.
First `grep -n "inspected" frontend/src` and keep every display that uses it sensible.
Then run `npm --prefix frontend run build`.

Board side, in this order:
1. Extend `push_to_board.ps1` `$files` with `"src/features/__init__.py", "src/features/ciciot_features.py",
   "src/data/__init__.py", "src/data/dataset_loader.py", "src/live/cic_live.py", "models/saved/scaler.json"`.
2. Add `pandas` to the `pip install numpy msgpack` line of `setup_board.sh`.
3. Re-push (P3.1).
4. **[HUMAN]** re-runs `bash ~/w-sentry/scripts/unoq/setup_board.sh` on the board.

Done when, on laptop A:
`.venv\Scripts\python.exe -m pytest tests/test_unoq_firewall.py tests/test_unoq_status.py tests/test_unoq_live.py tests/test_ciciot_features.py tests/test_roc_export.py -q`
passes, the P0.4 regression pattern still matches, and the frontend builds. On the board,
the agent runs
`~/w-sentry/.venv/bin/python -c "import sys; sys.path.insert(0, '/home/arduino/w-sentry'); import src.live.cic_live; print('live OK')"`
and it prints `live OK`.

**P6.7 Board gate (decides whether live mode is used in the demo).** **[HUMAN]** starts the
board with
`bash ~/w-sentry/scripts/unoq/run_detector.sh --mode live --never-block <LAPTOP_A_IP> --lights bridge`.
Drop `--lights bridge` if you use Route B. Then, from laptop B, with 60 s gaps so blocks
expire: 3 x `py real_traffic.py udpflood --duration 20`,
3 x `py real_traffic.py synflood --duration 20`, and 3 x `py real_traffic.py scan`.

**Benign control.** The board must also see real normal traffic at a rate that forms
windows. Otherwise "no block when idle" passes by construction. On the board:
`python3 -m http.server 8080 --directory ~/w-sentry/models/saved`. On laptop B, for
2 minutes, in cmd:
`for /L %i in (1,1,60) do curl.exe -s -o NUL http://<BOARD_IP>:8080/hybrid_model.pt`
plus `ping -t <BOARD_IP>` in another window.

For each run, record from the detector's `[live]` log lines (one per batch with threats:
frames, top source, share, class mix, action) and `/api/status`: the first verdict, the
time to block, and the class mix.

**Pass:** each flood type is blocked as DoS_Flood in at least 2 of 3 runs within 5 s,
the scan is labelled Intrusion_Probe and blocked in at least 2 of 3, and the benign
control causes no block. If a type fails, retry it once with `--block-packets 10`, and record both
results.
- **Gate passes:** live mode is the demo mode. Laptop B uses `real_traffic.py` and the
  replay menu is the backup.
- **Gate fails:** keep replay mode for the verdicts, and still use `real_traffic.py
  udpflood` for the real-packet proof (P5.8 item 5). Record the numbers; they belong in
  the report as a known limitation.

Never "fix" the gate by special-casing traffic patterns, port numbers or IPs into
the verdict. The verdict must come from the model.

---

### P7. Docs and demo-day kit (agent, about 30 min)

**P7.1** Write `docs/ARDUINO_UNOQ_DEMO.md`, a presenter runbook: the topology diagram
from section 4, the start commands (P4.1 to P4.3, plus `--mode live` if P6.7 passed),
the section 1 demo script, the six P5.8 proof moments with what to say for each, the
honest wording for replay vs live mode, the pre-demo checklist (P7.3), and the five most
likely failures from section 11.

**P7.2** Add one line under README "Phase 3: Dashboard + Live Demo":
`Arduino UNO Q edition (model + kernel firewall on the board): see docs/ARDUINO_UNOQ_DEMO.md.`

**P7.3 Pre-demo checklist (put it in the runbook):**
1. The board is on the hotspot. Read `hostname -I` again, because the IP may have changed.
2. `bash ~/w-sentry/scripts/unoq/run_detector.sh`, adding `--lights bridge` if P5 used
   Route A (not with Route B), and `--mode live --never-block <LAPTOP_A_IP>` if P6.7
   passed. Wait for `model ready`. Use a phone hotspot (P5.8 item 2).
3. The App Lab app `wsentry-lights` is running, the matrix shows the graph alternating
   with `ON`, and one button press toggles OFF/ON.
3a. The board's monitor shows `console.py` with the board identity and live counters.
4. Laptop A: set `VITE_DETECTOR_URL` to the current IP, start the dashboard, and confirm the panel says aarch64.
5. Laptop B: `run.cmd` finds the board, and `ping -t` replies.
6. Run one dry DoS (P4.4), wait 45 s for expiry, then "Reset" on the dashboard.
7. Fallback if the board misbehaves: run `scripts\run_laptopA.cmd` on laptop A (today's two-laptop demo, unchanged).

**P7.4 Optional autostart.** A systemd unit `scripts/unoq/wsentry.service` (`User=root`,
`WorkingDirectory=/home/arduino/w-sentry`,
`ExecStart=/home/arduino/w-sentry/.venv/bin/python scripts/detector_server.py --enforce iptables --threads 4`,
plus the same `--lights bridge` / `--mode live` choices as P7.3 item 2,
`Restart=on-failure`). Install it with `sudo cp ... /etc/systemd/system/ && sudo systemctl enable --now wsentry`.
`systemctl stop` sends SIGTERM, which runs the same cleanup as Ctrl+C.

---

### 7.8 Plan B: ONNX Runtime (use only if P3.2 or P3.3 gates fail on torch)

1. On laptop A, add `scripts/unoq/export_onnx.py`. It wraps `eng.model` and
   `eng.temp_scaler` in a module whose `forward(x)` returns `softmax(temp_scaler(model(x)))`,
   then calls `torch.onnx.export(..., torch.zeros(1,5,20), "models/saved/wsentry.onnx",
   input_names=["x"], output_names=["probs"], dynamic_axes={"x":{0:"batch"},"probs":{0:"batch"}},
   opset_version=17, dynamo=False)`. If this torch version removed `dynamo=False`, use the
   dynamo exporter (`pip install onnxscript`) with a dynamic batch dimension.
2. Add `src/live/inference_onnx.py` with `OnnxEngine.predict_batch(x)` returning the same
   `(cls, conf, label)` tuples, using `onnxruntime.InferenceSession(..., providers=["CPUExecutionProvider"])`.
3. Add `--engine {torch,onnx}` to `detector_server.py` and `check_parity.py`. Import torch
   and `src.live.inference` lazily, only for `torch`, and copy `THREAT_LABELS` into the
   server so the onnx path never imports torch.
4. Verify on laptop A that `check_parity.py --engine onnx` PASSes against the torch golden
   file, then put `onnxruntime numpy msgpack` (no torch) in `setup_board.sh`, push, and
   redo P3.3 with `--engine onnx`.

---

## 8. Definition of done

1. `pytest tests/test_unoq_firewall.py` passes on laptop A; P0.4 output is unchanged (dryrun default).
2. `check_parity.py` prints PASS on the UNO Q, and its latency is recorded.
3. P4.4 passes in full: 403 on laptop B, ping times out, two WSENTRY rules for laptop B's IP,
   the dashboard shows aarch64 and the iptables rule, and everything auto-expires after about 45 s.
4. P4.5 and P4.6 pass (menu modes work; Ctrl+C leaves no WSENTRY rules).
5. P5 passes: `tests/test_unoq_status.py` is green; the board console runs on the board's
   monitor; the matrix and button work (P5.5); and all six P5.8 proof moments have been
   rehearsed and logged.
6. P6: `tests/test_unoq_live.py` is green, P6.5 results are logged, and the P6.7 gate
   outcome (pass or fail, with numbers) is in the progress log and the runbook.
7. `docs/ARDUINO_UNOQ_DEMO.md` exists and `ARDUINO_PROGRESS.md` has every step ticked or explained.

## 9. Time budget

P0 15 min · P1 2-3 h · P2 45 min (parallel with P1) · P3 30 min (torch install up to 20 min) ·
P4 30 min · P5 about 3 h · P6 4-6 h · P7 30 min. Minimum working demo (P0-P4): about half
a day. With on-device proof (P5): about one day. With live mode (P6): about 1.5 days.

## 10. Risk register

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| torch won't install or import on Debian 13 aarch64 | low-medium | CPU index URL; Plan B (ONNX Runtime) |
| Hotspot isolates clients (no peer traffic) | medium | P2.4 ping check; use Windows Mobile Hotspot on laptop A |
| laptop B finds laptop A instead of the board | medium | never run `detector_server.py` on laptop A during the Arduino demo |
| Bridge API differs from this plan | medium | P5 is isolated; Route B; the demo works without lights |
| iptables rules left behind after a crash | low | the chain is flushed on every start; manual `sudo iptables -F WSENTRY` |
| Presenter locks themself out over SSH | low | SSH from laptop A or `adb shell` only (section 4.1) |
| Dashboard's idle simulation firewalls made-up IPs | was certain, now handled | `manual_block` only firewalls connected devices in iptables mode (P1.2 test) |
| Agent stalls on password prompts | high without P2.5 | key login (P2.5); `sudo` steps are [HUMAN]; agent checks via `/api/status` |
| No USB-C hub with HDMI and power delivery | medium | buy or borrow one early; fallback: console over `ssh -t` on laptop A (weaker proof) |
| Live mode misclassifies real floods (CIC IAT encodes capture time; per-batch state) | medium | P6.5/P6.5b laptop checks (ping sweep measured at 61% correct and confident), the P6.7 gate, the `--block-packets` knob; fall back to replay mode for verdicts |
| Live mode blocks the hotspot gateway or laptop A | low | the gateway is never-blocked automatically; pass `--never-block <LAPTOP_A_IP>`; block needs at least 50% of a batch from one source |
| Python capture can't keep up with a heavy flood | low-medium | `real_traffic.py` defaults to 2,000 pps; dropped frames don't change the verdict much; lower `--pps` if needed |
| Probe/Spoofing confidence below 0.85 on some samples | medium | lead with DoS; use P1.4 hit counts to pick demo attacks |

## 11. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `No Python at '...hermes...'` on laptop A | venv's base interpreter removed | rebuild `.venv` (P0.2) |
| `[detector] --enforce iptables needs root` | started without sudo | `bash scripts/unoq/run_detector.sh` |
| `iptables not found` | package missing | `sudo apt-get install -y iptables` |
| `[firewall] could not block ...: ... Permission denied` | not root, or nft backend missing | run via sudo; check `iptables -V` (should say nf_tables) |
| Laptop B: "Could not find W-SENTRY on this network" | different networks, client isolation, or detector not running | P2.4 ping; `curl <BOARD_IP>:8000/api/hello` from laptop A; run `python menu.py <BOARD_IP>` |
| Laptop B connects to the wrong machine | another detector running (laptop A) | close laptop A's detector; delete `laptop-b/.wsentry_target` |
| Dashboard says "model server offline" | `VITE_DETECTOR_URL` wrong or not set before `npm run dev` | set it in the same PowerShell, restart Vite; or put it in `frontend/.env.local` (gitignored) |
| Laptop B prints 403s but ping never times out | iptables mode not active, or rule failed | check the detector's startup line says `enforce=iptables`; `rules` in `curl <BOARD_IP>:8000/api/status`; read `[firewall]` lines |
| Unknown IPs show up in `rules`, or the matrix shows X while idle | `/api/block` not going through `manual_block` | the dashboard's idle simulation posts made-up IPs; fix P1.3(e) and re-run the P1.2 tests |
| Ping times out but laptop B shows `network error` instead of 403 | RETURN rule missing or wrong port | `sudo iptables -S WSENTRY` must list the `--dport 8000 -j RETURN` line before DROP |
| Block never expires | sweeper thread not started | check `main()` starts `sweeper`; `curl localhost:8000/api/status` |
| Model never blocks | protection OFF, or conf < 0.85 for that family | toggle W-SENTRY ON on the dashboard; use DoS; check P1.4 hit counts |
| `check_parity` FAIL on the board only | different weights copied, or numeric issue | re-push; compare `sha256sum models/saved/*` with laptop A's `Get-FileHash`; report |
| First attack slow on the board | torch cold start | start the detector at least 1 min early; it prints `model ready.` |
| `$'\r': command not found` running a `.sh` | CRLF line endings | `.gitattributes` forces LF; re-checkout, or `sed -i 's/\r$//' scripts/unoq/*.sh` |
| `[lights] bridge call failed` | sketch app not running, socket path or permission, or protocol mismatch | start the App Lab app; `ls -l /var/run/arduino-router.sock`; switch to Route B |
| Console: "detector not reachable on 127.0.0.1:8000" | detector not started, or console started on another machine | start `run_detector.sh` on the board; run `console.py` on the board itself |
| Console counters stay 0 on the board | wrong interface | check the startup line's `iface=`; pass `--iface wlan0` (see `ip -br link`) |
| "dropped by W-SENTRY" stays 0 during a replay attack | expected: replay traffic uses the exempt API port | run `real_traffic.py udpflood` alongside; those packets get dropped |
| Board button does nothing | sketch not running, wiring, or Route A failed | App Lab app running? D2 to GND? `bridge_ping.py` prints presses? use Route B |
| Live mode: `[live] sniffing` never prints, or a permission error | not root, or wrong iface | start via `run_detector.sh` (sudo); `--iface wlan0` |
| Live mode: no verdicts during a flood | batch never fills, or every packet filtered | check the flood targets the board IP; the target port must not be 8000 or 22 |
| Live mode: wrong class | dataset shift (P6 risks a-c) | retry with `--block-packets 10`; otherwise use replay mode for verdicts and log the numbers |
| Emergency: rules stuck, attacker still dropped | crashed with rules in place | `sudo iptables -F WSENTRY; sudo iptables -D INPUT -j WSENTRY; sudo iptables -X WSENTRY` |

## 12. Error report template (`ARDUINO_ERROR_REPORT.md`)

Write it when a step fails twice. Paste raw outputs; never include passwords, Wi-Fi keys
or tokens.

```markdown
# W-SENTRY UNO Q error report
- Step ID: (e.g. P3.3)
- When: (date, time)
- Machine: laptop A | laptop B | UNO Q
- Exact command:
- Full output (last 80 lines, unedited):
- Expected (the step's "Done when"):
- Attempts (each fix tried and its result):
  1.
  2.
- Environment:
  - repo: `git rev-parse --short HEAD` / `git status -sb` / `git diff --stat`
  - board: `uname -a`, `head -3 /etc/os-release`, `python3 -V`, `free -h`, `df -h /`,
    `~/w-sentry/.venv/bin/pip freeze | grep -iE "torch|numpy|msgpack|onnx"`, `hostname -I`,
    `sudo iptables -S WSENTRY`
  - laptop: `python -V`, `node -v`, Wi-Fi IPv4 from `ipconfig`
- Suspected cause:
- Can later phases continue without this? (yes/no, which)
- What the human needs to decide or do:
```

## 13. Progress log template (`ARDUINO_PROGRESS.md`)

```markdown
# W-SENTRY UNO Q progress
Facts: BOARD_IP= | board hostname= | LAPTOP_A_IP= | LAPTOP_B_IP= | Debian= | Python= | torch= | parity ms/artifact=
- [ ] P0.1 ... P0.5
- [ ] P1.2 tests fail first (count: , expect 8)
- [ ] P1.3 ... P1.9
- [ ] P2.1 ... P2.5
- [ ] P3.1 ... P3.4
- [ ] P4.1 ... P4.6
- [ ] P5.1 ... P5.8 (P5.7: real_traffic.py copied to laptop B; P5.8: six proof moments rehearsed)
- [ ] P6.2 ... P6.7 (P6.5 ping-sweep hit %, P6.5b flood hit %, gate result: PASS / FAIL, with numbers)
- [ ] P7.1 ... P7.3
Notes:
```
