# 「余裕だもん」 PV v4 — redesign spec (draft for the owner's approval)

Owner's requirements (2026-10-23), in priority order:
1. **No AI-generated look.** Logical coherence, visual stability, natural character motion.
2. **Strictly the original reference art** (`art/reference/oc_reference_sheet.webp`). Earlier versions drifted.
3. Polished PV aesthetic (Miku / VTuber / anime PVs): striking visuals, reflections, inverted shots, layered
   surreal composition; smooth, sophisticated, layered transitions of scenes, type and character.
4. More variation in the character shots; better typography and art direction.
5. One clean lyric layer; visuals land on the lyrics; no jarring fast cutting.
6. "Loli, tease" character: read here as her **acting** (smug, teasing, small and cheeky), with the sheet's
   design and proportions unchanged. Petite-redesign tests made before requirement 2 arrived changed her
   proportions and were discarded (not committed). Camera rule: no sexualised framing — no low angles on the
   legs, no thigh crops; close framings are face, hands, sleeves, boots.

Research behind this: `docs/research_pv_language.md`. Style frames and a motion test: `pv4/`.

## 1. Diagnosis of v3 (measured on `pv3/render_v3.py`)
- 84 shots in 178.6 s: median 1.81 s, 32 shots under 1.5 s; 69 of 83 cuts also switch layout family
  (scrap / burst / stream / close / ...). This is the "jarring" feeling: every cut changes colour, layout, pose
  and scale at once.
- 67 different generated drawings: each one is a slightly different reading of the sheet (face shape, chest,
  tie emblem, hair volume, eye colour) → the character is not stable.
- Text: a karaoke bar on every lyric line + a duplicate "accent word" on 31 shots + chat text = up to three text
  layers at once.
- Timing: `pv3/lyrics_timed.json` has wrong per-character times (examples: 強 72.70 → が 74.18; こ 76.70 → の
  78.38; いいこちゃんなんて / つまんないでしょ only 0.47 s apart). Cuts and type keyed to these land off the
  voice. Phrase onsets look closer but are unverified.
- Look: white sticker outlines, flat sheet lighting on unrelated pastel backgrounds, bloom on the character.

## 2. The v4 system

### 2.1 Character: three tiers, all traceable to the sheet
| Tier | Source | Used for | Motion |
|---|---|---|---|
| T1 | The sheet's own pixels (4x master `pv2/rig/master_x4.png`) deformed by the rig (`pv2/rig.py`) | Most shots: full body, bust, face close-ups, crops of hands/boots, mirrored and inverted framings | Breathing, blinks, head tilt/turn/nod, hair/ear/ahoge/tail follow-through, lip-sync, rig expressions (smile eyes, open mouth, blush, sweat, tears) |
| T2 | New key poses only where the story needs an action the sheet cannot do (finger wag, over-cool pose, fall, palm-out "wait", referee X, paw boop x3, arms crossed, wave, spin x2 ≈ 14 drawings) | 10-15 shots | Held key poses with anime timing (on 2s/3s), smears and camera, the rig's idle layer where possible |
| T3 (optional) | A human Live2D rigger / animator working from the sheet | The 3-4 hero motions (fall, boop, wave) if T2 is not natural enough | Real animation |

T2 production: NovelAI V4.5 Precise Reference with the sheet (5 Anlas per attempt) + V5 img2img 0.2 (0 Anlas),
then a **QA gate** before anything enters the edit: a 14-point design checklist (ahoge, ear inner colour, cat
clip position, eye colour/shape, collar stripes ×2, tie with black cat emblem, sleeping-cat patch, cuff stripes +
paw prints, shorts side stripe, tail colour, sock stripe + paw print, boots), palette ΔE against the sheet, and
face-proportion check against the sheet's face box. Fails are regenerated or dropped, never "fixed in the
edit". Generated video (the Seedance pack) is not used by default; a clip could enter only if it passes the same
gate on every frame plus a flicker test.

### 2.2 Worlds (logical coherence)
Three places, each with a fixed light logic; every world change is caused by an object in frame.
| World | Meaning | Light logic | Plate |
|---|---|---|---|
| ROOM | the real her, streaming at night | key = monitor (cobalt, front-low), rim = window (sky, back-right) | `art/generated/bg/b1_room.png` |
| STAGE | her confident imagination | key = spotlight (white, top), rim = cobalt back light | `art/generated/pv4/plates/p3_theatre.png`; final chorus: rooftop + inverted city `p2_city_roof.png` |
| MIRROR SEA | her honest inner voice | key = moon (behind-left): front in shadow, strong moon rim, water reflection | `p1_mirror_moon.png` |
Frame device per world: ROOM = her stream camera (crop marks, REC, LIVE, chat as UI); STAGE = the spotlight cone;
MIRROR SEA = the horizon line and the reflection. Colour: palette of README §3; plates are gradient-mapped to it.
Coral only for honest/feeling words, lemon only for gags.

