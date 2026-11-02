#!/bin/bash
# VTuber model v3 (2026-11-02): new bust-up. Source = paste-up of the owner's reference sheet (pixel/vt3.py:
# head tilt, optional raised sleeve, old high brow lines erased, short dark brow guides about half an eye height
# above the lash line). V5 img2img redraws it. Free normal-size generations (1024x1024, 28 steps, 0 Anlas).
# Only the takes used by pixel/vt3.py FRAMES (and the sources they came from) are kept in the repo; the other takes
# were moved out (their manifest rows stay). Re-running this script regenerates the missing ones.
# Run one set only with ONLY=<glob on the output file name>, e.g. ONLY='g_blink_*' bash prompts.sh; without it the
# script regenerates every missing take, including rejected ones that were moved out of the repo.
nai_guard() {
  local prev="" out=""
  for a in "$@"; do [ "$prev" = "--out" ] && out="$a"; prev="$a"; done
  if [ -n "$ONLY" ] && [[ "$(basename "$out")" != $ONLY ]]; then return 0; fi
  python3 .claude/skills/oc-gen/scripts/nai.py "$@"
}
NAI=nai_guard
M=nai-diffusion-5-full
OUT=art/generated/vtuber3
CHAR="1girl, solo, young girl, child, petite, round face, big eyes, cat girl, navy blue cat ears, pink inner ear, very long hair, straight hair, royal blue hair, messy bangs, hair between eyes, ahoge, blue cat hairclip, blue eyes, short eyebrows, thin eyebrows, dark blue eyebrows, eyebrows visible through hair"
OUTFIT="oversized navy sweater, navy sailor collar, blue stripes on collar, short navy necktie, black cat emblem on necktie, light blue cat face patch on chest"
STYLE="simple background, light grey background, anime, clean lineart, cel shading, flat color, sharp focus"
NEG="mature, adult, older, teenage, tall, long neck, tired, sleepy, half-closed eyes, droopy eyes, heavy eyelids, thick eyebrows, long eyebrows, blunt bangs, hime cut, human ears, text, watermark, signature, lowres, blurry, bad anatomy, bad hands, extra fingers, asymmetrical eyes, jpeg artifacts, multiple views, extra ears, cyan, purple hair, nsfw, suggestive"
gen() {  # name source strength seed tags
  [ -f "$OUT/$1.png" ] || $NAI img2img --model $M --image $OUT/$2 --strength $3 --seed $4 --w 1024 --h 1024 --prompt "$CHAR, $5, $OUTFIT, $STYLE" --negative "$NEG" --out "$OUT/$1.png"
}
# round 1: framing
for seed in 33001 33002; do
  for s in 0.50 0.60; do gen b_tilt_${s}_${seed} pasteup_tilt.png $s $seed "light smile, closed mouth, looking at viewer, head tilt, upper body"; done
  for s in 0.60 0.70; do gen b_sleeve_${s}_${seed} pasteup_sleeve.png $s $seed "light smile, closed mouth, looking at viewer, head tilt, upper body, hand up, sleeves past wrists, striped cuffs, hand near own face"; done
done
# round 2: in V5 "short eyebrows" means round dot brows (maro-mayu) high on the forehead; round 1 drew blue blobs there.
# Use thin brows drawn through the bangs instead; keep the hair royal blue (round 1 seed 33001 went cyan).
CHAR2="${CHAR/short eyebrows, thin eyebrows, dark blue eyebrows, eyebrows visible through hair/thin eyebrows, eyebrows visible through hair}"
NEG2="$NEG, short eyebrows, forehead mark, light blue hair, cyan hair, tail"
gen2() {  # name source strength seed tags
  [ -f "$OUT/$1.png" ] || $NAI img2img --model $M --image $OUT/$2 --strength $3 --seed $4 --w 1024 --h 1024 --prompt "$CHAR2, $5, $OUTFIT, $STYLE" --negative "$NEG2" --out "$OUT/$1.png"
}
for seed in 33002 33003 33004; do
  for s in 0.55 0.62; do gen2 c_sleeve_${s}_${seed} pasteup_sleeve.png $s $seed "light smile, closed mouth, looking at viewer, head tilt, upper body, hand up, sleeves past wrists, striped cuffs, hand near own face"; done
