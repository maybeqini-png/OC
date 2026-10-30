# OC PV — 「余裕だもん」 (working project brief)

Handoff document so any new session can continue without the original conversation.
Owner works solo (no team). Keep token use low: **do not run multi-agent workflows**; work inline.
Reply in the language of the owner's latest message (usually English). The OC is **XIYIN** (named by the owner
2026-10-29; written in Latin letters, no Chinese name). On-screen text is Japanese or English by default.
The owner has asked the assistant to work autonomously on the pixel PV (2026-10-29).

## 1. The OC: XIYIN (source of truth: `art/reference/oc_reference_sheet.webp`)
Anime cat-girl: long straight deep-navy hair, one ahoge, navy cat ears with pink inner ears, small blue
cat-shaped hair clip (position as in the sheet), blue half-lidded eyes, small confident closed-mouth smile.
Oversized navy sweater, sailor collar with cobalt stripes, navy tie with a small black cat emblem,
light-blue sleeping-cat chest patch, striped cuffs with paw prints, dark grey shorts with a cobalt side stripe,
navy cat tail, navy knee socks with a cobalt stripe and paw print, chunky black lace-up boots with blue accents.
Personality (owner, 2026-10-29): a **mischievous, cheeky little brat**: smug, teasing, pranks her chat, never
admits a mistake (「ノーカン!」), tongue-out あっかんべー, cat-paw めっ boop. Playful and kid-like; never needy.
Song arc: acts cool and smug → trips → "that doesn't count" → blushes → owns it.
Hard line: **strictly non-sexual**. No メスガキ-style innuendo, fanservice or suggestive poses or framing, in art,
prompts, lyrics or captions (also required by Bilibili / YouTube rules). Cheeky means pranks and attitude only.

## 2. The song (final audio in `audio/`)
- Base: Gemini/Lyria track 2 (Anime Idol Pop, ~136 BPM, C# major), opening repaired ("A2": the stray
  rising hum at 1.2-2.9 s removed, breath kept soft).
- `t2_optimized_full.mp3` = master (178.6 s, -13.2 LUFS, -1.0 dBTP): synthesized SFX — instrumental
  muffle on 「えっ」 42.6-44.2 s + thud 43.05 s, boop on 「めっ」 66.82 s and 137.36 s, shutter on 「スクショ」
  84.645 s; final chorus vocal +1.5 dB (125.8-153.6 s). Owner still has to confirm SFX levels by ear.
- Shorts: `t2_short30_cool_stumble_hook` (33.6-64.4 s), `t2_short16_stumble_teaser` (41.6-58.0 s),
  `t2_short16_meh_challenge` (53.0-69.5 s).
- Known AI-vocal limits: half-spoken lines 1-2, straight held notes with late vibrato, weak diction on
  ノーカン / めっ (use burned-in captions), stumble not acted (the PV/SFX carry it).
- Not verified: Gemini music commercial-use terms. Disclose AI use in descriptions.

Key vocal times (s): 3.7 ねえねえ / 7.6 ふふん そろそろ いくよ / 14.2 band in, 今日の私は だいてんさい /
≈27.8 ざんねんでした 余裕だもん / 34.4 ほら スマートに キメちゃうよ / 42.6 えっ, 42.98 あいたたた, 44.18 ちょっと待った /
45.8 いまのは カウントに はいりません / 49.2 あーもう にやけないでよ / 53.1 inhale, 54.5 せーの /
55.6 chorus 余裕だもん ほら 余裕だもん / 59.7 ノーカンじゃん / 64.4 笑ったでしょ, 66.82 めっ, 67.6 もういっかい /
84.6 スクショは きんし / 96.2 ぷいって / ≈104 吹き出しちゃうな / 116.2 震えるつま先で / 122.8 わらうな /
125.8 final chorus / 137.36 めっ / ≈147 最後まで 歌いきるよ / 154.0 ほらね やっぱり / 158.5 ふふん たぶんね /
≈163-172.5 また来てよね / outro to 178.6. Beat ≈0.4411 s (tempo drifts slightly; snap edits to local beats).

## 3. Creative direction (changed 2026-10-29)
Decided by the owner:
- **Pixel-art PV, rendered deterministically in code** (Python/Pillow/NumPy + FFmpeg; every frame a function of
  time). **No video generation models for any shot.**
