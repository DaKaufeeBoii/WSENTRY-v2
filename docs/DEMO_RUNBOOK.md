# W-SENTRY Live Two-Laptop Demo Runbook

This runbook guides the team through conducting the live two-laptop intrusion detection demonstration.

---

## 1. Architecture & Network Setup

```
[Laptop A: Attacker]                       [Laptop B: Detector]
  OS: Windows 11 + WSL 2                     OS: Windows 11 (Admin Terminal)
  Tools: hping3, nmap, scapy                 System: Streamlit Dashboard + Scapy
  IP: 192.168.1.50 (Example)                 IP: 192.168.1.100 (Example)
         |                                          |
         +----------------- LAN / Wi-Fi ------------+
```

### Pre-requisites:
1. Both laptops connected to the same LAN (Ethernet switch or Wi-Fi hotspot).
2. Note both IP addresses using `ipconfig` (Windows) or `ip a` (WSL).
3. Confirm ping between laptops:
   ```powershell
   ping 192.168.1.100   # From Attacker to Detector
   ping 192.168.1.50    # From Detector to Attacker
   ```

---

## 2. Laptop B (Detector) Setup

1. **Install Npcap**:
   - Download and install Npcap from [npcap.com](https://npcap.com).
   - Ensure *"Install Npcap in WinPcap API-compatible Mode"* is checked.

2. **Start the Dashboard**:
   Open an elevated (Administrator) terminal:
   ```powershell
   cd w-sentry-deliverables-20261002
   python -m streamlit run src/dashboard/app.py
   ```
   Or via the demo launcher:
   ```powershell
   python scripts/demo_launcher.py --role detector --peer-ip 192.168.1.50
   ```

3. **In the Web Browser (`http://localhost:8501`)**:
   - Navigate to the **📡 Live Monitor** tab.
   - In the NIC selector, pick the active LAN adapter (e.g., `Wi-Fi` or `Ethernet`).
   - Click **▶ Start Capture**.
   - Verify that the status changes to **● LIVE SNIFFING ACTIVE**.

---

## 3. Laptop A (Attacker) Setup

1. **WSL Setup (First-time only)**:
   ```bash
   wsl -e bash scripts/setup_wsl_attack.sh
   ```

2. **Configure Mirrored Networking** (`%USERPROFILE%\.wslconfig`):
   ```ini
   [wsl2]
   networkingMode=mirrored
   ```
   Restart WSL:
   ```powershell
   wsl --shutdown
   ```

---

## 4. Live Demo Execution Sequence

### Phase A: Normal Traffic Baseline (0:00 - 1:00)
- On Laptop A, browse normally or send benign HTTP requests:
  ```bash
  curl http://192.168.1.100:8501
  ```
- **Observe on Detector**:
  - Live table shows green `🟢 Normal` badges.
  - Threat Rate Gauge stays below 5%.

### Phase B: SYN Flood Attack (1:00 - 2:00)
- On Laptop A, launch a high-rate SYN Flood:
  ```bash
  python -m src.attack.runner syn-flood --target 192.168.1.100 --port 80 --duration 30 --rate 200
  ```
- **Observe on Detector**:
  - Live table displays red `🔴 DoS Flood` entries in real-time.
  - Threat rate spikes on the gauge.
  - Mitigation engine triggers: in Tab 6 (**🛡️ Connection Profiler**), `192.168.1.50` transitions to `🔴 BLOCKED`.
  - Check Windows Firewall rule:
    ```powershell
    netsh advfirewall firewall show rule name="W-SENTRY_BLOCK_192_168_1_50"
    ```

### Phase C: Stealth Reconnaissance Port Scan (2:00 - 3:00)
- On Laptop A, run an Nmap port sweep:
  ```bash
  python -m src.attack.runner port-scan --target 192.168.1.100 --ports 1-1024
  ```
- **Observe on Detector**:
  - Yellow `🟡 Probe` badges appear in the packet stream.
  - High port entropy triggers threat classification with calibrated confidence > 95%.

### Phase D: ARP Cache Poisoning (3:00 - 4:00)
- On Laptop A, run ARP spoofing against the target:
  ```bash
  python -m src.attack.runner arp-spoof --target 192.168.1.100 --gateway 192.168.1.1 --duration 30
  ```
- **Observe on Detector**:
  - Orange `🟠 Spoofing` entries appear immediately.
  - Mitigation logs the MAC/IP mismatch.

---

## 5. Offline Evaluation via Real PCAP Replay

If presenting without a secondary machine or without elevated NIC raw packet permissions:
1. Go to the **📡 Live Monitor** tab.
2. Select **Real PCAP File Replay** under Capture Source.
3. Provide the file path to any real network packet capture (e.g., `data/captures/traffic.pcap`).
4. Click **▶ Replay PCAP**.
5. Observe the live feature extractor, sliding window engine, calibrated inference, and mitigation engine process the authentic packet stream in real-time.

