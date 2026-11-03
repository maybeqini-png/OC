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
# ---- tense plates (2026-11-03). Owner: "the background fails to create a tense atmosphere". Muse Dash boss / tense
# sections: dark magenta-purple stages, bright neon accents, strong rim light. V5 img2img from the chosen plates
# (same layout, so the camera pans stay valid), strength 0.62.
NEGT="text, watermark, signature, logo, letters, words, numbers, humans, 1girl, 1boy, person, realistic, photo, 3d, render, blurry, jpeg artifacts, lowres, nsfw, pastel, washed out, calm, peaceful, daylight"
TENSE="dramatic, intense atmosphere, high contrast, deep shadows, strong rim light, glowing magenta and cyan light, dark crimson and violet palette, dynamic, $ANIME"
i2i() { [ -f "$OUT/$1_$2.png" ] || $NAI img2img --model $M --image "$OUT/$3.png" --strength 0.62 --w $4 --h $5 --seed $2 --prompt "$6" --negative "$NEGT" --out "$OUT/$1_$2.png"; }
for s in 9901 9902; do
  i2i x_festival $s p11_festival_9529 1536 640 "$BG, night summer festival climax, huge fireworks exploding across a dark crimson and violet sky, smoke lit magenta, rows of red paper lanterns glowing hot, festival stalls in silhouette, sparks raining down, $TENSE"
  i2i x_twilight $s p09_twilight_9507 1536 640 "$BG, ominous dusk, blood red and deep purple sky, dark storm clouds rolling in, riverside embankment in shadow, small bridge silhouette, street lights glowing, wind, $TENSE"
  i2i x_climb $s p10_climb_9508 704 1472 "$BG, vertical, tall image, racing upward through dark storm clouds, lightning glow inside the clouds, red full moon above, deep violet night sky with stars at the top, $TENSE"
done
# ---- absurd stages (2026-11-03). Owner: "Redo the backgrounds directly to match the benchmark game style; I want
# them absurd." Benchmark look (official Muse Dash trailer / screenshots): flat vector shapes, bold limited palette
# per stage, soft atmospheric haze for depth, almost no linework, surreal giant objects. Original XIYIN themes only.
NEGA="text, watermark, signature, logo, letters, words, numbers, humans, 1girl, 1boy, person, character, realistic, photo, 3d, render, detailed texture, thick lineart, sketch, blurry, jpeg artifacts, lowres, nsfw"
ABS="no humans, scenery, 2d side-scrolling game stage background, surreal, absurd, whimsical, giant objects, flat vector illustration, simple bold shapes, flat colors, limited palette, soft atmospheric haze, layered depth, no lineart, clean, vivid, wide shot"
ga() { [ -f "$OUT/$1_$2.png" ] || $NAI generate --model $M --w $3 --h $4 --seed $2 --prompt "$5, $ABS" --negative "$NEGA" --out "$OUT/$1_$2.png"; }
for s in 9951 9952; do
  ga y_sky $s 1536 640 "pastel sky world, giant smiling cat-shaped clouds, floating whipped cream islands, a huge game controller drifting like a blimp, rainbow ribbons, sky blue, white, sunny yellow and pink"
  ga y_sunset $s 1536 640 "sunset dessert land, gigantic pudding mountains with caramel tops, a river of syrup, the setting sun is a giant cat face wearing headphones, wafer towers, orange, peach and violet"
  ga y_pop $s 1536 640 "candy factory, towering gumball machines, lollipop trees, conveyor belts carrying giant sweets, pipes, candy pink, mint green and lemon yellow"
  ga y_night $s 1536 640 "neon night city made of giant speaker towers and streaming microphones, a huge cat head moon wearing headphones, glowing windows, deep purple and magenta with cyan and orange glows"
  ga y_pinkpop $s 1536 640 "pink pop world, buildings shaped like hearts and cameras, giant cat paw prints stamped across the sky, camera flash bursts, ribbons, pink and white checkerboard hills, hot pink, white and baby blue"
  ga y_twilight $s 1536 640 "dreamlike dusk, an upside-down town hanging from the sky, floating teacups and giant clocks, a mountain shaped like a sleeping cat, purple, pink and indigo"
  ga y_festival $s 1536 640 "wild summer festival climax, giant daruma and lucky cat statues towering over the stalls, fireworks shaped like cat faces, swarms of paper lanterns, crimson, gold and violet, dramatic"
  ga y_climb $s 704 1472 "vertical, tall image, an endless staircase of piano keys and game cartridges spiraling up into the sky, floating music notes, a giant cat face moon at the top, golden clouds at the bottom, violet night above"
