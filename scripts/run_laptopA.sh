#!/usr/bin/env bash
# W-SENTRY demo — laptop A (detector). Starts the live model server and the
# dashboard together, and stops both on Ctrl+C. Run from anywhere:
#   bash scripts/run_laptopA.sh
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Pick the project venv python (it has torch); fall back to system python.
if [ -x ".venv/Scripts/python.exe" ]; then PY=".venv/Scripts/python.exe"
elif [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"
else PY="python"; fi

echo "W-SENTRY laptop A"
echo "  repo:   $ROOT"
echo "  python: $PY"
echo

# One-time firewall rules (need admin; ignored if they fail or already exist).
if command -v netsh >/dev/null 2>&1; then
  netsh advfirewall firewall add rule name="W-SENTRY model" dir=in action=allow protocol=TCP localport=8000 >/dev/null 2>&1 \
    && echo "firewall: TCP 8000 allowed" || echo "firewall: TCP 8000 rule not added (run as admin once if laptop B can't connect)"
  netsh advfirewall firewall add rule name="W-SENTRY discovery" dir=in action=allow protocol=UDP localport=50505 >/dev/null 2>&1 \
    && echo "firewall: UDP 50505 allowed" || echo "firewall: UDP 50505 rule not added (run as admin once if discovery fails)"
  echo
fi

# Start the live model server (port 8000) in the background.
echo "starting detector (model server) on port 8000 ..."
"$PY" scripts/detector_server.py &
DET=$!

# Stop both when this script is interrupted.
cleanup() {
  echo
  echo "stopping ..."
  kill "$DET" 2>/dev/null
}
trap cleanup EXIT INT TERM

# Start the dashboard (port 5173) in the foreground; Ctrl+C stops everything.
echo "starting dashboard on port 5173 (Ctrl+C to stop both) ..."
echo
npm --prefix frontend run dev
