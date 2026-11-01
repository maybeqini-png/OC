#!/bin/bash
# v3 assets (2026-11-01): VTuber premise. Free V5 normal-size generations only (the balance is 8 Anlas).
# Run from the repo root. Each call appends to art/generated/v3/manifest.jsonl.
NAI="python3 .claude/skills/oc-gen/scripts/nai.py"
M=nai-diffusion-5-full
OUT=art/generated/v3
gen() {  # name seed w h prompt negative
  [ -f "$OUT/$1_$2.png" ] || $NAI generate --model $M --w $3 --h $4 --seed $2 --prompt "$5" --negative "$6" --out "$OUT/$1_$2.png"
}
NEGBG="text, watermark, signature, logo, letters, words, numbers, humans, 1girl, person, realistic, photo, 3d, blurry, jpeg artifacts, lowres, nsfw, cyberpunk, neon, sci-fi, hologram, dark"
ROOM="no humans, scenery, indoors, cute girl's bedroom streaming setup, desk with a computer monitor and keyboard, microphone on a boom arm, cat ear headphones, gaming chair, plushies, small cat plush, fairy lights, posters, bed with pillows, window, soft daylight, pastel blue white and pink, cozy, anime background, cel shading, clean lineart, vivid colors, 2d illustration"
for s in 9701 9702 9703 9704; do gen r01_room $s 1344 768 "$ROOM" "$NEGBG"; done
# in-game avatar: true side view facing right (the runner looks where she runs, never at the viewer)
PXS="pixel art, sprite, chibi, 2heads, full body, 1girl, solo, cat girl, from side, profile, facing right, looking ahead, big navy blue cat ears, pink inner ear, long hair, bright royal blue hair, ahoge, blue cat hairclip, blue eyes, oversized very dark navy sweater, sailor collar, short navy necktie, sleeves past wrists, dark grey shorts, navy cat tail, navy kneehighs, black boots, white background, simple background, limited palette, clean outline"
NEGS="looking at viewer, facing viewer, front view, three-quarter view, from front, blunt bangs, hime cut, text, watermark, signature, logo, lowres, bad anatomy, bad hands, extra fingers, human ears, extra ears, cyan hair, purple hair, grey hair, multiple views, character sheet, reference sheet, nsfw, suggestive, jpeg artifacts, blurry, realistic, 3d, gradient, painting, sketch"
for s in 9801 9802 9803; do gen a01_run $s 832 1216 "$PXS, running, mid stride, arms swinging" "$NEGS"; done
for s in 9811 9812; do gen a02_punch $s 832 1216 "$PXS, punching forward with her sleeve, cat punch, determined" "$NEGS"; done
for s in 9821 9822; do gen a03_airswipe $s 832 1216 "$PXS, jumping, mid-air, swiping one arm forward, knees bent" "$NEGS"; done
for s in 9831 9832; do gen a04_hurt $s 832 1216 "$PXS, hurt, flinching backward, eyes shut, knocked back" "$NEGS"; done
# game enemies (side view, coming from the right, so facing left)
NEGE="text, watermark, signature, logo, letters, humans, 1girl, person, realistic, 3d, blurry, jpeg artifacts, lowres, multiple views, gradient, painting"
gen e01_ground 9901 1024 1024 "pixel art, game sprite, single enemy, cute round grey mouse robot with big ears, side view, facing left, simple background, white background, limited palette, clean outline" "$NEGE"
gen e02_air 9902 1024 1024 "pixel art, game sprite, single enemy, cute round blue bird with small wings flying, side view, facing left, simple background, white background, limited palette, clean outline" "$NEGE"
gen e03_big 9903 1024 1024 "pixel art, game sprite, single enemy, big chubby grey mouse robot with a red bow, side view, facing left, simple background, white background, limited palette, clean outline" "$NEGE"
# room v2: the first takes had posters of other anime girls on the walls
NEGBG2="$NEGBG, poster, character poster, anime girl, figure, portrait, picture of a person, face"
ROOM2="no humans, scenery, indoors, cute girl's bedroom streaming setup, desk with a large computer monitor with a blank screen and a keyboard, microphone on a boom arm, cat ear headphones on a stand, white gaming chair, cat plushies, star garland, fairy lights, wall shelves, bed with pillows, window, soft daylight, pastel blue white and pink, cozy, anime background, cel shading, clean lineart, vivid colors, 2d illustration"
for s in 9711 9712 9713 9714; do gen r02_room $s 1344 768 "$ROOM2" "$NEGBG2"; done
