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
# ---- round 3 (2026-11-02): owner: "the monsters still don't look good enough". Diagnosis vs the Muse Dash close-ups:
# theirs are designed creatures with parts (helmet + visor + glowing eye, nested boxes + lens eyes), attitude (smug
# grins, angry brows, teeth) and clean cel finish (steady line weight, one shadow shape, light rim); round 2 were plain
# blobs with emoji faces. Round 3 explores with design sheets (one family per image keeps the style consistent).
SSTYLE="no humans, game enemy design sheet, six different small monsters, mobile rhythm game enemies, chibi creatures, clean vector illustration, crisp clean lineart, colored lineart, cel shading, one shadow tone, rim light, simple bold shapes, limited palette, mischievous expressions, smug grin, angry eyebrows, sharp little fangs, glowing eyes, dynamic poses, white background, simple background, evenly spaced"
SNEG="human, girl, boy, text, words, letters, watermark, signature, logo, black thick outline, sketch, messy lines, realistic, 3d, photo, gradient background, scenery, lowres, blurry, jpeg artifacts, nsfw"
gsh() {  # name seed tags  (V5 first, V4.5 if V5 is not free)
  nai_guard generate --model $M --prompt "$3, $SSTYLE" --negative "$SNEG" --w 1216 --h 832 --seed $2 --out "$OUT/$1_$2.png" ||
  nai_guard generate --model nai-diffusion-4-5-full --prompt "$3, $SSTYLE" --negative "$SNEG" --w 1216 --h 832 --seed $2 --out "$OUT/$1_${2}_v45.png"
}
for seed in 45001 45002 45003; do
  gsh sh_sky $seed "sky and clouds theme, cat theme, sky blue, white and sunny yellow with pink accents, cloud cat with wings, paper plane cat, round mochi cat with helmet visor, kite creature, propeller drone cat"
  gsh sh_night $seed "night city theme, cat theme, deep purple and magenta bodies with neon cyan and orange glowing eyes, round helmet cat orb with visor, bat-winged cat ghost, speaker robot cat, lantern creature, drone with lens eye"
done
# 2026-11-02 OWNER VERDICT (round 3): best is sh_night_45002 (V5): clean cel finish, glowing eyes, fangs, attitude.
# ---- round 4 (2026-11-02, V5 paid at the owner's discretion): one family sheet per stage in the sh_night_45002
# quality but with the style rules (coloured outline = darker shade of the body, flat 2-3 tones, stage palette) and
# the three game roles: ground enemy, flying enemy, spinning saw obstacle. Original XIYIN themes (cats, streaming,
# sweets).
FSTYLE="no humans, game enemy design sheet, three monsters in a row, mobile rhythm game enemies, chibi creatures, clean vector illustration, colored outline, outline darker shade of body color, flat color, cel shading, one shadow tone, rim light, simple bold shapes, limited palette, mischievous expressions, smug grin, angry eyebrows, sharp little fangs, glowing eyes, dynamic poses, white background, simple background, evenly spaced"
FNEG="human, girl, boy, text, words, letters, watermark, signature, logo, black outline, thick black lineart, sketch, messy lines, gradient, glossy, realistic, 3d, photo, scenery, gradient background, lowres, blurry, jpeg artifacts, nsfw"
gfam() { nai_guard generate --model $M --prompt "$3, $FSTYLE" --negative "$FNEG" --w 1216 --h 832 --seed $2 --out "$OUT/$1_$2.png"; }
for seed in 46001 46002; do
  gfam f_sky $seed "pastel sky theme, cat theme, sky blue and white bodies with sunny yellow and pink accents, left: round cloud cat walking with pilot goggles visor and glowing yellow eyes, middle: flying paper airplane cat with propeller and fangs, right: spinning pinwheel saw blade with a grumpy cat face in the center"
  gfam f_sunset $seed "sunset theme, sweets theme, cat theme, warm orange, peach and coral bodies with violet shadows, left: walking pudding cat with caramel top and angry eyebrows, middle: flying taiyaki fish cat with small bat wings, right: spinning orange slice saw blade with teeth and a smug face"
  gfam f_pop $seed "candy pop theme, sweets theme, cat theme, candy pink, mint and lemon yellow bodies, left: walking gumball machine cat robot with a camera lens eye, middle: flying wrapped candy bat cat, right: spinning swirl lollipop saw blade with jagged teeth and glaring eyes"
  gfam f_night $seed "night city theme, streaming theme, cat theme, deep purple and magenta bodies with neon cyan and orange glowing eyes, left: walking speaker robot cat with a lens eye, middle: flying bat-winged cat orb with fangs, right: spinning neon gear saw blade with a glowing visor eye"
  gfam f_festival $seed "summer festival theme, cat theme, red, gold and cream bodies, left: walking daruma cat with angry eyebrows, middle: flying paper lantern cat with little wings and glowing eyes, right: spinning firework pinwheel saw blade with a fanged grin"
