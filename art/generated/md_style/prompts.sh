#!/bin/bash
# Muse Dash-like game layer (2026-11-02): original enemies / obstacles in a flat HD style (thick outline, flat
# two-tone cel shading, bright colours, glowing accents), XIYIN-themed (cats, streaming). Reference study:
# docs/rhythm_game_style_reference.md. Free normal-size V5 (1024x1024, 28 steps, 0 Anlas).
# Run one set with ONLY=<glob on the output file name>.
# 2026-11-02 OWNER VERDICT: the m_* / o_* monster takes are REJECTED ("completely unsatisfactory": generic
# clip-art look, thick black outlines, glossy sticker shading, unrelated themes and palettes, static poses).
# Kept only as a record; not used in the video. x_run_* (HD chibi runner tests) not yet reviewed.
nai_guard() {
  local prev="" out=""
  for a in "$@"; do [ "$prev" = "--out" ] && out="$a"; prev="$a"; done
  if [ -n "$ONLY" ] && [[ "$(basename "$out")" != $ONLY ]]; then return 0; fi
  [ -f "$out" ] || python3 .claude/skills/oc-gen/scripts/nai.py "$@"
}
M=nai-diffusion-5-full
OUT=art/generated/md_style
STYLE="no humans, solo, mascot character, chibi, simple design, flat color, thick dark outline, cel shading, two-tone shading, vector art, bright saturated colors, glossy highlight, full body, centered, white background, simple background"
NEG="pixel art, sprite, 3d, realistic, photo, text, watermark, signature, multiple views, lowres, blurry, jpeg artifacts, gradient background, shadow on ground, human, girl, nsfw"
gen() {  # name seed tags
  nai_guard generate --model $M --prompt "$3, $STYLE" --negative "$NEG" --w 1024 --h 1024 --seed $2 --out "$OUT/$1_$2.png"
}
for seed in 41001 41002; do
  gen m_mouse $seed "cute round wind-up toy robot mouse, grey metal body, big round ears, red ribbon bow on ear, golden wind-up key on back, big shiny black eyes, small pink nose, tiny wheels, side view, facing left"
  gen m_box $seed "cute cardboard box creature, cat ears on top of the box, big round glowing yellow eyes peeking out from the box, small paws, tape on the box, side view, facing left"
  gen m_bubble $seed "cute flying speech bubble monster, light lavender bubble body, small bat wings, wide grinning mouth, laughing, closed eyes, fang, floating, facing left"
  gen m_taiyaki $seed "cute flying taiyaki fish monster, golden brown fish-shaped cake, small white angel wings, big round eyes, open mouth, floating, side view, facing left"
  gen o_yarn $seed "spiky ball of pink yarn, knitting needles sticking out, angry eyebrows, round obstacle, rolling, menacing but cute"
done
# XIYIN as an HD chibi runner in the same flat style (side view, facing right). Design tags from README section 1.
XY="1girl, solo, chibi, 2.5 heads tall, young girl, cat girl, navy blue cat ears, pink inner ear, very long hair, royal blue hair, messy bangs, ahoge, blue cat hairclip, blue eyes, oversized navy sweater, sleeves past wrists, navy sailor collar, light blue stripes on collar, navy shorts, black thighhighs, black boots, blue cat tail"
XSTYLE="flat color, thick dark outline, cel shading, two-tone shading, vector art, bright colors, game sprite, full body, white background, simple background"
XNEG="pixel art, 3d, realistic, text, watermark, signature, multiple views, lowres, blurry, mature, adult, tall, nsfw, suggestive, cleavage, panties, shadow on ground, cyan hair, purple hair"
gx() { nai_guard generate --model $M --prompt "$XY, $3, $XSTYLE" --negative "$XNEG" --w 1024 --h 1024 --seed $2 --out "$OUT/$1_$2.png"; }
for seed in 42001 42002 42003; do
  gx x_run $seed "running, from side, profile, facing right, dynamic pose, motion lines, determined smile"
done
# run cycle as one sheet (the same character is more consistent inside one image than across generations)
gsheet() { nai_guard generate --model $M --prompt "$XY, $3, $XSTYLE" --negative "$XNEG, different characters, different outfits" --w 1536 --h 640 --seed $2 --out "$OUT/$1_$2.png"; }
for seed in 43001 43002 43003 43004; do
  gsheet x_runsheet $seed "sprite sheet, running animation sequence, 4 frames in a row, same character repeated, from side, facing right, running, legs in different positions, evenly spaced"
done
