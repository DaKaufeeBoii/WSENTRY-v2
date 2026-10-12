# W-SENTRY Phase 3: Streamlit Dashboard and Live Demo

## Overview

Phase 3 delivers a 6-tab Streamlit dashboard that visualizes all Phase 1/2 results, a real-time packet capture pipeline for live intrusion detection, attack simulation via WSL Ubuntu, and a mitigation engine that issues firewall rules. The final deliverable is a two-laptop LAN demo where one machine attacks and the other detects, classifies, and mitigates in real time.

---

## Architecture

```
[Attacker Laptop]                  [Detector Laptop]
  WSL Ubuntu                         Windows 11
  hping3 / nmap / scapy             +-------------------------------+
        |                           | Streamlit Dashboard (6 tabs)  |
        | LAN (Ethernet/Wi-Fi)      |   |                           |
        +-------------------------->| scapy sniff() on NIC          |
                                    |   |                           |
                                    | PacketBuffer (ring buffer)    |
                                    |   |                           |
                                    | FeatureExtractor (20 feats)   |
                                    |   |                           |
                                    | HybridCNNBiLSTMAttention      |
                                    |   + TemperatureScaler         |
                                    |   |                           |
                                    | MitigationEngine              |
                                    |   netsh advfirewall / WSL     |
                                    |   iptables                    |
                                    +-------------------------------+
```

---

## Team Assignments

| Member  | Role                                             |
|---------|--------------------------------------------------|
| Riteesh | Architecture, model loading, inference pipeline  |
| Vikas   | Live feature extraction, attack simulation scripts|
| Gafar   | Dashboard tabs 1-4 (static visualizations)       |
| Tarun   | Dashboard tabs 5-6, live capture, mitigation engine|

---

## File Structure (New Files)

```
w-sentry/
  src/
    dashboard/
      __init__.py
      app.py                    # Streamlit entry point
      tabs/
        __init__.py
        tab_performance.py      # Tab 1: Performance Overview
        tab_live_monitor.py     # Tab 2: Live Monitor
        tab_transfer_matrix.py  # Tab 3: Transfer Matrix Heatmap
        tab_roc_auc.py          # Tab 4: ROC/AUC Curves
        tab_per_class.py        # Tab 5: Per-Class Metrics
        tab_profiler.py         # Tab 6: Connection Profiler + Mitigation Log
      components/
        __init__.py
        metric_cards.py         # Reusable metric display cards
        charts.py               # Shared chart builders (plotly)
    live/
      __init__.py
      capture.py                # Packet capture via scapy
      feature_extractor.py      # Raw packets -> 20 behavioral features
      inference.py              # Model loading + batch inference
      mitigation.py             # Firewall rule engine
      buffer.py                 # Thread-safe ring buffer
    attack/
      __init__.py
      flood.py                  # hping3 SYN/UDP/ICMP flood wrappers
      scan.py                   # nmap scan wrappers
      arp_spoof.py              # ARP spoofing via scapy (WSL)
      runner.py                 # CLI entry point for attack scripts
  scripts/
    setup_wsl_attack.sh         # WSL Ubuntu attack tool installer
    demo_launcher.py            # Orchestrates two-laptop demo
  tests/
    test_phase3_capture.py
    test_phase3_features.py
    test_phase3_mitigation.py
    test_phase3_dashboard.py
  requirements_phase3.txt
```

---

## Task Breakdown

### Task 3.1: Dashboard Skeleton and Static Tabs (Gafar)