done
# Round 4 pick: f_night_46002 (speaker robot cat, bat cat orb, gear saw with eye) for the first game-scale mock-up.
# Runners-up: f_sunset_46002 (pudding cat, taiyaki bat, orange saw), f_sky_46002 (goggles cloud cat).
# ---- solo sprites (one creature per image, white background) for clean cut-outs with pixel/mdsprites.py
SOLO="no humans, solo, single monster, mobile rhythm game enemy, chibi creature, full body, clean vector illustration, colored outline, outline darker shade of body color, flat color, cel shading, one shadow tone, rim light, simple bold shapes, limited palette, white background, simple background, centered, no shadow"
SNEG2="$FNEG, multiple views, character sheet, two monsters, shadow, cast shadow, floor, ground, motion blur, speed lines, effects, sparkles"
gsolo() { nai_guard generate --model $M --prompt "$3, $SOLO" --negative "$SNEG2" --w 1024 --h 1024 --seed $2 --out "$OUT/$1_$2.png"; }
for seed in 47001 47002 47003; do
  gsolo n_ground $seed "night city theme, streaming theme, small walking robot cat, deep purple armored body, round purple helmet with cat ears, black screen visor face with glowing cyan eyes and orange pupils, smug grin with sharp white fangs, orange speaker headphones on the sides, round speaker on the chest, stubby legs and paws, walking, from side, facing left"
  gsolo n_air $seed "night city theme, flying cat orb monster, round deep purple body, small cat ears, purple bat wings spread, glowing orange angry eyes, magenta belly, sly grin with two fangs, floating, facing left"
  gsolo n_saw $seed "night city theme, spinning circular saw blade obstacle, dark slate gear disc, neon magenta jagged teeth, glowing cyan ring, single glowing orange eye in the center with an angry eyelid, round, flat, front view"
done
# 2026-11-02 OWNER VERDICT (night mock-up, md_mock_night.png): "It looks good, but pay close attention to the art
# quality frame by frame." -> same recipe for the other families (designs from the round 4 sheets, *_46002 mostly).
for seed in 48001 48002 48003; do
  gsolo k_ground $seed "pastel sky theme, walking round cloud cat monster, fluffy white cloud body with sky blue shading, pointed cat ears, pilot goggles with a yellow tinted visor, glowing yellow eyes, smug grin with fangs, pink blush, little paws, medium blue outline, walking, from side, facing left"
  gsolo k_air $seed "pastel sky theme, flying paper airplane cat monster, white paper wings with sky blue folds, cat head with pointed ears at the front, propeller on top with a pink hub, sharp yellow eyes, open mouth with fangs, medium blue outline, flying, facing left"
  gsolo k_saw $seed "pastel sky theme, spinning circular saw blade obstacle, white jagged blade ring with sky blue outline, pink pinwheel petals inside, grumpy blue cat face in the center with fangs, round, flat, front view"
  gsolo u_ground $seed "sunset theme, sweets theme, walking pudding cat monster, custard yellow pudding body, dark caramel top with cat ears, angry white eyes, fanged scowl, short violet legs, violet outline, walking, from side, facing left"
  gsolo u_air $seed "sunset theme, sweets theme, flying taiyaki fish monster, golden brown fish shaped cake body, scale pattern, purple bat wings, angry eyes, open mouth, coral outline, flying, facing left"
  gsolo u_saw $seed "sunset theme, spinning orange slice saw blade obstacle, bright orange citrus slice with segments, jagged sawtooth rim, evil grin with sharp teeth, narrow violet eyes, round, flat, front view"
  gsolo p_ground $seed "candy pop theme, sweets theme, walking gumball machine robot cat, pink round glass dome head with cat ears, colorful gumballs inside the dome, big camera lens eye, smug grin with fangs, pink body, stubby legs, magenta outline, walking, from side, facing left"
  gsolo p_air $seed "candy pop theme, sweets theme, flying candy bat cat, round mint green body wrapped like a candy with pink striped twisted wrapper ends as wings, cat ears, angry eyes, fanged grin, teal outline, flying, facing left"
  gsolo p_saw $seed "candy pop theme, spinning swirl lollipop saw blade obstacle, pink and lemon yellow spiral candy disc, jagged white sugar teeth around the rim, mischievous glaring eyes and a fanged grin on the candy, round, flat, front view"
  gsolo f2_ground $seed "summer festival theme, walking daruma cat monster, round red daruma body with cat ears, cream face with bold angry eyebrows, golden pattern on the belly, small brown paws, dark red outline, walking, from side, facing left"
  gsolo f2_air $seed "summer festival theme, flying paper lantern cat monster, glowing cream paper lantern body with ribs, cat ears, small golden wings, glowing orange eyes, fanged grin, dark red outline, floating, facing left"
  gsolo f2_saw $seed "summer festival theme, spinning pinwheel saw obstacle, red and cream paper pinwheel blades with sharp tips, golden round center with a grinning face and sharp teeth, angry eyes, round, flat, front view"
