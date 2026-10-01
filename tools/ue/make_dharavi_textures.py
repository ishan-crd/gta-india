#!/usr/bin/env python3
"""Textures for the Mumbai / Dharavi map (system python + PIL, run on the PC):
  T_RainStreaks.png  - tileable vertical rain streaks (white on black) for the camera rain curtain
  T_Neon_01..06.png  - glowing shop signs (Marathi / Hindi / English) for the neon sign boxes
Writes to ~/gta-india/assets/dharavi/.
"""
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = os.path.expanduser("~/gta-india/assets/dharavi")
FONT_DIR = "/usr/share/fonts/truetype/noto"
HI = os.path.join(FONT_DIR, "NotoSansDevanagari-Bold.ttf")
EN = os.path.join(FONT_DIR, "NotoSans-Bold.ttf")
os.makedirs(OUT, exist_ok=True)


def rain_streaks(size=512, n=900, seed=5):
    rng = random.Random(seed)
    im = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(im)
    for _ in range(n):
        x = rng.uniform(0, size)
        y = rng.uniform(0, size)
        ln = rng.uniform(18, 70)
        v = int(rng.uniform(70, 255))
        w = 1 if rng.random() < 0.85 else 2
        for oy in (0, -size, size):          # wrap vertically so the texture tiles
            d.line([(x, y + oy), (x - ln * 0.04, y + ln + oy)], fill=v, width=w)
    im = im.filter(ImageFilter.GaussianBlur(0.6))
    im.convert("RGB").save(os.path.join(OUT, "T_RainStreaks.png"))


SIGNS = [
    # (file, w, h, lines [(text, font, colour)], frame colour, background)
    ("T_Neon_01", 1024, 256, [("गणेश जनरल स्टोर्स", HI, (255, 60, 70))], (255, 40, 60), (18, 8, 10)),
    ("T_Neon_02", 1024, 256, [("शिव वडा पाव", HI, (90, 255, 120))], (60, 255, 140), (6, 16, 10)),
    ("T_Neon_03", 256, 1024, [("REIA", EN, (255, 70, 120))], (255, 60, 110), (16, 6, 10)),
    ("T_Neon_04", 1024, 320, [("लक्ष्मी ज्वेलर्स", HI, (255, 210, 60)), ("LAXMI JEWELLERS", EN, (255, 240, 180))], (255, 200, 40), (16, 12, 4)),
    ("T_Neon_05", 1024, 256, [("मुंबई मोबाइल्स", HI, (80, 200, 255))], (60, 180, 255), (4, 10, 18)),
    ("T_Neon_06", 1024, 320, [("HOTEL SAI KRUPA", EN, (255, 140, 40)), ("शुद्ध शाकाहारी", HI, (255, 220, 160))], (255, 120, 30), (16, 8, 4)),
]


def fit(path, text, max_w, max_h, draw):
    size = max_h
    while size > 10:
        f = ImageFont.truetype(path, size)
        box = draw.textbbox((0, 0), text, font=f)
        if box[2] - box[0] <= max_w and box[3] - box[1] <= max_h:
            return f
        size -= 4
    return ImageFont.truetype(path, 10)


def neon(name, w, h, lines, frame, bg):
    vertical = h > w
    im = Image.new("RGB", (w, h), bg)
    glow = Image.new("RGB", (w, h), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.rectangle([10, 10, w - 11, h - 11], outline=frame, width=10)
    if vertical:
        text = lines[0][0]
        f = ImageFont.truetype(lines[0][1], int(w * 0.62))
        cell = (h - 60) / len(text)
        for i, ch in enumerate(text):
            box = gd.textbbox((0, 0), ch, font=f)
            gd.text(((w - (box[2] - box[0])) / 2 - box[0], 30 + i * cell + (cell - (box[3] - box[1])) / 2 - box[1]), ch, font=f, fill=lines[0][2])
    else:
        n = len(lines)
        band = (h - 40) / n
        for i, (text, font, col) in enumerate(lines):
            f = fit(font, text, w - 90, int(band * (0.78 if i == 0 else 0.6)), gd)
            box = gd.textbbox((0, 0), text, font=f)
            tw, th = box[2] - box[0], box[3] - box[1]
            gd.text(((w - tw) / 2 - box[0], 20 + i * band + (band - th) / 2 - box[1]), text, font=f, fill=col)
    halo = glow.filter(ImageFilter.GaussianBlur(14))
    im = Image.blend(im, halo, 0.55)
    im.paste(glow, (0, 0), glow.convert("L").point(lambda v: 255 if v > 30 else 0))
    im.save(os.path.join(OUT, name + ".png"))


if __name__ == "__main__":
    rain_streaks()
    for s in SIGNS:
        neon(*s)
    print("dharavi textures written to", OUT)
