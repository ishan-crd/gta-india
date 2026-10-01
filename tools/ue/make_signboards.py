#!/usr/bin/env python3
"""Generate weathered Hindi + English shop signboard textures (1024x256) for the town buildings.
Plain Python + Pillow (with raqm for Devanagari shaping). Output: ~/gta-india/assets/signs/"""
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = os.path.expanduser("~/gta-india/assets/signs")
FONT_DIR = "/usr/share/fonts/truetype/noto"
HI = os.path.join(FONT_DIR, "NotoSansDevanagari-Bold.ttf")
EN = os.path.join(FONT_DIR, "NotoSans-Bold.ttf")
R = random.Random(5)

SIGNS = [
    ("शर्मा जनरल स्टोर", "SHARMA GENERAL STORE", (180, 20, 20), (255, 230, 60)),
    ("गंगा मेडिकल हॉल", "GANGA MEDICAL HALL", (20, 90, 160), (255, 255, 255)),
    ("बनारसी साड़ी भंडार", "BANARASI SAREE BHANDAR", (120, 20, 60), (255, 210, 80)),
    ("काशी चाय वाला", "KASHI CHAI WALA", (250, 200, 30), (140, 20, 10)),
    ("पान भंडार", "PAAN BHANDAR", (20, 110, 50), (255, 255, 255)),
    ("मोबाइल रिचार्ज", "MOBILE RECHARGE & REPAIR", (230, 230, 225), (200, 20, 20)),
    ("मिश्रा मिठाई", "MISHRA MITHAI", (240, 120, 20), (255, 255, 240)),
    ("शिव टेलर्स", "SHIV TAILORS", (40, 40, 110), (255, 220, 120)),
    ("राम किराना स्टोर", "RAM KIRANA STORE", (200, 40, 30), (255, 255, 255)),
    ("लस्सी कॉर्नर", "LASSI CORNER", (250, 245, 230), (30, 90, 160)),
    ("बाबा फोटो स्टूडियो", "BABA PHOTO STUDIO", (20, 20, 20), (255, 200, 40)),
    ("गुप्ता हार्डवेयर", "GUPTA HARDWARE", (30, 120, 120), (255, 255, 255)),
]


def fit_font(path, text, max_w, start, draw):
    size = start
    while size > 12:
        f = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 4
    return ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)


def weather(img):
    """Dust, sun fade, rust streaks and a dirty border."""
    w, h = img.size
    over = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    for _ in range(900):
        x, y = R.randrange(w), R.randrange(h)
        r = R.randint(1, 6)
        c = R.choice([(90, 70, 50, R.randint(20, 70)), (240, 230, 210, R.randint(10, 50))])
        d.ellipse((x - r, y - r, x + r, y + r), fill=c)
    for _ in range(14):
        x = R.randrange(w)
        d.rectangle((x, R.randrange(h // 2), x + R.randint(2, 5), h), fill=(110, 60, 30, R.randint(25, 70)))
    d.rectangle((0, 0, w - 1, h - 1), outline=(60, 45, 30, 200), width=10)
    img = Image.alpha_composite(img.convert("RGBA"), over.filter(ImageFilter.GaussianBlur(1.2)))
    fade = Image.new("RGBA", (w, h), (235, 215, 180, 40))
    return Image.alpha_composite(img, fade).convert("RGB")


def main():
    os.makedirs(OUT, exist_ok=True)
    for i, (hi, en, bg, fg) in enumerate(SIGNS):
        img = Image.new("RGB", (1024, 256), bg)
        d = ImageDraw.Draw(img)
        fh = fit_font(HI, hi, 960, 128, d)
        fe = fit_font(EN, en, 900, 46, d)
        tw = d.textlength(hi, font=fh)
        d.text(((1024 - tw) / 2, 8), hi, font=fh, fill=fg, stroke_width=2, stroke_fill=(0, 0, 0))
        te = d.textlength(en, font=fe)
        d.text(((1024 - te) / 2, 182), en, font=fe, fill=fg)
        phone = f"Mob: 9{R.randint(100000000, 999999999)}"
        d.text((24, 226), phone, font=ImageFont.truetype(EN, 20), fill=fg)
        weather(img).save(os.path.join(OUT, f"T_Sign_{i:02d}.png"))
        print("sign", i, en)


main()