done
# picks: k 48001/48002/48003, u 48001 x3, p 48001/48002/48003, f2 ground 48001 (48002 has lettering), air 48002.
# Festival saws all had a pinwheel stick (wrong when spinning): saw again without one.
for seed in 48011 48012 48013; do
  gsolo f2_saw $seed "summer festival theme, spinning round saw blade obstacle shaped like a paper pinwheel, eight red and cream paper blades with sharp tips around a circle, golden round center with a grinning face and sharp teeth, angry eyes, no stick, no handle, round, flat, front view"
done
# ---- HD runner v2 (2026-11-02): on-model to the owner's sheet (x_run_4200x drew thighhighs and light shorts).
# True side view facing right; flat cel style with a clean dark navy line. The run cycle itself is rigged
# (one body drawing + drawn legs, as the approved pixel avatar), so only the body pose has to be good here.
XY2="1girl, solo, chibi, 2.5 heads tall, young girl, cat girl, from side, profile, facing right, looking ahead, navy blue cat ears, pink inner ear, very long straight hair, deep navy blue hair, one ahoge, small blue cat hairclip, blue half-closed eyes, smug, oversized dark navy sweater, sailor collar with cobalt blue stripes, navy necktie, sleeves past wrists, cobalt striped cuffs, dark grey shorts, navy cat tail, navy knee socks with a cobalt stripe, chunky black lace-up boots with blue soles"
XSTYLE2="game character sprite, full body, clean vector illustration, crisp clean lineart, dark navy lineart, flat color, cel shading, one shadow tone, simple design, white background, simple background, centered"
XNEG2="looking at viewer, front view, three-quarter view, from front, blunt bangs, hime cut, wide-eyed, cyan hair, purple hair, light blue hair, thighhighs, pantyhose, white shorts, skirt, pixel art, 3d, realistic, sketch, text, watermark, signature, multiple views, character sheet, lowres, blurry, jpeg artifacts, mature, adult, tall, nsfw, suggestive, shadow, floor, motion lines, speed lines, effects"
gx2() { nai_guard generate --model $M --prompt "$XY2, $3, $XSTYLE2" --negative "$XNEG2" --w 832 --h 1216 --seed $2 --out "$OUT/$1_$2.png"; }
for seed in 49001 49002 49003 49004 49005 49006; do gx2 y_run $seed "running, mid stride, arms swinging, leaning forward, hair flowing behind"; done
for seed in 49011 49012 49013; do gx2 y_punch $seed "cat punch, punching forward with one sleeve, arm fully extended forward, determined smug grin, running"; done
for seed in 49021 49022 49023; do gx2 y_air $seed "jumping, mid-air, swiping one arm forward and up, knees tucked, smug grin"; done
for seed in 49031 49032 49033; do gx2 y_hurt $seed "hurt, flinching backward, eyes shut tight, knocked back, arms up, comedic"; done
# y_* 4900x: poses and finish good and consistent, but hair and sweater read near-black (sheet: clearly blue hair).
# v3 of the tags: brighter hair, blue line instead of dark navy, black/dark hair in the negative.
XY3="${XY2/deep navy blue hair/royal blue hair, bright blue hair highlights}"
XY3="${XY3/oversized dark navy sweater/oversized navy blue sweater}"
XSTYLE3="${XSTYLE2/dark navy lineart/dark blue lineart}"
gx3() { nai_guard generate --model $M --prompt "$XY3, $3, $XSTYLE3" --negative "$XNEG2, black hair, dark hair, black sweater" --w 832 --h 1216 --seed $2 --out "$OUT/$1_$2.png"; }
for seed in 49101 49102 49103 49104; do gx3 z_run $seed "running, mid stride, arms swinging, leaning forward, hair flowing behind"; done
for seed in 49111 49112 49113; do gx3 z_punch $seed "cat punch, punching forward with one sleeve, arm fully extended forward, determined smug grin, running"; done
for seed in 49121 49122 49123; do gx3 z_air $seed "jumping, mid-air, swiping one arm forward and up, knees tucked, smug grin"; done
for seed in 49131 49132 49133; do gx3 z_hurt $seed "hurt, flinching backward, eyes shut tight, knocked back, arms up, comedic"; done
# picks for the HD runner: z_run_49102 (rig body), z_punch_49113, z_air_49123; hurt takes unused (none read as hurt).
# y_* takes: hair and sweater near-black, unused. All three picks are recoloured to the sheet by pixel/mdrecolor.py.
# ---- action pack (2026-11-03): owner asked for more varied character animation after a Muse Dash analysis
# (every hit a different attack drawing; see docs/rhythm_game_style_reference.md). Same tags and style as z_*.
for seed in 49201 49202 49203; do
  gx3 act_uppercut $seed "rising uppercut with one sleeve, cat paw punch upward, leaning back, one foot off the ground, determined grin"
  gx3 act_kick $seed "spinning roundhouse kick, one leg extended forward high, arms out for balance, hair swirling, smug"
  gx3 act_doublepaw $seed "pushing both sleeves forward together, double palm strike, cat paws, leaning forward, mouth open shouting"
  gx3 act_air_kick $seed "jumping, mid-air flying kick diagonally downward, one leg extended, arms back, determined"
  gx3 act_air_spin $seed "jumping, mid-air somersault, curled up spinning, tail and hair swirling, eyes closed smiling"
  gx3 act_air_slam $seed "jumping, mid-air, both sleeves raised overhead about to hammer down, mischievous grin"
  gx3 act_split $seed "mid-air split pose, one sleeve punching up and one leg kicking down at the same time, dynamic, confident"
  gx3 act_hold $seed "crouching low and leaning forward, one sleeve stretched forward, sliding, focused, wind in her hair"
  gx3 act_hurt $seed "knocked back, stumbling backward, eyes squeezed shut in a comic cry, arms flailing, small tears, cartoon dizzy"
  gx3 act_fever $seed "excited running, arms spread wide, big open smile, sparkling eyes, hair streaming"
  gx3 act_victory $seed "standing, victory pose, peace sign with one hand near her face, winking, smug smile, facing slightly toward the viewer"