- XIYIN must be **drawn as pixel art** (hand-placed sprites, fixed palette), not filtered down from the
  illustrations. `art/pixel_tests/` shows why: the filtered sprites lose value separation (hair, sweater and
  background merge into one navy) and at 96 px the half-lidded eyes break into noise.

Proposed by the assistant, approved by the owner 2026-10-29 (on-screen text in Japanese/English, not Chinese):
- Framing: XIYIN streams herself playing a rhythm game. The song's gag (brags 「大天才」 → MISS → 「ノーカン!」 →
  counter → 「めっ」) maps onto judgement text (PERFECT / MISS / NO COUNT) and a combo counter, so the pixel/game
  look is in character for her (as it is for Silver Wolf, whose official PV uses rhythm-game UI and pixel fonts).
- Pixel value fixes: hair clearly brighter than the sweater (cobalt → sky ramp), near-black navy sweater, light
  warm backgrounds; eyes as a fixed hand-drawn 3-4 px half-lid shape; the sleeping-cat chest patch enlarged as a
  recurring signature (small details like the clip and tie emblem vanish at pixel size).
- Hook text: 余裕だもん / ノーカン / めっ shown large in Japanese with a short English line (e.g. ノーカン →
  "DOESN'T COUNT!"), easy for viewers to repeat in comments and danmaku.
- First test before any full render: one hand-drawn 128 px bust + a 6-frame MISS → ノーカン sprite animation.
- Release the 16-30 s Shorts first and measure completion and like rate before the full PV.

