#!/bin/bash
# retarget every clip onto SK_Player's GI_Human skeleton (see gi_retarget.py). Usage: build_all_anims.sh [clip-regex]
cd ~/gta-india/repo/tools/blender
L=~/gta-india/assets/characters/_work/logs; mkdir -p $L
FILTER=$1
R() { clip=$1; shift; [ -n "$FILTER" ] && [[ ! "$clip" =~ $FILTER ]] && return; /snap/bin/blender -b -t 4 --python gi_retarget.py -- --clip $clip "$@" > $L/$clip.log 2>&1; echo "$clip $? $(grep -E 'EXPORTED|Error' $L/$clip.log | tail -1)"; }
R A_Idle    --src an_idle --loop --xy inplace --z ground --note "Breathing Idle, full clip" &
R A_Walk    --src an_walk --start 0 --end 31 --loop --xy inplace --z ground --note "Mr Man Walking (same mocap as an_bearded walk)" &
R A_Run     --src an_bearded --action run --reorient --start 1 --end 23 --loop --xy inplace --z ground --note "an_bearded run (an_run is a camera-holding run)" &
R A_Jump    --src an_jump --start 15 --end 32 --xy inplace --z pin --upright 5 --note "take-off + rise; source is a forward flip, torso counter-rotated upright, feet pinned (capsule does the height)" &
R A_Fall    --src an_jump --start 36 --end 46 --loop --xy inplace --z pin --upright 5 --note "airborne tuck from an_jump, loop-closed" &
wait
R A_Land    --src an_jump --start 44 --end 71 --xy inplace --z pin --upright 5 --note "impact crouch + recover" &
R A_Swim    --src an_swim_warrior --start 24 --end 160 --loop --xy inplace --z center --note "prone/horizontal crawl-style swim cycle; hips centred at standing hip height" &
R A_Tread   --src an_tread --start 0 --end 80 --loop --xy inplace --z center --upright 10 --note "treading water, torso lean reduced to 10 deg" &
R A_SitIdle --src an_sit_idle --start 0 --end 129 --loop --xy keep --z ground --note "seated, hips ~0.45 m (chair height)" &
R A_SitTalk --src an_sit_talk --loop --xy keep --z ground --note "seated talking, 45 s" &
wait
R A_PickUp  --src an_bearded --action picking --reorient --xy zero --z first --note "an_bearded picking_up" &
R A_Death   --src an_bearded --action death --reorient --xy zero --z pinall --note "an_bearded death, falls backwards (root stays; hips travel kept)" &
wait
