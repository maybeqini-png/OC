#!/bin/bash
# Upscale the chosen N5 plates (art/generated/anime_bg) to 1080 px height with Real-ESRGAN. Run from pixel/.
# MODELS = folder with realesr-animevideov3-x2.param/.bin from the realesrgan-ncnn-vulkan v0.2.5.0 release.
S=../art/generated/anime_bg
u() { python3 upscale.py $S/$1.png plates/$2.png --models "$MODELS" ${3:-}; }
u p01_curtain_closed_9501 curtain_closed
u p02_stage_open_9531 curtain_open
u z_sky_9972 sky      # XIYIN stage redraw (2026-11-03); before: t3_sky_9301
u z_sunset_9972 sunset      # XIYIN stage redraw (2026-11-03); before: p03_sunset_9502
u p05_shock_9513 shock
u p06_blush_9504 blush
u t1_pop_9101 pop   # not used: hand-made backdrop in pixel/mdbg.py
u z_night_9971 night      # XIYIN stage redraw (2026-11-03); before: p07_night_9505
u p08_pink_pop_9506 pinkpop   # not used: hand-made backdrop in pixel/mdbg.py
u z_twilight_9972 twilight      # XIYIN stage redraw (2026-11-03); before: p09_twilight_9507
u z_festival_9971 festival      # XIYIN stage redraw (2026-11-03); before: p11_festival_9529
u p12_dawn_9510 dawn
u t_climb_9962 climb "--height 0"   # weeping-eyes climb (2026-11-03, picked from t_climb_996x); before: z_climb_9972
python3 -c "
from PIL import Image
im = Image.open('plates/climb.png'); im.resize((1920, round(im.height * 1920 / im.width)), Image.Resampling.LANCZOS).save('plates/climb.png')"
# the streaming room (opening / ending, VTuber cam backdrop): v3 take 9712, fitted to 1920 px width, centre-cropped to 1080
u ../v3/r02_room_9712 room "--height 0"
python3 -c "
from PIL import Image
im = Image.open('plates/room.png'); im = im.resize((1920, round(im.height * 1920 / im.width)), Image.Resampling.LANCZOS)
t = (im.height - 1080) // 2; im.crop((0, t, 1920, t + 1080)).save('plates/room.png')"  # monitor screen = stream.MON
