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

## Status (2026-11-02, after the owner approved the night mock-up)
- Monster families, all V5 (0 Anlas), cut out by `pixel/mdsprites.py`: sky (goggles cloud cat, propeller paper-plane
  cat, star blade), sunset (pudding cat, bat-winged taiyaki, orange-slice saw), pop (gumball robot cat, candy bat,
  lollipop saw), night (speaker robot cat, bat cat orb, gear with an eye), festival (daruma cat, lantern cat,
  pinwheel saw). Stages without their own family reuse one (pinkpop = pop, twilight = sunset, climb = sky).
- XIYIN's HD runner (`pixel/mdrunner.py`): one V5 run drawing on rigged legs (one body for every run / jump frame),
  V5 punch and air-swipe drawings for the strike frames; all three recoloured to the owner's sheet
  (`pixel/mdrecolor.py`) after the owner noted the hair colour was wrong.
- HD game layer (`pixel/mdgame.py`) used by `pixel/stream.py`. The HP / FEVER bars stay at the top centre: the
  bottom band holds the lyric key-caps and subtitles.

## Hit and speed effects (frame-by-frame study, 2026-11-02)
Owner: "For hit effects and speed boost effects, conduct thorough online research and examine them frame by frame.
The current look feels rather plain."

Sources (viewed for analysis, kept in the session scratchpad only, never fed to the image model):
- Official Muse Dash Steam trailer (1920x1080, 30 fps, 101 s) and the 8 official store screenshots; hits stepped
  frame by frame at 12.13-12.53 s, 15.18-15.45 s and 19.27-19.77 s.
- Game-feel write-ups: GamineAI "Pixel Art Combat FX Guide" (hitstop / smear / flash timing), Sword Arcade
  "Game Feel: Hit-Stop and Screen Shake", ParticleFX "Anime Dash Afterimage" (layer breakdown), Woodpunch
  "Anime speed lines", Prolific Studio and Bloop Animation on smear frames. VFX Apprentice returned 403.

Observed in the trailer (one hit, 30 fps):
- f0-2: one big asymmetric 4-5 point impact star, 200-260 px at 1080p, hot core + light rim, tilted, at the hit.
- f3-4: a white-cored star with a coloured rim; f5-9: it shrinks to a small spike star and is gone by f10.
- Thin spark dashes radiate from the hit; a white crescent swoosh from the weapon for 1-2 frames.
- 15-25 filled confetti stars (purple / blue / pink, 20-60 px) thrown out and drifting for 0.5-1 s, much longer
  than the impact star.
- PERFECT: chunky letters in horizontal colour bands (pink, or yellow / orange on dark stages), white outline,
  dark extrusion, tilted about -8 deg; pops in with smeared ghost copies for 2-3 frames; stacks on rapid hits;
  about 0.5 s.
- White smoke puffs where enemies are destroyed; dust puffs at the feet.
From the articles: hit-stop 2-4 frames (35-90 ms; over 120 ms reads as a dropped frame); a high-contrast flash for
1-2 frames; shake 4-8 frames, vertical first; particles thrown in a cone along the strike, not radially; speed
lines thin, tapered and flickering; afterimages as staggered tinted ghosts that pulse.

How the PV does it (`pixel/mdfx.py`, used by `pixel/mdgame.py`): the timeline above per hit, plus a 2-frame
hit-stop with squash and a 1-frame white flash on the monster, smear ghosts on its flight, a 4-frame 7 px vertical
shake of the play area, palettes per stage (pink / gold, blue for pickups). Fever: translucent diagonal bands
sweeping the background, 44 flickering tapered speed streaks (4-frame life), three flat-colour afterimages that
breathe with the beat, and a radial speed-line burst with a 2-frame flash when Fever starts. Hit effects draw over
every object so a saw at the hit point never hides them.

## Obstacle dodge and stage tension (2026-11-02)
Owner: "There are no special effects for obstacle dodging, and the background fails to create a tense atmosphere."
Observed (official trailer and store screenshots): a cleared obstacle gets its own judgement, an orange "PASS",
next to PERFECT; boss / tense sections sit on dark magenta-purple stages under a bright neon double frame, with
the boss on the right edge. Text sources on near-miss or background build-up in other games gave nothing usable.
PV dodge (pixel/mdfx.py): take-off ring and dust, a 3-frame jump smear (pale silhouettes), sparks thrown back off
the saw's teeth as it passes under her, orange banded PASS, landing ring and dust; jump over saws raised to 210 px.
Stage tension: N5 redraws of the plates are pending (the NovelAI key returned HTTP 401 in this session).

## Sound (2026-11-03)
Owner: "I need hit impact sound effects and tense background ambience to match the lyrics. Do not remove the main
song." Reference: the official trailer's audio (Steam), measured at the hit frames studied above: a hit adds a sharp
mid snap (500-2000 Hz, x2-2.6) plus top sparkle, sometimes a low thump. The PV (`pixel/sfx.py`) layers per hit a
punch body + a click snap + a glass sparkle (+-5 % pitch), a whoosh and PASS chime on saw jumps, plucks on notes,
a bell and shimmer on the hold note, a riser + bell on Fever, and in the climb a low drone with a lub-dub heartbeat
on every beat rising into Fever. Kenney CC0 samples; synthesized whooshes / riser / drone / heartbeat. Pixabay
answered with a bot check (not bypassed); Mixkit's licence terms could not be read, so it was not used. Mix: the
song untouched; effects 3-9 dB under it (climb ambience 6.5 dB under); master -14 LUFS.
Revision (owner: the cute pops / boings "sound like Mario"): Muse Dash's own hit-sound keys (documented by the
MDMods CustomHitSound mod) are named by musical dynamics - sfx_piano_2, sfx_mezzo_1 (small / medium enemies),
sfx_forte_2 / sfx_forte_3 (large, hammer) - plus sfx_score (note), sfx_hp (heart), sfx_press_top / sfx_press (hold)
and char_common_empty_jump: hits are percussion that plays along with the song, not cartoon effects. The PV now
synthesizes a tight drum-like strike (pitch-dropping body, 1.5-6 kHz crack, click, a trace of a crunch recording)
at mezzo, forte in Fever; swishes for jumps; short chimes for notes / hearts; hits about 9 dB under the song.

