# Reference research: polished Miku / VTuber / anime PVs (for 「余裕だもん」 v4)

Date: 2026-10-23. Complements `docs/reference_breakdown.md` (ロリ神レクイエム, ひっひっふー, うみゃうにゃ, GREATEST,
メズマライザー). Focus asked by the owner: striking scenes, reflections, inverted shots, layered surreal composition,
typography, and **smooth, sophisticated, layered transitions between scenes, type and character**.

## Method and evidence levels
- YouTube is blocked from this environment (bot check). Frames came from **Bilibili's player preview sprites**
  (`x/player/videoshot`) of official or mirrored uploads: ~1 frame/s for the first 100 s of some videos, one per
  ~5 s for others, 480x270 (160x90 for two). Script: scratchpad `bili.py` (not committed). Frames are used for
  analysis only, never stored in the repo or used in the PV.
- Downloading the videos themselves was refused by Bilibili (HTTP 412), so **cut lengths and transitions are
  inferred from 1 fps or sparser previews**: transitions shorter than ~1 s are seen only as their middle frame.
- Labels: **observed** = visible in the preview frames; **credit (source)** = from a cited page;
  **inferred** = my reading of a sequence of frames; **practice** = general PV/anime production practice, not
  measured here.

| # | Work | Upload used | Frames |
|---|---|---|---|
| R1 | DECO*27 「ラビットホール」 feat. 初音ミク | BV1aa4y1u7Ct (DECO27_Official) | 31, every ~5 s |
| R2 | DECO*27 「モニタリング」 feat. 初音ミク | BV1qDUPYKEzf (DECO27_Official) | 35, 1/s (0-34 s) |
| R3 | ピノキオピー 「神っぽいな」 | BV1iP4y1Y7NE (ピノキオピー_official) | 30, 1/s (0-29 s) |
| R4 | Gawr Gura 「REFLECT」 | BV1Hi4y1k7Ph (mirror with burned-in CN subs) | 35, every ~7 s |
| R5 | 柊マグネタイト 「マーシャル・マキシマイザー」 | BV1rme4esEJQ (mirror) | 17, every ~10 s |
| R6 | 星街すいせい 「ビビデバ」 | BV1Cw4m1y7gu (星街彗星Official) | 32, 1/s (0-31 s) |
| R7 | 星街すいせい 「Stellar Stellar」 | BV1jr421g7gm (星街彗星Official) | 59, every ~5 s |
| R8 | 宝鐘マリン 「美少女無罪♡パイレーツ」 | BV1Tw4m117Yj (mirror) | 45, every ~5 s |
| R9 | Kanaria 「KING」 | BV1Ya4y1E7pk (mirror) | 23, 160x90 |
| R10 | きくお 「愛して愛して愛して」 | BV1Qx411A7TS (mirror) | 169, 160x90 |
| R11 | 『ぼっち・ざ・ろっく!』 NCOP 「青春コンプレックス」 | BV1h3411U7EK | 10 (0-9 s only) |
| R12 | 『【推しの子】』 第2期 NCOP 「ファタール」 | BV1qi421Y7LD | 18, every ~5 s |

