# OC PV — 「余裕だもん」 (working project brief)

Handoff document so any new session can continue without the original conversation.
Owner works solo (no team). Keep token use low: **do not run multi-agent workflows**; work inline.
Reply in the language of the owner's latest message (usually English). The OC has **no name yet** (ask).

## 1. The OC (source of truth: `art/reference/oc_reference_sheet.webp`)
Anime cat-girl: long straight deep-navy hair, one ahoge, navy cat ears with pink inner ears, small blue
cat-shaped hair clip (position as in the sheet), blue half-lidded eyes, small confident closed-mouth smile.
Oversized navy sweater, sailor collar with cobalt stripes, navy tie with a small black cat emblem,
light-blue sleeping-cat chest patch, striped cuffs with paw prints, dark grey shorts with a cobalt side stripe,
navy cat tail, navy knee socks with a cobalt stripe and paw print, chunky black lace-up boots with blue accents.
Personality for this song: acts cool and smug → trips → "that doesn't count" → blushes → owns it.
Teasing and self-assured; never needy; never sexualised or "brat"-framed.

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

## 3. Creative direction (decided)
**Cinematic 2.5D anime**: full-quality anime illustrations, cut out and layered in depth, 3D camera moves
(parallax, push-ins), depth of field, bloom, light rays, light film grain. Pixel art was tested
(`art/pixel_tests/`) and set aside except as optional game-style pop-ups (MISS!, NO COUNT).
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

## 4. Storyboard (times on `t2_optimized_full`)
Asset tags: S still+motion, E expression swap, C chibi, A needs generated motion, T text/graphics (done in code).
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
| 11 | 43.05-43.9 | あいたたた | fall: chibi or generated motion (C/A) | thud, lemon 「ドテッ」 |
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

## 6. Generation plan (owner wants the assistant to generate everything via API)
- Images: compare **NovelAI V5** (anime-specialised; transparent backgrounds; V5 Full inpainting; but
  Precise Reference / Vibe Transfer reportedly still fall back to V4.5) vs the **OpenAI image model**
  (passed the alignment test with masked edits; slightly flatter style than the sheet). Pick one for ALL assets.
- Video (only ~4 shots: fall, めっ combo, ぷいっ turn, wave): **fal.ai** bake-off with start+end frames —
  Wan 3.0, MiniMax H3, Kling O3/3.0 Pro, Vidu Q3 Pro; 2 shots × 2 takes × ~3 s ≈ $5-10. Score by measurement:
  on-model colours, line/flat-shading retention, flicker, end-frame match, clean background for cutout.
- Always quote cost and get the owner's OK before any paid run.
- Keys are **network secrets injected by the environment's proxy** as request headers (no env vars; the
  assistant never sees them): NovelAI `Authorization: Bearer` for `*.novelai.net`; OpenAI `Authorization: Bearer`
  for `api.openai.com`; fal `Authorization: Key` for `*.fal.run`. Scripts must NOT add auth headers themselves.
  `fal.media` / `*.fal.media` (result downloads) are plain allowed domains.

## 7. Files
- `audio/` final master + Shorts (MP3). Large WAVs/stems not committed; rebuild with `tools/`.
- `art/` reference sheet, aligned ChatGPT face frames, pixel-art tests.
- `tools/` separate.py (UVR MDX-Net vocal separation via onnxruntime), analyze.py (technical/music/vocal
  measurements), asr.py (sherpa-onnx Whisper-small + ReazonSpeech lyric intelligibility), optimize.py
  (SFX/mix/Shorts), plot_window.py, compare_opening.py, pixelize.py. Paths inside are the old session's
  scratchpad; adjust before reuse.
- `data/` measurements and ASR results for all five Gemini versions (t1-t5).

## 8. Open items
1. Owner: confirm SFX levels by ear (phone + headphones). 2. Owner: choose the OC's name.
3. Owner: add API keys/domains, start a new session. 3b. Assistant, first task of the new session: write and
live-test a repo skill at `.claude/skills/oc-gen/` (SKILL.md + scripts) for NovelAI V5 / OpenAI image generation
and masked edits (always attach the reference sheet), fal start/end-frame video jobs (submit, poll, download),
a cost quote + explicit owner OK before every paid call, and a manifest log of prompt/model/seed per output.
Never send or write keys: the proxy injects auth headers for the allowed hosts. 4. Assistant: image-model test (NAI V5 vs OpenAI),
then generate the asset list. 5. Assistant: fal video bake-off. 6. Assistant: cue sheet (frame-exact captions +
shot list), 2.5D compositing, final edit of PV + 3 Shorts.
