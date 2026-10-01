"""gi_box_texture.py - 1024 px atlas for SM_DeliveryBox (python3 + PIL). python3 gi_box_texture.py OUT.png
Red insulated delivery backpack (Zomato style): red nylon, black piping on every edge, white wordmark on the
outward face and both sides, black webbing straps.
UV atlas (v up):  [0,.5]x[.5,1] = outward face (+Y, logo)   [.5,1]x[.5,1] = side faces (+-X)
                  [0,.5]x[0,.5] = top/bottom/back (+-Z, -Y)  [.5,1]x[0,.5] = straps / handle (black webbing)
All regions map box height z in [-0.22, 0.22] linearly to the region's v range.
"""
import random
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = 1024
H = S // 2
RED = (196, 22, 32)
RED_DARK = (150, 14, 22)
PIPING = (22, 20, 20)
WHITE = (246, 244, 240)
FONT = "/usr/share/fonts/truetype/ubuntu/Ubuntu-BI.ttf"

im = Image.new("RGB", (S, S), RED)
d = ImageDraw.Draw(im)


def panel(x0, y0, pocket=False):
    """One face: red nylon with black piping all round (the bag's sewn edges) and soft panel shading."""
    d.rectangle([x0, y0, x0 + H - 1, y0 + H - 1], fill=RED)
    # gentle vertical shading / puffiness
    for i in range(40):
        a = int(18 * (1 - i / 40))
        d.rectangle([x0 + i, y0 + i, x0 + H - 1 - i, y0 + H - 1 - i], outline=(RED[0] - a // 2, RED[1], RED[2]))
    d.rectangle([x0, y0, x0 + H - 1, y0 + H - 1], outline=PIPING, width=16)
    if pocket:
        # side pocket with its own piping + zip line
        d.rounded_rectangle([x0 + 70, y0 + 250, x0 + H - 70, y0 + H - 40], radius=26, fill=RED_DARK, outline=PIPING, width=10)
        d.line([x0 + 95, y0 + 285, x0 + H - 95, y0 + 285], fill=(40, 40, 42), width=6)


def wordmark(x0, y0, size, cy):
    f = ImageFont.truetype(FONT, size)
    txt = "zomato"
    w = d.textlength(txt, font=f)
    d.text((x0 + (H - w) / 2, y0 + cy), txt, font=f, fill=WHITE)


panel(0, 0)                    # outward face
wordmark(0, 0, 128, 170)
panel(H, 0, pocket=True)       # sides
wordmark(H, 0, 92, 120)
panel(0, H)                    # top / bottom / back
# top flap seam + buckle strap running over the lid (centre column of the region)
d.rectangle([0 + H // 2 - 22, H, H // 2 + 22, S - 1], fill=PIPING)
d.rounded_rectangle([H // 2 - 34, H + 300, H // 2 + 34, H + 360], radius=8, fill=(30, 30, 32), outline=(90, 90, 95), width=4)
# straps / handle: black webbing with a woven texture
d.rectangle([H, H, S - 1, S - 1], fill=(26, 26, 28))
for yy in range(H, S, 5):
    d.line([H, yy, S - 1, yy], fill=(40, 40, 43))
for xx in range(H, S, 9):
    d.line([xx, H, xx, S - 1], fill=(33, 33, 36))

# nylon weave noise + a little grime at the bottom
random.seed(3)
px = im.load()
for _ in range(90000):
    x, y = random.randrange(S), random.randrange(S)
    r, g, b = px[x, y]
    k = random.randint(-9, 9)
    px[x, y] = (max(0, min(255, r + k)), max(0, min(255, g + k)), max(0, min(255, b + k)))
for x0, y0 in ((0, 0), (H, 0)):
    for yy in range(y0 + H - 70, y0 + H):
        t = (yy - (y0 + H - 70)) / 70.0
        for xx in range(x0, x0 + H, 2):
            r, g, b = px[xx, yy]
            px[xx, yy] = (int(r * (1 - 0.22 * t)), int(g * (1 - 0.18 * t)), int(b * (1 - 0.18 * t)))
im = im.filter(ImageFilter.SMOOTH)
im.save(sys.argv[1])
print("saved", sys.argv[1])
