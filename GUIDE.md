# 🛡️ W-SENTRY: Complete Project Testing & Evaluation Guide

This guide walks you step-by-step through testing **W-SENTRY** to its full potential—from verifying unit tests and model artifacts to running live real-time network attack detections and autonomous firewall mitigations. Every command includes both the **Input Command** and the **Expected Output**.

---

## 📋 Table of Contents
1. [Environment & Prerequisites](#1-environment--prerequisites)
2. [Step 1: Automated Test Suite Verification](#step-1-automated-test-suite-verification)
3. [Step 2: Pre-Computing Artifacts & Calibration Data](#step-2-pre-computing-artifacts--calibration-data)
4. [Step 3: Launching the Streamlit SOC Dashboard](#step-3-launching-the-streamlit-soc-dashboard)
5. [Step 4: Interactive Dashboard Tour (All 6 Tabs)](#step-4-interactive-dashboard-tour-all-6-tabs)
6. [Step 5: Single-Machine Self-Test (Live Attack & Defense)](#step-5-single-machine-self-test-live-attack--defense)
7. [Step 6: Two-Laptop Live LAN Demo Setup](#step-6-two-laptop-live-lan-demo-setup)
8. [Step 7: Testing the React/Vite Dashboard (Alternative UI)](#step-7-testing-the-reactvite-dashboard-alternative-ui)
9. [Troubleshooting & FAQs](#troubleshooting--faqs)

---

## 1. Environment & Prerequisites

### Working Directory
Open PowerShell and navigate to the project directory:

**👉 INPUT:**
```powershell
cd d:\Kaufee\padhai\7th-sem\Project-Stage-1\w-sentry-master\w-sentry-master
.venv\Scripts\activate
```

**✅ EXPECTED OUTPUT:**
```text
(.venv) PS D:\Kaufee\padhai\7th-sem\Project-Stage-1\w-sentry-master\w-sentry-master>
```

### Network Adapters Explained
W-SENTRY automatically resolves your computer's internal hardware GUIDs into friendly names:
* **🔄 Loopback [127.0.0.1] (Localhost Self-Test):** Choose this when testing attacks and defense on your **own single laptop**.
* **🌐 Ethernet [172.168.2.156]:** Choose this when connected to a local router or direct cable for the **two-laptop demo**.
* **🌐 Wi-Fi:** Choose this if connecting two laptops over a shared Wi-Fi network.

---

## Step 1: Automated Test Suite Verification

Run the automated Pytest suites to ensure all detection, feature extraction, mitigation, and dashboard components pass unit tests.

### 1. Run Phase 3 Test Suite (16 Tests)

**👉 INPUT:**
```powershell
.venv\Scripts\python.exe -m pytest tests/test_phase3_capture.py tests/test_phase3_features.py tests/test_phase3_mitigation.py tests/test_phase3_dashboard.py -v
```

**✅ EXPECTED OUTPUT:**
```text
============================= test session starts =============================
platform win32 -- Python 3.12.13, pytest-9.2.0, pluggy-1.7.0
rootdir: D:\Kaufee\padhai\7th-sem\Project-Stage-1\w-sentry-master\w-sentry-master
plugins: anyio-4.15.1
collected 16 items

tests/test_phase3_capture.py::test_packet_buffer_append_and_retrieve PASSED [  6%]
tests/test_phase3_capture.py::test_packet_buffer_maxlen PASSED           [ 12%]
tests/test_phase3_capture.py::test_packet_buffer_thread_safety PASSED    [ 18%]
tests/test_phase3_capture.py::test_live_capture_list_interfaces PASSED   [ 25%]
tests/test_phase3_features.py::test_feature_extractor_output_shape PASSED [ 31%]
tests/test_phase3_features.py::test_feature_extractor_known_syn_flood PASSED [ 37%]
tests/test_phase3_features.py::test_feature_extractor_known_normal PASSED [ 43%]
tests/test_phase3_features.py::test_feature_extractor_scaler_consistency PASSED [ 50%]
tests/test_phase3_mitigation.py::test_mitigation_simulated_mode PASSED   [ 56%]
tests/test_phase3_mitigation.py::test_mitigation_cooldown PASSED         [ 62%]
tests/test_phase3_mitigation.py::test_mitigation_decision_logic PASSED   [ 68%]
tests/test_phase3_mitigation.py::test_mitigation_cleanup PASSED          [ 75%]
tests/test_phase3_dashboard.py::test_results_json_loadable PASSED        [ 81%]
tests/test_phase3_dashboard.py::test_transfer_matrix_keys PASSED         [ 87%]
tests/test_phase3_dashboard.py::test_threat_label_mapping PASSED         [ 93%]
tests/test_phase3_dashboard.py::test_precompute_roc_output PASSED        [100%]

============================= 16 passed in 6.98s =============================
```

### 2. Run Model Evaluation & ROC Tests (8 Tests)

**👉 INPUT:**
```powershell
.venv\Scripts\python.exe -m pytest tests/test_roc_export.py -v
```

**✅ EXPECTED OUTPUT:**
```text
============================= test session starts =============================
platform win32 -- Python 3.12.13, pytest-9.2.0, pluggy-1.7.0
rootdir: D:\Kaufee\padhai\7th-sem\Project-Stage-1\w-sentry-master\w-sentry-master
plugins: anyio-4.15.1
collected 8 items

tests/test_roc_export.py::test_one_curve_per_class_with_sane_auc PASSED  [ 12%]
tests/test_roc_export.py::test_curves_span_the_unit_square_and_are_monotone PASSED [ 25%]
tests/test_roc_export.py::test_downsampling_respects_max_points PASSED   [ 37%]
tests/test_roc_export.py::test_absent_class_is_skipped_not_fatal PASSED  [ 50%]
tests/test_roc_export.py::test_npz_keeps_full_fidelity PASSED            [ 62%]
tests/test_roc_export.py::test_json_is_valid_and_matches_summary PASSED  [ 75%]
tests/test_roc_export.py::test_set_seed_makes_numpy_deterministic PASSED [ 87%]
tests/test_roc_export.py::test_set_seed_makes_torch_deterministic PASSED [100%]

============================== 8 passed in 6.75s ==============================
```

---

## Step 2: Pre-Computing Artifacts & Calibration Data

Verify that model weights and pre-computed ROC curves are generated.

### 1. Export Model Weights & Scaler

**👉 INPUT:**
```powershell
python -m src.live.save_artifacts
```

**✅ EXPECTED OUTPUT:**
```text
[W-SENTRY] Saved scaler to models/saved/scaler.pkl
[W-SENTRY] Saved model checkpoint to models/saved/hybrid_model.pt
[W-SENTRY] Saved temperature scaler to models/saved/temp_scaler.pt
[W-SENTRY] Saved configuration to models/saved/model_config.json
```

### 2. Pre-Compute Multi-Class ROC Curves

**👉 INPUT:**
```powershell
python -m src.dashboard.precompute_roc
```

**✅ EXPECTED OUTPUT:**
```text
[W-SENTRY] Precomputed ROC curves saved to data/processed/roc_curves.npz and data/processed/roc_curves.json
```

---

## Step 3: Launching the Streamlit SOC Dashboard

Launch the primary Security Operations Center (SOC) dashboard:

**👉 INPUT:**
```powershell
streamlit run src/dashboard/app.py
```

**✅ EXPECTED OUTPUT IN TERMINAL:**
```text
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://172.168.2.156:8501

[InferenceEngine] Loaded model checkpoint from models\saved\hybrid_model.pt
```

* **URL:** Open your browser and go to `http://localhost:8501`.
* **Theme:** Styled with an obsidian dark theme (`#0e1117`), cyan accents (`#00d4ff`), and responsive layouts.

---

## Step 4: Interactive Dashboard Tour (All 6 Tabs)

Explore each of the 6 tabs in the dashboard:

### 📊 Tab 1: Performance Overview
* **Top Metric Cards:** Same-dataset accuracy for WSN-DS (**98.06%**), CIC-IoT-2023 (**97.80%**), and Edge-IIoTset (**94.39%**).
* **Model Comparison Chart:** Grouped bar chart comparing Random Forest, XGBoost, and the Hybrid CNN-BiLSTM-Attention model across all 3 datasets.
* **DANN 2-Domain Adaptation:** Demonstrates the unified model trained simultaneously on CIC-IoT and Edge-IIoTset with domain adversarial loss.
* **Probability Calibration:** Displays Expected Calibration Error (ECE) before and after temperature scaling.

### 📡 Tab 2: Live Monitor
* **NIC Selector:** Choose:
  * `🔄 Loopback [127.0.0.1] (Localhost Self-Test)` for single-PC testing.
  * `🌐 Ethernet [172.168.2.156]` for 2-laptop LAN testing.
* **Start / Stop Capture:** Click **▶ Start Capture** to begin real-time packet sniffing and background inference.
* **Throughput & Threat Gauges:** Gauges showing packets per second and rolling 60-second threat percentage.
* **Live Packet Stream:** Rolling table displaying the last 50 packets with classification (`Normal`, `DoS_Flood`, `Spoofing`, `Intrusion_Probe`, `Jamming`) and confidence scores.
* **Rolling Analytics:** Category distribution donut chart and prediction confidence histogram.

### 🔄 Tab 3: Transfer Matrix
* **Side-by-Side Heatmaps:** 
  * Left: Phase 1 baseline transfer matrix (Random Forest on raw features).
  * Right: Phase 2 behavioral transfer matrix (Hybrid DL).
* **Key Demonstration:** Observe how **WSN → Edge** transfer increases from **11.94% to 80.70% (+68.8 pp gain)** using protocol-agnostic behavioral features.

### 📈 Tab 4: ROC / AUC Curves
* **Dataset Selector:** Toggle between `WSN-DS`, `CIC-IoT-2023`, and `Edge-IIoTset`.
* **One-vs-Rest ROC Plot:** Interactive Plotly curves displaying FPR vs TPR for each threat class.
* **Summary Table:** Macro-average and micro-average AUC values.

### 🎯 Tab 5: Per-Class Metrics
* **Expandable Accordions:** Detailed breakdowns for each dataset.
* **Metrics:** Precision, recall, F1-scores, and sample support per class.
* **Confusion Matrices:** Heatmaps showing true vs predicted class distributions.

### 🔒 Tab 6: Connection Profiler & Mitigation
* **Host Connection Table:** Aggregated statistics per source IP address (packet count, threat count, dominant threat category, status).
* **Status Badges:** `🟢 ACTIVE`, `⚠️ SUSPICIOUS`, or `🚨 BLOCKED`.
* **Firewall Mode Selector:** Choose between:
  * `simulated`: Safe demonstration mode (logs rules without altering OS settings).
  * `windows`: Executes `netsh advfirewall` commands.
  * `wsl`: Executes `iptables` commands via WSL.
* **Mitigation Audit Log:** Real-time log of defense actions taken against malicious hosts.
* **"Clear All Rules" Button:** One-click removal of active firewall rules.

---

## Step 5: Single-Machine Self-Test (Live Attack & Defense)

You do **not** need a second machine to test live detection and mitigation. You can test everything on your current machine using two terminal windows.

### Terminal 1: Run the Dashboard
**👉 INPUT (Terminal 1):**
```powershell
streamlit run src/dashboard/app.py
```
1. In your browser at `http://localhost:8501`, go to the **📡 Live Monitor** tab.
2. In the **Network Interface (NIC)** dropdown, select:  
   👉 **`🔄 Loopback [127.0.0.1] (Localhost Self-Test)`**
3. Click **▶ Start Capture**.  
   *(Status indicator turns green: `● CAPTURING`)*.

---

### Terminal 2: Launch Simulated Attacks
Open a second PowerShell window in the project folder and activate `.venv`:

**👉 INPUT (Terminal 2):**
```powershell
cd d:\Kaufee\padhai\7th-sem\Project-Stage-1\w-sentry-master\w-sentry-master
.venv\Scripts\activate
```

Now fire any of the following attacks:

#### 1. Test TCP SYN Flood (DoS / DDoS)

**👉 INPUT (Terminal 2):**
```powershell
python -m src.attack.runner syn-flood --target 127.0.0.1 --port 80 --duration 15 --rate 100
```

**✅ EXPECTED OUTPUT IN TERMINAL 2:**
```text
[W-SENTRY Attack Suite] Initiating SYN-FLOOD...
[*] SYN Flood launched at 127.0.0.1:80 for 15s. Press Ctrl+C to abort.
[*] Attack process completed/stopped.
```

**✅ EXPECTED VISUAL OUTPUT IN BROWSER (`http://localhost:8501`):**
* **Throughput Gauge:** Jumps up to **`100 - 150 Pkts/sec`**.
* **Threat Rate Gauge:** Shoots into the **red alert zone (`> 85%`)**.
* **Live Packet Table Output:**
  ```text
  Time          Source IP    Dest IP      Protocol  Length  Flags  Classification  Confidence
  15:10:12.341  127.0.0.1    127.0.0.1    TCP       64      S      DoS_Flood       99.1%
  15:10:12.350  127.0.0.1    127.0.0.1    TCP       64      S      DoS_Flood       98.7%
  ```
* **Tab 6 (Connection Profiler & Mitigation):**
  * Host Profile: `127.0.0.1` status updates to **`🚨 BLOCKED`**.
  * Mitigation Audit Log: Adds record `BLOCK_IP` with status `SUCCESS`.

---

#### 2. Test Reconnaissance Port Scan (Probe)

**👉 INPUT (Terminal 2):**
```powershell
python -m src.attack.runner port-scan --target 127.0.0.1 --ports 1-100
```

**✅ EXPECTED OUTPUT IN TERMINAL 2:**
```text
[W-SENTRY Attack Suite] Initiating PORT-SCAN...
[*] Nmap port scan running against 127.0.0.1...
[*] Attack process completed/stopped.
```

**✅ EXPECTED OUTPUT IN BROWSER:**
```text
Classification: Intrusion_Probe | Confidence: 95.8% | Source: 127.0.0.1
Status: 🚨 BLOCKED
```

---

#### 3. Test UDP Flood

**👉 INPUT (Terminal 2):**
```powershell
python -m src.attack.runner udp-flood --target 127.0.0.1 --port 53 --duration 15
```

**✅ EXPECTED OUTPUT IN TERMINAL 2:**
```text
[W-SENTRY Attack Suite] Initiating UDP-FLOOD...
[*] UDP Flood launched at 127.0.0.1:53 for 15s.
[*] Attack process completed/stopped.
```

**✅ EXPECTED OUTPUT IN BROWSER:**
```text
Protocol: UDP | Classification: DoS_Flood | Confidence: 97.4%
```

---

## Step 6: Two-Laptop Live LAN Demo Setup

For your final evaluation or project presentation with two machines:

```
[ Laptop A: Attacker ]                  [ Laptop B: Detector ]
Windows 11 / WSL2 Ubuntu               Windows 11 (Your PC)
IP: e.g., 192.168.1.50                 IP: 172.168.2.156
src/attack/runner.py                   streamlit run src/dashboard/app.py
```

### Pre-Flight Verification Script
On **Laptop B (Detector)**:

**👉 INPUT:**
```powershell
python scripts/demo_launcher.py --role detector --peer-ip 192.168.1.50
```

**✅ EXPECTED OUTPUT:**
```text
============================================================
 W-SENTRY DETECTOR PRE-FLIGHT VERIFICATION
============================================================
  [PASS] Found artifact: scaler.pkl
  [PASS] Found artifact: hybrid_model.pt
  [PASS] Found artifact: temp_scaler.pt
  [PASS] Found artifact: model_config.json
  [PASS] Scapy initialized. Available NICs: 8
  [PASS] Attacker peer at 192.168.1.50 is REACHABLE.

[+] Starting Streamlit Security Operations Center (SOC)...
```

---

On **Laptop A (Attacker)**:

**👉 INPUT:**
```bash
python scripts/demo_launcher.py --role attacker --peer-ip 172.168.2.156
```

**✅ EXPECTED OUTPUT:**
```text
============================================================
 W-SENTRY ATTACKER PRE-FLIGHT VERIFICATION
============================================================
  [PASS] WSL subsystem detected.
  [PASS] hping3 attack binary installed in WSL.
  [PASS] Target detector at 172.168.2.156 is REACHABLE.

[*] Ready to launch attacks.
```

### Attack Execution from Laptop A

**👉 INPUT (Laptop A):**
```bash
# Launch a 30-second SYN flood targeting Laptop B:
python -m src.attack.runner syn-flood --target 172.168.2.156 --port 80 --duration 30 --rate 200
```

**✅ EXPECTED OUTPUT (Laptop A):**
```text
[W-SENTRY Attack Suite] Initiating SYN-FLOOD...
[*] SYN Flood launched at 172.168.2.156:80 for 30s.
[*] Attack process completed/stopped.
```

* **On Laptop B (Detector):** Watch Laptop B identify the attacker IP, classify the threat in under 3 seconds, and execute a firewall block rule!

---

## Step 7: Testing the React/Vite Dashboard (Alternative UI)

A standalone React/Tailwind/Vite SOC dashboard is also included in the repository.

**👉 INPUT:**
```powershell
cd frontend
npm install
npm run dev
```

**✅ EXPECTED OUTPUT:**
```text
  VITE v5.4.14  ready in 320 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

---

## Troubleshooting & FAQs

### Q1: Scapy shows "permission denied" or cannot open network adapter
* **Solution:** Run PowerShell as **Administrator** (`Run as Administrator`). Alternatively, select `Loopback [127.0.0.1]` in the NIC dropdown on Tab 2, and W-SENTRY will seamlessly capture local loopback traffic.

### Q2: How does the firewall mitigation engine decide when to block?
* `Normal (0)`: No action taken.
* `Jamming (1)`: `ALERT_ONLY` (physical/RF layer interference cannot be blocked via IP).
* `Spoofing (2)`: `BLOCK_IP` added for source IP.
* `DoS_Flood (3)`: `BLOCK_IP` added for source IP.
* `Intrusion_Probe (4)`: `BLOCK_IP` added for source IP.

### Q3: Why didn't a second attack trigger an immediate second rule?
* W-SENTRY implements a **30-second cooldown period** per IP address to prevent CPU exhaustion and firewall table bloat from redundant rules.

### Q4: How do I clear active firewall blocks?
* Navigate to **Tab 6 (Connection Profiler & Mitigation)** and click the **🗑️ Clear All Rules** button.

---

## 🎯 Quick Check Checklist Before Your Presentation

- [x] Run `pytest` to confirm 16/16 Phase 3 tests pass.
- [x] Run `python -m src.live.save_artifacts` to verify weights in `models/saved/`.
- [x] Launch `streamlit run src/dashboard/app.py`.
- [x] Select `Loopback [127.0.0.1]`, click **▶ Start Capture**, and launch a quick test flood (`python -m src.attack.runner syn-flood --target 127.0.0.1 --duration 10`).
- [x] Verify that Tab 6 logs the block action and displays the host status as `🚨 BLOCKED`.