done
# 2026-11-03 OWNER VERDICT: x_* (tense img2img) superseded before review; y_* (absurd stages) REJECTED: "It looks too
# AI-generated, I don't like it. No cybernetic AI aesthetic." Kept as a record only; not used (plates/build.sh unchanged).
# ---- XIYIN stages (2026-11-03). Owner: "Design the scenes to fit my character, following the reference game style.
# I mainly dislike the cyber aesthetic." Her palette (navy, cobalt, sky blue, white, soft pink) and her motifs (cats,
# school rooftop, her room, ribbons, stars, the sleeping-cat patch), flat hazy storybook stages; no neon / tech.
NEGX="text, watermark, signature, logo, letters, words, numbers, signboard, humans, 1girl, 1boy, person, character, realistic, photo, 3d, render, neon, cyberpunk, sci-fi, futuristic, glowing lights, hologram, technology, machine, robot, speakers, screens, pipes, game controller, skyscrapers, city skyline, detailed texture, busy, cluttered, thick lineart, blurry, jpeg artifacts, lowres, nsfw"
XST="no humans, scenery, 2d side-scrolling game stage background, whimsical storybook, flat vector illustration, simple bold shapes, minimal details, flat colors, limited palette, navy blue, cobalt blue, sky blue, white and soft pink, soft atmospheric haze, layered depth, no lineart, cute, wide shot"
gx() { [ -f "$OUT/$1_$2.png" ] || $NAI generate --model $M --w $3 --h $4 --seed $2 --prompt "$5, $XST" --negative "$NEGX" --out "$OUT/$1_$2.png"; }
for s in 9971 9972; do
  gx z_sky $s 1536 640 "bright blue sky, a school rooftop with a fence floating among giant cat-shaped clouds, paper airplanes, a blue ribbon streaming across the sky"
  gx z_sunset $s 1536 640 "sunset over a small town whose rooftops have cat ears, telephone poles, a huge sleeping navy cat lying on the far hills, warm orange sky fading to navy"
  gx z_pop $s 1536 640 "a giant cozy toy room landscape, mountains of cat plushies, huge yarn balls, stacked building blocks, ribbons and stars, blue and pink pop colors"
  gx z_night $s 1536 640 "quiet night, a calm river and small houses, the moon is a sleeping cat curled up, many stars, soft navy sky, a few warm paper lanterns"
  gx z_pinkpop $s 1536 640 "a stage made of giant cushions and pillows, big hearts, cat paw stamps and polka dots in the sky, ribbons, pink and baby blue"
  gx z_twilight $s 1536 640 "purple and navy dusk, rolling hills shaped like cat tails, a school silhouette, a cat-shaped moon rising, first stars"
  gx z_festival $s 1536 640 "summer night festival, rows of cat-face paper lanterns, a giant lucky cat statue, fireworks shaped like cat faces and stars, blank stalls with no signs, navy sky with red and gold accents"
  gx z_climb $s 704 1472 "vertical, tall image, a tall staircase of stacked books and cushions rising into the night sky, a crescent moon with a cat curled on it at the top, stars, soft clouds at the bottom"
done
# z_* picks shown to the owner (not yet wired into plates/build.sh): sky 9972, sunset 9972, pop 9971, night 9971,
# pinkpop 9971, twilight 9972, festival 9971 (9972 has lettering on stalls), climb 9972.
# 2026-11-03 OWNER: y_climb_9951 / 9952 (piano-key staircase to a cat-face moon) "I think this design is great. Do you
# have anything even better?" -> variations on that design in the same ABS style.
for s in 9981 9982 9983 9984 9985 9986; do
  ga w_climb $s 704 1472 "vertical, tall image, a winding staircase of white piano keys spiraling up into a violet starry sky, a giant smiling cat face moon wearing a blue ribbon at the top, falling music notes and little stars, a navy blue ribbon twisting around the stairs, golden and orange clouds at the bottom, magical and grand"
done
