#!/usr/bin/env python3
"""End-to-end stream test: headless Chrome opens the Selkies page, checks video, sends input."""
import os, sys, time
from playwright.sync_api import sync_playwright

PASS = open(os.path.expanduser("~/.secrets/stream_pass")).read().strip()
OUT = "/tmp/gi_stream_test"
os.makedirs(OUT, exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True,
                          args=["--autoplay-policy=no-user-gesture-required", "--use-gl=angle"])
    ctx = b.new_context(http_credentials={"username": "ishan", "password": PASS}, viewport={"width": 1600, "height": 900})
    page = ctx.new_page()
    logs = []
    page.on("console", lambda m: logs.append(m.text))
    page.goto("http://127.0.0.1:8080/", wait_until="load")
    time.sleep(12)
    page.screenshot(path=f"{OUT}/1_loaded.png")
    page.mouse.click(800, 450)
    time.sleep(2)
    page.mouse.click(165, 475)          # KHELO (Play) button (1920x1080 shown at 1600x900)
    time.sleep(1)
    page.keyboard.press("Enter")
    time.sleep(8)
    page.screenshot(path=f"{OUT}/2_after_enter.png")
    page.keyboard.down("w")
    time.sleep(3)
    page.keyboard.up("w")
    time.sleep(1)
    page.screenshot(path=f"{OUT}/3_after_walk.png")
    print("\n".join(logs[-25:]))
    b.close()
