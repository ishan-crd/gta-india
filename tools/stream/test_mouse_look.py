#!/usr/bin/env python3
"""Mouse-look over the stream: headless Chrome (no pointer lock, so Selkies sends absolute positions)
moves the mouse in small steps; frames are grabbed from :5 to check the camera turns smoothly
instead of spinning / pinning to a top-down view."""
import os, subprocess, time
from playwright.sync_api import sync_playwright

PASS = open(os.path.expanduser("~/.secrets/stream_pass")).read().strip()
OUT = "/tmp/gi_mouse_test"
os.makedirs(OUT, exist_ok=True)


def grab(name):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "x11grab", "-video_size", "1920x1080", "-i", ":5",
                    "-frames:v", "1", "-vf", "scale=480:-1", f"{OUT}/{name}.jpg"], env={**os.environ, "DISPLAY": ":5"})


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True,
                          args=["--autoplay-policy=no-user-gesture-required", "--use-gl=angle"])
    ctx = b.new_context(http_credentials={"username": "ishan", "password": PASS}, viewport={"width": 1600, "height": 900})
    page = ctx.new_page()
    page.goto("http://127.0.0.1:8080/", wait_until="load")
    time.sleep(10)
    x, y = 800, 700
    page.mouse.move(x, y)
    time.sleep(1)
    grab("0_start")

    def drag(dx, dy, steps, name):
        global x, y
        for _ in range(steps):
            x += dx
            y += dy
            page.mouse.move(x, y)
            time.sleep(1 / 60)
        time.sleep(0.5)
        grab(name)

    drag(2, 0, 60, "1_right120")
    drag(-2, 0, 60, "2_left120")
    drag(0, -2, 40, "3_up80")
    drag(0, 2, 40, "4_down80")
    drag(0, -2, 180, "5_up360")
    drag(3, 0, 120, "6_right360")
    print("pointer lock:", page.evaluate("!!document.pointerLockElement"))
    b.close()
print("frames in", OUT)
