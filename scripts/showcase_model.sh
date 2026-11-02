#!/usr/bin/env bash
#
# W-SENTRY — run the model showcase (quantitative proof the model detects threats).
# Trains a checkpoint first if none exists, then runs the showcase.
#
#   scripts/showcase_model.sh
#
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -x ".venv/bin/python" ]]; then PY=".venv/bin/python"
elif [[ -x ".venv/Scripts/python.exe" ]]; then PY=".venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then PY="python3"
else PY="python"; fi

if [[ ! -f "data/processed/showcase_eval.json" ]]; then
  echo "[showcase] No trained model found — training one first (a few minutes) ..."
  "$PY" scripts/train_model.py
fi
exec "$PY" scripts/showcase_model.py
