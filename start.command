#!/bin/sh
cd "$(dirname "$0")" || exit 1
export LABWISE_PORT="${LABWISE_PORT:-8001}"
if [ -x .venv/bin/python ]; then
  exec .venv/bin/python launcher.py "$@"
else
  exec python3 launcher.py "$@"
fi
