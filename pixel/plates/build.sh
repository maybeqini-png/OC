#!/bin/bash
# Upscale the chosen N5 plates (art/generated/anime_bg) to 1080 px height with Real-ESRGAN. Run from pixel/.
# MODELS = folder with realesr-animevideov3-x2.param/.bin from the realesrgan-ncnn-vulkan v0.2.5.0 release.
S=../art/generated/anime_bg
u() { python3 upscale.py $S/$1.png plates/$2.png --models "$MODELS" ${3:-}; }
u p01_curtain_closed_9501 curtain_closed
u p02_stage_open_9531 curtain_open
u t3_sky_9301 sky
u p03_sunset_9502 sunset
u p05_shock_9513 shock
u p06_blush_9504 blush
u t1_pop_9101 pop
u p07_night_9505 night
u p08_pink_pop_9506 pinkpop
u p09_twilight_9507 twilight
u p11_festival_9529 festival
u p12_dawn_9510 dawn
u p10_climb_9508 climb "--height 0"
python3 -c "
from PIL import Image
im = Image.open('plates/climb.png'); im.resize((1920, round(im.height * 1920 / im.width)), Image.Resampling.LANCZOS).save('plates/climb.png')"