Kept from the earlier direction: the story device, palette roles, hidden details and signature gesture below.
Earlier direction (2026-10-21, superseded for the picture style): **cinematic 2.5D anime** (cut-out
illustrations layered in depth, 3D camera moves, depth of field, bloom, light rays, grain); pixel art was then
used only for game-style pop-ups (MISS!, NO COUNT).
Story device: **cool her vs real her** (comedic take on Gura's REFLECT split face). Navy streaming room at
night turns into an imaginary stage when she is confident, collapses back when she fails. Chat = the audience.
Palette: ink navy #1B2340, cobalt #3C6DF0, sky #9CC4FF, white #F4F6FB; coral #FF7B8A only for feelings
(blush, めっ, honest lines); lemon #FFD64A only for gags (stamps, SFX words). Room backgrounds must be
clearly lighter than her navy sweater (or add a cobalt rim light).
Hidden detail: the sleeping-cat chest patch opens one eye at each fail; a ノーカン counter ticks up and is
pawed back to 0 at the end. Signature gesture: 「めっ」 cat-paw boop (lean-in squint → boop → finger up).
References studied (ideas only, never copy designs): Shigure Ui 「粛聖!! ロリ神レクイエム☆」 (text wall,
chat-as-crowd, prop gag, copyable dance) and 「ひっひっふー」, Gawr Gura 「REFLECT」, Mizumiya Su
「うみゃうにゃはっぴーらいふ」 (sticker titles), Otonose Kanade 「GREATEST」/「アイシカケ」 (cinematic close-up),
32ki 「メズマライザー」 (copyable pose, hidden details), Frieren character PVs (name card).
Pixel references from the owner (2026-10-29), analysed in `docs/pixel_reference_breakdown.md`: the Opus 5.5
Alice MV (BV11unF6fEmq, a game session in which the lyrics are the level), the Undertale Asgore fight (BV1PUHf6cEG6,
game mechanics as story beats, 「*」 narration), the pixel Silver Wolf rhythm PV (BV1xW4y197K9, one fixed Muse
Dash-like layout and a result screen), plus similar JP/US works (sasakure.UK dot PV, TORIENA 「PULSE FIGHTER」,
ゆず 「ALWAYS」). Each borrows attention (a game IP's fandom, a famous song, or the Opus 5.5 trend) and uses a style
that fits its subject. XIYIN borrows none of that, so the premise has to come from her own story.
Approved combination (2026-10-29): a fixed rhythm-stage layout as the backbone, 「*」 narration
boxes for the gags, tile-built words only for the hooks (余裕, 大天才, ノーカン, めっ), LIVE on/off bookends and a
result-screen end card.
Research write-up on deterministic PV production: https://claude.ai/artifact/VGp4FeD6AcqwvPXWxyuS7g (private).
Backgrounds (owner feedback 2026-10-30): code-drawn pixel cities read as generic ("too AI-generated, lacking the
right elements") and N5 pixel-art scenes read as "too AI, too cyber" (lo-fi neon / cyberspace look, garbled fake
lettering). Current direction: **2D anime pop backgrounds built from the song**, Alice-MV game grammar on top.
- Plates and props are NovelAI V5 drawings in a flat anime style (cel shading, clean lineart): summer sky, sunset
  town, manga speed lines, blush pattern, sunburst rays, starry riverbank, pink checker pop, dusk riverside, a sky
  climb, a festival with fireworks, a dawn rooftop; props are lyric motifs as white-bordered stickers (crown for
  大天才, mic for この声, camera + prohibition sign for スクショは きんし, bandage for あいたたた, heart for めっ,
  penlights for きみも, trophy for the result screen, a navy cat plush). No cyber / neon scenes, no text in images
  (takes with garbled lettering are regenerated).
- XIYIN stays a pixel sprite; lyrics are bold block words (M PLUS Rounded 1c ExtraBold sampled onto a tile
  grid) that assemble from flying tiles; key-cap lyric row, game HUD, coins / hop blocks / chorus targets.

## 4. Storyboard (times on `t2_optimized_full`)
Written for the 2.5D direction: shot content stands, the picture treatment will be redone in pixel art.
Asset tags: S still+motion, E expression swap, C chibi, A real motion (now a hand-drawn pixel sprite animation,
never a video model), T text/graphics (done in code).
| # | Time | Lyric | Picture | Text / FX |
|---|---|---|---|---|
| 1 | 0-3.2 | intro | dark room, monitor glow, silhouette from behind, ear twitches on beat (S) | grain, LIVE dot |
| 2 | 3.2-3.7 | breath | turns head to camera (S) | |
| 3 | 3.7-6.6 | ねえねえ… | close-up to camera, base smile, small tilts (E) | speech bubbles |
| 4 | 7.6-11.1 | ふふん そろそろ いくよ | nose-up, stands, pull back (S) | chat starts |
| 5 | 11.1-14.2 | break | name card (T) | name / "Vocal: AI (Gemini)" |
| 6 | 14.2-19.8 | 今日の私は だいてんさい | room → stage (paw wipe), fisheye low angle (S) | 「大天才」 sticker |
| 7 | ≈19.8-24.6 | 準備もバッチリ | checklist with paw ticks, peace sign (S+T) | |
| 8 | ≈27.8-33.5 | ざんねんでした 余裕だもん | finger wag, logo slam (S+T) | sticker logo |
| 9 | 34.4-42.4 | ほら スマートに キメちゃうよ | over-cool pose held, slow push-in (S) | |
| 10 | 42.6 | えっ | freeze, stage cracks to room, patch opens one eye (E) | counter 1 |
| 11 | 43.05-43.9 | あいたたた | fall: chibi or sprite animation (C/A) | thud, lemon 「ドテッ」 |
| 12 | 44.18-45.1 | ちょっと待った | palm-out "wait", ears flat (E) | |
| 13 | 45.8-48.7 | いまのは カウントに… | referee X with sleeves (S) | lemon ノーカン stamp |
| 14 | 49.2-≈52 | あーもう にやけないでよ | pout, chat floods ニヤニヤ (E) | coral blush |
| 15 | ≈52-55.6 | 深呼吸 せーの | sleeves to cheeks, inhale, crouch, freeze (S) | |
| 16 | 55.6-≈59.5 | 余裕だもん ほら… | stage + glowing 余裕だもん text wall (S+T) | pulses on kick |
| 17 | 59.7-64.1 | ノーカンじゃん | split screen cool her / blushing her (E×2) | counter 2 |
| 18 | 64.4-68.8 | 笑ったでしょ めっ もういっかい | signature combo, boop at 66.82 (A) | boop, coral めっ |
| 19 | ≈69-73 | よそ見しないで… | flicks a chat bubble with her tail (S+T) | |
| 20 | ≈73-77 | 強がりだって 本気だもん | cinematic soft-light honest close-up (E) | thin lettering |
| 21 | ≈77-83 | この声で キメちゃうよ | stage, mic up, light sweep (S) | |
| 22 | 84.6-89.7 | スクショは きんし… | sleeve over lens, 禁止 stamp 86.3, wink (S) | shutter; 「※冗談です」 |
| 23 | ≈90-95 | なまいきなんて… | arms crossed, fisheye (S) | |
| 24 | 96.2-≈104 | ぷいって そっぽ… | slow head turn + tail swish, peek back (S/A) | lemon ぷいっ |
| 25 | ≈104-110 | 吹き出しちゃうな | bursts out laughing (E) | counter 3, patch both eyes |
| 26 | ≈110-113 | 悔しいままで… | reflection in dark monitor (S) | thin lettering |
| 27 | 112.9-116 | いいこちゃんなんて… | grin, kicks counter away (C) | |
| 28 | 116.2-122.4 | 震えるつま先で… | boots close-up, trembling toes, firm step (S) | |
| 29 | 122.8-125.2 | わらうな こっからが… | room unfolds into the biggest stage (T) | paw wipe |
| 30 | 125.8-≈130 | 余裕だもん もっと… | wide stage, double text wall, chat lights (S+T) | |
| 31 | ≈130.2-133.5 | 転んだあとが 見せ場じゃん | slow-mo fall replayed as a spin (A/S) | +1 → ✕ |
| 32 | 133.5-≈138.5 | 笑ったでしょ めっ… | boop again at 137.36, mirrored (A) | boop |
| 33 | ≈139-147 | よそ見しないで / 巻き込んで | chat bubbles become cat-ear silhouettes (T) | bilingual chat |
| 34 | ≈147-153.6 | 最後まで 歌いきるよ | held note, bloom, wide (S) | |
| 35 | 154-158.5 | ほらね やっぱり 余裕でしょ | back to room, base face (E) | grain |
| 36 | 158.5-≈163 | ふふん たぶんね | small shrug (E) | |
| 37 | ≈163-172.5 | また来てよね | small wave, switches off the light herself (S) | LIVE dot off |
| 38 | 172.5-178.6 | outro | end card, counter pawed to 0, patch winks (T) | AI credit |
Shorts map: stumble teaser = shots 10-16; めっ challenge = 15-18; short30 = 9-17.

## 5. Assets
Done (ChatGPT, 1254×1254, pixel-aligned): `art/chatgpt_frames/` a_base_bust, eyes_half, eyes_closed,
mouth_open_fixed (image-7 mouth transplanted onto the base). Missing: half-open mouth.
Needed: expressions E3 shocked, E4 flustered, E5 めっ squint, E6 laughing, E7 honest; poses P1 over-cool,
P2 referee X, P3 ぷいっ, P4 せーの crouch, P5 wave, P6 fallen, P7 paw boop; chibi C1 fallen, C2 kick;
backgrounds B1 room (mid-tone, lighter than her sweater), B2 small stage, B3 big stage, each 16:9 and 9:16.
Rules: always use the reference sheet; plain light-grey background; no text; never name real artists or
VTubers in image prompts; face-only variants via masked edits (or transplant the changed region onto the base).
For the pixel PV, these illustrations (and `art/generated/`, `pv3/stickers/`) are the design and colour source
for the sprites; the sprite list is set after the pixel test.

## 6. Generation plan (updated 2026-10-29)
- **Video generation models: not used** (owner decision 2026-10-29). The fal.ai bake-off is cancelled.
  `pv3/seedance/` (Seedance 2.5 first/last-frame pack) is kept only as history; do not submit it.
- Image model: **NovelAI V5 ("N5") via `.claude/skills/oc-gen`**, which the owner allows the assistant to use
  directly (2026-10-29), as source material for the pixel sprites (generate on the reference sheet, then reduce to
  a fixed pixel grid and palette and clean up by hand). ChatGPT / OpenAI images are no longer needed.
- Always quote cost and get the owner's OK before any paid run.
- Keys are **network secrets injected by the environment's proxy** as request headers (no env vars; the
  assistant never sees them): NovelAI `Authorization: Bearer` for `*.novelai.net`; OpenAI `Authorization: Bearer`
  for `api.openai.com`; fal `Authorization: Key` for `*.fal.run`. Scripts must NOT add auth headers themselves.
  `fal.media` / `*.fal.media` (result downloads) are plain allowed domains.

## 7. Files
- `audio/` final master + Shorts (MP3). Large WAVs/stems not committed; rebuild with `tools/`.
- `art/` reference sheet, aligned ChatGPT face frames, pixel-art tests.
- `pixel/fonts/` pixel fonts with their licenses: Fusion Pixel 12px ja (lyrics; zh_hans kept as a spare), Press
  Start 2P (judgement / score), 美咲ゴシック 8px (tiny HUD). DotGothic16 was tested and dropped (strokes drop out
  at 16 px without anti-aliasing).
- `tools/` separate.py (UVR MDX-Net vocal separation via onnxruntime), analyze.py (technical/music/vocal
  measurements), asr.py (sherpa-onnx Whisper-small + ReazonSpeech lyric intelligibility), optimize.py
  (SFX/mix/Shorts), plot_window.py, compare_opening.py, pixelize.py. Paths inside are the old session's
  scratchpad; adjust before reuse.
- `data/` measurements and ASR results for all five Gemini versions (t1-t5).

## 7b. Production status (2026-10-21)
- All assets generated with NovelAI via `.claude/skills/oc-gen` (60 Anlas spent by the assistant; normal-size V5 = 0).
- `pv/preprocess.py` (cutouts, plates, beats, lip-sync envelope) and `pv/render.py` (all 38 shots, code-rendered:
  2.5D camera, expression swaps, blink + lip-sync, stamps, chat, ノーカン counter, captions, grain) produce draft 1.
- Render: `render.py segment i 4` x4 in parallel, concat, mux `audio/t2_optimized_full.mp3`. Video files are not
  committed (size); rebuild from the repo. No video model used; key-pose cuts replace motion shots.
- 2026-10-23: `pv2/` (puppet rig from the reference sheet + 撮影-style compositing) and `pv3/` (phrase-synced
  storyboard, `autorig.py` deformation, one typographic system, 75 drawings). Reuse `pv3/lyrics_timed.json`
  (ASR-aligned syllable timing) for the pixel PV. Both are superseded for the picture style.
- 2026-10-29: **pixel PV test** (`pixel/`), 41.6-69.0 s (stumble → ノーカン → chorus → めっ), rendered in code:
  - Sprite sources: 7 chibi poses from NovelAI V5 (0 Anlas), `art/generated/pixel_src/` (`prompts.sh`, manifest).
  - `pixel/sprite.py convert` turns a source into an editable text grid (`sprites/*.auto.txt`, one character per
    palette role; hair and sweater split per image by 2-means so the hair is always brighter than the sweater).
    `pixel/faces.py` smooths the grid, redraws the face from hand-made eye/mouth templates, fixes parts the
    converter gets wrong and writes `sprites/*.txt` + `*.png` (about 48x80 px, shown at x5).
  - `pixel/stage.py` draws the rhythm stage on a 384x216 screen (x5 = 1080p): pastel grid stage, scrolling floor,
    paw / cat notes on the sung syllables, PERFECT bursts, combo (99 → MISS on えっ), score, MISS counter pawed
    back to 0, LIVE badge, rising chat, karaoke lyric line, 「＊」 narration boxes with typewriter blips, block
    words (ドテッ, ノーカン, べー, 余裕, めっ!), PAUSE, READY?/GO!, めっ x2 zoom, RETRY? menu.
    `python3 pixel/stage.py preview <t...> --out sheet.png` for stills;
    `python3 pixel/stage.py render --t0 41.6 --t1 69.0 --out clip.mp4` renders in about 1 minute.
  - QC of the test render: 822 frames, video and audio both 27.40 s, 0 decode errors, BT.709 tags, -13.1 LUFS,
    peak -0.9 dBFS (limiter at -1 dB); notes vs audio onsets: median 12 ms, 20/24 within 100 ms.

- 2026-10-30: **sprite v2** after owner feedback (v1 sprites looked unattractive; hair colour off-model).
  Sources are now drawn by NovelAI V5 *as pixel art* (2-head chibi, big eyes; prompt `PX` in
  `art/generated/pixel_src/prompts.sh`), then `pixel/snap.py` snaps them to a true grid (160 px tall, shown x3 on
  a 640x360 game screen) and repaints hair / tail / ears, sweater, socks / boots and accents with ramps sampled
  from the reference sheet (hair base (73, 99, 173), sweater (56, 61, 89)). Output in `pixel/sprites2/`.
  Still to do on v2: socks partly hair-blue in the run poses, sweater side panel / cuff stripes, the remaining
  poses (punch, jump-swipe, trip, ノーカン, あっかんべー, めっ, giggle), run cycle, background, 640x360 stage.
- 2026-10-30: **sprite v3 (sharpness)** after owner feedback ("looks blurry"). Measured causes: (1) the NovelAI
  "pixel art" is soft (over half of its colour runs are 1 px), and v2 re-gridded those in-between colours; (2) odd
  display scales (x3, and x5 in the first test) put sprite-pixel edges across the 2x2 chroma blocks of 4:2:0
  video: test encode, sprite-edge error 95th percentile 17.3 at x3 vs 5.3 at x2 and 4.0 at x4.
  Fix: `snap.clean()` maps every source pixel to one fixed role-based palette (from the sheet) before the
  majority snap, thin features win thin cells, then a clean 1 px outline; sprites are 200 px tall
  (`pixel/sprites3/`, heights per pose in `heights.json`) on a **960x540 game screen shown at x2** (even scale);
  a 3840x2160 master (x4) can be exported for YouTube. Dropped: `p02_run_b` (eyes came out dark).
  Consistency plan: gameplay motion is rigged from one side-view master (run A) instead of new generations;
  gag poses keep the fixed palette. Known: some tails stay navy where they touch the sweater.

- 2026-10-30: **full PV v1** (0-178.65 s), `pixel/pv.py` (+ `scene.py`, `blocks.py`, `anim.py`):
  - Two layers per frame: an HD layer (1920x1080: anime plate, stickers, English subtitle) and the 960x540 pixel
    game layer at x2 (ground tiles per section, block words, coins / hop blocks / chorus targets with PERFECT
    bursts, XIYIN, HUD with LIVE/OFF, LV/EXP, score, MISS, combo, key-cap lyric row, chat, 「＊」 narration,
    menus). Every frame is a function of t; four segments render in parallel and are joined losslessly.
  - Run cycle rigged from the one run-A master (`anim.py`: legs split at the hips and swung with a RotSprite-style
    resample, hair flutter, feet grounded, one stride per beat; beat grid 136 BPM, phase 0.024 s, measured from the
    onset envelope with no drift). Gag poses are the v3 front poses.
  - Flow: stage curtain title (PRESS START, curtains open on ねえねえ) → tile-flip into the summer sky (大天才 +
    crown, ticked checkboxes, 完璧 + trophy) → sunset town (余裕, キメ + star) → trips on a 「っ」 block: MISS, manga
    shock lines, PAUSE menu, 「＊」 narration, ノーカン stamp (MISS pawed back to 0 and the combo restored), chat
    ニヤニヤ, あっかんべー, blush pattern, READY?/GO! → chorus on sunburst rays (targets every beat, a second ノーカン,
    めっ punch-in, RETRY?) → starry riverbank (本気, この声 + mic, shooting stars) → pink pop (camera flash, the
    screenshot becomes a polaroid, 禁止 + prohibition sign, tossed away; なまいき) → dusk riverside (ぷいっ facing
    away, ぷふっ giggle, 悔しい, つまんない) → rainbow block stairs one step per beat (本番) → curtain closes and
    opens on the festival (fireworks, 見せ場, めっ, きみも + penlights, 最後まで) → STAGE CLEAR result → dawn rooftop
    (余裕でしょ, また来てよね, LIVE → OFF, save card, credits) → power off.
  - Plates: `art/generated/anime_bg/prompts.sh` (all V5 normal size, 0 Anlas), upscaled x2 with Real-ESRGAN
    `realesr-animevideov3` on CPU (`pixel/upscale.py`, `pixel/plates/build.sh`; the plates are not committed).
  - Render: `python3 pixel/pv.py render --out pv.mp4 --jobs 4` (about 0.3 s per frame per process);
    `python3 pixel/pv.py preview <t...> --out sheet.png` for stills.
  - QC of v1: 5360 frames, video 178.67 s / audio 178.65 s, 0 decode errors, BT.709 tags, -13.8 LUFS integrated,
    true peak -0.4 dBTP (aim for -1 next time: lower the limiter), segment joins checked frame by frame.

## 8. Open items (2026-10-29)
1. Owner: confirm SFX levels by ear (phone + headphones), and watch / listen to the pixel test.
2. Approved by the owner (2026-10-29, "proceed autonomously"): the combination in section 3 and the pixel test.
3. Assistant, next: a cleaner jump / cheer source (the jump pose's bent legs read as one skin-coloured blob); the
   sleeping-cat chest patch on the sprites; 2-3 frame idle and hit animations; then extend the stage to the whole
   song (0-178.6 s) with the remaining gags, and 9:16 versions for the 3 Shorts. Never send or write keys: the
   proxy injects auth headers for the allowed hosts.
