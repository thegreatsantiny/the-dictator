#!/bin/bash
TOGGLE_FILE="/tmp/voice-dictation.toggle"
DEBUG_LOG="/tmp/vd_run_debug.log"

echo "$(date '+%Y-%m-%d %H:%M:%S') - run.sh invoked" >> "$DEBUG_LOG"

if pgrep -f "voice-dictation.py" > /dev/null 2>&1; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Process found, sending toggle" >> "$DEBUG_LOG"
    touch "$TOGGLE_FILE"
    exit 0
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') - No process found, starting new" >> "$DEBUG_LOG"

cd /home/shaun/Builds/The-Dictator
export GROQ_API_KEY="your-api-key-here"
nohup python3 voice-dictation.py > /dev/null 2>&1 &
