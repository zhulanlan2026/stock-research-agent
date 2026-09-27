#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COLLECTOR_DIR="$PROJECT_DIR/apps/akshare-collector"
PYTHON="$PROJECT_DIR/.venv/bin/python"

if pgrep -f "akshare_collector.main" >/dev/null 2>&1; then
    echo "collector is already running"
    exit 0
fi

if command -v tmux >/dev/null 2>&1; then
    tmux new-session -d -s akshare-collector \
        "cd '$COLLECTOR_DIR' && exec '$PYTHON' -m akshare_collector.main >> collector.log 2>&1"
    echo "collector started in tmux session 'akshare-collector'"
else
    cd "$COLLECTOR_DIR"
    nohup "$PYTHON" -m akshare_collector.main >> collector.log 2>&1 &
    echo "collector started with nohup (pid $!)"
fi