done
for seed in 33003 33004; do gen2 c_tilt_0.50_${seed} pasteup_tilt.png 0.50 $seed "light smile, closed mouth, looking at viewer, head tilt, upper body"; done
# round 3 (base): chosen framing c_sleeve_0.62_33002; pixel/vt3.py brow_guides() erases the faint high brow lines
# and paints short dark brow strokes about half an eye height above the lash line -> guide_base.png; light redraw.
CHAR3="${CHAR2/thin eyebrows, eyebrows visible through hair/thin eyebrows, 1.3::eyebrows visible through hair::}"
POSE="light smile, closed mouth, looking at viewer, head tilt, upper body, hand up, sleeves past wrists, striped cuffs, hand near own face"
gen3() {  # name source strength seed tags
  [ -f "$OUT/$1.png" ] || $NAI img2img --model $M --image $OUT/$2 --strength $3 --seed $4 --w 1024 --h 1024 --prompt "$CHAR3, $5, $OUTFIT, $STYLE" --negative "$NEG2" --out "$OUT/$1.png"
}
for seed in 34001 34002; do for s in 0.35 0.42; do gen3 d_base_${s}_${seed} guide_base.png $s $seed "$POSE"; done; done
# round 3b: dark strokes over the hair came back as pale hair-clip bars; guide v2 = thinner, tapered, lash-coloured
# (48,36,52) brows with a slight arch; plain brow tags (no weight)
for seed in 34001 34003; do for s in 0.38 0.45; do
  [ -f "$OUT/e_base_${s}_${seed}.png" ] || $NAI img2img --model $M --image $OUT/guide_base2.png --strength $s --seed $seed --w 1024 --h 1024 --prompt "$CHAR2, eyebrows, $POSE, $OUTFIT, $STYLE" --negative "$NEG2, hairclip on bangs, hair bar" --out "$OUT/e_base_${s}_${seed}.png"
done; done
# round 4 (expression test): whole-image img2img of the chosen base with brow-carrying expression tags; only the
# face is used later (pixel/vt3.py). Tests whether V5 draws visible brows over the bangs by itself.
EXPOSE="looking at viewer, head tilt, upper body, hand up, sleeves past wrists, striped cuffs, hand near own face"
gx() {  # name strength seed tags
  [ -f "$OUT/x_$1.png" ] || $NAI img2img --model $M --image $OUT/c_sleeve_0.62_33002.png --strength $2 --seed $3 --w 1024 --h 1024 --prompt "$CHAR2, $4, $EXPOSE, $OUTFIT, $STYLE" --negative "$NEG2" --out "$OUT/x_$1.png"
}
for s in 0.50 0.60; do
  gx angry_${s}_35001 $s 35001 "2::angry::, 2::v-shaped eyebrows::, furrowed brow, glaring, pout, puffed cheeks, closed mouth"
  gx smug_${s}_35001 $s 35001 "2::smug::, 2::raised eyebrow::, half-closed eyes, smirk, fang, :3"
  gx worried_${s}_35001 $s 35001 "2::flustered::, 2::worried eyebrows::, blush, wavy mouth, teary eyes"
  gx shock_${s}_35001 $s 35001 "2::surprised::, 2::raised eyebrows::, wide-eyed, small pupils, open mouth, :o"
done
# round 5 (neutral): V5 draws visible brows when the prompt carries them (round 4), so the neutral face is also a V5
# take of the chosen base; its face becomes the new base face.
for seed in 36001 36002 36003 36004; do
  gx neutral_0.45_${seed} 0.45 $seed "2::light smile::, closed mouth, calm, 1.5::thin eyebrows::, eyebrows visible through hair, confident"
