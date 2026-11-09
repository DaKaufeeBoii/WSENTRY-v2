# W-SENTRY on Arduino UNO Q: Presenter Runbook & Demo Guide

## 1. Demo Topology

```text
  LAPTOP B (Attacker)                 ARDUINO UNO Q (Defended Device)              LAPTOP A (SOC Screen)
  ┌──────────────────────┐            ┌─────────────────────────────────────────┐  ┌────────────────────────┐
  │ laptop-b/menu.py      │ UDP 50505  │ Linux Side (Qualcomm QRB2210, Debian 13)│  │ Dashboard (Vite :5173) │
  │  (Linux Mint / Win)   │───────────▶│  scripts/detector_server.py             │  │ VITE_DETECTOR_URL =    │
  │                       │ HTTP 8000  │   --enforce iptables --threads 4        │  │ http://<BOARD_IP>:8000 │
  │                       │───────────▶│   InferenceEngine -> hybrid_model.pt    │◀─│ (aarch64 reported)     │
  │ ping -t <BOARD_IP>    │◀── 403 ────│   Firewall -> iptables chain WSENTRY    │  └────────────────────────┘
  │  (kernel DROP test)   │   ICMP     │   lights_loop --(Bridge RPC)──┐         │
  │                       │───── X ───▶│                               │         │
  └──────────────────────┘            │ MCU Side (STM32U585): LED matrix        │
                                      │  8x13 live packet graph / DDOS BLOCKED  │
                                      └─────────────────────────────────────────┘
```

All three devices are joined to the same Wi-Fi network (e.g. mobile hotspot).
- **Arduino UNO Q (`wsentry-board`):** runs `detector_server.py` with real CPU PyTorch inference and real kernel firewall enforcement via `iptables`.
- **Laptop A (SOC View):** runs the web dashboard (`http://localhost:5173`) displaying telemetry streamed via Server-Sent Events (SSE) from the board.
- **Laptop B (Attacker):** runs the attacker script or menu (`laptop-b/menu.py` or `real_traffic.py`).

---

## 2. Pre-Demo Checklist (P7.3)

Run through this checklist 15 minutes before the presentation:

1. **Verify Network & IP:**
   Check the board's IP address:
   ```bash
   ssh arduino@<BOARD_IP> "hostname -I"
   ```
   *(Ensure you use a phone hotspot rather than university Wi-Fi to prevent client-isolation and IP drift).*

2. **Start the Board Detector:**
   On the Arduino (via SSH or attached terminal):
   ```bash
   bash ~/w-sentry/scripts/unoq/run_detector.sh --lights bridge
   ```
   *(Or in live packet mode if enabled: `bash ~/w-sentry/scripts/unoq/run_detector.sh --mode live --never-block <LAPTOP_A_IP> --lights bridge`)*.
   Wait until `model ready` appears.

3. **Verify MCU LED Matrix & Firewall Button:**
   - Ensure App Lab app `wsentry-lights` is running on the board.
   - The 8x13 LED matrix should show an animated packet histogram alternating with `ON`.
   - Pressing the pushbutton (D2 to GND) toggles the firewall to `OFF` (static text `OFF`), and pressing it again restores `ON`.

4. **Verify On-Board Console (SBC Mode or SSH):**
   Run the terminal console on the board (or via `ssh -t` from Laptop A):
   ```bash
   python3 ~/w-sentry/scripts/unoq/console.py
   ```
   Confirm it shows board identity (Qualcomm Cortex-A53, aarch64, Debian 13), `FIREWALL: ON`, and live packet counters.

5. **Start SOC Dashboard on Laptop A:**
   In PowerShell on Laptop A:
   ```powershell
   $env:VITE_DETECTOR_URL = "http://<BOARD_IP>:8000"
   npm --prefix frontend run dev
   ```
   Open `http://localhost:5173`. Confirm the status badge reads `live model on wsentry-board (aarch64)`.

6. **Verify Laptop B Attacker Connectivity:**
   On Laptop B:
   ```bash
   python3 laptop-b/menu.py
   ```
   Confirm auto-discovery detects the board at `<BOARD_IP>:8000`. In a separate window, verify `ping <BOARD_IP>` replies.

7. **Rehearse One Test DoS:**
   Trigger a 10s DoS attack from Laptop B. Confirm 403s on Laptop B, packet drop on ping, LED matrix scrolling `DDOS BLOCKED`, and auto-expiry after 45s. Click "Reset" on the dashboard.

---

## 3. Demo Script (90-Second Walkthrough)

### Step 1: The Defended System (15s)
- **Show:** The Arduino UNO Q sitting on the table.
- **Narrate:** *"W-SENTRY is running natively on this Arduino UNO Q. The board's Qualcomm quad-core A53 processor runs our full PyTorch deep-learning model on Linux, while the onboard STM32 microcontroller manages physical state indicators on the LED matrix. The SOC dashboard on Laptop A is connected directly to the board over the network."*
- **Point out:** The dashboard shows `live model on wsentry-board (aarch64)`. The LED matrix shows live network packet intake.

### Step 2: The Attack (25s)
- **Show:** Laptop B with two terminal windows: `ping <BOARD_IP>` and `menu.py`.
- **Narrate:** *"Laptop B represents an attacker on the same local network. Ping shows normal connectivity with zero dropped packets. Now we launch a Denial-of-Service flood."*
- **Action:** Select option 1 (DoS Flood) in `menu.py`.