done
# ---- bosses (2026-11-03): owner asked for mini-boss and main-boss scenes. Muse Dash bosses stay at the right edge
# and fire projectiles into both lanes. Same SOLO style as the monster families; facing left toward XIYIN.
for seed in 49301 49302 49303; do
  gsolo b_mini $seed "candy pop theme, giant boss version of a gumball machine robot cat, huge pink glass dome head full of colorful gumballs, cat ears, big camera lens eye glowing, smug fanged grin, chunky pink robot body with candy cannon arms, magenta outline, imposing, facing left"
  gsolo b_main $seed "summer festival theme, giant final boss, enormous red daruma lucky cat king, golden crown, one paw raised beckoning, glowing angry eyes, fanged grin, lantern ornaments, fireworks launcher on its back, dark red outline, imposing, facing left"
done
# close-up splash panel for the shatter transition (comic panel, no text)
SPL="$XY3, close-up, upper body, from side, three-quarter view, dynamic angle, determined smug grin, fist raised toward the viewer, speed lines background, manga style splash panel, bold flat colors, clean lineart, cel shading"
for seed in 49401 49402 49403; do
  nai_guard generate --model $M --prompt "$SPL" --negative "$XNEG2, text, letters, words, speech bubble, black hair" --w 1216 --h 832 --seed $seed --out "$OUT/splash_$seed.png"
done
# ---- weapons and floating companion (2026-11-03). Owner: "in Muse Dash and similar games the characters have cute
# weapons and hover gear". Observed (official trailer): each character attacks with a signature prop (a bass guitar,
# a violin-bow sword, a lollipop, a carrot) swung in a crescent smear, and a small winged chibi "Elfin" floats behind
# the character's shoulder. XIYIN versions, original designs tied to her streamer / cat theme and her palette.
WST="no humans, single object, game weapon item icon, cute, chunky shapes, clean vector illustration, crisp clean lineart, dark blue lineart, flat color, cel shading, one shadow tone, navy blue, cobalt blue, sky blue, white and soft pink, white background, simple background, centered"
WNEG="text, letters, words, logo, watermark, signature, human, girl, hand, realistic, 3d, photo, metal texture, gradient background, lowres, blurry, jpeg artifacts"
gw() { nai_guard generate --model $M --prompt "$3, $WST" --negative "$WNEG" --w 1024 --h 1024 --seed $2 --out "$OUT/$1_$2.png"; }
CST="no humans, single small mascot creature, chibi, floating, game companion fairy, clean vector illustration, crisp clean lineart, colored lineart, flat color, cel shading, one shadow tone, white background, simple background, centered"
gc() { nai_guard generate --model $M --prompt "$3, $CST" --negative "$WNEG" --w 1024 --h 1024 --seed $2 --out "$OUT/$1_$2.png"; }
for seed in 49501 49502; do
  gw w_pawmic $seed "oversized streaming microphone used as a hammer, big round navy mic head with a pink cat paw print grille, cat ears on top of the mic head, cobalt handle wrapped with a sky blue ribbon"
  gw w_pawhammer $seed "giant squeaky toy hammer shaped like a cat paw, soft round navy paw head with pink paw pads, white stitched seam, cobalt handle with a bell and a ribbon"
  gw w_cattail $seed "magical girl wand shaped like a long cat tail curling into a star at the tip, navy and cobalt stripes, small golden bell, sky blue ribbon"
  gc c_catdrone $seed "tiny floating round navy cat head drone with small propeller and cat ears, big blue screen eyes, little headphones, smug smile"
  gc c_sleepcat $seed "tiny sleepy light blue cat spirit floating on a small cloud, eyes closed, nightcap, little angel wings, round and soft"