## Chart and character actions (2026-11-03)
Sources: Steam guide "Enemy Types" (steamcommunity.com/sharedfiles/filedetails/?id=1871949394), the official wiki's
gameplay page (via search), the MDMods CustomHitSound key list, the fan charting guide (via search), trailer frames.
- Note types: small / medium / big enemies (big ones have their own hit sound), Gemini = two linked enemies on both
  lanes hit together, sheet (hold) notes that can be held while still hitting the other lane, ghosts (vanish, no
  penalty), hammers swinging in from the top, gear obstacles on either lane (dodge only), raiders entering from the
  top / bottom, mash enemies (rapid hits), bosses that stay on screen and throw enemies; collectables: blue music
  notes and hearts.
- Charting: the first note sits on the song's first key sound; sections start ground-only and bring in the air lane
  when the music asks for it; repeated music sections reuse (and mirror) the same pattern; notes follow the
  percussion and the vocal rhythm. Lanes: blue = air, pink = ground.
- Character actions (Marija, trailer 60-63 s at 8 fps): every hit uses a different attack drawing (3-4 ground
  swings, 3 air swings) and rarely repeats one twice in a row; each attack pose holds 2-3 frames with a crescent
  smear, then she is straight back to running; consecutive air notes keep her airborne with a new pose per hit.
  The developers describe the hit action as following the chart arrangement.

## Weapons and companions (2026-11-03)
Owner: "in Muse Dash and similar games the characters have cute weapons and hover gear". Observed (official trailer
close-ups; character / Elfin guides): each character attacks with one signature prop tied to her identity (Rin a bass
guitar, Marija a violin-bow sword, outfits swap it for a bat, a lollipop, a carrot), swung in a big crescent smear;
a small winged chibi companion ("Elfin": Mio, Angela, Thanatos, Rabot-233, Little Witch, Dragon Girl, Lilith ...)
floats behind her shoulder and only adds a passive effect. XIYIN takes (N5, 0 Anlas): weapons w_pawmic (a streaming
mic used as a hammer, paw-print grille, cat ears), w_pawhammer (squeaky paw hammer), w_cattail (cat-tail star wand);
companions c_sleepcat (sleepy cat spirit on a cloud, wings, nightcap - echoes her sleeping-cat chest patch) and
c_catdrone (cat-head drone; more techy); wx_swing = XIYIN holding the paw mic, to test drawing her with the weapon.

## Motion and transitions (2026-11-03)
Owner: "the transitions and movements feel a bit stiff". Official trailer studied frame by frame at 30 fps
(11.5-14.5 s, 60-61.6 s): poses snap instead of floating; she reaches the air lane and drops back in 2-3 frames and
hangs in the lane with a slight bob; a ground note right after air notes pulls her straight down onto it; landings
kick up dust puffs; each hit lunges toward the enemy with a 1-2 frame smear and she is straight back to running;
scene changes whip (zoom, roll, motion blur) behind a tilted band with the character's big close-up, rings and
speed lines (fast in, short drift, fast out). Game-feel guides (smear / squash-stretch / hit-stop articles): smear
1-2 frames, squash-stretch 2-4 frames, hits settle within about 5 frames.
PV (`pixel/stream.py` avatar_height / air_runs, `pixel/mdgame.py` motion / draw_avatar, `pixel/mdcutin.py`):
air lane up 0.08 s / drop 0.09 s with a 5 px hover bob; drop lands exactly on a following ground note; saw jumps
rise fast, hang, drop fast; take-off stretch, landing squash with ring and dust; hits lunge 38 px with a 7 deg lean
and a stretch that settle in 0.12 s, two smear ghosts for 2 frames; the first five stage changes are character
cut-ins with her approved busts (smug, happy, wink, sing, pout), the HUD steady on top; the climb keeps its slow
rise and the festival its curtain.

## Boss fight (2026-11-03, frame by frame)
Owner: "the bosses lack menace; the ranged attacks look like they strike from thin air". Official trailer 91.0-92.6 s
at 30 fps: the boss is large at the right edge (about half the playfield height) with visible cannon arms; every
bullet appears at a muzzle inside a big white smoke burst that lingers 6-10 frames, then flies straight along its
lane (ground and air bullets in different colours); the boss recoils on each shot; the whole stage is dark.
PV (`pixel/mdboss.py`): bosses 560-580 px; every note of the fight is fired from the boss's muzzle (megaphone /
daruma mouth) - it does not exist before it leaves the muzzle, then settles into its lane in 0.2 s; 0.12 s
anticipation (draws back, muzzle charges) and recoil; white star flash, ring and lingering smoke at the muzzle;
the mini-boss shoots mocking ｗｗ speech bubbles, the daruma spits its mini-daruma minions; glowing eyes and a
pulsing aura on the beat; stage dimmed 46 % with a breathing vignette; entrance shakes.
