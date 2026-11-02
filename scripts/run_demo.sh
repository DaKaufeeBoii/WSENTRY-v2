#!/usr/bin/env bash
#
# W-SENTRY — scripted live attack showcase (attacker side).
#
# Runs a timed sequence of simulated attacks against the detector so the SOC
# dashboard visibly lights up each threat class and the mitigation engine blocks
# the source IP. Run the dashboard on the detector first:
#   scripts/run_dashboard.sh         (then Live Monitor tab -> Start Capture)
#
# AUTHORIZED lab use only — target must be your own detector on a private LAN.
#
# Usage:
#   scripts/run_demo.sh --target <DETECTOR_IP> [--gateway <GW_IP>] [--duration 25]
#   WSENTRY_YES=1 scripts/run_demo.sh --target 192.168.1.100 --gateway 192.168.1.1
#
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
HERE="$(dirname "${BASH_SOURCE[0]}")"

TARGET=""
GATEWAY=""
DURATION=25
GAP=8   # seconds of quiet between scenarios so classes are distinguishable

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)   TARGET="$2"; shift 2 ;;
    --gateway)  GATEWAY="$2"; shift 2 ;;
    --duration) DURATION="$2"; shift 2 ;;
    --gap)      GAP="$2"; shift 2 ;;
    -h|--help)  grep '^#' "$0" | grep -v '^#!' | sed 's/^#//'; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

[[ -z "$TARGET" ]] && { echo "[run_demo] --target <DETECTOR_IP> required." >&2; exit 1; }

# Non-interactive: the per-scenario confirmation would stall the sequence.
export WSENTRY_YES=1

banner() {
  echo ""
  echo "############################################################"
  echo "# $1"
  echo "############################################################"
}

banner "W-SENTRY LIVE DEMO  ->  target=$TARGET  duration=${DURATION}s"
echo "Make sure the detector dashboard is capturing before you continue."
read -r -p "Press Enter to begin the attack sequence... " _ || true

banner "1/4  DoS — TCP SYN Flood   (expect: DoS_Flood, IP BLOCKED)"
"$HERE/run_attack.sh" syn-flood --target "$TARGET" --duration "$DURATION" --rate 200 || true
sleep "$GAP"

banner "2/4  Recon — Stealth Port Scan   (expect: Intrusion_Probe)"
"$HERE/run_attack.sh" port-scan --target "$TARGET" --ports 1-1024 || true
sleep "$GAP"

banner "3/4  DoS — UDP Flood   (expect: DoS_Flood, IP BLOCKED)"
"$HERE/run_attack.sh" udp-flood --target "$TARGET" --duration "$DURATION" || true
sleep "$GAP"

if [[ -n "$GATEWAY" ]]; then
  banner "4/4  MITM — ARP Cache Poisoning   (expect: Spoofing)"
  "$HERE/run_attack.sh" arp-spoof --target "$TARGET" --gateway "$GATEWAY" --duration "$DURATION" || true
else
  banner "4/4  ARP spoof skipped (no --gateway provided)"
fi

banner "DEMO COMPLETE"
echo "Review the detector's Live Monitor + Connection Profiler & Mitigation tabs."
echo "Teardown: on the detector, click 'Clear All Rules' then 'Stop Capture'."
