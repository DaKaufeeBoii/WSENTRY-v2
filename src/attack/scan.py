"""
Network reconnaissance and scanning wrappers via nmap.
"""
import shutil
import subprocess


def _is_wsl_available() -> bool:
    return shutil.which("wsl") is not None


def port_scan(target_ip: str, port_range: str = "1-1024") -> subprocess.Popen:
    """
    Launch SYN stealth scan.
    Command: wsl -e sudo nmap -sS -p {port_range} -T4 {target_ip}
    """
    if _is_wsl_available():
        cmd = ["wsl", "-e", "sudo", "nmap", "-sS", "-p", str(port_range), "-T4", target_ip]
    else:
        cmd = ["nmap", "-sS", "-p", str(port_range), "-T4", target_ip]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc


def os_fingerprint(target_ip: str) -> subprocess.Popen:
    """
    Launch OS detection and service version scan.
    Command: wsl -e sudo nmap -O -sV {target_ip}
    """
    if _is_wsl_available():
        cmd = ["wsl", "-e", "sudo", "nmap", "-O", "-sV", target_ip]
    else:
        cmd = ["nmap", "-O", "-sV", target_ip]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc


def ping_sweep(subnet: str = "192.168.1.0/24") -> subprocess.Popen:
    """
    Host discovery ping sweep.
    Command: wsl -e sudo nmap -sn {subnet}
    """
    if _is_wsl_available():
        cmd = ["wsl", "-e", "sudo", "nmap", "-sn", subnet]
    else:
        cmd = ["nmap", "-sn", subnet]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc

