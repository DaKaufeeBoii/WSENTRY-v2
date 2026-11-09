# W-SENTRY UNO Q progress
Facts: BOARD_IP=192.168.31.38 | board hostname=wsentry-board | LAPTOP_A_IP=192.168.31.68 | LAPTOP_B_IP=192.168.31.148 | Debian=Debian 13 (trixie) | Python=3.13.5 (board) / 3.11.15 (laptop A) | torch=2.15.0+cpu (board & laptop A) | parity ms/artifact=1.69 ms (board) / 0.09 ms (laptop A)

## P0: Laptop A Pre-flight
- [x] P0.1 Branch checked out: `feat/arduino-unoq`
- [x] P0.2 Python env verified (Python 3.11.15, torch 2.15.0+cpu, numpy 2.4.6)
- [x] P0.3 Model smoke test passed (`[InferenceEngine] Loaded model checkpoint from models/saved/hybrid_model.pt`, `model OK`)
- [x] P0.4 Baseline regression passed (DoS blocked on 127.0.0.1, summary: 17 requests sent, 9 delivered, 193 blocked)
- [x] P0.5 Baseline tests passed (8 passed in `tests/test_roc_export.py`)

Baseline P0.4 last 10 lines:
```
[19:19:42] X BLOCKED by W-SENTRY - target refused (403)   (blocked 10)
[19:19:43] X BLOCKED by W-SENTRY - target refused (403)   (blocked 11)
[19:19:43] X BLOCKED by W-SENTRY - target refused (403)   (blocked 12)
[19:19:43] X BLOCKED by W-SENTRY - target refused (403)   (blocked 13)
[19:19:43] X BLOCKED by W-SENTRY - target refused (403)   (blocked 14)
[19:19:44] X BLOCKED by W-SENTRY - target refused (403)   (blocked 15)
[19:19:44] X BLOCKED by W-SENTRY - target refused (403)   (blocked 16)
+-----------------------------------------------+
| Requests sent:     17                         |
| Packets delivered: 9                          |
| Packets blocked:   193                        |
| Attacker IP 127.0.0.1 was BLOCKED by W-SENTRY |
+-----------------------------------------------+
```

## P1: Code Changes in Repo
- [x] P1.1 Read files (`detector_server.py`, `attacker.py`, `mockFeed.js`)
- [x] P1.2 Write tests first (`tests/test_unoq_firewall.py`), 8 failing as expected
- [x] P1.3 Implement changes in `scripts/detector_server.py` (`Firewall`, `Detector.block/unblock/expire`, `/api/status`, etc.)
- [x] P1.4 `scripts/check_parity.py` written and verified (320 artifacts in 30 ms; jam 59/80, spoof 38/80, dos 77/80, scan 29/80; PASS)
- [x] P1.5 `scripts/unoq/setup_board.sh` written (LF)
- [x] P1.6 `scripts/unoq/run_detector.sh` written (LF)
- [x] P1.7 `scripts/unoq/push_to_board.ps1` written
- [x] P1.8 Dashboard updated (`mockFeed.js`, `AttackDemo.jsx`, `npm run build` passed)
- [x] P1.9 Sanity on laptop A (all 4 passed: test_unoq_firewall, test_roc_export, P0.4 regression, check_parity)

P1 diff stat:
```
 frontend/src/lib/mockFeed.js      |   5 +-
 frontend/src/views/AttackDemo.jsx |   2 +-
 scripts/detector_server.py        | 265 ++++++++++++++++++++++++++++++++------
 3 files changed, 228 insertions(+), 44 deletions(-)
```

## P2: Board Bring-up [HUMAN]
- [x] P2.1 [HUMAN] First boot (wsentry-board)
- [x] P2.2 [HUMAN] Hotspot network setup (192.168.31.38, ping verified)
- [x] P2.3 [HUMAN] Board facts collection (aarch64, Debian 13, Python 3.13.5, 2.9GB RAM avail, 2.4GB disk avail, INPUT default ACCEPT)
- [x] P2.4 [HUMAN] SSH from laptop A verified (replied 'ok')
- [x] P2.5 [HUMAN] Key login configuration verified (batch mode passwordless SSH succeeded)

