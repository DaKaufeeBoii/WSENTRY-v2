#!/usr/bin/env bash
#
# W-SENTRY — launch the Streamlit SOC dashboard (detector side).
#
# Starts the six-tab Security Operations Center at http://localhost:8501.
# On Windows, run this from WSL or use:  python -m streamlit run src/dashboard/app.py
#
# Usage:
#   scripts/run_dashboard.sh [--port 8501] [--headless]
#
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PORT=8501
HEADLESS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)      PORT="$2"; shift 2 ;;
    --headless)  HEADLESS="--server.headless true"; shift ;;
    -h|--help)
      grep '^#' "$0" | grep -v '^#!' | sed 's/^#//'; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# Pick a Python interpreter: project venv if present, else python3/python.
if [[ -x ".venv/bin/python" ]]; then
  PY=".venv/bin/python"
elif [[ -x ".venv/Scripts/python.exe" ]]; then
  PY=".venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  PY="python"
fi

echo "[W-SENTRY] Python: $PY"
if ! "$PY" -c "import streamlit" >/dev/null 2>&1; then
  echo "[W-SENTRY] Streamlit not found. Install Phase 3 deps:" >&2
  echo "           $PY -m pip install -r requirements_phase3.txt" >&2
  exit 1
fi

# Warn if the model checkpoint is missing or still the untrained scaffold.
if [[ ! -f "models/saved/hybrid_model.pt" ]]; then
  echo "[W-SENTRY] WARNING: models/saved/hybrid_model.pt not found."
  echo "           Train a real checkpoint first:  $PY scripts/train_model.py"
fi

echo "[W-SENTRY] Launching SOC dashboard on http://localhost:${PORT} ..."
exec "$PY" -m streamlit run src/dashboard/app.py \
  --server.port "$PORT" $HEADLESS
