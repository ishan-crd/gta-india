#!/usr/bin/env bash
# Render gameplay screenshots headless: shots.sh <shots.txt> [editor|packaged] [Map]  (Map default: Varanasi)
source "$(dirname "$0")/env.sh"
LIST=$(readlink -f "$1")
DIR=$(dirname "$LIST"); rm -rf "$DIR/out"; mkdir -p "$DIR/out"
if [ "${2:-editor}" = "packaged" ]; then
  BIN=~/gta-india/build/Linux/GTAIndia.sh
  timeout 2400 "$BIN" ${3:+/Game/Maps/$3} -RenderOffScreen -ResX=1920 -ResY=1080 -Windowed -GIShots="$LIST" -NoSound -log > "$LOGS/shots.log" 2>&1
else
  timeout 2400 "$EDITOR" "$UPROJECT" /Game/Maps/${3:-Varanasi} -game -RenderOffScreen -ResX=1920 -ResY=1080 -Windowed -GIShots="$LIST" -NoSound -unattended -log > "$LOGS/shots.log" 2>&1
fi
ls -la "$DIR/out"