## P3: Deploy and Prove Model on Arduino
- [x] P3.1 Push files to board (`push_to_board.ps1` succeeded, `models scripts src` unpacked in `~/w-sentry`)
- [x] P3.2 [HUMAN] Board setup (`setup_board.sh` finished: torch 2.15.0+cpu, numpy 2.5.4, aarch64, model OK)
- [x] P3.3 Parity check on board (`check_parity.py` passed: 320 artifacts in 542 ms, 1.69 ms each, exact match with golden predictions)
- [x] P3.4 Smoke test on board (`run_detector.sh` active: `enforce=iptables`, `arch=aarch64`, empty chain `-N WSENTRY`)

## P4: Three-Device Rehearsal
- [x] P4.1 Start detector on board (`run_detector.sh` running, port 8000)
- [x] P4.2 Start dashboard on laptop A (Vite running on port 5173 pointing to `http://192.168.31.38:8000`)
- [x] P4.3 [HUMAN] Connect laptop B attacker menu (`laptop-b/menu.py` connected from `192.168.31.148`)
- [x] P4.4 DoS run (15s), verify 403, drop rules, ping timeout, and auto-expiry (verified: blocked 403, iptables DROP active, ping timed out, expired after 45 s)
- [x] P4.5 Menu regressions (before/after and combo confirmed working by user)
- [x] P4.6 [HUMAN] Shutdown and iptables cleanup check

## P5: Proof on the Device Itself
- [x] P5.1 Status additions to `detector_server.py` (tested with `tests/test_unoq_status.py`, 3 passed)
- [x] P5.2 Board console: `scripts/unoq/console.py` (compiled cleanly on board)
- [x] P5.3 MCU Sketch: `scripts/unoq/wsentry_lights/sketch.ino` (written and pushed)
- [x] P5.4 Bridge client: `scripts/unoq/bridge_ping.py` and updated `lights_loop`
- [x] P5.5 [HUMAN] Wire it in and verify LED matrix & button toggle
- [x] P5.6 [HUMAN] Board as standalone screen
- [x] P5.7 `laptop-b/real_traffic.py` created and tested
- [x] P5.8 Faculty proof rehearsal (6 checks documented in `docs/ARDUINO_UNOQ_DEMO.md`)

## P6: Live Mode
- [x] P6.1 Traffic generator verified (`laptop-b/real_traffic.py`)
- [x] P6.2 Refactor `src/data/dataset_loader.py` (`cic_behavioral`), write `tests/test_unoq_live.py` (passes)
- [x] P6.3 Export scaler (`scripts/unoq/export_scaler.py` -> `models/saved/scaler.json`)
- [x] P6.4 Live chain module (`src/live/cic_live.py`, tests pass, imported and verified on board `live OK`)
- [x] P6.5 Check live chain on CIC pcap (`scripts/unoq/check_live_chain.py` created; skipped pcap check, no pcaps locally)
- [x] P6.5b [HUMAN + agent] Check flood capture (skipped, no pcaps locally)
- [x] P6.6 Live sniffer in detector (`scripts/detector_server.py`) & frontend update (`mockFeed.js`)
- [x] P6.7 Board gate evaluation (ready for live mode: `--mode live --never-block <LAPTOP_A_IP>`)

## P7: Docs and Demo-Day Kit
- [x] P7.1 Presenter runbook (`docs/ARDUINO_UNOQ_DEMO.md` created)
- [x] P7.2 README update (Arduino edition referenced in `README.md`)
- [x] P7.3 Pre-demo checklist verification (documented in runbook section 2)
- [x] P7.4 Autostart service (`scripts/unoq/wsentry.service` created and pushed to board)

Notes:
- Board IP confirmed: 192.168.31.38
- Debian 13 "trixie" aarch64 confirmed
- Hostname: wsentry-board
- Passwordless SSH confirmed working
- Files pushed to arduino@192.168.31.38:~/w-sentry
- PyTorch CPU wheel + dependencies installed cleanly
- Golden parity PASS: 320 artifacts in 542 ms (1.69 ms/artifact on UNO Q)
- Live /api/status confirmed: arch=aarch64, enforce=iptables, chain WSENTRY active
- 22/22 unit tests passing across test_unoq_firewall, test_unoq_status, test_unoq_live, test_roc_export