### 2.3 Typography (one lyric layer)
- Every sung line appears **once**, as part of the composition, in one of three voices:
  - **Mincho** (Zen Old Mincho, vertical, tracking +0.2-0.3 em) for verse and honest lines;
  - **Heavy gothic** (Dela Gothic One) for at most one hook word per chorus line — the word *is* the lyric, set
    behind or around her (depth-sorted), never a duplicate of a caption;
  - **Diegetic UI text** (Zen Kaku Gothic New) for gag lines: stream telop, system dialog, chat.
- Thin Latin (Cormorant Garamond, wide tracking) only for section markers and credits — never a translation
  track. English lyrics, if wanted, go in a separate YouTube CC file.
- Reveal on the sung syllables (glyph fade + 14 px rise + blur → sharp, staggered); exit by dissolve or with the
  camera. No karaoke bar.

### 2.4 Edit rhythm
- One world per section; within a section the frame device stays.
- Verses: holds of 3-6 s with a continuous camera move (push, drift, parallax). Choruses: cuts on bar lines
  (≈1.76 s) or every 2 bars; a 1-beat stutter only on designed hits (めっ, ノーカン).
- Target ≈ 45-55 cuts (v3: 84), median ≥ 3 s outside the choruses.
- Transitions (from the research): push into a screen; the dark monitor's reflection → MIRROR SEA; lamp click →
  spotlight; shatter (stage cracks into the room at えっ); whip-tilt through the waterline into the inverted
  world; stage flats falling to reveal the city (わらうな こっからが ほんばん); "rewind" on もういっかい; white
  bloom-out at section ends.

