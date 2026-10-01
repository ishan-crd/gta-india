#!/bin/bash
# build every SK_ character (player first: it writes the template)
cd ~/gta-india/repo/tools/blender
B="/snap/bin/blender -b -t 4 --python gi_build_char.py --"
L=~/gta-india/assets/characters/_work/logs; mkdir -p $L
$B --src ch_man_blue --name SK_Player --height 1.75 --gender male --template --recolor > $L/SK_Player.log 2>&1
run() { $B --src $1 --name $2 --height $3 --gender $4 > $L/$2.log 2>&1; echo "$2 $?"; }
export -f run; export B L
cat <<LIST | xargs -P 5 -L 1 bash -c 'run $0 $1 $2 $3'
ch_man_blue SK_ManBlue 1.75 male
ch_man_red SK_ManRed 1.72 male
ch_sareewoman SK_SareeWoman 1.60 female
ch_man_kurta SK_ManKurta 1.74 male
ch_man_kurta2 SK_ManKurta2 1.76 male
ch_woman_saree SK_WomanSaree 1.62 female
ch_teen SK_Teen 1.60 male
ch_office_woman SK_OfficeWoman 1.63 female
ch_man_dhoti SK_ManDhoti 1.70 male
LIST
