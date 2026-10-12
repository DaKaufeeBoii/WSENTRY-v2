"""
W-SENTRY Pre-flight checks and orchestrator for the two-laptop live demo.
"""
import argparse
import os
import subprocess
import sys
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def check_npcap() -> bool:
    """Check if Npcap / WinPcap service or DLL exists on Windows."""
    if os.name != "nt":
        return True
    system32 = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32")
    wpcap = os.path.join(system32, "wpcap.dll")
    packet = os.path.join(system32, "packet.dll")
    npcap_dir = os.path.join(system32, "Npcap")
    found = os.path.exists(wpcap) or os.path.exists(packet) or os.path.exists(npcap_dir)
    return found


def check_models() -> bool:
    """Check required model inference artifacts in models/saved/."""
    required = ["scaler.pkl", "hybrid_model.pt", "temp_scaler.pt", "model_config.json"]
    saved_dir = os.path.join(REPO_ROOT, "models", "saved")
    for r in required:
        if not os.path.exists(os.path.join(saved_dir, r)):
            return False
    return True


def check_wsl() -> bool:
    """Check if WSL is available."""
    try:
        res = subprocess.run(["wsl", "--status"], capture_output=True, text=True, check=False)
        return res.returncode == 0
    except Exception:
        return False


def ping_peer(ip: str) -> bool:
    """Verify ICMP connectivity to peer IP."""
    param = "-n" if os.name == "nt" else "-c"
    try:
        res = subprocess.run(["ping", param, "1", ip], capture_output=True, text=True, check=False)
        return res.returncode == 0
    except Exception:
        return False


def run_detector(nic: str, peer_ip: str) -> None:
    print("\n=======================================================")
    print("  W-SENTRY DETECTOR PRE-FLIGHT VERIFICATION")
    print("=======================================================")

    npcap_ok = check_npcap()
    print(f"  [1/4] Npcap / WinPcap packet driver: {'[PASS]' if npcap_ok else '[WARN - Scapy will use simulation/raw socket]'}")

    models_ok = check_models()
    if not models_ok:
        print("  [2/4] Model artifacts missing in models/saved/! (hybrid_model.pt, scaler.pkl, etc.)")
        print("        Please ensure real trained model checkpoints exist in models/saved/.")
        sys.exit(1)
    else:
        print("  [2/4] Model artifacts (models/saved/): [PASS]")

    from src.live.capture import LiveCapture
    ifaces = LiveCapture.list_interfaces()
    print(f"  [3/4] Available network interfaces: {len(ifaces)} detected")
    for ifc in ifaces[:4]:
        print(f"        - {ifc['name']} ({ifc['ip']})")

    if peer_ip:
        reachable = ping_peer(peer_ip)
        print(f"  [4/4] Peer connectivity to {peer_ip}: {'[PASS]' if reachable else '[UNREACHABLE - check IP]'}")
    else:
        print("  [4/4] Peer IP not specified (skipping ping test)")

    print("\n[W-SENTRY] Launching Streamlit Dashboard...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "src/dashboard/app.py"], cwd=REPO_ROOT)


def run_attacker(peer_ip: str) -> None:
    print("\n=======================================================")
    print("  W-SENTRY ATTACKER PRE-FLIGHT VERIFICATION")
    print("=======================================================")

    wsl_ok = check_wsl()
    print(f"  [1/3] WSL Environment: {'[PASS]' if wsl_ok else '[FAIL - WSL not found]'}")

    if peer_ip:
        reachable = ping_peer(peer_ip)
        print(f"  [2/3] Peer connectivity to detector ({peer_ip}): {'[PASS]' if reachable else '[FAIL - Detector not reachable]'}")
    else:
        print("  [2/3] Peer IP: [SKIPPED]")

    print("  [3/3] Ready to simulate attacks.")
    print("\nExample attack commands:")
    print(f"  python -m src.attack.runner syn-flood --target {peer_ip or '192.168.1.100'} --port 80 --duration 30")
    print(f"  python -m src.attack.runner port-scan --target {peer_ip or '192.168.1.100'}")
    print(f"  python -m src.attack.runner arp-spoof --target {peer_ip or '192.168.1.100'} --gateway 192.168.1.1")


def main() -> None:
    parser = argparse.ArgumentParser(description="W-SENTRY Two-Laptop Demo Launcher")
    parser.add_argument("--role", choices=["detector", "attacker"], required=True, help="Host role in the demo")
    parser.add_argument("--nic", default="Wi-Fi", help="Network interface for detector")
    parser.add_argument("--peer-ip", default="", help="IP of the partner laptop")
    args = parser.parse_args()

    if args.role == "detector":
        run_detector(args.nic, args.peer_ip)
    else:
        run_attacker(args.peer_ip)


if __name__ == "__main__":
    main()
