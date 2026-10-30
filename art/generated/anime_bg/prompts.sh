#!/bin/bash
# Style test (2026-10-30): song-motif props and graphic backdrops in a 2D anime pop style (N5, 0 Anlas sizes).
# Takes rejected for garbled lettering or an off-brief subject were deleted after review (s4_curtain_9404,
# t2_stage_9201, p05_shock_9503, p11_festival_9509/9519, k01_check_9601/9621, k02_trophy_9602, k11_lantern_9611,
# p02_stage_open_9532); their manifest rows stay for provenance. Chosen takes: pixel/scene.py, pixel/plates/build.sh.
NAI="python3 .claude/skills/oc-gen/scripts/nai.py"
M=nai-diffusion-5-full
OUT=art/generated/anime_bg
NEG="text, watermark, signature, logo, letters, words, numbers, humans, 1girl, 1boy, person, realistic, photo, 3d, render, blurry, jpeg artifacts, lowres, nsfw, cyberpunk, neon, sci-fi, hologram"
ANIME="anime style, flat color, clean lineart, cel shading, kawaii, pop, vivid colors, 2d illustration"
STK="no humans, sticker, single object, centered, simple background, white background, $ANIME"
gen() { [ -f "$OUT/$1_$2.png" ] || $NAI generate --model $M --w $3 --h $4 --seed $2 --prompt "$5" --negative "$NEG" --out "$OUT/$1_$2.png"; }
gen t1_pop 9101 1536 640 "no humans, abstract background, pop art, sunburst rays, polka dot pattern, big stars, hearts, cat paw prints, ribbons, confetti, royal blue and white and pink, $ANIME"
gen t2_stage 9201 1536 640 "no humans, scenery, anime background, small theater stage, navy blue velvet curtains, warm spotlights, confetti, golden stars, wooden stage floor, $ANIME"
gen t3_sky 9301 1536 640 "no humans, scenery, anime background, bright blue summer sky, huge white cumulus clouds, school rooftop with fence, water tank, $ANIME"
gen s1_crown 9401 1024 1024 "$STK, golden crown with blue gems, sparkles"
gen s2_phone 9402 1024 1024 "$STK, smartphone with a camera on screen, big red x mark, sparkles"
gen s3_mic 9403 1024 1024 "$STK, vintage microphone with a navy ribbon bow, music notes"
gen s4_curtain 9404 1536 640 "no humans, theater stage curtains, navy blue velvet curtains with gold trim, drawn open, empty center, spotlight, $ANIME"
# ---- full set (2026-10-30): plates per song section + lyric props
BG="no humans, scenery, anime background, cel shading, clean lineart, vivid colors, 2d illustration"
gen p01_curtain_closed 9501 1536 640 "no humans, theater stage, closed navy blue velvet curtains with gold trim and gold fringe, warm spotlight circle on the curtain, wooden stage floor, $ANIME"
gen p03_sunset 9502 1536 640 "$BG, evening, orange and pink sunset sky, big clouds lit from below, residential town rooftops, telephone poles and power lines, warm light"
gen p05_shock 9503 1536 640 "no humans, abstract background, manga style, concentration lines, speed lines, screentone dots, navy blue and white, dramatic"
gen p06_blush 9504 1536 640 "no humans, abstract background, pastel pink, hearts, polka dot pattern, sparkles, soft stripes, kawaii, pop, $ANIME"
gen p07_night 9505 1536 640 "$BG, night sky full of stars, milky way, shooting stars, grassy riverbank, calm river reflecting stars, distant town lights"
gen p08_pink_pop 9506 1536 640 "no humans, abstract background, pop art, pink and white checkerboard, polka dots, stars, sparkles, camera flash bursts, ribbons, $ANIME"
gen p09_twilight 9507 1536 640 "$BG, dusk, purple and pink sky, first stars, riverside embankment, small bridge, quiet town, street lights turning on"
gen p10_climb 9508 704 1472 "$BG, vertical, tall image, sky above the clouds, golden sunset clouds at the bottom, deep blue night sky with stars at the top, crescent moon"
gen p11_festival 9509 1536 640 "$BG, night summer festival, big colorful fireworks in the sky, rows of paper lanterns, festival stalls, warm glow"
gen p12_dawn 9510 1536 640 "$BG, early morning sunrise, pastel pink and blue sky, soft clouds, school rooftop with fence, water tank, fresh light"
gen k01_check 9601 1024 1024 "$STK, clipboard with a checklist and big green check marks"
gen k02_trophy 9602 1024 1024 "$STK, shiny gold trophy cup with a blue ribbon, sparkles"
gen k03_stamp 9603 1024 1024 "$STK, red rubber stamp with a wooden handle"
gen k04_star 9604 1024 1024 "$STK, big shiny yellow star with a cute face, sparkles"
gen k05_camera 9605 1024 1024 "$STK, cute pink instant camera, flash"
gen k06_heart 9606 1024 1024 "$STK, glossy pink heart with a white highlight"
gen k07_penlight 9607 1024 1024 "$STK, two glowing blue concert penlights crossed"
gen k08_bandage 9608 1024 1024 "$STK, adhesive bandage with a cat paw print"
gen k09_controller 9609 1024 1024 "$STK, retro white game controller with blue buttons"
gen k10_catplush 9610 1024 1024 "$STK, navy blue cat plushie, round, sitting"
gen k11_lantern 9611 1024 1024 "$STK, red paper lantern glowing"
gen k12_ribbon 9612 1024 1024 "$STK, big navy blue ribbon bow"
# v2 of the takes that came out with garbled lettering (AI tell): stronger no-text negatives, letter-free subjects
NEGT="$NEG, katakana, hiragana, kanji, onomatopoeia, sound effects, signboard, writing, label, plaque, caption"
gen2() { [ -f "$OUT/$1_$2.png" ] || $NAI generate --model $M --w $3 --h $4 --seed $2 --prompt "$5" --negative "$NEGT" --out "$OUT/$1_$2.png"; }
gen2 p05_shock 9513 1536 640 "no humans, abstract background, manga style, concentration lines, speed lines, screentone dots, navy blue and white, dramatic, empty, no text"
gen2 p11_festival 9519 1536 640 "$BG, night summer festival by a river, huge colorful fireworks in the sky, long string of glowing paper lanterns, reflections on the water, crowd-free, no signs"
gen2 p11_festival 9529 1536 640 "$BG, night sky full of big colorful fireworks, rooftops of a small town, strings of glowing paper lanterns, warm glow, no signs"
gen2 k01_check 9621 1024 1024 "$STK, clipboard with blank paper and three big green check marks, no text"
gen2 k02_trophy 9622 1024 1024 "$STK, shiny gold trophy cup with a navy ribbon bow, star on top, sparkles, no text"
# open stage v2 (2026-10-30): the first open-curtain take had a flat grey centre
gen2 p02_stage_open 9531 1536 640 "no humans, theater stage seen from the audience, navy blue velvet curtains drawn open with gold trim, painted backdrop of a bright blue sky with big white clouds, warm spotlights, wooden stage floor, $ANIME"
gen2 p02_stage_open 9532 1536 640 "no humans, small cute theater stage, navy blue velvet curtains drawn open, gold tassels, backdrop with stars and a crescent moon cutout, warm spotlights, footlights, wooden stage floor, $ANIME"
