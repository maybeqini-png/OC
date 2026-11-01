#!/bin/bash
# VTuber model v2 (2026-11-01): base = the owner's reference sheet bust (art/reference/oc_reference_sheet.webp,
# crop 176,0,848,672), upscaled x2 with Real-ESRGAN animevideov3 and resized to 1024 (base_sheet_bust.png). Each
# expression is a V5 img2img of that base; pixel/vtmodel.py pastes only the face back onto the base.
# Free normal-size generations (1024x1024).
NAI="python3 .claude/skills/oc-gen/scripts/nai.py"
M=nai-diffusion-5-full
OUT=art/generated/vtuber2
SRC=$OUT/base_sheet_bust.png
BASE="1girl, solo, young girl, child, petite, round face, big eyes, cat girl, navy blue cat ears, pink inner ear, very long hair, straight hair, royal blue hair, messy bangs, hair between eyes, ahoge, blue cat hairclip, blue eyes, looking at viewer, upper body, front view, oversized navy sweater, navy sailor collar, blue stripes on collar, short navy necktie, black cat emblem on necktie, light blue cat face patch on chest, white background, simple background, anime, clean lineart, cel shading, flat color"
NEG="mature, adult, older, teenage, tall, long neck, tired, sleepy, droopy eyes, heavy eyelids, blunt bangs, hime cut, hands, human ears, text, watermark, signature, lowres, bad anatomy, asymmetrical eyes, jpeg artifacts, multiple views, extra ears, cyan, purple hair, nsfw, suggestive"
ex() {  # name strength seed tags
  [ -f "$OUT/$1_raw.png" ] || $NAI img2img --model $M --image $SRC --strength $2 --seed $3 --w 1024 --h 1024 --prompt "$BASE, $4" --negative "$NEG" --out "$OUT/$1_raw.png"
}
for s in 0.40 0.50; do for seed in 31001 31002; do
  ex blink_${s}_${seed} $s $seed "2::closed eyes::, smile, closed mouth"
  ex talk_${s}_${seed} $s $seed "2::open mouth::, smile, :d, talking, eyes open"
done; done
# blink v2: 0.40-0.50 kept the eyes open or winked; stronger closed-eye weight, wink in the negative
NEGB="$NEG, one eye closed, wink, open eyes"
exb() { [ -f "$OUT/$1_raw.png" ] || $NAI img2img --model $M --image $SRC --strength $2 --seed $3 --w 1024 --h 1024 --prompt "$BASE, $4" --negative "$NEGB" --out "$OUT/$1_raw.png"; }
for seed in 31003 31004; do for s in 0.55 0.62; do
  exb blinkb_${s}_${seed} $s $seed "3::closed eyes::, 2::both eyes closed::, eyelashes, smile, closed mouth"
done; done
# blink v3: source = base with the eyes erased (base_noeyes.png, made by erasing two eye ellipses with skin colour)
exn() { [ -f "$OUT/$1_raw.png" ] || $NAI img2img --model $M --image $OUT/base_noeyes.png --strength $2 --seed $3 --w 1024 --h 1024 --prompt "$BASE, $4" --negative "$NEGB" --out "$OUT/$1_raw.png"; }
for seed in 31005 31006; do for s in 0.45 0.55; do
  exn blinkc_${s}_${seed} $s $seed "3::closed eyes::, both eyes closed, eyelashes, smile, closed mouth"
done; done
# expressions (2026-11-01): source = base with eyes and mouth erased (base_noface.png); only eyes / mouth (and
# cheeks where noted in pixel/vtmodel.py) are pasted back onto the base
exf() { [ -f "$OUT/$1_raw.png" ] || $NAI img2img --model $M --image $OUT/base_noface.png --strength 0.5 --seed $2 --w 1024 --h 1024 --prompt "$BASE, $3" --negative "$NEG" --out "$OUT/$1_raw.png"; }
for seed in 32001 32002; do
  exf smug_$seed $seed "2::smug::, half-closed eyes, smirk, fang, :3, confident"
  exf wink_$seed $seed "2::one eye closed::, wink, ;), smile, closed mouth"
  exf determined_$seed $seed "2::determined::, confident smile, sparkling eyes, closed mouth"
  exf cheer_$seed $seed "2::happy::, big smile, open mouth, sparkling eyes, excited, blush"
  exf shocked_$seed $seed "2::surprised::, wide-eyed, small pupils, open mouth, :o"
  exf pain_$seed $seed "2::>_<::, eyes shut tight, wince, open mouth, teary"
  exf angry_$seed $seed "2::angry::, pout, puffed cheeks, furrowed brow, glaring, closed mouth"
  exf hmph_$seed $seed "2::closed eyes::, pout, hmph, offended, closed mouth"
  exf flustered_$seed $seed "2::embarrassed::, blush, wavy mouth, teary eyes, flustered"
  exf honest_$seed $seed "gentle smile, soft eyes, half-closed eyes, calm, closed mouth"
  exf sing_$seed $seed "2::singing::, closed eyes, open mouth, happy"
  exf laugh_$seed $seed "2::laughing::, closed eyes, ^_^, open mouth, happy tears, blush"
  exf frustrated_$seed $seed "2::frustrated::, teary eyes, pout, trembling lips, blush"
done