### Step 3: Real-Time Edge Detection & Kernel Mitigation (30s)
- **Show:** Simultaneous reaction across all devices:
  1. **Laptop B:** Switches from delivered packets to `X BLOCKED by W-SENTRY - target refused (403)`. Simultaneously, the `ping` window halts with `Request timed out`.
  2. **Arduino Board:** The LED matrix scrolls `DDOS BLOCKED` with a flashing warning bar. The console turns red showing `ATTACKER BLOCKED BY THE KERNEL FIREWALL`.
  3. **Laptop A Dashboard:** An immediate threat alert triggers (`DoS_Flood`, 100% confidence). The mitigation panel displays the generated `iptables` drop rule.
- **Narrate:** *"Within 1.7 milliseconds of feature window ingestion, our deep learning model identifies the DoS signature with 100% confidence. It immediately installs an in-kernel iptables DROP rule. Notice that the ping is completely dropped at the kernel layer, protecting host resources while leaving our management API open to log and signal the incident."*

### Step 4: Rule Expiry & Normal Operation (20s)
- **Show:** After 45 seconds, the block auto-expires.
- **Narrate:** *"W-SENTRY includes automated rule lifecycle management. The kernel firewall rule expires, the ping resumes, and the LED matrix returns to monitoring real-time network traffic."*

---

## 4. The Six Faculty Proof Moments (P5.8)

For faculty or skeptical evaluators who ask *"Is the Arduino really doing this, or is the laptop faking it?"*:

| Proof Moment | Physical Action | What It Proves | What to Say |
|---|---|---|---|
| **1. Hardware Identity** | Type on board terminal: `cat /proc/device-tree/model; uname -m; lscpu \| head -15` | Genuine ARM64 Linux hardware, not x86 simulation. | *"This is running on Debian 13 on a Qualcomm QRB2210 Cortex-A53 quad-core processor."* |
| **2. Laptop A Disconnect** | Start a DoS from Laptop B, then **close Laptop A's lid or disable its Wi-Fi**. | Laptop A is purely an observation screen; detection & firewall are on the board. | *"Laptop A is completely powered down/disconnected. Notice Laptop B is still blocked with 403s, ping still drops, and the Arduino matrix still scrolls DDOS BLOCKED."* |
| **3. Board Radio Control** | Run `sudo nmcli radio wifi off` directly on the board. | Defense is executing on the board's network stack. | *"When the board's radio is disabled, Laptop B gets network destination unreachable errors immediately."* |
| **4. Physical Hardware Button** | Press pushbutton on pin D2 / GND. | Physical control toggles kernel firewall protection. | *"Pressing the physical button instantly toggles firewall enforcement OFF (matrix says OFF). Re-attacking now shows unblocked traffic. Pressing it again restores full autonomous protection."* |
| **5. Real Kernel Packet Drops** | Run `python3 laptop-b/real_traffic.py udpflood --target <BOARD_IP>` alongside attack. | Real UDP flood packets are dropped in kernel space. | *"These are real UDP raw packets. The board console and iptables counters show thousands of real packets per second being dropped by the kernel netfilter."* |
| **6. Multi-Class Classification** | Run Port Scan (`scan`) or Jamming (`jam`) after unblocking. | Model is performing multi-class neural inference, not hardcoded thresholding. | *"The model distinguishes attack taxonomy: port scans are classified as Intrusion_Probe, spoofing as Spoofing, and DoS as DoS_Flood, with exact confidence ratings."* |

---

## 5. Honest Framing (Replay vs Live Mode)

When presenting to judges and technical evaluators, use this precise wording:

- **Replay Mode (Primary):**
  > *"In replay mode, Laptop B transmits validated, held-out attack sample windows over HTTP while simultaneously generating real UDP traffic. The model inference on the Arduino's CPU is 100% real (1.69 ms latency). The firewall block and iptables packet drops are 100% real in the Linux kernel."*
- **Live Mode (P6):**
  > *"In live mode, the Arduino captures raw network packets directly from the Wi-Fi interface using raw sockets, processes them through our onboard port of the CICIoT2023 feature extractor, normalizes them via RobustScaler, and feeds the resulting sliding windows directly into the model."*

---

## 6. Top 5 Failure Modes & Fast Fixes

1. **Laptop B prints: `Could not find W-SENTRY on this network`**
   - *Cause:* Wi-Fi client isolation enabled on the router, or detector server not running.
   - *Fix:* Ensure all devices are on a mobile hotspot (not campus Wi-Fi). Run `python3 menu.py <BOARD_IP>` to specify the IP directly.
2. **Dashboard shows: `model server offline`**
   - *Cause:* `VITE_DETECTOR_URL` not set before starting Vite, or board IP changed.
   - *Fix:* Stop dev server (Ctrl+C), set `$env:VITE_DETECTOR_URL = "http://<BOARD_IP>:8000"`, and rerun `npm --prefix frontend run dev`.
3. **Laptop B gets 403s but ping continues to reply**
   - *Cause:* Detector was started with `--enforce dryrun` instead of `--enforce iptables` (usually because it was run without `sudo`).
   - *Fix:* Restart with `bash ~/w-sentry/scripts/unoq/run_detector.sh`. Verify `/api/status` shows `"enforce": "iptables"`.
4. **Console or detector shows: `Address already in use`**
   - *Cause:* Previous detector instance still running in background.
   - *Fix:* On the board, run: `sudo pkill -f detector_server.py`.
5. **Bridge RPC or LED Matrix not updating (`[lights] bridge call failed`)**
   - *Cause:* Arduino App Lab sketch `wsentry-lights` not started.
   - *Fix:* Open Arduino App Lab on the board, open `wsentry-lights`, and click Upload/Run. If unavailable, detector gracefully continues full defense without lights.
