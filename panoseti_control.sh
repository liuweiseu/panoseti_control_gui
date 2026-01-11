#!/usr/bin/env bash
set -e

CONFIG="${1:-configs/panoseti_config.json}"

if [ ! -f "$CONFIG" ]; then
    echo "Config not found: $CONFIG" >&2
    exit 1
fi

PYTHON=$(jq -r '.["pyqt"]["python_path"]' "$CONFIG")
SCRIPT="main.py"

if [ ! -x "$PYTHON" ]; then
    echo "Python not executable: $PYTHON" >&2
    exit 2
fi

if [ ! -f "$SCRIPT" ]; then
    echo "Script not found: $SCRIPT" >&2
    exit 3
fi

exec "$PYTHON" -u "$SCRIPT"