done
for seed in 49511 49512; do
  gx3 wx_swing $seed "swinging an oversized navy microphone like a hammer with both hands, big round mic head with a pink cat paw print and cat ears, running, determined smug grin"
done
# ---- armed action pack v2 (2026-11-03). Owner: "the unarmed poses aren't working well". Pose rules from research
# (Clip Studio / Adobe dynamic-pose guides, cartoon movement fundamentals): one strong curved line of action through
# the whole body, pushed further than real, a clear silhouette with negative space, twisted torso / asymmetric
# shoulders and hips, the weapon extending the line of action, anticipation and follow-through as separate frames.
# Every pose holds her paw mic (w_pawmic): Muse Dash characters attack with one signature prop.
MIC="holding an oversized navy blue microphone used as a hammer, big round mic head with a pink cat paw print and two cat ears, sky blue handle with a ribbon"
DYN="dynamic pose, line of action, exaggerated pose, twisted torso, leaning, full body, from side"
ga2() { nai_guard generate --model $M --prompt "$XY3, $MIC, $DYN, $3, $XSTYLE3" --negative "$XNEG2, black hair, dark hair, black sweater, motion lines, speed lines, effects, stiff, standing straight, symmetrical" --w 832 --h 1216 --seed $2 --out "$OUT/$1_$2.png"; }
for seed in 49601 49602 49603; do
  ga2 v2_windup $seed "anticipation, winding up, microphone pulled far back behind her head with both hands, body coiled, leaning back, knees bent, smug grin, facing right"
  ga2 v2_smash $seed "smashing the microphone down onto the ground in front of her, bent forward deeply, one leg back, hair flying up, fierce grin, facing right"
  ga2 v2_swing $seed "follow-through of a big horizontal swing, microphone swung across her body to the left, spinning on one foot, other leg kicked out, hair and tail whipping around"
  ga2 v2_upper $seed "swinging the microphone upward from low to high, jumping off one foot, stretched upward, arm fully extended above her head, facing right"
  ga2 v2_airslam $seed "jumping, mid-air, microphone raised high overhead with both hands about to slam down, back arched, knees tucked, fierce smug grin, facing right"
  ga2 v2_airspin $seed "jumping, mid-air, spinning sideways with the microphone held out at arm's length, horizontal body, hair and tail swirling in a spiral"
  ga2 v2_dive $seed "jumping, diving down diagonally, microphone thrust forward and down ahead of her, body in a straight diagonal line, legs trailing behind"
  ga2 v2_double $seed "mid-air split, thrusting the microphone upward with one arm while kicking straight down with one leg, body stretched between the two"
  ga2 v2_hold $seed "riding the microphone like a surfboard, crouching on it, one arm out for balance, sliding forward, wind in her hair, happy"
  ga2 v2_hurt $seed "knocked back in the air, dropping the microphone, arms and legs flailing, eyes shut in a comic cry, small tears, tumbling backward"
  ga2 v2_fever $seed "running fast while singing into the microphone, head thrown back, eyes closed happily, free arm spread wide, big open mouth"
  ga2 v2_victory $seed "victory pose, microphone raised high in one hand, peace sign with the other hand, winking, standing on one leg, smug smile"
done
# v2 review notes: strongest = windup 49601/49602, smash 49601-49603, upper 49602, airslam 49601/49602, airspin 49603
# (the mic draws its own arc), dive 49602, hold 49602 (riding the mic), victory 49602. Weak: hurt (does not read as
# hurt), fever (singing pose lost). Not yet recoloured or cut out.
# 2026-11-03 OWNER VERDICT (v2): "the weapon is distorted, inconsistent in length, and the details are wrong".
# Fix: N5 no longer draws the weapon. Poses are drawn gripping a plain light blue stick (easy to find by colour);
# pixel/mdweapon.py lays ONE canonical paw-mic sprite (w_pawmic_49502) along that stick at a fixed size and puts her
# fingers back on top, so the weapon is identical in every frame.
STK="holding a plain straight light blue stick with both hands, simple cylinder pole"
ga3() { nai_guard generate --model $M --prompt "$XY3, $STK, $DYN, $3, $XSTYLE3" --negative "$XNEG2, black hair, dark hair, black sweater, motion lines, speed lines, effects, stiff, standing straight, microphone, hammer, weapon head, ribbon on stick" --w 832 --h 1216 --seed $2 --out "$OUT/$1_$2.png"; }
for seed in 49701 49702; do
  ga3 v3_windup $seed "anticipation, winding up, stick pulled far back behind her head, body coiled, leaning back, knees bent, smug grin, facing right"
  ga3 v3_smash $seed "smashing the stick down onto the ground in front of her, bent forward deeply, one leg back, hair flying up, fierce grin, facing right"
  ga3 v3_upper $seed "swinging the stick upward from low to high, jumping off one foot, stretched upward, facing right"
  ga3 v3_airslam $seed "jumping, mid-air, stick raised high overhead about to slam down, back arched, knees tucked, fierce grin, facing right"