done
# round 6 (neutral with guides): short lash-coloured brow guides (lift 0.45 / 0.60 eye heights) on the chosen base,
# redrawn at 0.50-0.55 with a neutral prompt; the brow tag "short eyebrows" stays in the negative (round 2).
for lift in 45 60; do for seed in 36011 36012; do for s in 0.50 0.55; do
  [ -f "$OUT/n_l${lift}_${s}_${seed}.png" ] || $NAI img2img --model $M --image $OUT/guide_base_l${lift}.png --strength $s --seed $seed --w 1024 --h 1024 --prompt "$CHAR2, eyebrows, 2::light smile::, closed mouth, calm, confident, $EXPOSE, $OUTFIT, $STYLE" --negative "$NEG2, hairclip on bangs, hair bar" --out "$OUT/n_l${lift}_${s}_${seed}.png"
done; done; done
# round 7 (neutral, no guides): at 0.50-0.55 V5 hid the guide brows under the bangs (round 6); heavier brow weights
for seed in 36021 36022 36023 36024; do
  gx neutral2_0.50_${seed} 0.50 $seed "2::light smile::, closed mouth, calm, confident, 2::eyebrows visible through hair::, 1.5::thin eyebrows::"
done
# round 8 (expression set): sources = the chosen base (full), base_noeyes.png (eyes painted over in skin tone, for
# closed-eye frames) and base_noface.png (eyes + mouth painted over, for mouth shapes). pixel/vt3.py pastes only
# the brow/eye band, the mouth and the cheeks of each take onto the base.
NEGC="$NEG2, ^_^, open eyes"
gs() {  # name source strength seed tags [extra negative]
  [ -f "$OUT/f_$1.png" ] || $NAI img2img --model $M --image $OUT/$2 --strength $3 --seed $4 --w 1024 --h 1024 --prompt "$CHAR2, $5, $EXPOSE, $OUTFIT, $STYLE" --negative "${6:-$NEG2}" --out "$OUT/f_$1.png"
}
for seed in 37001 37002; do
  gs blink_$seed base_noeyes.png 0.50 $seed "2::closed eyes::, light smile, closed mouth, calm, thin eyebrows, eyebrows visible through hair" "$NEGC, wink"
  gs talka_$seed base_noface.png 0.45 $seed "2::open mouth::, talking, light smile, eyebrows visible through hair"
  gs talko_$seed base_noface.png 0.45 $seed "2:::o::, small open mouth, talking, eyebrows visible through hair"
  gs smug_$seed c_sleeve_0.62_33002.png 0.55 $seed "2::smug::, 2::raised eyebrow::, v-shaped eyebrows, half-closed eyes, smirk, fang, :3, closed mouth"
  gs wink_$seed base_noeyes.png 0.50 $seed "2::one eye closed::, wink, ;), raised eyebrow, smile, closed mouth, fang"
  gs happy_$seed c_sleeve_0.62_33002.png 0.55 $seed "2::happy::, :d, open mouth, big smile, 2::raised eyebrows::, sparkling eyes, blush"
  gs sing_$seed base_noeyes.png 0.50 $seed "2::singing::, closed eyes, open mouth, smile, raised eyebrows" "$NEGC"
  gs pout_$seed base_noeyes.png 0.50 $seed "2::pout::, puffed cheeks, 2::closed eyes::, hmph, v-shaped eyebrows, blush" "$NEGC"
  gs pain_$seed base_noeyes.png 0.50 $seed "2::>_<::, eyes shut tight, wince, 2::furrowed brow::, teary, open mouth" "$NEGC"
