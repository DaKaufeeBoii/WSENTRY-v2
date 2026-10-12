"""
Reconnaissance scanning attacks via WSL nmap or local fallback.
"""
import subprocess
import sys


def port_scan(target_ip: str, port_range: str = "1-1024") -> subprocess.Popen:
    """
    SYN stealth scan.
    Command: wsl -e sudo nmap -sS -p {port_range} -T4 {target_ip}
    """
    cmd = ["wsl", "-e", "sudo", "nmap", "-sS", "-p", str(port_range), "-T4", target_ip]
    print(f"[ATTACK] Launching SYN Port Scan on {target_ip} (ports {port_range})...")
    try:
        return subprocess.Popen(cmd)
    except Exception:
        fallback_cmd = [
            sys.executable, "-c",
            f"import socket; print('Scanning ports on {target_ip}...'); "
            f"for p in [21, 22, 23, 25, 53, 80, 110, 143, 443, 3389, 8080]: "
            f"  s = socket.socket(); s.settimeout(0.1); "
            f"  try: s.connect(('{target_ip}', p)); print(f'Port {{p}} open') "
            f"  except: pass; s.close()"
        ]
        return subprocess.Popen(fallback_cmd)


def os_fingerprint(target_ip: str) -> subprocess.Popen:
    """
    OS detection + service version scan.
    Command: wsl -e sudo nmap -O -sV {target_ip}
    """
    cmd = ["wsl", "-e", "sudo", "nmap", "-O", "-sV", target_ip]
    print(f"[ATTACK] Launching OS Fingerprinting on {target_ip}...")
    try:
        return subprocess.Popen(cmd)
    except Exception:
        fallback_cmd = ["nmap", "-O", "-sV", target_ip]
        return subprocess.Popen(fallback_cmd)


def ping_sweep(subnet: str = "192.168.1.0/24") -> subprocess.Popen:
    """
    Host discovery ping sweep.
    Command: wsl -e sudo nmap -sn {subnet}
    """
    cmd = ["wsl", "-e", "sudo", "nmap", "-sn", subnet]
    print(f"[ATTACK] Launching Ping Sweep on subnet {subnet}...")
    try:
        return subprocess.Popen(cmd)
    except Exception:
        fallback_cmd = ["nmap", "-sn", subnet]
        return subprocess.Popen(fallback_cmd)