done
# 2026-11-03 OWNER: "Don't forget character consistency and harmony. Some frames don't even show her face properly."
# Rules for every action take: her face visible in profile or three-quarter (never hidden by hair or turned away),
# same chibi proportions (2.5 heads), the sheet's colours. Test: V5 tags vs V4.5 Precise Reference with her approved
# run drawing recoloured to the sheet (ref/xiyin_run_sheetcolours.png) as the identity reference.
FACE="face visible, profile, looking ahead, clear face, eyes visible, 2.5 heads tall, same character"
FNEG="face hidden, hair over face, from behind, back view, head down, looking down, covered eyes, black hair, dark hair, black sweater, motion lines, speed lines, effects, multiple views"
gf5() { nai_guard generate --model $M --prompt "$XY3, $STK, $DYN, $FACE, $3, $XSTYLE3" --negative "$XNEG2, $FNEG, microphone, hammer" --w 832 --h 1216 --seed $2 --out "$OUT/$1_$2.png"; }
gf45() { nai_guard generate --model nai-diffusion-4-5-full --charref "$OUT/ref/xiyin_run_sheetcolours.png" --charref-mode "character&style" --prompt "$XY3, $STK, $DYN, $FACE, $3, $XSTYLE3" --negative "$XNEG2, $FNEG, microphone, hammer" --w 832 --h 1216 --seed $2 --out "$OUT/$1_$2.png"; }
for seed in 49801 49802; do
  for f in gf5 gf45; do
    $f c_${f}_smash $seed "smashing the stick down onto the ground in front of her, bent forward, head up looking at the enemy, fierce grin, facing right"
    $f c_${f}_swing $seed "follow-through of a big horizontal swing, stick swung across her body, spinning on one foot, other leg kicked out, smug face visible, facing right"
    $f c_${f}_airspin $seed "jumping, mid-air, spinning sideways with the stick held out at arm's length, face toward the viewer side, grin"
    $f c_${f}_dive $seed "jumping, diving down diagonally, stick thrust forward and down ahead of her, determined face visible, facing right"
  done
done
# test result: V5 + face tags = faces visible but stiffer poses; V4.5 Precise Reference = most consistent identity
# (sheet colours, same face) but static poses. Hybrid: the dynamic V5 stick poses re-rendered by V4.5 img2img with the
# same Precise Reference, so the pose stays and her identity locks.
ghy() {  # name seed source strength
  nai_guard img2img --model nai-diffusion-4-5-full --image "$OUT/$3.png" --strength $4 --charref "$OUT/ref/xiyin_run_sheetcolours.png" --charref-mode "character&style" --prompt "$XY3, $STK, $DYN, $FACE, $XSTYLE3" --negative "$XNEG2, $FNEG, microphone, hammer, thick stick" --w 832 --h 1216 --seed $2 --out "$OUT/$1_$2.png"
}
for src in v3_airslam_49702 v3_upper_49701 c_gf5_dive_49802 c_gf5_swing_49802 c_gf5_smash_49802; do
  ghy h45_${src} 49901 $src 0.45
  ghy h60_${src} 49901 $src 0.60
