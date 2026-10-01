"""contact_sheet.py - tile preview PNGs into labelled sheets for quick review (dev helper, python3 + PIL)."""
import sys, os, glob
from PIL import Image, ImageDraw
src, dst = sys.argv[1], sys.argv[2]
names = sys.argv[3].split(',') if len(sys.argv) > 3 and sys.argv[3] else sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(src, '*.png')))
cols, rows, s = 4, 3, 384
os.makedirs(dst, exist_ok=True)
for k in range(0, len(names), cols * rows):
    sheet = Image.new('RGB', (cols * s, rows * s), (30, 30, 30))
    d = ImageDraw.Draw(sheet)
    for i, n in enumerate(names[k:k + cols * rows]):
        p = os.path.join(src, n + '.png')
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert('RGB').resize((s, s))
        x, y = (i % cols) * s, (i // cols) * s
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + s, y + 16], fill=(0, 0, 0))
        d.text((x + 4, y + 2), n, fill=(255, 255, 255))
    sheet.save(os.path.join(dst, 'sheet_%02d.png' % (k // (cols * rows))))
print('ok')