**Estimated hours: 14**
**Dependencies: None (uses existing phase1_results.json, phase2_results.json)**
**Files: src/dashboard/app.py, src/dashboard/tabs/*.py, src/dashboard/components/*.py**

#### 3.1.1 Streamlit App Entry Point

File: `src/dashboard/app.py`

```python
def main() -> None:
    """
    Configure Streamlit page, load cached results, render 6-tab layout.
    Uses st.set_page_config(layout="wide", page_title="W-SENTRY").
    Dark theme via .streamlit/config.toml.
    """
```

Config file: `.streamlit/config.toml`

```toml
[theme]
base = "dark"
primaryColor = "#00d4ff"
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#1a1d23"
textColor = "#fafafa"
```

Tabs are created via `st.tabs()`:

```python
tabs = st.tabs([
    "Performance Overview",
    "Live Monitor",
    "Transfer Matrix",
    "ROC / AUC",
    "Per-Class Metrics",
    "Connection Profiler",
])
```

#### 3.1.2 Tab 1: Performance Overview

File: `src/dashboard/tabs/tab_performance.py`

```python
def render(phase1: dict, phase2: dict) -> None:
    """
    Top row: 3 metric cards (WSN 98.06%, CIC 97.80%, Edge 94.39%)
    using st.columns(3) + st.metric().

    Middle row: grouped bar chart comparing RF, XGBoost, CNN-BiLSTM-Attention
    across datasets. Metrics: accuracy, F1, FAR.
    Uses plotly.graph_objects.Bar with barmode='group'.

    Bottom row: DANN improvement comparison.
    - Native same-dataset vs DANN 2-domain accuracy.
    - Calibration ECE values (WSN 1.70%, CIC 0.23%, Edge 1.78%).

    Data source: data/processed/phase1_results.json, phase2_results.json.
    """
```

Metric card component:

```python
# src/dashboard/components/metric_cards.py
def render_metric_card(label: str, value: float, suffix: str = "%",
                       delta: float | None = None) -> None:
    """Wrapper around st.metric with consistent formatting."""
```

#### 3.1.3 Tab 3: Transfer Matrix Heatmap

File: `src/dashboard/tabs/tab_transfer_matrix.py`

```python
def render(phase1: dict, phase2: dict) -> None:
    """
    Two heatmaps side by side using st.columns(2):
    - Left: Phase 1 raw transfer matrix (RF baselines).
    - Right: Phase 2 behavioral transfer matrix.

    Uses plotly.figure_factory.create_annotated_heatmap.
    Matrix values from phase1_results.json["transfer_matrix"]
    and phase2_results.json["behavioral_transfer_matrix"].

    Color scale: RdYlGn (red=low transfer, green=high).
    Annotations show percentage values in each cell.

    Highlight key findings:
    - WSN->Edge improved from 11.94% to 80.7% with behavioral features.
    - Edge->CIC: 67.64% -> 61.77% (behavioral).
    """
```

#### 3.1.4 Tab 4: ROC/AUC Curves

File: `src/dashboard/tabs/tab_roc_auc.py`

```python
def render(roc_data: dict | None) -> None:
    """
    Multi-class ROC curves per dataset.
    If pre-computed ROC data exists (data/processed/roc_curves.npz),
    load and plot. Otherwise, show placeholder with instructions
    to run: python -m src.dashboard.precompute_roc

    Uses plotly with one-vs-rest ROC per class.
    Micro/macro average curves included.
    """
```

Pre-computation script:

```python
# src/dashboard/precompute_roc.py
def precompute_roc_data(model_path: str, dataset_name: str,
                        output_path: str = "data/processed/roc_curves.npz") -> None:
    """
    Load trained model checkpoint, run inference on test split,
    compute per-class ROC via sklearn.metrics.roc_curve,
    save FPR/TPR/AUC arrays to .npz file.
    """
```

#### 3.1.5 Tab 5: Per-Class Metrics

File: `src/dashboard/tabs/tab_per_class.py`

```python
def render(phase1: dict, phase2: dict) -> None:
    """
    Expandable sections per dataset (st.expander).
    Each section shows:
    - Per-class precision, recall, F1 as horizontal bar chart.
    - Confusion matrix as heatmap.
    - Class distribution pie chart.

    Classes: Normal(0), Jamming(1), Spoofing(2), DoS_Flood(3), Intrusion_Probe(4).
    Data from phase1_results.json confusion matrices + classification reports.
    """
```

---

### Task 3.2: Live Packet Capture Pipeline (Vikas + Tarun)

**Estimated hours: 18 (Vikas: 10, Tarun: 8)**
**Dependencies: Working NIC with promiscuous mode or admin privileges**
**Files: src/live/capture.py, src/live/feature_extractor.py, src/live/buffer.py**

#### 3.2.1 Ring Buffer

File: `src/live/buffer.py`

```python
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any

@dataclass
class PacketRecord:
    timestamp: float
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str          # "TCP", "UDP", "ICMP", "ARP", "OTHER"
    length: int
    flags: str             # TCP flags string, e.g. "SYN", "SYN+ACK"
    raw_features: dict     # Extracted feature dict (20 behavioral features)
    prediction: int        # Threat class (0-4), -1 if not yet classified
    confidence: float      # Calibrated softmax probability
    label: str             # Human-readable: "Normal", "DoS_Flood", etc.

class PacketBuffer:
    """Thread-safe ring buffer for packet records."""

    def __init__(self, maxlen: int = 10000) -> None:
        self._buffer: deque[PacketRecord] = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._stats: dict[str, int] = {
            "total_packets": 0,
            "threats_detected": 0,
            "by_class": {0: 0, 1: 0, 2: 0, 3: 0, 4: 0},
        }

    def append(self, record: PacketRecord) -> None: ...
    def get_recent(self, n: int = 100) -> list[PacketRecord]: ...
    def get_stats(self) -> dict: ...
    def get_threat_rate(self, window_seconds: float = 60.0) -> float: ...
    def clear(self) -> None: ...
```

#### 3.2.2 Packet Capture

File: `src/live/capture.py`

```python
import scapy.all as scapy_all
import threading

class LiveCapture:
    """
    Wraps scapy.sniff() in a background thread.
    Captures on a specified NIC, extracts features per packet window,
    feeds into the ring buffer.
    """

    def __init__(self, iface: str, buffer: PacketBuffer,
                 feature_extractor: "LiveFeatureExtractor",
                 window_size: int = 5) -> None:
        """
        Args:
            iface: Network interface name. On Windows, use the NPF device
                   name or friendly name (e.g., "Ethernet", "Wi-Fi").
                   List available with scapy.get_if_list().
            buffer: PacketBuffer to write records into.
            feature_extractor: Converts raw packet window to 20 features.
            window_size: Sliding window of packets for feature extraction
                         (matches preprocessor.py time_steps=5).
        """

    def start(self) -> None:
        """Start capture in daemon thread."""

    def stop(self) -> None:
        """Signal the sniffer to stop."""

    def _packet_callback(self, packet: scapy_all.Packet) -> None:
        """
        Called per packet by scapy.
        1. Parse src/dst IP, ports, protocol, flags, length.
        2. Append to internal sliding window deque.
        3. When window is full, call feature_extractor.extract(window).
        4. Create PacketRecord with raw_features (prediction=-1 initially).
        5. Append to buffer.
        """

    @staticmethod
    def list_interfaces() -> list[dict]:
        """Return available NICs with name, description, IP."""
```

Required privilege: Run Streamlit with admin/elevated terminal on Windows, or use Npcap in WinPcap-compatible mode.

#### 3.2.3 Live Feature Extractor

File: `src/live/feature_extractor.py`

```python
import numpy as np
from typing import List
from scapy.all import Packet

class LiveFeatureExtractor:
    """
    Converts a sliding window of raw scapy packets into the 20 behavioral
    features matching FEATURE_COLS from src/data/dataset_loader.py.

    Feature mapping from packet fields:
    - f_volume:         sum of packet lengths in window
    - f_rate:           f_volume / window_duration_seconds
    - f_send_recv_ratio: count(src_port < 1024) / count(dst_port < 1024) + 1
    - f_control_ratio:  count(SYN|FIN|RST flags) / total_packets
    - f_ack_ratio:      count(ACK flags) / total_packets
    - f_syn_ratio:      count(SYN flags) / total_packets
    - f_fin_rst_ratio:  count(FIN|RST flags) / total_packets
    - f_variability:    std(packet_lengths) / mean(packet_lengths) + 1
    - f_port_entropy:   Shannon entropy of unique dst_ports
    - f_flag_intensity: count(PSH|URG|ECE flags)
    - f_payload_ratio:  sum(payload_bytes) / f_volume + 1
    - f_timing:         mean(inter-arrival times)
    - f_burst:          max(packets_per_100ms_bin)
    - f_protocol_type:  mode protocol as float (TCP=1, UDP=2, ICMP=3, other=0)
    - f_energy:         sum(length^2) (proxy for energy)
    - f_distance:       count(unique dst_ips)
    - f_rank:           max_packet_length / mean_packet_length
    - f_anomaly_score:  abs(f_send_recv_ratio - 1) * f_rate
    - f_conn_state:     count(SYN) + count(ACK) + count(FIN)
    - f_mqtt_activity:  count(packets with dst_port in {1883, 8883})
    """

    def __init__(self, scaler_path: str = "models/saved/scaler.pkl") -> None:
        """Load the fitted RobustScaler from training."""

    def extract(self, packets: List[Packet]) -> np.ndarray:
        """
        Args:
            packets: List of scapy Packet objects (window_size packets).
        Returns:
            np.ndarray of shape (1, window_size, 20) ready for model input.
            Applies log-transform, clip, and RobustScaler (matching preprocessor.py).
        """

    def _parse_packet(self, pkt: Packet) -> dict:
        """Extract per-packet raw fields: src_ip, dst_ip, src_port, dst_port,
        protocol, flags, length, payload_length, timestamp."""
```

Scaler serialization (added to training pipeline):

```python
# Addition to run_phase2.py or a new script: src/live/save_artifacts.py
def save_inference_artifacts(scaler, model, temp_scaler, output_dir="models/saved/"):
    """
    Saves:
    - models/saved/scaler.pkl          (RobustScaler via joblib)
    - models/saved/hybrid_model.pt     (model state_dict)
    - models/saved/temp_scaler.pt      (TemperatureScaler state_dict)
    - models/saved/model_config.json   (n_features, n_classes, hidden_dim)
    """
```

---

### Task 3.3: Model Inference Pipeline (Riteesh)

**Estimated hours: 8**
**Dependencies: Task 3.2.3 (feature extractor), saved model artifacts**
**Files: src/live/inference.py, src/live/save_artifacts.py**

#### 3.3.1 Inference Engine

File: `src/live/inference.py`

```python
import torch
import numpy as np
from src.models.hybrid_dl import HybridCNNBiLSTMAttention
from src.models.calibration import TemperatureScaler

THREAT_LABELS = {0: "Normal", 1: "Jamming", 2: "Spoofing",
                 3: "DoS_Flood", 4: "Intrusion_Probe"}

class InferenceEngine:
    """
    Loads trained model + temperature scaler, provides single-window inference.
    Designed for low-latency (<50ms per window on CPU).
    """

    def __init__(self, model_dir: str = "models/saved/",
                 device: str = "cpu") -> None:
        """
        Loads:
        - model_config.json -> n_features, n_classes, hidden_dim
        - hybrid_model.pt -> HybridCNNBiLSTMAttention state_dict
        - temp_scaler.pt -> TemperatureScaler state_dict
        Sets model to eval mode. Disables gradient computation globally.
        """

    def predict(self, features: np.ndarray) -> tuple[int, float, str]:
        """
        Args:
            features: np.ndarray of shape (1, time_steps, n_features).
        Returns:
            (predicted_class: int, confidence: float, label: str)
        Applies temperature scaling before softmax.
        """

    def predict_batch(self, features: np.ndarray) -> list[tuple[int, float, str]]:
        """Batch inference for multiple windows."""

    def get_probabilities(self, features: np.ndarray) -> np.ndarray:
        """Return full calibrated probability distribution (1, n_classes)."""
```

#### 3.3.2 Artifact Export Script

File: `src/live/save_artifacts.py`

```python
def export_model_artifacts(
    dataset_name: str = "wsn",
    model_checkpoint: str = None,
    output_dir: str = "models/saved/"
) -> None:
    """
    Run after Phase 2 training to export inference artifacts.
    Steps:
    1. Load dataset, preprocess (to get fitted scaler).
    2. Load or re-train model.
    3. Fit temperature scaler on validation set.
    4. Save scaler.pkl, hybrid_model.pt, temp_scaler.pt, model_config.json.

    Usage: python -m src.live.save_artifacts --dataset wsn
    """
```

---

### Task 3.4: Live Monitor Dashboard Tab (Tarun)

**Estimated hours: 12**
**Dependencies: Tasks 3.2, 3.3**
**Files: src/dashboard/tabs/tab_live_monitor.py**

#### 3.4.1 Tab 2: Live Monitor

```python
def render(buffer: PacketBuffer, engine: InferenceEngine,
           capture: LiveCapture | None) -> None:
    """
    Layout:
    +-------------------------------------------------+
    | [NIC Selector] [Start/Stop] [Status Indicator]  |
    +-------------------------------------------------+
    | Threat Rate Gauge | Packets/sec | Threats Count  |
    +-------------------------------------------------+
    | Real-time packet table (last 50 packets)         |
    | Columns: Time, Src IP, Dst IP, Protocol, Class,  |
    |          Confidence, Action Taken                 |
    | Color-coded rows: green=Normal, red=DoS,         |
    |   orange=Spoofing, yellow=Probe, purple=Jamming  |
    +-------------------------------------------------+
    | Threat distribution pie (rolling 60s window)     |
    | Confidence histogram (last 200 predictions)      |
    +-------------------------------------------------+

    Uses st.empty() containers with 2-second refresh via
    st.rerun() or streamlit-autorefresh component.

    NIC selector: populated from LiveCapture.list_interfaces().
    Start/Stop: toggles capture thread via st.session_state.

    Inference loop:
    1. capture._packet_callback fills buffer with raw features.
    2. Background thread polls buffer for records with prediction==-1.
    3. Calls engine.predict() on each, updates record in-place.
    4. If threat detected, triggers mitigation engine.
    """
```

Session state management:

```python
# In app.py, initialize once:
if "buffer" not in st.session_state:
    st.session_state.buffer = PacketBuffer(maxlen=10000)
if "capture" not in st.session_state:
    st.session_state.capture = None
if "engine" not in st.session_state:
    st.session_state.engine = InferenceEngine()
if "mitigation" not in st.session_state:
    st.session_state.mitigation = MitigationEngine()
```

---

### Task 3.5: Connection Profiler and Mitigation (Tarun)

**Estimated hours: 14**
**Dependencies: Task 3.4**
**Files: src/live/mitigation.py, src/dashboard/tabs/tab_profiler.py**

#### 3.5.1 Mitigation Engine

File: `src/live/mitigation.py`

```python
import subprocess
import logging
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

class MitigationMode(Enum):
    SIMULATED = "simulated"    # Log only, no actual firewall changes
    WINDOWS = "windows"        # netsh advfirewall on Windows
    WSL = "wsl"                # iptables via WSL

@dataclass
class MitigationAction:
    timestamp: datetime
    threat_class: int
    threat_label: str
    src_ip: str
    dst_ip: str
    action: str               # "BLOCK_IP", "RATE_LIMIT", "ALERT_ONLY"
    rule_command: str          # Actual command that was/would be executed
    mode: MitigationMode
    success: bool
    details: str

class MitigationEngine:
    """
    Issues firewall rules in response to detected threats.
    Supports three modes: simulated (logging only), Windows (netsh),
    and WSL (iptables).
    """

    def __init__(self, mode: MitigationMode = MitigationMode.SIMULATED,
                 cooldown_seconds: float = 30.0,
                 max_rules: int = 50) -> None:
        """
        Args:
            mode: Execution mode.
            cooldown_seconds: Minimum time between rules for same src_ip.
            max_rules: Maximum active firewall rules before cleanup.
        """
        self._log: list[MitigationAction] = []
        self._active_blocks: dict[str, datetime] = {}

    def respond(self, record: "PacketRecord") -> MitigationAction | None:
        """
        Decision logic based on threat class:
        - Normal (0): No action.
        - Jamming (1): ALERT_ONLY (cannot block at network layer).
        - Spoofing (2): BLOCK_IP for src_ip.
        - DoS_Flood (3): BLOCK_IP for src_ip + RATE_LIMIT.
        - Intrusion_Probe (4): BLOCK_IP for src_ip.

        Returns None if cooldown not expired for this src_ip.
        """

    def _execute_block_windows(self, src_ip: str, rule_name: str) -> tuple[bool, str]:
        """
        Execute:
        netsh advfirewall firewall add rule name="W-SENTRY_{rule_name}"
            dir=in action=block remoteip={src_ip} protocol=any

        Returns (success, stderr_or_empty).
        Requires elevated privileges.
        """

    def _execute_block_wsl(self, src_ip: str) -> tuple[bool, str]:
        """
        Execute via WSL:
        wsl -e sudo iptables -A INPUT -s {src_ip} -j DROP

        Returns (success, stderr_or_empty).
        """

    def _execute_rate_limit_wsl(self, src_ip: str,
                                 limit: str = "10/minute") -> tuple[bool, str]:
        """
        Execute via WSL:
        wsl -e sudo iptables -A INPUT -s {src_ip} -m limit
            --limit {limit} -j ACCEPT
        wsl -e sudo iptables -A INPUT -s {src_ip} -j DROP
        """

    def cleanup_expired(self, max_age_seconds: float = 300.0) -> int:
        """Remove firewall rules older than max_age_seconds. Returns count removed."""

    def get_log(self) -> list[MitigationAction]: ...
    def get_active_blocks(self) -> dict[str, datetime]: ...
```

#### 3.5.2 Tab 6: Connection Profiler + Mitigation Log

File: `src/dashboard/tabs/tab_profiler.py`

```python
def render(buffer: PacketBuffer, mitigation: MitigationEngine) -> None:
    """
    Layout:
    +-----------------------------------------------+
    | Connection Table (grouped by src_ip)           |
    | Columns: Src IP, Packet Count, Threat Count,  |
    |   Dominant Class, Avg Confidence, Status       |
    | Status: ACTIVE / BLOCKED / RATE_LIMITED        |
    +-----------------------------------------------+
    | Mitigation Mode Selector (Simulated/Win/WSL)  |
    | [Clear All Rules] button                       |
    +-----------------------------------------------+
    | Mitigation Log (scrollable)                    |
    | Columns: Time, Src IP, Threat, Action, Rule,  |
    |   Mode, Success                                |
    | Color: green=success, red=failed               |
    +-----------------------------------------------+
    | Active Blocks Summary                          |
    | IP -> Time Remaining before auto-cleanup       |
    +-----------------------------------------------+

    Uses st.dataframe with column_config for colored status cells.
    Mitigation mode stored in st.session_state.mitigation_mode.
    """
```

---

### Task 3.6: Attack Simulation Scripts (Vikas)

**Estimated hours: 12**
**Dependencies: WSL Ubuntu installed with tools**
**Files: src/attack/*.py, scripts/setup_wsl_attack.sh**

#### 3.6.1 WSL Attack Environment Setup

File: `scripts/setup_wsl_attack.sh`

```bash
#!/bin/bash
# Run inside WSL Ubuntu: wsl -e bash scripts/setup_wsl_attack.sh
set -euo pipefail

echo "[W-SENTRY] Installing attack tools in WSL..."

sudo apt-get update -qq
sudo apt-get install -y -qq \
    hping3 \
    nmap \
    python3-pip \
    python3-scapy \
    net-tools \
    arping \
    tcpdump

pip3 install --user scapy

# Enable IP forwarding for ARP spoof
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward > /dev/null

echo "[W-SENTRY] Attack tools installed."
echo "  hping3 version: $(hping3 --version 2>&1 | head -1)"
echo "  nmap version:  $(nmap --version | head -1)"
echo "  scapy:         $(python3 -c 'import scapy; print(scapy.VERSION)')"
```

#### 3.6.2 SYN/UDP/ICMP Flood

File: `src/attack/flood.py`

```python
import subprocess

def syn_flood(target_ip: str, target_port: int = 80,
              duration: int = 30, rate: int = 100) -> subprocess.Popen:
    """
    Launch SYN flood via WSL hping3.
    Command: wsl -e sudo hping3 -S -p {port} --flood -c {rate*duration} {target_ip}

    Args:
        target_ip: Victim IP on LAN.
        target_port: Target port.
        duration: Seconds to run.
        rate: Approximate packets per second.
    Returns:
        subprocess.Popen handle for the attack process.
    """

def udp_flood(target_ip: str, target_port: int = 53,
              duration: int = 30, packet_size: int = 512) -> subprocess.Popen:
    """
    Command: wsl -e sudo hping3 --udp -p {port} --flood
             -d {packet_size} -c {count} {target_ip}
    """

def icmp_flood(target_ip: str, duration: int = 30,
               packet_size: int = 1024) -> subprocess.Popen:
    """
    Command: wsl -e sudo hping3 --icmp --flood
             -d {packet_size} -c {count} {target_ip}
    """

def stop_flood(proc: subprocess.Popen) -> None:
    """Terminate the hping3 process."""
```

#### 3.6.3 Nmap Scanning

File: `src/attack/scan.py`

```python
def port_scan(target_ip: str, port_range: str = "1-1024") -> subprocess.Popen:
    """
    Command: wsl -e sudo nmap -sS -p {port_range} -T4 {target_ip}
    SYN stealth scan.
    """

def os_fingerprint(target_ip: str) -> subprocess.Popen:
    """
    Command: wsl -e sudo nmap -O -sV {target_ip}
    OS detection + service version scan.
    """

def ping_sweep(subnet: str = "192.168.1.0/24") -> subprocess.Popen:
    """
    Command: wsl -e sudo nmap -sn {subnet}
    Host discovery ping sweep.
    """
```

#### 3.6.4 ARP Spoofing

File: `src/attack/arp_spoof.py`

```python
def arp_spoof(target_ip: str, gateway_ip: str,
              iface: str = "eth0", duration: int = 60) -> subprocess.Popen:
    """
    ARP spoofing via scapy in WSL.
    Runs a Python script inside WSL that:
    1. Sends gratuitous ARP replies to target claiming to be gateway.
    2. Sends gratuitous ARP replies to gateway claiming to be target.
    3. Loops every 2 seconds for {duration} seconds.
    4. Restores correct ARP tables on exit.

    Command: wsl -e sudo python3 -c "
        from scapy.all import *
        import time, sys
        target, gateway, iface = '{target_ip}', '{gateway_ip}', '{iface}'
        target_mac = getmacbyip(target)
        gateway_mac = getmacbyip(gateway)
        end = time.time() + {duration}
        try:
            while time.time() < end:
                send(ARP(op=2, pdst=target, hwdst=target_mac, psrc=gateway), verbose=0)
                send(ARP(op=2, pdst=gateway, hwdst=gateway_mac, psrc=target), verbose=0)
                time.sleep(2)
        finally:
            send(ARP(op=2, pdst=target, hwdst=target_mac,
                      psrc=gateway, hwsrc=gateway_mac), count=3, verbose=0)
            send(ARP(op=2, pdst=gateway, hwdst=gateway_mac,
                      psrc=target, hwsrc=target_mac), count=3, verbose=0)
    "
    """
```

#### 3.6.5 Attack Runner CLI

File: `src/attack/runner.py`

```python
"""
CLI to launch attacks from the attacker laptop.

Usage:
    python -m src.attack.runner syn-flood --target 192.168.1.100 --port 80 --duration 30
    python -m src.attack.runner udp-flood --target 192.168.1.100 --port 53 --duration 30
    python -m src.attack.runner icmp-flood --target 192.168.1.100 --duration 30
    python -m src.attack.runner port-scan --target 192.168.1.100 --ports 1-1024
    python -m src.attack.runner os-scan --target 192.168.1.100
    python -m src.attack.runner ping-sweep --subnet 192.168.1.0/24
    python -m src.attack.runner arp-spoof --target 192.168.1.100 --gateway 192.168.1.1

All attacks run via WSL. Requires: wsl -e which hping3 to return a path.
"""
import argparse
```

---

### Task 3.7: Integration and Inference Thread (Riteesh + Tarun)

**Estimated hours: 8**
**Dependencies: Tasks 3.2, 3.3, 3.4, 3.5**
**Files: src/live/inference_thread.py**

```python
import threading
import time
from src.live.buffer import PacketBuffer, PacketRecord
from src.live.inference import InferenceEngine
from src.live.mitigation import MitigationEngine

class InferenceThread(threading.Thread):
    """
    Background daemon thread that:
    1. Polls PacketBuffer for records with prediction == -1.
    2. Batches up to 32 records for inference.
    3. Calls InferenceEngine.predict_batch().
    4. Updates records with prediction, confidence, label.
    5. Passes threat records to MitigationEngine.respond().
    6. Sleeps 100ms between polls (configurable).

    Runs as daemon thread so it dies with the main Streamlit process.
    """

    def __init__(self, buffer: PacketBuffer, engine: InferenceEngine,
                 mitigation: MitigationEngine,
                 poll_interval: float = 0.1, batch_size: int = 32) -> None: ...

    def run(self) -> None: ...
    def stop(self) -> None: ...
```

---

### Task 3.8: Two-Laptop Demo Setup (All)

**Estimated hours: 6**
**Dependencies: All previous tasks**
**File: scripts/demo_launcher.py, docs/DEMO_RUNBOOK.md**

#### Network Setup

```
Laptop A (Attacker)                    Laptop B (Detector)
+------------------+                   +------------------+
| Windows 11       |                   | Windows 11       |
| WSL Ubuntu       | --- Ethernet ---  | Streamlit app    |
| IP: 192.168.1.50 |    or Wi-Fi LAN   | IP: 192.168.1.100|
| Attack scripts   |                   | scapy capture    |
+------------------+                   +------------------+
```

Steps:
1. Connect both laptops to same LAN (direct Ethernet cable or shared router).
2. Assign static IPs or note DHCP-assigned IPs.
3. On Laptop B (detector): verify connectivity with `ping 192.168.1.50`.
4. On Laptop B: install Npcap (https://npcap.com) with "WinPcap API-compatible mode" checked.
5. On Laptop B: `cd w-sentry && .venv\Scripts\activate && streamlit run src/dashboard/app.py`.
6. On Laptop A: `wsl -e bash scripts/setup_wsl_attack.sh` (first time only).
7. On Laptop A: `python -m src.attack.runner syn-flood --target 192.168.1.100 --duration 60`.
8. On Laptop B: observe Live Monitor tab detecting and classifying the flood.

#### Demo Launcher Script

File: `scripts/demo_launcher.py`

```python
"""
Pre-flight checks and launcher for the demo.

Checks:
1. Npcap installed (Windows).
2. Model artifacts exist in models/saved/.
3. scapy can open a capture on the selected NIC.
4. WSL available and hping3 installed (attacker only).
5. Network connectivity to peer IP.

Usage:
    python scripts/demo_launcher.py --role detector --nic "Ethernet" --peer-ip 192.168.1.50
    python scripts/demo_launcher.py --role attacker --peer-ip 192.168.1.100
"""
```

---

### Task 3.9: Testing (All)

**Estimated hours: 8**
**Dependencies: Tasks 3.2-3.7**

#### Test Files

File: `tests/test_phase3_capture.py`

```python
def test_packet_buffer_append_and_retrieve():
    """Buffer stores and returns records in order."""

def test_packet_buffer_maxlen():
    """Buffer drops oldest when full."""

def test_packet_buffer_thread_safety():
    """Concurrent append/read from multiple threads."""

def test_live_capture_list_interfaces():
    """Returns at least one interface on the host."""
```

File: `tests/test_phase3_features.py`

```python
def test_feature_extractor_output_shape():
    """5-packet window produces (1, 5, 20) array."""

def test_feature_extractor_known_syn_flood():
    """Synthetic SYN packets produce high f_syn_ratio, f_rate."""

def test_feature_extractor_known_normal():
    """Synthetic HTTP GET packets produce low threat features."""

def test_feature_extractor_scaler_consistency():
    """Output range matches training data distribution."""
```

File: `tests/test_phase3_mitigation.py`

```python
def test_mitigation_simulated_mode():
    """Simulated mode logs but does not execute commands."""

def test_mitigation_cooldown():
    """Same src_ip within cooldown returns None."""

def test_mitigation_decision_logic():
    """DoS_Flood -> BLOCK_IP, Normal -> no action, Jamming -> ALERT_ONLY."""

def test_mitigation_cleanup():
    """Expired rules are removed after max_age."""
```

File: `tests/test_phase3_dashboard.py`

```python
def test_results_json_loadable():
    """phase1_results.json and phase2_results.json parse without error."""

def test_transfer_matrix_keys():
    """All 9 source->target pairs exist in both matrices."""

def test_threat_label_mapping():
    """THREAT_LABELS covers classes 0-4."""
```

Run all tests:

```bash
cd w-sentry
PYTHONPATH=. pytest tests/test_phase3_*.py -v
```

---

## Dependencies (requirements_phase3.txt)

```
streamlit>=1.32.0
plotly>=5.18.0
scapy>=2.5.0
joblib>=1.3.0
streamlit-autorefresh>=1.0.1
# Already in .venv from Phase 1/2:
# torch, numpy, pandas, scikit-learn, xgboost, imbalanced-learn
```

Install:

```bash
cd w-sentry
.venv\Scripts\activate
pip install -r requirements_phase3.txt
```

Windows-specific: install Npcap from https://npcap.com (required for scapy raw capture on Windows).

---

## Schedule

| Week | Tasks                                              | Owner(s)         |
|------|----------------------------------------------------|------------------|
| 1    | 3.1 (Dashboard skeleton + static tabs 1,3,4,5)    | Gafar            |
| 1    | 3.2.1-3.2.2 (Buffer + capture)                    | Tarun            |
| 1    | 3.2.3 (Live feature extractor)                     | Vikas            |
| 1    | 3.3 (Inference engine + artifact export)           | Riteesh          |
| 2    | 3.4 (Live Monitor tab)                             | Tarun            |
| 2    | 3.5 (Mitigation engine + Profiler tab)             | Tarun + Riteesh  |
| 2    | 3.6 (Attack scripts + WSL setup)                   | Vikas            |
| 2    | 3.1 continued (ROC pre-computation, polish)        | Gafar            |
| 3    | 3.7 (Inference thread integration)                 | Riteesh + Tarun  |
| 3    | 3.8 (Two-laptop demo setup + runbook)              | All              |
| 3    | 3.9 (Testing + bug fixes)                          | All              |

**Total estimated hours: 100** (Riteesh: 22, Vikas: 22, Gafar: 20, Tarun: 36)

---

## Risks and Mitigations

| Risk                                          | Mitigation                                                  |
|-----------------------------------------------|-------------------------------------------------------------|
| Npcap driver issues on Windows                | Fallback to reading PCAP files instead of live capture      |
| Admin privileges required for scapy/netsh     | Document elevation requirement; simulated mode as fallback  |
| WSL networking isolation (no LAN access)      | Use WSL2 mirrored networking mode (`wsl --set-default-version 2`, enable `networkingMode=mirrored` in `.wslconfig`) |
| Feature distribution mismatch (live vs train) | Compare live feature histograms against training set stats  |
| Inference latency too high for real-time      | Batch windows, use CPU-optimized torch; target <50ms/window |
| hping3 detected/blocked by Windows Defender   | Add firewall exception; or use scapy-based flood in WSL    |

---

## WSL Networking Configuration

For WSL2 to send/receive packets on the LAN (required for attack scripts):

File: `%USERPROFILE%\.wslconfig`

```ini
[wsl2]
networkingMode=mirrored
dnsTunneling=true
autoProxy=true
```

After editing, restart WSL:

```powershell
wsl --shutdown
wsl
```

Verify WSL can reach the detector laptop:

```bash
# Inside WSL
ping 192.168.1.100
```

If mirrored mode is unavailable (older Windows builds), use NAT + port forwarding:

```powershell
# On attacker laptop (PowerShell, admin)
netsh interface portproxy add v4tov4 listenport=0 connectaddress=$(wsl hostname -I)
```

---

## Success Criteria

1. All 6 dashboard tabs render with real Phase 1/2 data; no placeholder content.
2. Live Monitor captures packets from NIC and displays classified results within 3 seconds.
3. At least 3 attack types (SYN flood, port scan, ARP spoof) are detected and classified correctly during live demo.
4. Mitigation engine issues at least one real firewall rule (netsh or iptables) during demo.
5. All `test_phase3_*.py` tests pass.
6. Two-laptop demo runs end-to-end without manual intervention beyond starting the scripts.
