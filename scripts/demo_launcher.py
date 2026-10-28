"""
Two-Laptop Demo Launcher & Pre-Flight Verification Script for W-SENTRY.
Checks environment prerequisites and launches appropriate demo services.
"""
import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def check_ping(ip: str) -> bool:
    """Verifies ICMP reachability to peer IP."""
    param = "-n" if sys.platform.startswith("win") else "-c"
    try:
        res = subprocess.run(["ping", param, "1", ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False


def run_detector_checks(peer_ip: str | None = None, nic: str | None = None):
    print("=" * 60)
    print(" W-SENTRY DETECTOR PRE-FLIGHT VERIFICATION")
    print("=" * 60)

    # 1. Model Artifacts
    model_dir = PROJECT_ROOT / "models" / "saved"
    required_artifacts = ["scaler.pkl", "hybrid_model.pt", "temp_scaler.pt", "model_config.json"]
    all_artifacts = True
    for art in required_artifacts:
        art_path = model_dir / art
        if art_path.exists():
            print(f"  [PASS] Found artifact: {art}")
        else:
            print(f"  [FAIL] Missing artifact: {art}")
            all_artifacts = False

    if not all_artifacts:
        print("\n  [!] Exporting artifacts now...")
        from src.live.save_artifacts import export_model_artifacts
        export_model_artifacts(str(model_dir))
        print("  [+] Model artifacts successfully generated.")

    # 2. Scapy & NIC Enumeration
    try:
        import scapy.all as scapy_all
        ifaces = scapy_all.get_if_list()
        print(f"  [PASS] Scapy initialized. Available NICs: {len(ifaces)}")
    except Exception as e:
        print(f"  [WARN] Scapy capture warning: {e}. (Ensure Npcap is installed on Windows)")

    # 3. Peer IP reachability
    if peer_ip:
        if check_ping(peer_ip):
            print(f"  [PASS] Attacker peer at {peer_ip} is REACHABLE.")
        else:
            print(f"  [WARN] Attacker peer at {peer_ip} not responding to ping. Check LAN/Subnet.")

    print("\n[+] Starting Streamlit Security Operations Center (SOC)...")
    app_path = PROJECT_ROOT / "src" / "dashboard" / "app.py"
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    subprocess.run(cmd)


def run_attacker_checks(peer_ip: str):
    print("=" * 60)
    print(" W-SENTRY ATTACKER PRE-FLIGHT VERIFICATION")
    print("=" * 60)

    # 1. WSL Availability
    wsl_bin = shutil.which("wsl")
    if wsl_bin:
        print("  [PASS] WSL subsystem detected.")
        # Check hping3 inside WSL
        res = subprocess.run(["wsl", "-e", "which", "hping3"], capture_output=True, text=True)
        if res.returncode == 0:
            print("  [PASS] hping3 attack binary installed in WSL.")
        else:
            print("  [WARN] hping3 missing in WSL. Run: wsl -e bash scripts/setup_wsl_attack.sh")
    else:
        print("  [WARN] WSL not found. Will use pure-Python attack fallback.")

    # 2. Peer IP reachability
    if check_ping(peer_ip):
        print(f"  [PASS] Target detector at {peer_ip} is REACHABLE.")
    else:
        print(f"  [WARN] Target detector at {peer_ip} is NOT responding to ping.")

    print("\n[*] Ready to launch attacks. Example commands:")
    print(f"  python -m src.attack.runner syn-flood --target {peer_ip} --duration 30")
    print(f"  python -m src.attack.runner port-scan --target {peer_ip}")
    print(f"  python -m src.attack.runner udp-flood --target {peer_ip} --duration 30")


def main():
    parser = argparse.ArgumentParser(description="W-SENTRY Two-Laptop Demo Launcher")
    parser.add_argument("--role", choices=["detector", "attacker"], required=True, help="Role of this machine")
    parser.add_argument("--peer-ip", default=None, help="IP address of the other laptop")
    parser.add_argument("--nic", default=None, help="Network adapter name (detector only)")

    args = parser.parse_args()

    if args.role == "detector":
        run_detector_checks(peer_ip=args.peer_ip, nic=args.nic)
    elif args.role == "attacker":
        if not args.peer_ip:
            print("Error: --peer-ip is required for attacker role.")
            sys.exit(1)
        run_attacker_checks(peer_ip=args.peer_ip)


if __name__ == "__main__":
    main()

