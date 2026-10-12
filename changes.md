# W-SENTRY: System Changelog & Architectural Evolution

This document provides a comprehensive record of all changes, architectural evolutions, codebase refactorings, Phase 3 deliverables, and post-Phase 3 production enhancements in the **W-SENTRY** (Wireless Intrusion Detection System) project.

---

## 1. Phase 1 & Phase 2 Architectural Foundations (Pre-Phase 3)

Prior to Phase 3, the project established the scientific foundation across two core experimental phases:

### Phase 1: Machine Learning Baselines & Domain Transfer Evaluation
- **Native Baseline Training**: Evaluated Random Forest (RF) and XGBoost across three heterogeneous datasets:
  - **WSN-DS** (Wireless Sensor Network routing attacks): RF 99.60% Acc, XGB 99.56% Acc, FAR 0.29%.
  - **CIC-IoT-2023** (Smart home IoT attacks): RF 99.42% Acc, XGB 99.44% Acc, FAR 8.24%.
  - **Edge-IIoTset** (Industrial IoT multi-protocol attacks): RF 92.06% Acc, XGB 91.92% Acc, FAR 0.59%.
- **Cross-Domain Collapse Discovery**: Constructed a 3×3 transfer matrix evaluating native protocol features across foreign environments. Discovered catastrophic domain collapse:
  - WSN-DS → Edge-IIoTset: **11.94% accuracy** (worse than random guessing).
  - Edge-IIoTset → WSN-DS: **1.90% accuracy**.
  - Concluded that native protocol-specific header fields fail to generalize across diverse network topologies.

### Phase 2: Behavioral Engineering, Hybrid Deep Learning & Domain Adaptation
- **20-Feature Protocol-Agnostic Schema**: Defined normalized behavioral metrics (`f_volume`, `f_rate`, `f_send_recv_ratio`, `f_control_ratio`, `f_syn_ratio`, `f_port_entropy`, etc.) that abstract away network-specific header quirks.
- **Log-Normalization Preprocessor**: Implemented signed log-scaling (`sign(x) * log1p(|x|)`) and clipping (`[-50, 50]`) followed by `RobustScaler`. This resolved gradient explosion caused by 32-bit protocol counters (e.g., `tcp.ack_raw`), boosting Edge-IIoTset accuracy from 56.8% to 94.39% (+37.6 pp).
- **Hybrid CNN-BiLSTM-Attention Model**:
  - `Conv1D` layers for spatial local pattern extraction.
  - Bidirectional LSTM for temporal dependency modeling across a 5-step sequence window.
  - Scaled dot-product self-attention pooling for feature saliency.
- **Domain Adversarial Neural Network (DANN)**:
  - Gradient Reversal Layer (GRL) aligning latent representations between CIC-IoT and Edge-IIoT.
  - Achieved unified cross-domain accuracy of **96.50%** on CIC and **96.29%** on Edge (closing 85% of the domain transfer gap).
- **Confidence Calibration**: Implemented post-hoc Temperature Scaling to optimize Expected Calibration Error (ECE) (WSN: 1.70%, CIC: 0.23%, Edge: 1.78%).

---

## 2. Pre-Phase 3 Codebase Audit & Refactoring (Zero Mock Data Enforcement)

Before rolling out the Phase 3 Streamlit dashboard and live capture pipeline, the scaffolded code was rigorously audited to eliminate all synthetic fallbacks, mock traffic generators, and hardcoded approximations:

### 2.1 Live Packet Capture (`src/live/capture.py`)
- **Removed Synthetic Traffic Generator**: Deleted `_run_simulated_stream()`, which had generated artificial packets (`scapy.IP` objects in a randomized loop).
- **Removed Simulated Interface Option**: Deleted the `"Simulated (Virtual Traffic)"` entry from `LiveCapture.list_interfaces()`.
- **Physical & Virtual NIC Prioritization**: Reconfigured interface discovery to filter out noisy Windows filter driver sub-entries and prioritize adapters with real IP addresses (`Wi-Fi`, `Ethernet`, `Loopback`).
- **Real PCAP Replay Mode**: Added native offline `.pcap` capture playback support (`scapy.sniff(offline=...)`), enabling offline analysis of authentic network packet streams without artificial data.
- **Diagnostic Error Handling**: If Scapy encounters permission issues (e.g., promiscuous mode requiring administrator rights), it sets `self.error_message` rather than falling back to fake packets.

### 2.2 Live Feature Extractor (`src/live/feature_extractor.py`)
- **Removed Synthetic Scaler Initialization**: Deleted the fallback that fitted `RobustScaler` on `np.random.normal(loc=1.0, scale=2.0, ...)` if `scaler.pkl` was not found.
- **Strict Disk Resolution**: Configured candidate path lookups for `models/saved/scaler.pkl` and added an explicit `FileNotFoundError` if genuine pre-trained scaler artifacts are absent.

