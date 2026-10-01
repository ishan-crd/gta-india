#!/usr/bin/env bash
# Compile the game module for the editor.
source "$(dirname "$0")/env.sh"
"$UE/Engine/Build/BatchFiles/Linux/Build.sh" GTAIndiaEditor Linux Development -Project="$UPROJECT" -WaitMutex 2>&1 | tee "$LOGS/build_editor.log" | grep -E "error|warning: unused|Result:|Total execution" | tail -60