done
# consistency test result (2026-11-03): faces now visible (V5 face tags), V4.5 Precise Reference img2img at 0.45
# keeps the pose; colour harmony NOT solved yet - separately generated frames differ in hair / sweater tone, and
# neither the colour-only snap nor the colour transfer from the approved run frame makes them match (hair turns
# near-black or blotchy). h*_ and c_gf* takes kept as a record.
# ---- on-model pack (2026-11-03). Owner: "keep everything consistent with the original look of my OC; the character
# consistency is really poor". Research (NovelAI docs, Precise Reference): a full-body neutral standing reference on a
# plain background at 1024x1536 works best; strength trades likeness against pose freedom. So every frame now uses
# the OWNER'S SHEET (art/reference/oc_reference_sheet.webp) as Precise Reference (character & style), with tags
# rewritten from the sheet itself: one flat royal blue hair colour (no cyan underlayer), half-closed smug blue eyes,
# navy-black sweater with a cobalt diagonal side panel, sailor collar with a cobalt stripe, navy tie with a black cat
# emblem, light blue sleeping-cat chest patch, striped cuffs with a paw print, dark grey shorts with a cobalt side
# stripe, black knee socks with a cobalt band and paw print, chunky black boots with blue trim, blue cat ears with
# white fluff, blue cat tail.
OC="1girl, solo, chibi, cat girl, blue cat ears, white inner ear fluff, long straight hair, royal blue hair, ahoge, blue cat hairclip, blue eyes, half-closed eyes, smug, oversized navy blue sweater, black sweater, blue side panel, navy sailor collar, blue stripe, navy necktie, cat emblem, light blue cat patch on chest, sleeves past wrists, striped sleeve cuffs, paw print, dark grey shorts, blue side stripe, black kneehighs, blue band, black boots, blue cat tail"
OCSTY="full body, from side, facing right, clean lineart, cel shading, anime, official art, flat color, white background, simple background"
OCNEG="cyan hair, light blue hair, gradient hair, two-tone hair, multicolored hair, streaked hair, black hair, purple hair, wide-eyed, thighhighs, pantyhose, skirt, face hidden, hair over face, from behind, back view, text, watermark, signature, multiple views, lowres, blurry, jpeg artifacts, mature, nsfw, motion lines, speed lines, effects, microphone, hammer, thick stick"
gom() {  # name seed strength tags
  nai_guard generate --model nai-diffusion-4-5-full --charref art/reference/oc_reference_sheet.webp --charref-mode "character&style" --charref-strength $3 --charref-fidelity 1.0 --prompt "$OC, $STK, $DYN, $FACE, $4, $OCSTY" --negative "$OCNEG" --w 832 --h 1216 --seed $2 --out "$OUT/$1_$2.png"
}
for st in 0.6 0.85; do
  gom om${st/./}_run 50001 $st "running, mid stride, holding the stick at her side with one hand, determined smug grin"
  gom om${st/./}_smash 50001 $st "smashing the stick down onto the ground in front of her, bent forward, head up looking ahead, fierce grin"
  gom om${st/./}_airslam 50001 $st "jumping, mid-air, stick raised high overhead about to slam down, knees tucked, fierce grin"
  gom om${st/./}_swing 50001 $st "follow-through of a big horizontal swing, stick swung across in front of her, spinning on one foot, smug"
done
# om* result: outfit now on-model (cobalt side panel, sock bands, shorts) but each frame still picks its own
# proportions and hair saturation. Fix: draw the WHOLE action set in ONE image (a character sheet), so every pose
# shares one face, one set of proportions and one palette; hair tagged muted blue as on the sheet.
OC2="${OC/royal blue hair/blue hair, muted dark blue hair, solid color hair}"
gsheet2() {  # name seed strength tags
  nai_guard generate --model nai-diffusion-4-5-full --charref art/reference/oc_reference_sheet.webp --charref-mode "character&style" --charref-strength $3 --charref-fidelity 1.0 --prompt "$OC2, character sheet, multiple views, same character, 4 action poses in a row, evenly spaced, each holding a plain straight light blue stick, $4, from side, facing right, face visible, chibi, full body, clean lineart, cel shading, anime, official art, flat color, white background, simple background, no text" --negative "${OCNEG/multiple views, /}, different characters, different outfits, text, letters" --w 1536 --h 1024 --seed $2 --out "$OUT/$1_$2.png"
}
for seed in 50101 50102 50103; do
  gsheet2 sheetA $seed 0.7 "pose 1 running, pose 2 smashing the stick down onto the ground, pose 3 jumping with the stick raised overhead, pose 4 swinging the stick across in front of her"
done
# sheetA_50101 = on-model chibi (muted blue hair, cobalt panel, half-closed eyes) but front-facing, weak poses;
# 50102 / 50103 broken. Step 1: a side-view chibi model of her (neutral standing, plain background) from the owner's
# sheet; step 2: every action frame from that one chibi model as the Precise Reference.
gchibi() { nai_guard generate --model nai-diffusion-4-5-full --charref art/reference/oc_reference_sheet.webp --charref-mode "character&style" --charref-strength 0.85 --charref-fidelity 1.0 --prompt "$OC2, chibi, 2.5 heads tall, standing, neutral pose, arms at sides, from side, profile, facing right, face visible, full body, clean lineart, cel shading, anime, official art, flat color, white background, simple background" --negative "$OCNEG" --w 832 --h 1216 --seed $2 --out "$OUT/$1_$2.png"; }
for seed in 50201 50202 50203 50204; do gchibi chibi_model $seed; done
# 2026-11-03 OWNER: "Discard all the previous flawed images and revert to fixing this character design" (the armed
# v3 pack). Removed from the repo (manifest rows kept): om06_*, om085_*, sheetA_*, chibi_model_*, h45_*, h60_*,
# c_gf5_*, c_gf45_* and the cut-out puppet (pixel/ocrig.py). The pack = v3_windup_49701, v3_smash_49702,
# v3_upper_49701, v3_upper_49702, v3_airslam_49701, v3_airslam_49702 (v3_smash_49701 dropped: face hidden by hair),
# fixed in code, no new generations: pixel/mdrecolor.recolor_pose snaps hair / sweater / socks / accents to the sheet's
# measured colours (one flat hair colour, no cyan underlayer; near-black navy sweater and socks; cobalt tie, stripes,
# soles), pixel/mdweapon.armed lays the one canonical paw mic BEHIND her so her face always shows.
# ---- bosses v2 (2026-11-03). Owner: "don't forget the main boss and mini-boss; they should match the oppressive vibe
# of the lyrics, though the track is not heavy overall". The pressure in the lyrics is being laughed at after the
# stumble (笑ったでしょ / 吹き出しちゃう / わらうな) and the tearful climb, so:
# mini-boss "The Grinning Chat" (twilight verse): the mocking chat as one huge smirk made of speech bubbles;
# main boss "Nanakorobi" (final chorus): a red daruma lucky-cat king - a daruma falls and gets back up (七転び八起き),
# which is the song's 転んだあとが見せ場じゃん. Cute but imposing; darker palette, glowing eyes. Same SOLO style.
for seed in 62001 62002 62003 62004; do
  gsolo b2_mini $seed "giant floating boss monster, a huge grinning cat face made of puffy lavender and pink speech bubbles, enormous crescent grin with rows of tiny white fangs, half-closed mocking eyes glowing magenta, small cat ears, little stubby paws covering its mouth as if snickering, small speech bubble clusters orbiting it, dusk purple and peach palette, dark purple outline, cute but menacing, imposing, facing left"
  gsolo b2_main $seed "giant final boss monster, enormous round red daruma doll shaped lucky cat king, golden crown, one paw raised beckoning, glowing yellow angry eyes with tiny pupils, wide smug fanged grin, black and gold patterns on its round body, paper lantern ornaments, festival rope belt, heavy and imposing, deep red and gold palette, dark maroon outline, cute but menacing, facing left"
