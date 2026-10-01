#!/usr/bin/env bash
# Run an editor Python script in the full editor (offscreen rendering; needed for level building).
source "$(dirname "$0")/env.sh"
SCRIPT=$(readlink -f "$1"); shift
NAME=$(basename "$SCRIPT" .py)
timeout 3600 "$EDITOR" "$UPROJECT" -ExecutePythonScript="$SCRIPT" -RenderOffScreen -unattended -nosplash -nop4 -NoSound -stdout -FullStdOutLogOutput "$@" 2>&1 \
  | grep -v "^\s*$" > "$LOGS/pyed_$NAME.log" &
PID=$!
# The editor stays open after the script: wait for our completion marker, then kill it.
for i in $(seq 1 3600); do
  if grep -qE "\[GI\] (level saved|DONE)|Traceback" "$LOGS/pyed_$NAME.log" 2>/dev/null; then sleep 5; break; fi
  if ! kill -0 $PID 2>/dev/null; then break; fi
  sleep 1
done
pkill -f "UnrealEditor $UPROJECT -ExecutePythonScript=$SCRIPT" 2>/dev/null
wait $PID 2>/dev/null
grep -E "\[GI\]|Error|Traceback|LogPython: Error" "$LOGS/pyed_$NAME.log" | tail -40
