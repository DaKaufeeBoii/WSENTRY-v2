# W-SENTRY: Changes and Pre-Phase 3 Enhancements

This document details the modifications, architectural evolutions, and codebase refactorings made prior to and leading into the Phase 3 implementation, including the transition to strict empirical data fidelity (zero mock data).

---

## 1. Phase 1 & Phase 2 Architectural Foundations

Before Phase 3 was initiated, the project developed the core scientific contributions:

### Phase 1: Machine Learning Baselines & Domain Transfer Evaluation
- **Native Baseline Training**: Evaluated Random Forest (RF) and XGBoost across three heterogeneous datasets:
  - **WSN-DS** (Wireless Sensor Network routing attacks): RF 99.6% Acc, XGB 99.56% Acc.
  - **CIC-IoT-2023** (Smart home IoT attacks): RF 99.42% Acc, XGB 99.44% Acc.
  - **Edge-IIoTset** (Industrial IoT multi-protocol attacks): RF 92.06% Acc, XGB 91.92% Acc.
- **Cross-Domain Collapse Finding**: Built the initial 3×3 transfer matrix evaluating native protocol features across foreign environments. Discovered catastrophic domain collapse:
  - WSN-DS → Edge-IIoTset: **11.94% accuracy** (worse than random guessing).
  - Edge-IIoTset → WSN-DS: **1.90% accuracy**.

### Phase 2: Behavioral Engineering, Hybrid Deep Learning & Domain Adaptation
- **20-Feature Protocol-Agnostic Schema**: Defined normalized behavioral metrics (`f_volume`, `f_rate`, `f_send_recv_ratio`, `f_control_ratio`, `f_syn_ratio`, `f_port_entropy`, etc.) that abstract away network-specific header quirks.
- **Log-Normalization Preprocessing**: Implemented signed log-scaling (`sign(x) * log1p(|x|)`) and clipping (`[-50, 50]`) followed by `RobustScaler`. This resolved gradient explosion caused by raw 32-bit protocol counters (e.g., `tcp.ack_raw`), boosting Edge-IIoTset accuracy from 56.8% to 94.4% (+37.6 pp).
- **Hybrid CNN-BiLSTM-Attention Model**:
  - `Conv1D` layers for spatial local pattern extraction.
  - Bidirectional LSTM for temporal dependency modeling across a 5-step sequence window.
  - Scaled dot-product self-attention pooling for feature saliency.
- **Domain Adversarial Neural Network (DANN)**:
  - Gradient Reversal Layer (GRL) aligning latent representations between CIC-IoT and Edge-IIoT.
  - Achieved unified cross-domain accuracy of **96.5%** on CIC and **96.3%** on Edge (closing 85% of the domain transfer gap).
- **Confidence Calibration**: Implemented post-hoc Temperature Scaling to optimize Expected Calibration Error (ECE) (WSN: 1.70%, CIC: 0.23%, Edge: 1.78%).

---

## 2. Pre-Phase 3 Codebase Audit & Refactoring (Zero Mock Data Enforcement)

Before rolling out the Phase 3 Streamlit dashboard and live capture pipeline, the scaffolded code was rigorously audited to eliminate all synthetic fallbacks, mock traffic generators, and hardcoded approximations.

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

## 3. Test Suite Expansion & Validation

The test suite was expanded and validated across all Phase 3 components:

- `tests/test_phase3_capture.py`: Added `test_live_capture_no_mock_fallback` to ensure no simulated generator attributes or mock interface options exist.
- `tests/test_phase3_dashboard.py`: Added `test_classification_report_parsing` and `test_real_confusion_matrices_shape` to verify report parser integrity and real confusion matrix contract adherence.
- `tests/test_phase3_features.py`: Verified 20-feature extraction output shape `(1, 5, 20)` and mathematical scaling consistency.
- `tests/test_phase3_mitigation.py`: Verified defense decision dispatch across Normal, Jamming (alert-only), Spoofing, DoS Flood, and Probe (blocking / rate-limiting).

**Test Results: 18 passed in 4.94s.**
