#!/bin/bash
# Face harmonisation (pixel/mdface.py). Owner 2026-11-03: features must fit the face shape; use N5 with the code.
# Source = guide_<drawing>.png (sheet colours + the canonical eye from pixel/mdeyes.py). V5 img2img of the whole guide,
# same seed and OC prompt for every drawing; only the face is used (feathered transplant in pixel/mdface.py).
# Normal size (832x1216, 28 steps) = 0 Anlas on the owner's plan. Strictly non-sexual.
# Run one set with ONLY=<glob on the output name>.
OUT=art/generated/md_style/face
M=nai-diffusion-5-full
CHAR="1girl, solo, chibi, cat girl, navy blue cat ears, pink inner ear, very long hair, straight hair, royal blue hair, messy bangs, hair between eyes, ahoge, blue cat hairclip, big eyes, round eyes, blue eyes, sparkling eyes, star-shaped highlight in eyes, thick upper eyelashes, small nose, small mouth, round face, soft cheeks, light blush, thin eyebrows"
OUTFIT="oversized navy sweater, navy sailor collar, navy necktie, sleeves past wrists, dark grey shorts, black knee socks, black boots, navy cat tail"
STYLE="anime, clean lineart, cel shading, flat color, white background, simple background"
NEG="half-closed eyes, narrow eyes, jitome, sanpaku, small eyes, slit pupils, heavy eyelids, angry eyes, cyan hair, purple hair, gradient hair, mature, adult, tall, text, watermark, signature, lowres, blurry, bad anatomy, extra eyes, asymmetrical eyes, nsfw, suggestive"
declare -A EXPR=(
  [z_run_49102]="smug, confident smile, closed mouth, :3, looking ahead, from side"
  [z_punch_49113]="grin, teeth, cheeky smile, determined, looking ahead, from side"
  [z_air_49123]="grin, teeth, cheeky smile, looking ahead, from side"
  [v3_windup_49701]="grin, teeth, cheeky smile, looking ahead, from side"
  [v3_smash_49702]="grin, clenched teeth, determined, looking down, from side"
  [v3_upper_49701]="smug, confident smile, closed mouth, looking up, from side"
  [v3_upper_49702]="smug, confident smile, closed mouth, :3, looking up, from side"
  [v3_airslam_49701]="grin, teeth, cheeky smile, blush, looking ahead, three-quarter view"
  [v3_airslam_49702]="big grin, teeth, happy, blush, looking ahead, three-quarter view"
)
for name in ${NAMES:-${!EXPR[@]}}; do
  for s in ${STRENGTHS:-0.35}; do
    o="$OUT/${name}_${s}_${SEED:-61001}.png"
    if [ -n "$ONLY" ] && [[ "$(basename "$o")" != $ONLY ]]; then continue; fi
    [ -f "$o" ] || python3 .claude/skills/oc-gen/scripts/nai.py img2img --model $M --image "$OUT/guide_$name.png" --strength $s --seed ${SEED:-61001} --w 832 --h 1216 --prompt "$CHAR, ${EXPR[$name]}, $OUTFIT, $STYLE" --negative "$NEG" --out "$o"
  done
done
# test 2026-11-03: 0.35 vs 0.50 on z_run / v3_windup. 0.50 redesigns the eye (gold star iris, new lashes) = off-model; 0.35 keeps the canonical eye and fits eyes, mouth and cheeks to the head -> 0.35 for all.
# seeds 61002 / 61003 for v3_upper_49702, v3_airslam_49701, v3_airslam_49702 (61001: pale pupil-less eye, muddy
# rims); picked 61003 for all three (pixel/mdface.SEEDS). Irises are snapped to the canonical ramp after transplant.