done
# b2_mini rejected: a round purple grinning ghost with a jagged grin reads too close to an existing franchise
# creature. Redesign: a tall stack of chat speech bubbles shaped like a smirking cat with a megaphone, warm palette.
# b2_main pick: 62003 (crown, beckoning paw, glowing eyes, clean belly; 62004 has a glyph on its belly).
for seed in 62011 62012 62013 62014; do
  gsolo b3_mini $seed "giant floating boss monster, a tall cat-shaped cloud built from stacked puffy cream and pink chat speech bubbles, two pointed cat ears made of bubbles, sly smirking cat mouth :3 with one small fang, smug half-closed glowing pink eyes, blushing cheeks, holding a big pink megaphone in one stubby paw, tiny heart and dot bubbles floating around it, peach cream and hot pink palette, dark magenta outline, cute but mocking and imposing, facing left"
done
# picks (2026-11-03): mini-boss b3_mini_62011 (smug chat-bubble cloud cat with a megaphone, swirl tail - floats),
# main boss b2_main_62003. Used by pixel/mdboss.py.
# bosses v4 (2026-11-03). Owner: "the bosses lack menace; ranged attacks strike from thin air". Muse Dash boss fight
# (official trailer 91.0-92.6 s, frame by frame): the boss is big at the right edge with visible cannons, every
# bullet leaves a muzzle in a white smoke burst, the stage is dark. Mini-boss redrawn darker and meaner, the megaphone
# pointing left as its cannon (the projectiles come out of it); main boss kept (b2_main_62003).
for seed in 64001 64002 64003 64004; do
  gsolo b4_mini $seed "giant floating boss monster, a huge dark violet storm cloud shaped like a cat, made of stacked dark purple speech bubbles, two sharp pointed cat ears, glowing hot pink slit eyes, enormous wide toothy grin full of sharp white fangs, mocking laugh, one big hot pink megaphone held out pointing left like a cannon, tiny speech bubbles swirling around it, dark purple and hot pink palette, black purple outline, menacing, imposing, facing left"
done
# b4_mini rejected: purple cat-ghost with a jagged grin is too close to an existing franchise creature (as b2_mini).
# b5_mini: the chosen silhouette b3_mini_62011 (fluffy chat-bubble cloud cat with megaphone) redrawn by img2img to be
# meaner - dusk shading, glowing eyes, fangs - so its shape stays original.
for s in 0.45 0.55; do for seed in 64011 64012; do
  o="$OUT/b5_mini_${s}_${seed}.png"
  [ -f "$o" ] || python3 .claude/skills/oc-gen/scripts/nai.py img2img --model $M --image "$OUT/b3_mini_62011.png" --strength $s --seed $seed --w 1024 --h 1024 --prompt "giant floating boss monster, tall fluffy cloud cat made of stacked speech bubbles, dusk mauve and dark rose palette with deep purple shadows, glowing hot pink eyes, sly menacing smirk with sharp little fangs, holding a big hot pink megaphone, dark magenta outline, menacing, imposing, facing left, $SOLO" --negative "$SNEG2" --out "$o"
done; done
# b5_mini (img2img 0.45-0.55) barely changed the take; the menace is done in code instead (pixel/mdboss.py: dusk
# shading, glowing eyes, aura). Picks unchanged: b3_mini_62011, b2_main_62003.
