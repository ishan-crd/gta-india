#!/bin/bash
# filmstrip.sh CHAR ANIMS VIEW TAG [fracs] -> previews/tmp/TAG.png (rows=anims, cols=fracs)
cd ~/gta-india/repo/tools/blender
P=~/gta-india/assets/characters/previews/tmp/$4; rm -rf $P; mkdir -p $P
FR=${5:-0,0.2,0.4,0.6,0.8}
/snap/bin/blender -b -t 8 --python gi_contact.py -- --chars $1 --anims $2 --out $P --view $3 --fracs $FR --size 384 2>&1 | grep -E "ANIM|Error|error"
python3 - $P $P.png $1 $2 $FR <<'PY'
import sys, os
from PIL import Image, ImageDraw
P, out, c, anims, fr = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(","), sys.argv[5].split(",")
s = 220
im = Image.new("RGB", (len(fr) * s, len(anims) * s), (20, 20, 20)); d = ImageDraw.Draw(im)
for i, an in enumerate(anims):
    for k in range(len(fr)):
        p = os.path.join(P, f"{c}__{an}@{k}.png")
        if os.path.exists(p): im.paste(Image.open(p).convert("RGB").resize((s, s)), (k * s, i * s))
        d.text((k * s + 3, i * s + 3), f"{an} {fr[k]}", fill=(255, 255, 0))
im.save(out)
PY
