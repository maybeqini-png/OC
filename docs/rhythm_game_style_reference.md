# Muse Dash visual style study (for the PV's game layer, 2026-11-02)

Owner, after the stream PV v3b: "there is still a gap compared to Muse Dash" ... "follow the reference materials,
including the monsters found online and the style of Muse Dash". The first monster set (thick black outlines,
glossy sticker shading, unrelated themes) was rejected as "completely unsatisfactory".

## Sources (viewed for analysis; kept in the session scratchpad only, not in the repo, not used in the video)
- Official Steam store page, Muse Dash (app 774171): 8 screenshots at 1920x1080 and the store trailer.
- Gameplay recordings on Bilibili, 《Muse Dash》喵斯快跑 全曲目第1弹 (BV1YA411x7Rj), parts 1, 5 and 9 (1080p30,
  about 3 min each): frames every 8 s plus full-resolution stills of the monsters.
- YouTube gameplay could not be used: it asked for a sign-in bot check, which was not bypassed.

Evidence level: **observed** (measured or read on the frames above).

## What the game layer looks like (observed)
**Stage / background**
- Soft, hazy, low-contrast pastel scenery (lavender forest, magenta factory), almost no black linework; depth by
  atmospheric fade. The playfield floor is a flat two-tone band. Bright characters and monsters pop against it.

**Monsters**
- Flat fills in 2-3 tones, **no black outline**: the outline is a darker (or lighter) shade of the body colour,
  thin and slightly wobbly, hand-drawn.
- Very simple primitive shapes: round orb, cat-head blob with tiny wings, cloud, cone, box, drone.
- Minimal faces: dot or line eyes and a simple mouth, or a visor with one glowing half-moon eye.
- Palette tied to the stage: cyan / yellow / pink on the pastel stage; purple and pink with one neon eye colour
  (orange, green, cyan) on the dark stage. Each stage has its own small family of 3-4 monster types.
- Size at 1080p: monsters about 120-180 px; the player about 250 px tall; air lane about y 380, ground lane about
  y 680, floor about y 780.
- Motion: slight bob and tilt, smear on fast movers, knocked away on a hit with a star burst.

**Notes and effects**
- Pickups: a blue eighth-note glyph, hearts. Hold notes: a glowing star at each end of a music-staff ribbon with
  white notes on it. Double notes: two monsters linked by a rainbow.
- Dashed target rings in front of the player on both lanes.
- Judgement: chunky bubble letters ("PERFECT" pink / "GREAT" purple / "PASS" orange) with a light outline, popping
  near the player; combo: big yellow number with a pink outline on a pink paint-splat.
- HUD: score top-left, combo near the top centre, a slanted pink HP bar with a heart and a cyan Fever bar at the
  bottom; a small companion character floats top-left.

## How the PV follows it (rules for our own designs)
- Original monsters only (XIYIN themes: cats, streaming, sweets); Muse Dash images are never fed into the image model.
- One family per stage (ground enemy, air enemy, saw-type obstacle) in that stage's palette plus one accent.
- N5 prompt rules: flat colour, flat shading with one darker shadow tone, coloured outline in a darker shade of the
  body colour, simple rounded shapes, minimal face, dynamic tilted pose; negatives: black / thick outline, glossy,
  gradient, detailed, sticker, emoji.
- Cut-out (pixel/mdsprites.py): background = light unsaturated pixels connected to the border; edge pixels are
  un-mixed from white (alpha from the projection onto the inside colour, colour = inside colour), so no white rim.
- Stage plates get a pastel haze (blur + tint) so the monsters and XIYIN read as in Muse Dash.

## Status
- Sky stage family drafted (V4.5, free): cat-mochi (ground), cat paper-plane (air), pinwheel (saw). Mock-up at
  game scale with the hazed sky plate and an HD chibi runner test (V5). Awaiting the owner's verdict before the
  other stage families, the HD runner frames, notes, judgement graphics and HUD are built.
- The V5 free allowance ran out again on 2026-11-02 (HTTP 402, 30 Anlas per image); V4.5 stays free.