Credits found: R1 illustration おむたつ ([pixiv dic](https://dic.pixiv.net/a/ラビットホール/)); R2 end card
"OTOIRO" (observed); R4 art "Mochizuki Mochi" / movie "Nebiru" (names as written) per [Siliconera](https://www.siliconera.com/gawr-gura-reflect-music-video-released-includes-lyrics/)
(role of Nebiru not stated); R6 MV by 擬態するメタ (しまぐちニケ + Bivi), Clio Music 2025 bronze
([KAI-YOU](https://kai-you.net/article/91810), [電撃オンライン](https://dengekionline.com/article/202411/24309)).
The YOASOBI 「アイドル」 MV preview could not be fetched.

## 1. Findings per work

**R1 ラビットホール** (observed) — One high-quality character illustration is reused all through the MV, but
never the same way twice: tilted, extreme crops (one eye, mouth), mirrored, zoomed, masked by a circle. Variety
comes from **crop + camera + graphic layer**, not from new drawings. Typography is the second protagonist:
giant kanji 誰 / 頭+身体 set as a fixed layout while the objects between them swap. A retro OS window stack and a
circular iris mask (inferred: iris-wipe transitions around 1:02-1:09). One colour world (pink glitter + sky).

**R2 モニタリング** (observed) — **One optical device for the whole MV**: a fisheye peephole lens. Every shot
sits inside the same circular vignette, so even colour flips and fast cuts read as one continuous look. Lyrics
curve along the lens edge. Transitions are optical: the iris closes to a dot, an extreme eye close-up becomes
the pupil, the pupil becomes black (inferred match cut eye → pupil → black, 0:13-0:16). Colour flips between a
grey real corridor and neon psychedelia happen *inside* the same frame device.

**R3 神っぽいな** (observed) — Strict palette: grey, black, white + one red. Lyrics are small vertical Mincho
set in black boxes next to the character; a giant red kanji (風 / 神) only at a few hits. Large flat black/white
silhouette shapes of hair fill the frame between shots (inferred: **silhouette-matte transitions**: a shape of the
character wipes to the next shot). Repeated drawings, extreme crops, lots of negative space. Restraint is the
polish.

**R4 REFLECT** (observed) — **Duality by colour world**: blue underwater "true" world vs red glitch "reflection"
world, alternating by section. Bubbles, glass shards and floating debris pass in the foreground as depth layers
(inferred: foreground objects crossing the lens hide cuts). Thin, wide-tracked Latin type (R E F / E C T split
logo, "without"), large moon backlight with a small silhouette, white bloom-outs.

**R5 マーシャル・マキシマイザー** (observed) — A single still illustration for the whole song; **kinetic
typography carries everything**: Mincho vertical columns, giant kanji, Latin words, several text layers moving
at different speeds (typographic parallax) on one teal field. Proof that typography alone can be the motion.

**R6 ビビデバ** (observed) — Toon-shaded 3D character in a real backstage/theatre set. The camera moves
continuously from the fairy-tale stage set to the bare backstage and back (inferred: one-take feel, set walls and
camera whips used as hidden cuts, 0:00-0:24), then out to a night city. The idea is "stage vs backstage" —
directly our "cool her vs real her". Very few hard cuts in the first 30 s.

**R7 Stellar Stellar** (observed) — Long holds (successive frames 5 s apart are often the same shot), muted
night city photography with shallow depth of field, the character shown **inside screens** (laptop, phone) and
then in the space itself (inferred screen-within-screen transition, 0:27-1:14), white-outs, black-and-white
close-ups, a full moon finale. Lyrics: small thin hand-lettering in negative space; a few giant kanji (考, 歌, 愛)
with motion blur at peaks.

**R8 美少女無罪♡パイレーツ** (observed) — TV-anime quality; the cute/teasing idol tone closest to our OC's
personality. Bold logo typography (無罪 sign), heart-shaped frames, spotlight stage, extreme eye close-up (heart
pupil), phone screen POV, sketch/line-art break, chibi gag cutaways. Colour script pink/red day vs navy night.

**R9 KING / R10 愛して愛して愛して** (observed) — Limited palettes (black/white/red), text as texture, very fast
cutting. Tone does not fit our song; kept only as proof that a strict palette makes chaos read as design.

**R11 ぼっち・ざ・ろっく! NCOP** (observed, 0-9 s) — an **inverted top-down shot** of the head within the first
seconds, flat graphic colour fields, neon-sign typography (STARRY), match from logo to performance.

**R12 【推しの子】 S2 NCOP** (observed) — Theatre stage lighting, silhouettes against light, a character image
the size of a building inside the city (scale layering), title type with the star replacing a counter, rooftop
geometry seen from extreme angles.

## 2. Cross-cutting principles (what makes them feel polished)

### Scenes
1. **Few worlds, each with a fixed light logic** (R2, R4, R6, R7): one key-light direction and one rim colour per
   world. A world change is a story event, not a shot change.
2. **One frame device per work** (R2 lens, R1 circle/OS windows, R5 text field): fast cuts stay calm when the
   device is constant.
3. **Reflections and inversions are motivated**: water, glass, screens, the dark monitor (R4, R7, R11). The
   mirror image carries a meaning (true self, other world).
4. **Scale layering**: a tiny figure against a huge moon (R4, R7), a giant image of her inside a set (R12),
   foreground objects crossing the lens (R4).

### Typography
5. **One text layer at a time; the lyric is set once.** Small vertical Mincho for quiet lines (R3, R7), a giant
   word only at true hits (R3 red kanji, R7 考/歌), diegetic UI text for gags (R1 OS windows, R8 sign).
6. **Type is placed in the composition** (negative space, on the moon, along the lens edge), never as a bottom
   bar plus a duplicate word.
7. **Strict type families**: a Mincho + a heavy gothic + a thin Latin, tracking opened up; no generated lettering.

### Character
8. **Variety from crop, angle, scale, mirror and camera**, not from many inconsistent drawings (R1, R3, R5).
9. **Repetition is fine when designed** (motif pose, same hero image) and the surroundings change.

### Transitions (smooth, layered)
10. **Optical / physical transitions** (inferred from R1, R2, R4, R6, R7): iris and lens closes, eye-to-pupil
    match cuts, push into a screen, camera whip through a set wall, foreground object wipes, silhouette mattes,
    white bloom-outs at section changes.
11. **Continuous camera across a world change** (R6) beats a cut: the move hides the seam.
12. **Every transition is caused by something in frame** (a screen, water, light, her hair, a word), so the
    viewer never feels a jump.

## 3. Why v1-v3 looked AI-generated, and the countermeasures (v4 rules)

| Symptom (v3) | Cause | v4 rule |
|---|---|---|
| Character drifts between shots (face shape, chest, tie, hair volume) | 75 separate generations, each a slightly different reading of the sheet | The sheet is the only source. Default: the sheet's own pixels moved by the rig. New poses only through a QA gate against the sheet |
| Pasted-sticker look | White outlines, flat sheet lighting on any background | No outlines; relight into each world (ambient, rim from the world's key light, contact shadow / reflection) |
| "AI glow" | Bloom on everything incl. skin and lines | Bloom only on light sources; line art never glows |
| Mushy, over-detailed backgrounds | Generator texture noise, off-palette hues | Plates gradient-mapped to the palette, defocused behind her, crisp geometry (UI, lights, type) drawn in code |
| Random sparkles and stamps | Decoration without cause | Particles only where a light source motivates them; ≤ 50 |
| Morphing / floaty motion (video models) | Generated video | No generated video by default; rig motion with follow-through, held key poses with anime timing |
| Jarring cuts (84 shots, median 1.8 s, 69 layout switches) | New layout family on almost every phrase | One world per section, cuts on bars, transitions motivated by objects |
| Two text tracks + chat | Bottom karaoke line + duplicate accent word + chat panel | One lyric layer, set once in the composition |

## 4. Measured benchmarks (added 2026-10-23, second pass)
Method: 360p analysis copies from Bilibili (scratchpad only, never committed or used), every frame analysed
(scratchpad `analyze_pv.py`): shot boundaries from alignment-compensated frame change (catches cuts and
dissolves), boundary type (hard cut vs gradual: dissolve / wipe / whip), camera move per shot from optical flow,
plus 1 fps page sheets for visual study. Evidence: **measured** (numbers below; detector errors of a few shots are
possible, burned-in subtitles in some mirrors), **observed** (page sheets).

| Work | Shots | Median shot | Hard cuts / gradual | Moving camera (share of time) | Flash frames |
|---|---|---|---|---|---|
| 天使うと 「UTOPIA」 (BV17L411j7yK) | 58 | 2.32 s | 5 / 52 | 15 % | 5 |
| Gawr Gura 「REFLECT」 (BV1Hi4y1k7Ph) | 144 | 1.02 s | 95 / 48 | 45 % | 30 |
| Gawr Gura 「Ash Again」 (BV1frLVzdERM) | 136 | 1.35 s | 81 / 54 | 18 % | 17 |
| Gawr Gura 「Full Color」 (BV1RN411e7Jm, 3D live) | 100 | 1.69 s | 52 / 47 | 71 % | 20 |
| DECO*27 「モニタリング」 (BV1qDUPYKEzf) | 66 | 1.23 s | 34 / 31 | 23 % | 14 |
| our v3 | 84 | 1.81 s | (all hard cuts) | every shot zooms | — |

What the numbers say:
- **Speed was not v3's problem.** REFLECT cuts faster (median 1.0 s) and still feels polished. v3 felt jarring because
  almost every cut also changed layout, colour world, scale and pose at once (69 of 83), with no motivating object.
- **Smoothness = gradual transitions.** UTOPIA joins 52 of 57 shots with dissolves, white-outs, ring and wave wipes;
  even the fast Gura MVs make a third of their joins gradual.
- **Camera**: the 2D illustration MVs (UTOPIA, Ash Again) mostly hold the frame and move layers inside it; REFLECT
  moves the camera on 45 % of its running time (slow pushes/pulls/tilts over stills with debris layers).

### UTOPIA (天使うと) — observed on all 231 s
- **Colour script**: morning pastel white/sky (0-80 s) → night navy with moon and falling feathers (100-170 s) →
  morning again (170-230 s). Everything is recoloured into her palette (white hair, sky blue).
- **Few hero illustrations, held long**: about 6-8 full illustrations, each 10-25 s (58-70 s one close-up; 200-213 s a
  slow pan across one large illustration from legs to face), plus a chibi version for light passages.
- **The scene acts with her**: feathers fall, the moon and clouds drift, concentric rings expand behind her face on
  emotional lines (136-140 s), bubbles rise — the illustration is still, the world around it is not.
- **Frame device**: a dashed stationery border with mascot icons at the corners for the room passages.
- **Typography**: one line at a time inside a designed container — rounded labels with a thin outline, text along a
  circle path, inside a wave band, inside a cloud bubble; small, pastel, never a bottom karaoke bar.
- **Transitions**: white-outs, soft dissolves, ring and wave wipes; dark fades into the night section.

### REFLECT (Gawr Gura) — observed shot by shot
- About 15 illustrations of Gura (and the red alter ego), used as large crops: profile, eyes, reaching hand, hair.
  Character acting is minimal; life comes from the camera and from **debris layers at several depths** (bubbles,
  glass shards, rocks) crossing the frame.
- Two colour worlds (blue underwater / red glitch) switched on hard cuts; the shards and white flashes hide the
  switches. Giant kanji (恐, 海の底, 過去, 今, 私) and stylised Latin (Begin again, RETURN, without) as graphics;
  the lyric line itself small and thin.

### Ash Again (Gawr Gura × Casey Edwards) — observed
- Fully hand-animated 2D, grey + red with yellow/pink/blue silhouette pops. **Spatial typography**: lyric words set
  on the walls and floor of a perspective room ("DON'T TELL ME / EVERYONE IS WAITING"), so type is architecture.

### Full Color (Gawr Gura, 3D concert) — observed
- 3D model on a stage set; the camera circles and pans on 71 % of the running time; close-ups intercut with wides
  and audience shots. Camera grammar only (we are 2D).

## 5. What changes in our plan because of this
1. Keep the v4 cut budget (~45-55) but allow REFLECT-speed bursts at climaxes **only when the world, palette and
   motif stay constant** across the burst.
2. Default join = gradual (dissolve, white-out through the world's light colour, ring wipe from her voice, water
   ripple wipe); hard cuts only on drum hits with a flash or a shard pass.
3. Every shot has **scene acting** tied to the lyric's mood: wind, light swelling, ripples, feathers/petals,
   debris layers — never a static plate (owner requirement, 2026-10-23).
4. Type: one line, inside a container or on a surface of the scene (spatial type on water, stage floor, monitor),
   giant words only at true hits.
5. Character: a few strong illustrations held long with camera and layers (UTOPIA/REFLECT method) + selected acting
   clips (MiniMax H3 from on-model first frames) where the lyric needs a gesture.

## 6. Composition and character-scene integration (added 2026-10-23, third pass)
Works: 『りゅうおうのおしごと!』 NCOP 「コレカラ」 and NCED 「守りたいもののために」 (BV1as411w71U p1/p2),
『ノーゲーム・ノーライフ』 NCOP 「This game」, NCED 「オラシオン」, ED2 「THERE IS A REASON」 (BV1ag411e7D4 p1-p3),
YOASOBI 「アイドル」 official MV (BV1Ws4y1A7fS), plus UTOPIA / REFLECT from §4. Method: every shot measured
(scratchpad `analyze_pv.py`), one mid-frame per shot inspected with a thirds grid and a character matte
(scratchpad `compose_study.py`). The matte (isnet-anime) misses heavily stylised characters (NGNL OP), so
composition numbers below are only shot counts and timings; layout findings are **observed** on the frames.

| Work | Shots | Median shot | Hard / gradual joins | Moving camera |
|---|---|---|---|---|
| Ryuuou NCOP | 61 | 1.17 s | 47 / 13 | 53 % |
| Ryuuou NCED | 14 | 2.42 s (mean 6.5 s; holds of 9-28 s) | 5 / 8 | 29 % |
| NGNL NCOP | 44 | 1.08 s | 13 / 30 | 67 % |
| NGNL NCED | 29 | 2.00 s | 11 / 17 | 33 % |
| NGNL ED2 | 21 | 4.6 s | — | — |

### Observed layout rules
1. **The place is shown on its own first.** Ryuuou NCOP: 21 of 47 measured shots have no character
   (Dotonbori, the Ferris wheel, Osaka castle through cherry blossoms, the shogi hall, its signboard). When the
   characters appear in those places they are small (about a fifth of the frame height), on the lower third, in deep
   one-point perspective, lit by the same daylight and grounded by their shadows. Integration comes from the place
   being established and from matching perspective and light, not from putting a big figure in front of a plate.
2. **Inserts carry the story.** Hands on the shogi pieces (top-down board with a hand entering from the top,
   oblique table-level hand, a hand pressing a glowing board), feet walking, a hair ribbon in extreme close-up, eyes
   in a horizontal strip. In the ED a figure is shown with **her head out of frame** (hand on the umbrella handle,
   arm brushing a shoji): body language instead of a face.
3. **Shadows and light tie her to the set.** Ryuuou NCED: the umbrella seen from above with its cast shadow on
   textured ground; her shadow on the shoji while she walks past; a profile at the left third, backlit by a warm
   window, looking into the open right two thirds. NGNL NCED: tiny figure on a white paper void with one long
   diagonal cast shadow.
4. **One light colour per shot, character included.** NGNL NCOP grades every shot into a single hue (white, violet,
   cyan, crimson); the characters take that hue. Ryuuou NCED does the same with sunset orange and window gold.
5. **Symmetry for relationships, diagonals for motion.** NGNL: two faces meeting on the centre line (foreheads and
   hands together); two figures falling upside down on a diagonal across a white void while the camera tilts with
   them; one tiny figure at the vanishing point of symmetric architecture.
6. **Scale contrast.** Tiny figure against a vast sky/void (NGNL ED: two children on a cloud field; a lone figure at
   the right edge of a black frame) followed by an extreme close-up; never several medium shots in a row.
7. **Inversion and mirroring as statements** (「アイドル」): three upside-down heads in a row; tiny figures standing on a
   glossy white floor with their reflections and a rainbow vignette; split screens; eyes as a full-width strip.
8. **Long holds for quiet songs.** Ryuuou NCED holds single shots for 9, 14.6, 17 and 27.9 s with a slow pan or
   push; NGNL ED2 median 4.6 s. Our verse 2 and the bridge should use this, not chorus cutting.

### Applied to block 64.4-84.6 s
- 笑ったでしょ: tease close-up on the right two thirds, the hook word set into the left third and **behind** her
  (matte), single stage-light colour.
- よそ見しないで: waist shot on the right third, the moon in the left third as the light source; her rim light
  comes from it (generated in-scene by H3 from our relit first frame).
- 強がりだって / 本気だもん: small full figure on the right third, horizon on the lower third, moon filling the
  left, reflection = her cast "shadow" on the water (rule 3); the moonlight swells on 本気 (rule 4).
- この声で: centred symmetric figure in front of the moon (rule 5), shown **inverted** after the whip-tilt
  (rule 7), ripple rings timed to her voice.
- Not yet applied (needs new art): an establishing shot of the MIRROR SEA without her before よそ見 (rule 1), and
  a body-language insert (boots stepping on the water / hand on her chest, rule 2).