done
gs shock_37001 c_sleeve_0.62_33002.png 0.55 37001 "2::surprised::, 2::raised eyebrows::, wide-eyed, small pupils, open mouth, :o"
gs angry_37001 c_sleeve_0.62_33002.png 0.55 37001 "2::angry::, 2::v-shaped eyebrows::, furrowed brow, glaring, pout, puffed cheeks, closed mouth"
gs flustered_37001 c_sleeve_0.62_33002.png 0.55 37001 "2::flustered::, 2::worried eyebrows::, blush, wavy mouth, teary eyes"
# round 9: at 0.50 V5 left the painted-over eyes blank (round 8). Closed-lid hint curves (pixel/vt3.py
# closed_eye_guides -> base_closed*.png) and higher strength; mouth shapes from base_nomouth.png (eyes kept).
for seed in 37001 37002; do for s in 0.55 0.62; do
  gs blink_${s}_$seed base_closed.png $s $seed "2::closed eyes::, light smile, closed mouth, calm, thin eyebrows, eyebrows visible through hair" "$NEGC, wink"
  gs sing_${s}_$seed base_closed.png $s $seed "2::singing::, 2::closed eyes::, open mouth, smile, raised eyebrows" "$NEGC"
  gs pout_${s}_$seed base_closed.png $s $seed "2::pout::, puffed cheeks, 2::closed eyes::, hmph, v-shaped eyebrows, blush" "$NEGC"
  gs pain_${s}_$seed base_closed_happy.png $s $seed "2::>_<::, eyes shut tight, wince, 2::furrowed brow::, teary, open mouth" "$NEGC"
done; done
for seed in 37001 37002; do for s in 0.45 0.52; do
  gs talka_${s}_$seed base_nomouth.png $s $seed "2::open mouth::, talking, light smile, eyebrows visible through hair"
  gs talko_${s}_$seed base_nomouth.png $s $seed "2:::o::, small open mouth, talking, eyebrows visible through hair"
done; done
# round 10: pain needs both eyes shut (round 9 takes closed only one)
for seed in 37003 37004 37005 37006; do
  gs pain_0.62_$seed base_closed_happy.png 0.62 $seed "2::>_<::, 2::both eyes closed::, eyes shut tight, wince, 2::furrowed brow::, teary, open mouth" "$NEGC, one eye closed, wink"
done
# round 11: wink from a source with only the viewer-right eye painted over plus a closed-lid hint (base_wink.png);
# round 8's wink tinted the open eye pink
for seed in 37011 37012 37013 37014; do
  gs wink_0.50_$seed base_wink.png 0.50 $seed "2::one eye closed::, 2::wink::, ;), raised eyebrow, smile, closed mouth, fang, blue eyes" "$NEG2, heterochromia, red eyes, pink eyes"
done
# round 12 (neutral): rounds 5-7 kept the neutral brows as thin lines 1-1.7 eye heights up through the bangs; a light
# touch of smug / v-shaped brows to bring them down for her cheeky resting face
for seed in 36031 36032 36033; do
  gx neutral3a_0.50_${seed} 0.50 $seed "light smile, closed mouth, confident, 0.6::smug::, 1.3::eyebrows visible through hair::, thin eyebrows"
  gx neutral3b_0.50_${seed} 0.50 $seed "light smile, closed mouth, 0.6::v-shaped eyebrows::, 1.3::eyebrows visible through hair::, thin eyebrows"
done
# round 13 (blink v2, NOT RUN): blink takes from round 9 left a flat pale wash and different strands around the
# eyes. Source = the composed neutral frame with the eyes filled from the surrounding skin (vt3.skin_fill) and calm
# closed-lid hints -> neutral_closed.png; low strengths so hair and skin stay close to the neutral frame.
# 2026-11-02: every request returned HTTP 402 (13-15 Anlas required, 1 left): the Opus plan's free normal-size
# generations were used up. The blink frame instead uses round 9's take with a skin correction (vt3 relight).
# Before that, a plain re-run of this script regenerated 11 rejected takes (rounds 1-2, free, deleted again); hence
# the ONLY filter above.
for seed in 37021 37022 37023; do for s in 0.42 0.50; do
  [ -f "$OUT/g_blink_${s}_$seed.png" ] || $NAI img2img --model $M --image $OUT/neutral_closed.png --strength $s --seed $seed --w 1024 --h 1024 --prompt "$CHAR2, 2::closed eyes::, light smile, closed mouth, calm, $EXPOSE, $OUTFIT, $STYLE" --negative "$NEGC, wink" --out "$OUT/g_blink_${s}_$seed.png"
done; done
