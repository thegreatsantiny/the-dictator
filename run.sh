#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOGGLE_FILE="/tmp/voice-dictation.toggle"
PID_FILE="/tmp/voice-dictation.pid"
DEBUG_LOG="/tmp/vd_run_debug.log"

echo "$(date '+%Y-%m-%d %H:%M:%S') - run.sh invoked" >> "$DEBUG_LOG"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Process $PID found, sending toggle" >> "$DEBUG_LOG"
        touch "$TOGGLE_FILE"
        exit 0
    fi
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') - No process found, starting new" >> "$DEBUG_LOG"

cd "$SCRIPT_DIR"
source .env
export GROQ_API_KEY

PYTHON="$SCRIPT_DIR/venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="python3"

nohup "$PYTHON" voice-dictation.py > /dev/null 2>&1 &
