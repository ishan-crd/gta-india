#!/bin/bash
# preview.sh CHARS ANIMS VIEW TAG [frac] : render + sheet into previews/tmp/TAG.png
cd ~/gta-india/repo/tools/blender
P=~/gta-india/assets/characters/previews/tmp/$4
rm -rf $P; mkdir -p $P
/snap/bin/blender -b -t 8 --python gi_contact.py -- --chars $1 --anims $2 --out $P --view $3 --frac ${5:-0.5} 2>&1 | grep -E "CHAR|POSE|ANIM|Error|error"
python3 gi_sheet.py $P $P.png $1 $2 ${6:-256}
