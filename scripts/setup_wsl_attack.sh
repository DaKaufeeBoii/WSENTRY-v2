#!/bin/bash
# Run inside WSL Ubuntu: wsl -e bash scripts/setup_wsl_attack.sh
set -euo pipefail

echo "[W-SENTRY] Installing attack tools in WSL..."

sudo apt-get update -qq
sudo apt-get install -y -qq \
    hping3 \
    nmap \
    python3-pip \
    python3-scapy \
    net-tools \
    arping \
    tcpdump

pip3 install --user scapy --break-system-packages 2>/dev/null || pip3 install --user scapy

# Enable IP forwarding for ARP spoof
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward > /dev/null

echo "[W-SENTRY] Attack tools successfully installed."
echo "  hping3 version: $(hping3 --version 2>&1 | head -1 || echo 'Installed')"
echo "  nmap version:  $(nmap --version 2>&1 | head -1 || echo 'Installed')"
echo "  scapy:         $(python3 -c 'import scapy; print(scapy.VERSION)' 2>/dev/null || echo 'Installed')"

