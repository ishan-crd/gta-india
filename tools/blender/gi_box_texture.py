"""gi_box_texture.py - 1024 px atlas for SM_DeliveryBox (python3 + PIL). python3 gi_box_texture.py OUT.png
UV atlas (v up):  [0,.5]x[.5,1] = outward face (+Y, text)   [.5,1]x[.5,1] = side faces (+-X)
                  [0,.5]x[0,.5] = top/bottom/back (+-Z, -Y)  [.5,1]x[0,.5] = straps (dark webbing)
All regions map box height z in [-0.22, 0.22] linearly to the region's v range, so the band wraps around.
"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random
S = 1024; H = S // 2
YEL = (242, 194, 0); DARK = (176, 128, 0); INK = (40, 28, 6)
im = Image.new("RGB", (S, S), YEL)
d = ImageDraw.Draw(im)
BAND = (0.36, 0.52)   # band as fraction of box height from bottom


def region(x0, y0, band=True):
    # y0 = top pixel row of a 512 region (image rows go down; v goes up)
    d.rectangle([x0, y0, x0 + H - 1, y0 + H - 1], fill=YEL)
    if band:
        top = y0 + int(H * (1 - BAND[1])); bot = y0 + int(H * (1 - BAND[0]))
        d.rectangle([x0, top, x0 + H - 1, bot], fill=DARK)
        d.rectangle([x0, top - 6, x0 + H - 1, top - 1], fill=(250, 235, 200))   # reflective piping
        d.rectangle([x0, bot + 1, x0 + H - 1, bot + 6], fill=(250, 235, 200))


region(0, 0)          # outward face (u 0..0.5, v 0.5..1 -> rows 0..511)
region(H, 0)          # sides
region(0, H, band=False)
# straps: dark webbing
d.rectangle([H, H, S - 1, S - 1], fill=(38, 38, 40))
for yy in range(H, S, 6):
    d.line([H, yy, S - 1, yy], fill=(52, 52, 55))
f1 = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf", 92)
f2 = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf", 34)


def ctext(txt, font, cy, fill, x0=0):
    w = d.textlength(txt, font=font)
    d.text((x0 + (H - w) / 2, cy), txt, font=font, fill=fill)


ctext("GANGA", f1, 40, INK)
ctext("EXPRESS", f1, 140, INK)
bt = int(H * (1 - BAND[1]))
ctext("VARANASI  FOOD DELIVERY", f2, bt + 18, (255, 240, 200))
# thin dark border on faces for a seam look
for x0, y0 in ((0, 0), (H, 0), (0, H)):
    d.rectangle([x0 + 4, y0 + 4, x0 + H - 5, y0 + H - 5], outline=(200, 150, 0), width=5)
# subtle fabric noise
random.seed(3)
px = im.load()
for _ in range(60000):
    x, y = random.randrange(S), random.randrange(S)
    r, g, b = px[x, y]; k = random.randint(-10, 10)
    px[x, y] = (max(0, min(255, r + k)), max(0, min(255, g + k)), max(0, min(255, b + k)))
im.save(sys.argv[1])
print("saved", sys.argv[1])
