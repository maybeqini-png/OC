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

# ---- round 2 (2026-11-02): the owner rejected round 1. Rules taken from Muse Dash gameplay (Steam screenshots,
# Bilibili gameplay; see docs/rhythm_game_style_reference.md): flat fills in 2-3 tones, no black outline (outline = a
# darker or lighter shade of the body colour, thin, slightly wobbly), very simple primitive shapes (orb, blob, cloud,
# cone, box), minimal faces (dot / line eyes, or a visor with one glowing half-moon eye), palette tied to the stage.
# Original XIYIN-themed designs (cats, streaming, sweets), not copies of Muse Dash creatures.
# V5 free allowance ran out (HTTP 402, 30 Anlas per image), so round 2 uses V4.5 (free on Opus, measured 0 Anlas).
MSTYLE="no humans, solo, game enemy sprite, simple shapes, flat color, no lineart, colored outline, thin outline, minimalist, limited palette, two-tone, cute, kawaii, centered, white background, simple background"
MNEG="black outline, thick outline, dark outline, lineart, sketch, glossy, shiny, highlight, gradient, shading, detailed, texture, realistic, 3d, sticker, emoji, text, watermark, signature, multiple views, lowres, blurry, jpeg artifacts, shadow, ground, human, nsfw"
gm() { nai_guard generate --model nai-diffusion-4-5-full --prompt "$3, $MSTYLE" --negative "$MNEG" --w 1024 --h 1024 --seed $2 --out "$OUT/$1_$2.png"; }
# sky stage family (pastel blue sky): palette cyan / white / sunny yellow / pink accents
for seed in 44001 44002 44003; do
  gm s_mochi $seed "round mochi blob creature with cat ears, pale cyan body, light blue outline, tiny dot eyes, small open smiling mouth, pink blush dots, bouncing"
  gm s_plane $seed "small flying paper airplane creature with cat ears, white and sky blue paper, simple dot eyes, cheeky smile, flying left, speed lines"
  gm s_pinwheel $seed "spinning toy pinwheel saw obstacle, four pastel yellow and cyan blades, round pink center, simple, flat"
done
# round 2b: one flat shadow tone, a coloured outline all around, readable face at small size, a XIYIN touch
MSTYLE2="no humans, solo, game enemy sprite, simple rounded shapes, flat color, flat shading with one darker shadow tone, colored outline, outline darker shade of body color, minimalist, limited palette, saturated pastel colors, cute, kawaii, dynamic tilted pose, centered, white background, simple background"
gm2() { nai_guard generate --model nai-diffusion-4-5-full --prompt "$3, $MSTYLE2" --negative "$MNEG" --w 1024 --h 1024 --seed $2 --out "$OUT/$1_$2.png"; }
for seed in 44011 44012 44013 44014; do
  gm2 s2_mochi $seed "round mochi blob creature with pointed cat ears, mint cyan body, darker teal outline, tiny navy sailor collar with light blue stripe, black dot eyes, small open smiling mouth with a fang, pink blush dots, hopping, facing left"
  gm2 s2_plane $seed "paper airplane folded into a cat head shape, white paper with sky blue folds and outline, cat ears, two black dot eyes, cheeky open mouth, flying fast toward the left, tilted, speed lines"
done
