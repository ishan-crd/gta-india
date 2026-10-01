"""Inject relative mouse motion into :5 exactly like Selkies (XTest relative MotionNotify) and grab
frames, to check camera look over the stream. Run with Selkies' python (has python-xlib)."""
import subprocess, sys, time
from Xlib import X, display
from Xlib.ext import xtest

d = display.Display(":5")
root = d.screen().root
out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/mprobe"
subprocess.run(["mkdir", "-p", out])

def grab(name):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "x11grab", "-video_size", "1920x1080",
                    "-i", ":5", "-frames:v", "1", "-vf", "scale=640:-1", f"{out}/{name}.jpg"])

def ptr():
    p = root.query_pointer()
    return p.root_x, p.root_y

def move(dx, dy, steps, label):
    for _ in range(steps):
        xtest.fake_input(d, X.MotionNotify, detail=True, root=X.NONE, x=dx, y=dy)
        d.sync()
        time.sleep(1 / 60)
    time.sleep(0.3)
    print(label, "pointer", ptr(), flush=True)
    grab(label)

print("start pointer", ptr())
grab("0_start")
move(4, 0, 60, "1_right")      # 240 px right
move(-4, 0, 60, "2_left")      # back
move(0, -3, 40, "3_up")        # 120 px up
move(0, 3, 80, "4_down")       # 240 px down
move(-8, 0, 60, "5_left_more")
