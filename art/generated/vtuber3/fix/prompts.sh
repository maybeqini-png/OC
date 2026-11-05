#!/bin/bash
# Pout face fix (owner 2026-11-05: "the colours on the face look off" at 1:40). The pout frame's closed eyes have
# grey-blue smudges under the eyes, dark grey lids and stray brow strokes. Source = the face crop of final/pout.png at
# full resolution (1024x1024 from the 2048 frame); V5 img2img redraws it clean in the same expression; the face area is
# transplanted back (pixel/vtfix.py). Normal size = 0 Anlas.
OUT=art/generated/vtuber3/fix
P="1girl, solo, cat girl, close-up, face, royal blue hair, messy bangs, blue cat hairclip, pouting, puffed cheeks, closed mouth, eyes closed tightly, ><, clean closed eyelids, thin dark eyelashes, soft pink blush on cheeks, clean bright skin, anime, clean lineart, cel shading, flat color, sharp focus"
N="grey skin, bluish skin, dark circles, shadows under eyes, dirty face, smudge, purple blush, extra eyebrows, messy lines, lowres, blurry, jpeg artifacts, open eyes, mature, nsfw"
for s in 0.30 0.40; do for seed in 69001 69002; do
  o="$OUT/pout_${s}_${seed}.png"
  [ -f "$o" ] || python3 .claude/skills/oc-gen/scripts/nai.py img2img --model nai-diffusion-5-full --image "$OUT/pout_crop.png" --strength $s --seed $seed --w 1024 --h 1024 --prompt "$P" --negative "$N" --out "$o"
done; done
