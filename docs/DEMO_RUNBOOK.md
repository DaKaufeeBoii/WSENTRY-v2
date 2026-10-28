# W-SENTRY: Live Two-Laptop Demo Runbook

This runbook guides you through orchestrating the live demonstration of W-SENTRY across two machines on a shared local area network (LAN).

---

## 1. Network Topology

```
+------------------------------------+          +------------------------------------+
|        LAPTOP A (Attacker)         |          |        LAPTOP B (Detector)         |
| OS: Windows 11 / WSL2 Ubuntu       |   LAN    | OS: Windows 11                     |
| IP: 192.168.1.50                   | <------> | IP: 192.168.1.100                  |
| Tool: src/attack/runner.py         |          | Tool: Streamlit SOC Dashboard      |
| Tools: hping3, nmap, scapy         |          | Engine: Scapy + PyTorch Inference  |
+------------------------------------+          +------------------------------------+
```

---

## 2. Pre-Demo Setup

### On Laptop B (Detector):
1. **Install Npcap:**
   * Download and install from [npcap.com](https://npcap.com).
   * Ensure checkbox *"Install Npcap in WinPcap API-compatible Mode"* is checked.
2. **Activate Environment:**
   ```bash
   cd w-sentry
   .venv\Scripts\activate
   ```
3. **Run Pre-Flight Checks & Launch SOC:**
   ```bash
   python scripts/demo_launcher.py --role detector --peer-ip 192.168.1.50
   ```
   * Open the dashboard at `http://localhost:8501`.
   * Switch to the **Live Monitor** tab.
   * Select your active Wi-Fi or Ethernet adapter and click **"Start Capture"**.

---

### On Laptop A (Attacker):
1. **WSL Setup (One-time):**
   ```bash
   wsl -e bash scripts/setup_wsl_attack.sh
   ```
2. **Configure WSL2 Mirrored Networking (`%USERPROFILE%\.wslconfig`):**
   ```ini
   [wsl2]
   networkingMode=mirrored
   dnsTunneling=true
   autoProxy=true
   ```
3. **Verify Connectivity to Detector:**
   ```bash
   ping 192.168.1.100
   ```

---

## 3. Demo Attack Scenarios

### Scenario 1: TCP SYN Flood (DoS / DDoS)
* **On Attacker:**
  ```bash
  python -m src.attack.runner syn-flood --target 192.168.1.100 --port 80 --duration 30 --rate 200
  ```
* **Observed on Detector:**
  1. Live throughput spikes to 200+ pkts/sec.
  2. Threat rate gauge jumps into the red zone.
  3. Packet stream displays classified rows labeled `DoS_Flood` with high confidence.
  4. In the **Connection Profiler & Mitigation** tab, `192.168.1.50` transitions to `BLOCKED`.
  5. Windows Firewall (`netsh`) rule added to drop inbound packets from attacker IP.

---

### Scenario 2: Stealth Port Scan (Intrusion / Probe)
* **On Attacker:**
  ```bash
  python -m src.attack.runner port-scan --target 192.168.1.100 --ports 1-1024
  ```
* **Observed on Detector:**
  1. Feature `f_port_entropy` spikes due to rapid scanning across diverse destination ports.
  2. Model classifies packets as `Intrusion_Probe`.
  3. Mitigation engine executes automatic host block.

---

### Scenario 3: ARP Cache Poisoning (Man-in-the-Middle)
* **On Attacker:**
  ```bash
  python -m src.attack.runner arp-spoof --target 192.168.1.100 --gateway 192.168.1.1 --duration 45
  ```
* **Observed on Detector:**
  1. Unsolicited gratuitous ARP reply bursts detected.
  2. Classified under category `Spoofing`.
  3. Host flagged in Connection Profiler with active block status.

---

## 4. Post-Demo Teardown
1. On Detector Laptop, navigate to **Connection Profiler & Mitigation** tab and click **"Clear All Rules"**.
2. Stop the packet capture by clicking **"Stop Capture"**.

