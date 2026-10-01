#!/usr/bin/env bash
# Run an editor Python script headless: ue_python.sh <script.py> [extra editor args]
source "$(dirname "$0")/env.sh"
SCRIPT=$(readlink -f "$1"); shift
NAME=$(basename "$SCRIPT" .py)
"$EDITOR_CMD" "$UPROJECT" -run=pythonscript -script="$SCRIPT" -unattended -nosplash -nop4 -NoSound -stdout -FullStdOutLogOutput "$@" 2>&1 \
  | grep -v "^\s*$" > "$LOGS/py_$NAME.log"
echo "exit=$?  log=$LOGS/py_$NAME.log"
grep -E "\[GI\]|Error|error:|Traceback|LogPython: Error" "$LOGS/py_$NAME.log" | tail -40
