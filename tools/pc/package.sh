#!/usr/bin/env bash
# Cook + package a Linux Shipping build into ~/gta-india/build
source "$(dirname "$0")/env.sh"
CONFIG=${1:-Shipping}
"$UE/Engine/Build/BatchFiles/RunUAT.sh" BuildCookRun -project="$UPROJECT" -noP4 -platform=Linux \
  -clientconfig=$CONFIG -serverconfig=$CONFIG -map=/Game/Maps/Varanasi+/Game/Maps/Dharavi -build -cook -stage -pak -iostore -archive \
  -archivedirectory=$HOME/gta-india/build -utf8output -unattended 2>&1 | tee "$LOGS/package.log" \
  | grep -E "Error|error:|BUILD SUCCESSFUL|BUILD FAILED|AutomationTool exiting" | tail -30
