#!/bin/bash
# XIYIN's cheeky-brat acting pack for the game layer (owner 2026-11-04: "make her more captivating"; work through
# reference games and Japanese illustration guides). Research: Muse Dash characters show short flourishes between
# hits and a victory pose; Japanese pose dictionaries list akanbe (index finger pulling down the lower eyelid,
# tongue out), finger-pointing, peace sign and the smug doyagao (raised brows, half eyes, chin up) as the stock
# gestures of a cheeky character. Strictly non-sexual: pranks and attitude only.
# Identity lock: NovelAI V4.5 Precise Reference (character & style) on her approved game drawing
# (ref/xiyin_run_v2.png: sheet colours, canonical eye, N5-fitted face); same tags as her game drawings.
# Run one set with ONLY=<glob on the output file name>.
OUT=art/generated/md_style/brat
REF=art/generated/md_style/ref/xiyin_run_v2.png
M=nai-diffusion-4-5-full
XY="1girl, solo, chibi, 2.5 heads tall, young girl, cat girl, navy blue cat ears, pink inner ear, very long straight hair, royal blue hair, one ahoge, small blue cat hairclip, big round blue eyes, sparkling eyes, oversized dark navy sweater, sailor collar with cobalt blue stripes, navy necktie, sleeves past wrists, cobalt striped cuffs, dark grey shorts, navy cat tail, navy knee socks with a cobalt stripe, chunky black lace-up boots with blue soles"
STY="full body, game character sprite, clean vector illustration, crisp clean lineart, dark blue lineart, flat color, cel shading, one shadow tone, white background, simple background, centered"
NEG="half-closed eyes heavy, narrow eyes, black hair, cyan hair, purple hair, gradient hair, thighhighs, pantyhose, skirt, mature, adult, tall, multiple views, character sheet, text, watermark, signature, lowres, blurry, jpeg artifacts, shadow, floor, motion lines, effects, nsfw, suggestive, cleavage"
g() {  # name seed tags [strength]
  o="$OUT/$1_$2.png"
  if [ -n "$ONLY" ] && [[ "$(basename "$o")" != $ONLY ]]; then return 0; fi
  [ -f "$o" ] || python3 .claude/skills/oc-gen/scripts/nai.py generate --model $M --charref "$REF" --charref-mode "character&style" --charref-strength ${4:-0.8} --charref-fidelity 1.0 --prompt "$XY, $3, $STY" --negative "$NEG" --w 832 --h 1216 --seed $2 --out "$o"
}
for seed in 65001 65002 65003; do
  g t_akanbe $seed "akanbe, pulling down her lower eyelid with one index finger, tongue out, teasing, mischievous, other hand on hip, standing, turned toward the viewer, three-quarter view"
  g t_wag $seed "smug, doyagao, wagging her index finger at the viewer, tsk tsk, raised eyebrows, chin up, :3, other hand on hip, standing, three-quarter view"
  g m_fluster $seed "stumbling forward, flustered, surprised, open mouth, eyes wide, blush, sweat drop, cat ears flattened back, arms flailing, comedic, from side, facing right"
  g v_peace $seed "victory pose, peace sign next to her face, winking, smug grin, standing on one leg, other leg kicked up behind, three-quarter view, facing the viewer"
  g b_boop $seed "scolding, leaning forward toward the viewer, cat paw boop, poking toward the viewer with one sleeve, squinting, pouting, puffed cheeks, light blush, three-quarter view"
done
# armed poses at her run proportions (owner: the paw-mic poses were stubbier than the run cycle). Plain stick as
# before (pixel/mdweapon.py lays the one canonical paw mic along it).
STK="holding a plain straight light blue stick with both hands, simple cylinder pole"
for seed in 65001 65002; do
  g a_windup $seed "$STK, dynamic pose, winding up, stick pulled far back behind her head, leaning back, knees bent, smug grin, face visible, from side, facing right"
  g a_smash $seed "$STK, dynamic pose, smashing the stick down onto the ground in front of her, bent forward, head up, fierce grin, face visible, from side, facing right"
  g a_upper $seed "$STK, dynamic pose, swinging the stick upward from low to high, jumping off one foot, face visible, grin, from side, facing right"
  g a_airslam $seed "$STK, dynamic pose, jumping, mid-air, stick raised high overhead about to slam down, knees tucked, fierce grin, face visible, from side, facing right"
done
# companion (Muse Dash's floating "Elfin"): the sleepy cat spirit c_sleepcat_49502 in three states by img2img
CM=nai-diffusion-5-full
CP="no humans, tiny light blue cat spirit sitting on a small fluffy cloud, blue nightcap with a white pompom, little angel wings, round and soft, chibi creature, clean vector illustration, colored outline, flat color, cel shading, white background, simple background, centered, no shadow"
CN="human, girl, text, watermark, shadow, floor, multiple views, lowres, blurry"
for st in "wink|one eye open, the other eye closed, sleepy curious peek" "awake|wide awake, both eyes open, big round sparkling eyes, determined, cheering, tiny fist raised"; do
  n=${st%%|*}; tags=${st#*|}
  for seed in 65101 65102; do
    o="$OUT/c_$n_$seed.png"; o="$OUT/c_${n}_${seed}.png"
    if [ -n "$ONLY" ] && [[ "$(basename "$o")" != $ONLY ]]; then continue; fi
    [ -f "$o" ] || python3 .claude/skills/oc-gen/scripts/nai.py img2img --model $CM --image art/generated/md_style/c_sleepcat_49502.png --strength 0.5 --seed $seed --w 1024 --h 1024 --prompt "$CP, $tags" --negative "$CN" --out "$o"
  done
done
# companion v2: img2img 0.5 kept the eyes closed; 0.7 with weighted eye tags
for st in "wink2|2::one eye open::, one eye closed, winking, curious peek, :o" "awake2|2::eyes open::, 2::big round sparkling blue eyes::, awake, excited, cheering, tiny paw raised, open mouth smile"; do
  n=${st%%|*}; tags=${st#*|}
  for seed in 65111 65112; do
    o="$OUT/c_${n}_${seed}.png"
    if [ -n "$ONLY" ] && [[ "$(basename "$o")" != $ONLY ]]; then continue; fi
    [ -f "$o" ] || python3 .claude/skills/oc-gen/scripts/nai.py img2img --model $CM --image art/generated/md_style/c_sleepcat_49502.png --strength 0.7 --seed $seed --w 1024 --h 1024 --prompt "$CP, $tags" --negative "$CN, closed eyes, sleeping" --out "$o"
  done
done
