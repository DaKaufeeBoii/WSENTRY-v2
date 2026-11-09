#!/usr/bin/env bash
# One-time setup ON the UNO Q (Linux side). Run in an interactive shell: it asks for the
# arduino password (sudo).   bash ~/w-sentry/scripts/unoq/setup_board.sh
set -euo pipefail
cd "$HOME/w-sentry"
echo "== system packages"
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip iptables
echo "== python venv"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install numpy msgpack pandas
# CPU-only wheel. The plain PyPI torch for aarch64 may pull GBs of CUDA packages.
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
echo "== versions"
uname -m
python3 -V
.venv/bin/python -c "import torch, numpy; print('torch', torch.__version__, 'numpy', numpy.__version__, 'threads', torch.get_num_threads())"
echo "== model smoke test"
.venv/bin/python -c "import sys; sys.path.insert(0, '.'); from src.live.inference import InferenceEngine; InferenceEngine(); print('model OK')"
