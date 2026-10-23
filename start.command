#!/bin/sh
cd "$(dirname "$0")" || exit 1
export LABWISE_PORT="${LABWISE_PORT:-8001}"
printf 'Open http://127.0.0.1:%s/pilot.html\n' "$LABWISE_PORT"
python3 server.py
