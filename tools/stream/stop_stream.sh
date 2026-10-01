#!/usr/bin/env bash
# Stop the game loop and Selkies (leaves the headless X screen running; it idles at ~0% GPU).
tmux kill-session -t gtagame 2>/dev/null
pkill -f "[G]TAIndia-Linux-Shipping" 2>/dev/null
fuser -k 8080/tcp >/dev/null 2>&1
echo "stopped"
