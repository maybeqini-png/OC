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
# v2 (owner: "no" - the right cheek still showed a half-transparent hair tip, both cheeks looked painted on): inpaint
# both cheeks and the hair tip of the clean redraw with V5 inpainting (mask cheek_mask.png).
for seed in 69101 69102 69103; do
  o="$OUT/pout_inpaint_$seed.png"
  [ -f "$o" ] || python3 .claude/skills/oc-gen/scripts/nai.py infill --model nai-diffusion-5-full-inpainting --image "$OUT/pout_0.30_69002.png" --mask "$OUT/cheek_mask.png" --seed $seed --w 1024 --h 1024 --prompt "1girl, cat girl, close-up, puffed cheeks, pout, eyes closed, smooth clean bright skin, soft pink blush, solid royal blue hair strands with crisp dark outline, anime, clean lineart, cel shading, flat color" --negative "transparent hair, faded hair, blurry, smudge, dirty skin, grey skin, shadows on cheeks, extra lines, lowres, jpeg artifacts" --out "$o"
done
# v2 inpainting (nai-diffusion-5-full-inpainting) returned flat grey / bubble patches: rejected and deleted.
# v3: the smug frame's face crop (same pose and hair, its right-cheek strand drawn solid, clean cheeks) redrawn into
# the pout by V5 img2img; the whole face is taken, the seam stays in the hair.
P3="1girl, solo, cat girl, close-up, face, royal blue hair, messy bangs, blue cat hairclip, 2::pouting::, 2::puffed cheeks::, closed mouth, wavy mouth, 2::eyes closed tightly::, ><, annoyed, soft pink blush on cheeks, smooth clean bright skin, solid hair, anime, clean lineart, cel shading, flat color, sharp focus"
for s in 0.50 0.58; do for seed in 69201 69202; do
  o="$OUT/smugpout_${s}_${seed}.png"
  [ -f "$o" ] || python3 .claude/skills/oc-gen/scripts/nai.py img2img --model nai-diffusion-5-full --image "$OUT/smug_crop.png" --strength $s --seed $seed --w 1024 --h 1024 --prompt "$P3" --negative "$N, open eyes, smile, transparent hair" --out "$o"
done; done
