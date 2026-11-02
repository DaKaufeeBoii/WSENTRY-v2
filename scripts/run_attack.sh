#!/usr/bin/env bash
#
# W-SENTRY — launch a single simulated attack against the detector (attacker side).
#
# This is a thin, safety-guarded wrapper around `python -m src.attack.runner`.
# It is for AUTHORIZED lab use only: run it against your own detector laptop on a
# private LAN as part of the W-SENTRY two-machine demo. It refuses public targets.
#
# Scenarios:
#   syn-flood   TCP SYN flood           -> detected as DoS_Flood
#   udp-flood   UDP flood               -> detected as DoS_Flood
#   icmp-flood  ICMP (ping) flood       -> detected as DoS_Flood
#   port-scan   Nmap SYN stealth scan   -> detected as Intrusion_Probe
#   os-scan     Nmap OS/version scan    -> detected as Intrusion_Probe
#   arp-spoof   ARP cache poisoning     -> detected as Spoofing
#
# Usage:
#   scripts/run_attack.sh <scenario> --target <IP> [extra runner args...]
#   scripts/run_attack.sh syn-flood  --target 192.168.1.100 --duration 30 --rate 200
#   scripts/run_attack.sh port-scan  --target 192.168.1.100 --ports 1-1024
#   scripts/run_attack.sh arp-spoof  --target 192.168.1.100 --gateway 192.168.1.1
#
# Env:
#   WSENTRY_YES=1   skip the confirmation prompt (for scripted demos)
#
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

usage() { grep '^#' "$0" | grep -v '^#!' | sed 's/^#//'; }

[[ $# -lt 1 ]] && { usage; exit 1; }
SCENARIO="$1"; shift

case "$SCENARIO" in
  syn-flood|udp-flood|icmp-flood|port-scan|os-scan|arp-spoof) ;;
  -h|--help) usage; exit 0 ;;
  *) echo "[run_attack] Unknown scenario: $SCENARIO" >&2; usage; exit 1 ;;
esac

# Extract --target for the safety check (kept in the args passed through).
TARGET=""
ARGS=("$@")
for ((i=0; i<${#ARGS[@]}; i++)); do
  [[ "${ARGS[$i]}" == "--target" ]] && TARGET="${ARGS[$((i+1))]:-}"
done

if [[ -z "$TARGET" ]]; then
  echo "[run_attack] --target <IP> is required." >&2
  usage; exit 1
fi

# Refuse anything that is not a private/loopback IPv4 address — lab use only.
is_private() {
  local ip="$1"
  [[ "$ip" =~ ^10\. ]] && return 0
  [[ "$ip" =~ ^192\.168\. ]] && return 0
  [[ "$ip" =~ ^172\.(1[6-9]|2[0-9]|3[0-1])\. ]] && return 0
  [[ "$ip" =~ ^127\. ]] && return 0
  [[ "$ip" == "localhost" ]] && return 0
  return 1
}
if ! is_private "$TARGET"; then
  echo "[run_attack] REFUSED: '$TARGET' is not a private LAN / loopback address." >&2
  echo "             W-SENTRY attack simulations are for your own lab network only" >&2
  echo "             (10.x, 172.16-31.x, 192.168.x, 127.x)." >&2
  exit 2
fi

# Confirm aggressive floods unless WSENTRY_YES=1.
case "$SCENARIO" in
  syn-flood|udp-flood|icmp-flood|arp-spoof)
    if [[ "${WSENTRY_YES:-0}" != "1" ]]; then
      echo "[run_attack] About to run '$SCENARIO' against $TARGET on your LAN."
      read -r -p "            Proceed? [y/N] " ans
      [[ "$ans" =~ ^[Yy]$ ]] || { echo "[run_attack] Aborted."; exit 0; }
    fi
    ;;
esac

# Pick interpreter.
if [[ -x ".venv/bin/python" ]]; then PY=".venv/bin/python"
elif [[ -x ".venv/Scripts/python.exe" ]]; then PY=".venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then PY="python3"
else PY="python"; fi

echo "[run_attack] $SCENARIO -> $TARGET"
echo "[run_attack] python -m src.attack.runner $SCENARIO $*"
exec "$PY" -m src.attack.runner "$SCENARIO" "$@"
