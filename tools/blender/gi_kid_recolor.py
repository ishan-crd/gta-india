#!/usr/bin/env python3
"""gi_kid_recolor.py - recolour an already-built SK_ character's base-colour textures in place (python3 + PIL + numpy).

Run AFTER gi_build_char.py.  Rewrites textures/<Short>/T_<Short>_<slot>_BaseColor.* and the copy in SK_<Name>.fbm/
(the FBX references those file names, so no re-export is needed).

python3 gi_kid_recolor.py SK_KidGreen Topmat=garment:0.10,0.42,0.12 Hairmat=hair Bodymat=skin
ops:  garment:r,g,b   whole texture -> colour, shading from luminance (keeps folds)
      flat:r,g,b      whole texture -> nearly flat colour (kills prints/logos)
      hair            whole texture -> near-black hair keeping strand shading (alpha kept)
      skin[:k]        skin-hued pixels -> South-Asian brown (k = darkness, default 1)
"""
import os, sys, glob
import numpy as np
from PIL import Image

OUT = os.path.expanduser("~/gta-india/assets/characters")
name = sys.argv[1]
short = name[3:]


def lum(rgb):
    return rgb[..., 0] * 0.3 + rgb[..., 1] * 0.55 + rgb[..., 2] * 0.15


def op_garment(rgb, arg, flat=False):
    col = np.array([float(x) for x in arg.split(",")], dtype=np.float32)
    L = lum(rgb)
    ref = float(np.percentile(L, 80)) + 1e-4
    shade = np.clip(L / ref, 0.15, 1.15) ** 0.85
    if flat:
        shade = 0.88 + 0.12 * np.clip(shade, 0, 1.1)
    return np.clip(col[None, None, :] * shade[..., None], 0, 1)


def op_hair(rgb, arg):
    L = lum(rgb)
    L = L / max(float(np.percentile(L, 98)), 1e-3)
    return np.stack([0.030 + 0.065 * L, 0.024 + 0.050 * L, 0.021 + 0.040 * L], -1).clip(0, 1)


def op_skin(rgb, arg):
    k = float(arg) if arg else 1.0
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = rgb.max(-1); mn = rgb.min(-1); sat = (mx - mn) / (mx + 1e-6)
    m = ((r > g) & (g >= b * 0.85) & (sat > 0.08) & (sat < 0.75) & (mx > 0.12)).astype(np.float32)
    m = m * np.clip((sat - 0.08) / 0.06, 0, 1)
    tgt = rgb * np.array([0.66, 0.50, 0.40], dtype=np.float32) ** k
    return rgb * (1 - m[..., None]) + tgt * m[..., None]


OPS = {"garment": op_garment, "flat": lambda rgb, a: op_garment(rgb, a, True), "hair": op_hair, "skin": op_skin}

for spec in sys.argv[2:]:
    slot, op = spec.split("=", 1)
    opn, _, arg = op.partition(":")
    pat = f"T_{short}_{slot}_BaseColor.*"
    files = glob.glob(os.path.join(OUT, "textures", short, pat)) + glob.glob(os.path.join(OUT, name + ".fbm", pat))
    if not files:
        raise SystemExit("no texture for " + spec)
    for f in files:
        im = Image.open(f)
        mode = im.mode
        a = np.asarray(im.convert("RGBA"), dtype=np.float32) / 255.0
        a[..., :3] = OPS[opn](a[..., :3], arg)
        out = Image.fromarray((a * 255 + 0.5).clip(0, 255).astype(np.uint8), "RGBA")
        if mode != "RGBA":
            out = out.convert("RGB")
        if f.lower().endswith((".jpg", ".jpeg")):
            out.convert("RGB").save(f, quality=95)
        else:
            out.save(f)
        print("recoloured", os.path.relpath(f, OUT), opn, arg)
