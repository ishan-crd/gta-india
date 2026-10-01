#!/usr/bin/env python3
"""hue_variants.py <src.png> <out_dir> <base> : recolour the saturated yellow/orange (saree) band."""
import os
import sys

import numpy as np
from PIL import Image

HUES = {"Saffron": 24, "Red": 0, "Green": 125, "Blue": 220, "Magenta": 315}
src, out_dir, base = sys.argv[1:4]
a = np.asarray(Image.open(src).convert("RGB")).astype(np.float32) / 255.0
mx, mn = a.max(-1), a.min(-1)
d = mx - mn + 1e-6
r, g, b = a[..., 0], a[..., 1], a[..., 2]
h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60.0
s = d / (mx + 1e-6)
mask = (h > 36) & (h < 75) & (s > 0.35) & (mx > 0.25)
os.makedirs(out_dir, exist_ok=True)
for name, hue in HUES.items():
    hh = np.where(mask, hue, h) / 60.0
    c = mx * s
    x = c * (1 - np.abs(hh % 2 - 1))
    z = np.zeros_like(c)
    sec = np.floor(hh).astype(int) % 6
    rgb = np.stack([np.choose(sec, [c, x, z, z, x, c]), np.choose(sec, [x, c, c, x, z, z]), np.choose(sec, [z, z, x, c, c, x])], -1) + (mx - c)[..., None]
    rgb = np.where(mask[..., None], rgb, a)
    p = os.path.join(out_dir, f"{base}_{name}.png")
    Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).save(p)
    print(p)
print("masked_fraction", float(mask.mean()))
