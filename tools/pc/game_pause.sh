#!/usr/bin/env bash
# Pause / resume the streamed game (frees the GPU for editor screenshots): game_pause.sh stop|cont
PID=$(pgrep -f '^/home/[^ ]*/GTAIndia-Linux-Shipping')
[ -n "$PID" ] && kill -"${1:-STOP}" $PID && echo "game $1 $PID"
