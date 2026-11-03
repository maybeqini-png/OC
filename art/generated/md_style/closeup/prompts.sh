#!/bin/bash
# Game-style close-ups for the stage cut-ins (pixel/mdcutin.py). Owner 2026-11-03: the cut-ins showed the stream-cam
# bust, mixing the streamer with the in-game character. The close-up is now the in-game XIYIN: an upper-body crop of
# her game drawing (sheet colours, canonical eye, N5-fitted face, the one paw mic when armed) scaled up to 832x1216
# (guide_*.png), sharpened by a light V5 img2img (same seed and prompt for all). Normal size = 0 Anlas.
OUT=art/generated/md_style/closeup
M=nai-diffusion-5-full
P="1girl, solo, chibi, cat girl, navy blue cat ears, pink inner ear, very long hair, straight hair, royal blue hair, messy bangs, hair between eyes, ahoge, blue cat hairclip, big round blue eyes, sparkling eyes, oversized navy sweater, navy sailor collar, sleeves past wrists, striped cuffs, upper body, close-up, anime, clean lineart, cel shading, flat color, white background, simple background, sharp focus"
N="half-closed eyes, narrow eyes, cyan hair, purple hair, gradient hair, mature, adult, text, watermark, signature, lowres, blurry, bad anatomy, extra fingers, nsfw, suggestive"
for f in $OUT/guide_*.png; do
  n=$(basename $f .png); n=${n#guide_}
  o="$OUT/${n}_${S:-0.30}_63001.png"
  [ -f "$o" ] || python3 .claude/skills/oc-gen/scripts/nai.py img2img --model $M --image "$f" --strength ${S:-0.30} --seed 63001 --w 832 --h 1216 --prompt "$P" --negative "$N" --out "$o"
done
