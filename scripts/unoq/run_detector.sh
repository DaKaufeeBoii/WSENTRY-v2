#!/usr/bin/env bash
# Start W-SENTRY on the UNO Q with the real kernel firewall. Ctrl+C stops it and removes its rules.
#   bash ~/w-sentry/scripts/unoq/run_detector.sh                  (P4)
#   bash ~/w-sentry/scripts/unoq/run_detector.sh --lights bridge  (after P5)
cd "$HOME/w-sentry"
exec sudo "$HOME/w-sentry/.venv/bin/python" scripts/detector_server.py --enforce iptables --threads 4 "$@"
