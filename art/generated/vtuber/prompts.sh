#!/bin/bash
# XIYIN's VTuber model expressions (2026-11-01), same pipeline as art/generated/expr: V5 img2img of the young base
# bust (nai_test/a3_img2img_v5_s050.png, made from the owner's sheet) at seed 20261023, then pixel/vtmodel.py pastes
# only the face region onto the base so her body, hair and costume never change. Free normal-size generations.
NAI="python3 .claude/skills/oc-gen/scripts/nai.py"
M=nai-diffusion-5-full
OUT=art/generated/vtuber
SRC=art/generated/nai_test/a3_img2img_v5_s050.png
BASE="1girl, solo, cat girl, cat ears, pink inner ear, very long hair, straight hair, royal blue hair, messy bangs, hair between eyes, side-swept bangs, sidelocks, ahoge, blue cat-shaped hairclip, blue eyes, slight head tilt, looking at viewer, upper body, front view, oversized navy sweater, navy sailor collar, blue stripes on collar, navy necktie, black cat emblem on necktie, small light blue cat face patch on chest, simple background, plain light grey background, anime key visual, official art, clean lineart, cel shading, glossy eyes, vtuber, young girl, round face"
NEG="blunt bangs, hime cut, hands, human ears, text, watermark, signature, lowres, bad anatomy, jpeg artifacts, multiple views, extra ears, cyan, purple hair, mature, adult, older, nsfw"
ex() { [ -f "$OUT/$1_raw.png" ] || $NAI img2img --model $M --image $SRC --strength 0.55 --seed 20261023 --w 1024 --h 1024 --prompt "$BASE, $2" --negative "$NEG" --out "$OUT/$1_raw.png"; }
ex v08_pain "2::>_<::, eyes shut tight, wince, pain, teary, open mouth, ouch"
ex v09_angry "2::angry::, pout, puffed cheeks, furrowed brow, glaring, scolding, closed mouth"
ex v10_hmph "2::pout::, closed eyes, hmph, nose up, offended, head turned slightly away, closed mouth"
ex v11_smug "2::smug::, smirk, fang, open mouth, half-closed eyes, confident, teasing"
ex v12_determined "2::determined::, confident smile, sparkling eyes, raised eyebrows, closed mouth"
ex v13_frustrated "2::frustrated::, teary eyes, pout, trembling lips, embarrassed, blush"
ex v14_sing "2::singing::, closed eyes, open mouth, happy, music"
ex v15_cheer "2::happy::, big smile, open mouth, sparkling eyes, excited, blush"