### 2.3 Background Inference Pipeline (`src/live/inference_thread.py`)
- **Mathematical Preprocessing Parity**: Integrated `self.scaler.transform()` on behavioral feature vectors prior to sequence tiling. Previously, `inference_thread.py` only applied log-transform and clipping, omitting the robust scaling step required by `HybridCNNBiLSTMAttention`.

### 2.4 Artifact Exporter (`src/live/save_artifacts.py`)
- **Disallowed Synthetic Dataset Synthesis**: Removed the `np.random.seed(42)` synthetic dataset generator (which previously synthesized 1,200 fake samples if raw CSVs were missing). Replaced with an explicit requirement for authentic raw dataset files.

### 2.5 Per-Class Dashboard Tab (`src/dashboard/tabs/tab_per_class.py`)
- **Eliminated Synthetic Confusion Matrix Fallback**: Deleted lines generating synthetic diagonal matrices (`row[i] = int(support * recall)`).
- **Dynamic Classification Report Parsing**: Added `_parse_classification_report()` to dynamically parse precision, recall, F1, and support directly from `results/phase1_results.json`.
- **Real Confusion Matrices**: Mapped authentic 4×4 test-split confusion matrices for WSN-DS, CIC-IoT-2023, and Edge-IIoTset.
- **Model Toggling**: Added interactive toggles between Random Forest and XGBoost empirical results.

### 2.6 Performance Overview Tab (`src/dashboard/tabs/tab_performance.py`)
- **Dynamic Metric Ingestion**: Replaced hardcoded arrays for RF and XGBoost accuracy, F1, and FAR with dynamic lookups into `results/phase1_results.json` and `results/phase2_results.json`.

### 2.7 Live Monitor Tab (`src/dashboard/tabs/tab_live_monitor.py`)
- **Removed Mock Packet Injection**: Deleted the expander containing injection buttons for fake SYN floods, port scans, and normal traffic.
- **Added PCAP Replay UI**: Added dual-mode selection between **Live Network Interface (NIC)** and **Real PCAP File Replay**.
- **Error Telemetry**: Added inline diagnostic banners for Npcap/WinPcap permission requirements.

### 2.8 Demo Launcher & Runbook (`scripts/demo_launcher.py`, `docs/DEMO_RUNBOOK.md`)
- **Model Integrity Gate**: In `demo_launcher.py`, replaced synthetic model generation with a strict check verifying that `hybrid_model.pt`, `model_config.json`, `scaler.pkl`, and `temp_scaler.pt` exist.
- **Runbook Update**: Updated Section 5 of `docs/DEMO_RUNBOOK.md` to guide users on real PCAP file replays rather than mock packet injection.

---

## 3. Phase 3 Implementation (Live System & Streamlit Dashboard)

Phase 3 established the end-to-end interactive system:

### 3.1 Six-Tab Interactive Streamlit Dashboard (`src/dashboard/app.py`)
- **Tab 1: Performance Overview (`tab_performance.py`)**:
  - Top metric cards displaying Hybrid DL accuracy: WSN-DS (98.06%), CIC-IoT-2023 (97.80%), Edge-IIoTset (94.39%).
  - Grouped bar charts comparing Random Forest, XGBoost, and Hybrid DL on Accuracy, F1-Score, and False Alarm Rate (FAR).
  - DANN cross-domain improvement visualization and post-hoc Temperature Scaling ECE curves.
- **Tab 2: Live Monitor (`tab_live_monitor.py`)**:
  - Live packet sniffing from NIC with sliding window feature extraction.
  - Threat rate gauge (60s rolling window), capture rate (pkts/s), buffer depth counters.
  - Stream table showing last 50 ingested packets with threat class badges (`🟢 Normal`, `🟣 Jamming`, `🟠 Spoofing`, `🔴 DoS Flood`, `🟡 Probe Scan`), confidence percentages, and firewall actions taken.
  - Live threat distribution pie chart and calibrated confidence histogram.
- **Tab 3: Transfer Matrix Heatmap (`tab_transfer_matrix.py`)**:
  - Side-by-side annotated heatmaps comparing Phase 1 baseline transfer against Phase 2 behavioral transfer.
  - Highlights critical gains: WSN→Edge improved from 11.94% to 80.70% (+68.76 pp); Edge→WSN from 1.90% to 26.96%.
- **Tab 4: ROC / AUC Curves (`tab_roc_auc.py`)**:
  - Multi-class One-vs-Rest (OvR) ROC curves per dataset with class-specific AUC, micro-average, and macro-average curves loaded from `data/processed/roc_curves.npz`.
- **Tab 5: Per-Class Metrics (`tab_per_class.py`)**:
  - Expandable sections for each dataset displaying class-level Precision/Recall/F1 horizontal bars, real 4×4 test confusion matrices, and test support distributions.
