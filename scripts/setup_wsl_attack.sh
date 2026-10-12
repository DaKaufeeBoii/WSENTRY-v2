#!/bin/bash
# Run inside WSL Ubuntu: wsl -e bash scripts/setup_wsl_attack.sh
set -euo pipefail

echo "[W-SENTRY] Installing attack tools in WSL Ubuntu..."

sudo apt-get update -qq
sudo apt-get install -y -qq \
    hping3 \
    nmap \
    python3-pip \
    python3-scapy \
    net-tools \
    arping \
    tcpdump

pip3 install --user scapy || true

# Enable IP forwarding for ARP spoofing
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward > /dev/null

echo "[W-SENTRY] Attack tools successfully installed."
echo "  hping3: $(which hping3 || echo 'not found')"
echo "  nmap:   $(which nmap || echo 'not found')"
echo "  scapy:  $(python3 -c 'import scapy; print(scapy.VERSION)' 2>/dev/null || echo 'scapy installed')"
