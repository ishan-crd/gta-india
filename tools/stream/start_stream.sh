#!/usr/bin/env bash
# Start GTA India streaming on the Linux PC:
#   1. a private headless X screen (:5) on the RTX 3090 (never touches the physical monitor / VTs)
#   2. Selkies (browser streaming, NVENC H.264, input only into :5 via XTEST, virtual gamepads)
#   3. the packaged game, relaunched automatically if it exits
# On the Mac: ssh -f -N -L 8080:127.0.0.1:8080 linux, then open http://localhost:8080
# (user: ishan, password in ~/.secrets/stream_pass on the PC).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
GAME=${GAME:-$HOME/gta-india/build/Linux/GTAIndia.sh}
STREAM_DIR=$HOME/gta-india/stream
LOGS=$HOME/gta-india/logs
export XDG_RUNTIME_DIR=/tmp/gi-xdg
mkdir -p "$XDG_RUNTIME_DIR" "$LOGS" "$HOME/.secrets"
chmod 700 "$XDG_RUNTIME_DIR"

if [ ! -s "$HOME/.secrets/stream_pass" ]; then
  python3 -c "import secrets; print(secrets.token_urlsafe(9))" > "$HOME/.secrets/stream_pass"
  chmod 600 "$HOME/.secrets/stream_pass"
fi
PASS=$(cat "$HOME/.secrets/stream_pass")

# 1. Headless X
if ! DISPLAY=:5 xdpyinfo >/dev/null 2>&1; then
  sudo cp "$HERE/xorg-gi.conf" /etc/X11/xorg-gi.conf
  sudo nohup Xorg :5 -config xorg-gi.conf -sharevts -novtswitch -nolisten tcp -noreset -logfile /tmp/Xorg.gi.log >/dev/null 2>&1 &
  for i in $(seq 1 20); do DISPLAY=:5 xdpyinfo >/dev/null 2>&1 && break; sleep 0.5; done
fi
# Anyone on the machine may render to it (the X server runs as root).
DISPLAY=:5 xhost +SI:localuser:"$USER" >/dev/null 2>&1 || true
DISPLAY=:5 xset s off -dpms >/dev/null 2>&1 || true
# The headless screen can come up at the driver's maximum (8192x4096) after a reboot: the game would then
# sit in a corner of a huge black desktop in the stream. Pin it to the game resolution.
DISPLAY=:5 xrandr --fb 1920x1080 >/dev/null 2>&1 || true

# Patch Selkies for mouse look (see patch_selkies.py): absolute browser moves become deltas while the
# game hides the cursor, and a plain click grabs pointer lock.
python3 "$HERE/patch_selkies.py" "$STREAM_DIR/squashfs-root" || true
CORE=$(ls "$STREAM_DIR"/squashfs-root/usr/conda/lib/python3.*/site-packages/selkies/selkies_web/assets/selkies-core-*.js 2>/dev/null | head -1)

# 2. Selkies (bound to localhost; reached through the SSH tunnel)
if [ "$(curl -s -o /dev/null -w "%{http_code}" -u "ishan:$PASS" http://127.0.0.1:8080/)" != "200" ]; then
  fuser -k 8080/tcp >/dev/null 2>&1; sleep 1
  # NVIDIA's NvFBC capture must share the system libxcb; the AppImage's bundled copy corrupts its
  # mutexes (glibc tpp.c assertion as soon as a client connects). Preload the system one.
  (cd "$STREAM_DIR" && DISPLAY=:5 LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libxcb.so.1 nohup ./squashfs-root/AppRun --addr 127.0.0.1 --port 8080 --encoder h264enc --enable-resize false --web-root "$(dirname "$(dirname "$CORE")")" \
     --enable-basic-auth true --basic-auth-user ishan --basic-auth-password "$PASS" \
     > "$LOGS/selkies.log" 2>&1 < /dev/null &)
  sleep 8
fi

# 3. Game loop (Selkies starts a PulseAudio server under XDG_RUNTIME_DIR for audio)
if ! tmux has-session -t gtagame 2>/dev/null; then
  # Selkies hands browser gamepads to the game through its interposer (no kernel uinput devices).
  INTERPOSER=$STREAM_DIR/squashfs-root/usr/lib/selkies_input_interposer.so
  tmux new-session -d -s gtagame "while true; do DISPLAY=:5 PULSE_SERVER=unix:$XDG_RUNTIME_DIR/pulse/native LD_PRELOAD=$INTERPOSER \
    $GAME -ResX=1920 -ResY=1080 -FullScreen -NoSplash > $LOGS/game.log 2>&1; sleep 2; done"
fi

echo "Stream up on 127.0.0.1:8080 (tunnel: ssh -f -N -L 8080:127.0.0.1:8080 linux)"