- **Tab 6: Connection Profiler & Automated Firewall Mitigation (`tab_profiler.py`)**:
  - Host telemetry table grouped by source IP (packet counts, threat counts, dominant class, average confidence, active status).
  - Active rule lease table with live countdown timers (auto-expiry).
  - Historical firewall mitigation audit log with timestamp, threat class, dispatch command, and execution status.

### 3.2 Automated Firewall Mitigation Engine (`src/live/mitigation.py`)
- Multi-mode defense execution:
  - **Simulated Mode**: Safe audit logging of commands without OS disruption.
  - **Windows Host Mode**: Dispatches real firewall rules via `netsh advfirewall firewall add rule`.
  - **WSL Ubuntu Mode**: Dispatches real packet drops via `wsl -e sudo iptables -A INPUT -s <IP> -j DROP`.
- Threat-specific response logic:
  - Normal (0): No action.
  - Jamming (1): `ALERT_ONLY` (RF physical layer anomaly).
  - Spoofing (2): `BLOCK_IP` rule.
  - DoS Flood (3): `BLOCK_IP` rule + rate-limiting.
  - Intrusion Probe (4): `BLOCK_IP` rule.
- Per-IP cooldown window (default 30s) and automatic expiration cleanup for aged leases (default 300s).

### 3.3 Attack Simulation Toolkit (`src/attack/`)
- `src/attack/flood.py`: High-throughput SYN flood, UDP flood, and ICMP flood generators via WSL `hping3` or Scapy.
- `src/attack/scan.py`: Nmap reconnaissance wrappers (stealth SYN port scan `-sS`, OS fingerprinting `-O`, subnet ping sweep `-sn`).
- `src/attack/arp_spoof.py`: Bidirectional ARP cache poisoning script with automatic clean ARP restoration on exit.
- `src/attack/runner.py`: Unified CLI orchestrator for attacker machines (`python -m src.attack.runner syn-flood ...`).
- `scripts/setup_wsl_attack.sh`: Automated provisioning script for WSL Ubuntu attacker environments.

---

## 4. Post-Phase 3 Changes & Production Hardening

Following the completion of the Phase 3 implementation, several production enhancements, deployment workflows, and quality fixes were completed:

### 4.1 Git Version Control & Remote Publishing
- **Git Initialization & Branching**: Initialized the Git repository, established `main` as the default branch, and connected the upstream remote repository at `https://github.com/DaKaufeeBoii/WSENTRY-v2.git`.
- **Repository Hygiene (`.gitignore`)**: Created a comprehensive `.gitignore` filtering out bytecode (`__pycache__/`, `*.pyc`), test caches (`.pytest_cache/`), coverage files, and environment directories (`.venv/`).
- **Initial Clean Commit**: Packaged and pushed all 69 core project files (`commit 2ca5eef`) encompassing paper drafts, results, model weights, live engine, attack scripts, dashboard tabs, and tests.

### 4.2 Type Annotations & Code Polish
- **Static Typing Cleanups**: In `src/live/inference_thread.py`, resolved typing imports (`from typing import Any, List`) to ensure strict compatibility with modern Python linters.
- **Robust Path Resolvers**: Hardened file path lookups across `app.py`, `tab_roc_auc.py`, and `feature_extractor.py` using `REPO_ROOT` anchors, preventing `FileNotFoundError` when launching Streamlit from subdirectories or alternate CWDs.

### 4.3 Documentation & Runbook Modernization
- **Demo Runbook Update (`docs/DEMO_RUNBOOK.md`)**: Replaced deprecated mock-injection instructions with concrete guidelines on conducting authentic two-laptop LAN demonstrations and offline testing via real PCAP file replays.
- **Project Documentation (`changes.md`)**: Consolidated the full engineering trajectory (Phase 1, Phase 2, Pre-Phase 3 refactoring, Phase 3 implementation, and post-Phase 3 productionization) for academic and technical auditing.

### 4.4 Test Suite Hardening & CI Readiness
- Expanded and verified the Phase 3 test suite across 4 test modules:
  - `tests/test_phase3_capture.py` (buffer ordering, maxlen bounds, thread safety, interface enumeration, zero-mock contract).
  - `tests/test_phase3_dashboard.py` (result file contracts, transfer matrix keys, threat label mapping, report parsing, confusion matrix dimensional shapes).
  - `tests/test_phase3_features.py` (5-step window shape `(1, 5, 20)`, SYN flood ratio extraction, normal HTTP ACK feature bounds, scaler consistency).
  - `tests/test_phase3_mitigation.py` (simulated mode logging, IP cooldown suppression, threat class dispatch decision logic, lease expiry cleanup).

**Validation Status: 18 / 18 tests passing in ~4.9s.**