### 2.5 Shot plan (times = phrase onsets, to be re-timed; T1/T2 = character tier)
| # | Time | Lyric | World / picture | Type | Transition out |
|---|---|---|---|---|---|
| 1 | 0-3.7 | intro | ROOM dark; her reflection in the black monitor (T1, mirrored, dimmed) | — | monitor switches on |
| 2 | 3.7-7.6 | ねえねえ ちゃんと見ててよね | stream window close-up, leans in (T1) | UI telop | pull back out of the screen |
| 3 | 7.6-11.1 | ふふん そろそろ いくよ | room reveal, she at the desk (T1) | Mincho | lamp click → black |
| 4 | 11.1-14.2 | (break) | STAGE: spotlight hits; title card | logo + name | spotlight widens |
| 5 | 14.2-17.8 | 今日の私は | wide stage, small figure in the cone (T1) | Mincho | push-in |
| 6 | 17.8-19.5 | だいてんさい | giant 大天才 behind her (T1) | heavy word | light snap |
| 7 | 19.5-23.3 | 準備もバッチリ | three spotlights snap on, one per beat (= the checklist) (T1) | Mincho | push to face |
| 8 | 23.3-27.8 | 完璧じゃん | tease close-up, lens flare (T1) | heavy word | whip pan |
| 9 | 28.3-31.7 | ざんねんでした | finger wag (T2) | Mincho | match on the finger |
| 10 | 31.7-34.9 | 余裕だもん | logo slam, beams (T1) | heavy word | — |
| 11 | 34.9-42.6 | ほら スマートに キメちゃうよ | one 7 s push-in on the over-cool pose (T2) | Mincho | freeze |
| 12 | 42.6 | えっ | freeze; the stage cracks like glass, the room behind | — | shatter |
| 13 | 43.0-44.1 | あいたたた | ROOM: the fall, key poses on 3s + shake (T2) | lemon ドテッ | — |
| 14 | 44.1-46.3 | ちょっと待った | stream camera, palm out (T2) | UI telop | — |
| 15 | 46.3-49.7 | いまのは カウントに はいりません | referee X in the stream window (T2), counter 1 | UI telop | — |
| 16 | 49.7-52.0 | あーもう にやけないでよ | blush (T1 rig blush), chat icons flood | UI telop | push into the dark monitor |
| 17 | 52.0-55.6 | ほっぺが熱いけど 深呼吸 せーの | MIRROR SEA: breath (T1, breath amplified) | Mincho (coral) | せーの: 1 beat black |
| 18-22 | 55.6-68.8 | chorus 1 | STAGE bigger: 余裕だもん word wall; mirrored twin (T1 ×2); split cool / blush (T1 two rig expressions); 笑ったでしょ tease close-up (T1); めっ boop (T2 ×3) | heavy words / Mincho | もういっかい = rewind |
| 23 | 68.7-72.7 | よそ見しないで 見ててよね | MIRROR SEA, she looks at us (T1) | Mincho | — |
| 24 | 72.7-76.6 | 強がりだって 本気だもん | moon backlight, bluff above / truth in the water (T1) — **motion test** | Mincho ink / coral | whip-tilt through the water |
| 25 | 76.7-84.6 | この声で キメちゃうよ | inverted world under the water; ripple rings from her voice (T1) | Mincho | bloom-out |
| 26 | 84.8-89.9 | スクショは きんし 忘れてよね | ROOM: layered windows + system dialog, shutter 84.645 (T1) | UI dialog | — |
| 27 | 89.9-96 | なまいきなんて 言わせないもん | arms crossed, fisheye stream cam (T2) | UI telop | — |
| 28 | 98.9-103.7 | ぷいって そっぽ 向いてみても | head turn + tail swish (T1 rig) | lemon ぷいっ | — |
| 29 | 103.7-109.7 | きみと目があえば 吹き出しちゃうな | laughs (T1 smile eyes + open mouth) | Mincho | dark monitor |
| 30 | 109.7-113 | 悔しいままで 終わりたくない | her reflection in the monitor, honest (T1) | Mincho coral | — |
| 31 | 113-116.5 | いいこちゃんなんて つまんないでしょ | mirrored double, two rig expressions (T1 ×2) | Mincho | — |
| 32 | 116.5-123.1 | 震えるつま先で ステップ踏んで | boots crop from the sheet; ripple rings on each step (T1) | Mincho | — |
| 33 | 123.1-125.8 | わらうな こっからが ほんばんだもん | the room walls fall like stage flats → rooftop city | heavy word | continuous |
| 34-39 | 125.8-153.6 | final chorus | STAGE = rooftop + inverted city: 余裕だもん word, fall replayed as a spin (T2), mirrored boop (T2), her stream as a building-sized screen, pull back through many screens, held note + moon rise | heavy words / Mincho | bloom-out |
| 40 | 154.5-159.3 | ほらね やっぱり 余裕でしょ | ROOM, same angle as #3 (bookend) (T1) | Mincho | — |
| 41 | 159.3-163.3 | ふふん たぶんね | small shrug (T1 rig) | Mincho | — |
| 42 | 163.3-172.5 | また来てよね | wave (T2), she switches the light off, LIVE dot off | UI | black |
| 43 | 172.5-178.6 | outro | end card, ノーカン counter pawed back to 0 | credits | — |

## 3. Acceptance tests (each block of the edit must pass before the next)
1. **Identity**: every character pixel traces to the sheet (T1) or to a T2 drawing with a passed QA record.
2. **Timing**: each glyph within ±60 ms of the measured vocal onset; each cut on the beat grid (±1 frame).
3. **Rhythm**: median shot ≥ 3 s outside choruses; ≤ 1 lyric layer at any time; one world per section.
4. **Stability**: on held shots, the character's silhouette area changes < 2 % frame to frame except during
   designed actions; no flicker in plates (static plates only move by camera transforms).
5. **Look**: no bloom on line art; plates graded to the palette; blind test (README §7) at the first-chorus block.

## 4. Steps, cost, decisions
1. Re-time the lyrics: vocal separation (UVR MDX-Net, downloadable from GitHub releases) + ASR token timing +
   vocal onset snapping, then an owner spot-check of 10 lines. Cost 0.
2. Build the v4 renderer on `pv4/look.py` (worlds, type, transitions) and render the 42.6-84.6 s block (stumble →
   chorus 1 → verse 2) for review. Cost 0 (CPU).
3. T2 key poses: ~14 drawings × up to 4 attempts × 5 Anlas = **up to 280 Anlas** (balance 6,897). Needs the owner's OK.
4. Full PV + the three Shorts.
Decisions for the owner: approve the three worlds and the shot plan; approve step 3's Anlas; whether T3 (a human
rigger/animator) should be considered for the hero motions; the OC's name (title card still 「（なまえ）」).
