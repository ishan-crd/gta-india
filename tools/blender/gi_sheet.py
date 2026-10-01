"""gi_sheet.py - compose gi_contact renders into a labelled grid (rows=characters, cols=anims). python3 + PIL.
python3 gi_sheet.py DIR OUT.png SK_A,SK_B rest,A_Walk [cell]
"""
import sys, os
from PIL import Image, ImageDraw
src, dst, chars, anims = sys.argv[1], sys.argv[2], sys.argv[3].split(","), sys.argv[4].split(",")
s = int(sys.argv[5]) if len(sys.argv) > 5 else 256
lab = 110
sheet = Image.new("RGB", (lab + len(anims) * s, 20 + len(chars) * s), (25, 25, 25))
d = ImageDraw.Draw(sheet)
for j, an in enumerate(anims):
    d.text((lab + j * s + 4, 4), an, fill=(255, 255, 255))
for i, c in enumerate(chars):
    d.text((4, 20 + i * s + s // 2), c, fill=(255, 255, 255))
    for j, an in enumerate(anims):
        p = os.path.join(src, f"{c}__{an}.png")
        if os.path.exists(p):
            sheet.paste(Image.open(p).convert("RGB").resize((s, s)), (lab + j * s, 20 + i * s))
os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
sheet.save(dst)
print("sheet", dst, sheet.size)
