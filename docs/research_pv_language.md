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
