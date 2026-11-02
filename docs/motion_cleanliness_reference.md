# Motion and cleanliness reference (for the XIYIN stream PV, 2026-11-02)

Owner request after approving VTuber model v3: keep the character's motion, hair and details clean, with no
white artifacts; research thoroughly online; resume the PV.

Evidence levels: **source** (read in the code or page itself), **docs** (search extract of official docs; the page
host was not reachable from this session), **guide** (third-party tutorial or forum), **measured** (tested here).
Hosts not reachable from this session: docs.live2d.com, journal.novelai.net, clipstudio.net.

## 1. VTuber idle motion (Live2D conventions)
- **Breath / idle sway** (source: the Cubism Web Framework as bundled in `pixi-live2d-display@0.4.0`,
  `cubism4.es.js`, and `phaser3-rex-plugins` `cubismbreath.ts`): value = offset + peak * sin(2 pi t / cycle),
  added with a weight. The sample model uses five parameters at once with non-commensurate cycles:
  `ParamAngleX` peak 15, cycle 6.5345 s; `ParamAngleY` 8, 3.5345 s; `ParamAngleZ` 10, 5.5345 s;
  `ParamBodyAngleX` 4, 15.5345 s; `ParamBreath` 0.5, 3.2345 s (all weight 0.5). Odd cycles keep the sum from
  looping visibly.
- **Blinks** (source: `cubismeyeblink.ts`): defaults interval 4.0 s, closing 0.1 s, closed 0.05 s, opening 0.15 s;
  the next blink comes after a random 0 to 2x the interval (docs: "0秒から設定時間の2倍までのランダム性").
- **Lip-sync** (docs, Live2D MouthMovement): the SDK only drives mouth opening from the voice level (RMS x gain,
  clamped 0-1, smoothed); vowel shapes are not part of it and need custom handling.
- **Hair physics** (docs, Live2D physics settings): input = head / body angle, output = hair parameters through a
  pendulum chain; "ease of swinging" 0.7-0.99, duration sets the speed; the tips lag the roots.
- **Hand-drawn anime** (guide, Keio / IPSJ papers on anime hair; Adobe puppet-tool notes): hair moves as bundles
  with limited-animation timing, the tips follow later than the roots (follow-through); repeated mesh warps look
  "rubbery" (ぐにゃー) if the amplitude is large, so keep it small and keep the face rigid.
- **口パク** (guide, mynavi クリエイター連載): three mouths (closed / half / open), not random flapping but sequenced;
  anime is drawn on twos or threes.

## 2. Clean edges (no white or dark fringe)
- **Cause** (guide: Shawn Hargreaves "texture filtering alpha cutouts"; Khronos forum; Autodesk premultiplied
  alpha docs; A. R. Smith 1995 "Image Compositing Fundamentals"): when a cut-out is resampled (scaled, rotated,
  filtered), the colour of transparent pixels bleeds into the edge. Transparent pixels holding the old background
  colour (here V5's light grey) give a pale fringe; holding black gives a dark fringe.
- **Fix**: resample premultiplied (colour x alpha), or first replace the colour of every not-fully-opaque pixel with
  the nearest opaque colour ("edge padding" / dilation). Remove Color Matting / Unmult (Adobe docs) undoes a known
  background colour mixed into semi-transparent edges.
- **Pillow** (guide: Pillow issue #5304, PR #7888; measured here, Pillow 12.3): RGBA resize and rotate use
  premultiplied alpha internally, so they do not fringe by themselves; the fringe came from our pixels.
- **What we found** (measured): the v3 cut-out's partly transparent edge pixels still held V5's light grey
  (p99 "lighter than the pixel inside" = 214 levels); after edge padding it is 22 levels. One real white speck was
  opaque background seen in a gap between strands next to the raised hand, tinted bluish by the upscaler so the
  gap test missed it; the gap test now also takes light, low-saturation, non-reddish pixels.
- **Upscaler halos** (guide: Real-ESRGAN paper / docs, Selur forum): Real-ESRGAN trains against ringing and
  overshoot; deringing filters exist for bright outline artifacts. We saw none on the v3 frames at 2048.

## 3. Video encoding of line art
- 4:2:0 chroma subsampling halves colour resolution, so saturated thin edges can get colour fringes (guide:
  forasoft glossary, doom9 / videohelp forums on anime line art). Our deliverable stays yuv420p for player
  compatibility (unverified whether YouTube keeps 4:4:4 uploads); x264 `-tune animation`, CRF 16.

## 4. Runner animation
- Run cycle key poses: contact, down, push / passing, peak (flight), contact (guide: AnimSchool blog, Lynda
  course); landing on the ball of the foot; more airtime than a walk. Muse Dash itself: Unity; strike motions
  follow the chart (GCores). No public source on its frame counts.
- AI sprite-sheet tools keep a fixed "anchor" image for identity and describe only the motion (guide: Scenario,
  Summer Engine); single drawings per frame drift, which is why our avatar keeps one drawn master body.

## 5. NovelAI quota
- On Opus, V5 at normal size and up to 28 steps costs no Anlas but draws on a usage limit that recharges over time
  (guide: NovelAI journal "Understanding the Opus Usage Limit", as quoted in search; note.com イツキ measured about
  11% per day, roughly 190 images per day, on 2026-08-21). When it runs out, V5 costs Anlas (13-15 per image here).
- The limit applies only to V5; other models stay free on Opus (guide, same journal). **Measured** 2026-11-02:
  `nai-diffusion-4-5-full` at 1024x1024 cost 0 Anlas; V5 also cost 0 again at 09:07 UTC (partly recharged).

## 6. Applied in the PV (pixel/vtmotion.py, pixel/vt3.py, pixel/stream.py)
1. Edge padding of every not-fully-opaque pixel, then premultiplied resampling; one resample per frame (scale,
   roll, breath, nod, pop and hair in a single displacement map).
2. Idle: breath 3.2345 s (0.45% vertical), roll 0.4 deg at 5.5345 s + 0.3 deg at 15.5345 s about the bottom
   centre, a small nod on the beat while she plays.
3. Hair: only the long strands (viewer-left), the strands beyond the raised sleeve and the ahoge sway (5 / 3.5 /
   4 px in 1024 units), with the phase lagging down the strand; face, hand and sleeve are rigid.
4. Blinks: CubismEyeBlink timing (mean 4 s, 0-2x random, min 1.2 s apart), the closed frame for 0.17 s.
5. Lip-sync from the lyric syllables: vowel a / e / i -> open, o / u -> small round, ん / pauses -> closed; on twos;
   open and close pass through the small mouth; repeated syllables get a small mouth in between.
6. Expression accents on key words, switched on a cut with a 1.8% pop (no cross-fades between drawings).

## Sources
- Cubism framework source: [pixi-live2d-display 0.4.0 cubism4.es.js](https://unpkg.com/pixi-live2d-display@0.4.0/dist/cubism4.es.js),
  [cubismeyeblink.ts](https://unpkg.com/phaser3-rex-plugins@1.60.6/plugins/gameobjects/live2d/framework/src/effect/cubismeyeblink.ts),
  [cubismbreath.ts](https://unpkg.com/phaser3-rex-plugins@1.60.6/plugins/gameobjects/live2d/framework/src/effect/cubismbreath.ts)
- Live2D docs (search extracts): [自動まばたき](https://docs.live2d.com/cubism-sdk-manual/autoeyeblink),
  [Breath](https://docs.live2d.com/en/cubism-sdk-manual/breath), [MouthMovement](https://docs.live2d.com/en/cubism-sdk-manual/mouthmovement-unity/),
  [物理演算の設定](https://docs.live2d.com/en/cubism-editor-manual/physical-operation-setting/)
- Hair: [Automatic Generation of the Periodic Hair Motion of 3D Characters for Anime Production (IFIP)](https://dl.ifip.org/hal-02128610v1),
  [IPSJ EC2019008](https://ipsj.ixsq.nii.ac.jp/record/199401/files/IPSJ-EC2019008.pdf),
  [Adobe パペットツール](https://helpx.adobe.com/jp/after-effects/desktop/animate-in-after-effects/animate-with-puppet-tools/animating-puppet-tools.html),
  [Adobe コミュニティ: 一枚絵を別々に動かす方法](https://community.adobe.com/質問-132/一枚絵を別々に動かす方法-351566)
- 口パク: [マイナビ クリエイター連載 22](https://news.mynavi.jp/techplus/article/kurieita-22/)
- Alpha: [Shawn Hargreaves: texture filtering alpha cutouts](https://www.shawnhargreaves.com/blog/texture-filtering-alpha-cutouts.html),
  [Autodesk: Premultiplied Alpha](https://help.autodesk.com/cloudhelp/2016/ENU/3DSMax/files/GUID-E49782BE-6486-4B9D-929A-7A02535F1829.htm),
  [A. R. Smith 1995](https://www.cs.princeton.edu/courses/archive/spr08/cos426/papers/Smith95a.pdf),
  [Pillow issue 5304](https://github.com/python-pillow/Pillow/issues/5304),
  [Adobe: Unmult / Remove Color Matting](https://community.adobe.com/t5/after-effects-beta-discussions/new-in-beta-unmult-effect-about-time-right/td-p/15559127)
- Upscaler: [Real-ESRGAN anime models](https://mintlify.com/xinntao/Real-ESRGAN/models/anime-models),
  [Selur forum: DeRing vs DeHalo](https://forum.selur.net/thread-2099-newpost.html)
- Encoding: [forasoft: chroma subsampling](https://www.forasoft.com/learn/video-quality/glossary/terms-vqm/chroma-subsampling),
  [doom9: colour-cast lines in anime](https://forum.doom9.org/archive/index.php/t-184958.html)
- Runner: [AnimSchool: key poses of a run cycle](https://blog.animschool.edu/?p=634), [GCores on Muse Dash](https://www.gcores.com/articles/98377),
  [Scenario: spritesheets](https://help.scenario.com/en/articles/create-spritesheets-with-scenario)
- Stream layout: [MoguraVR: VTuber 配信画面デザイン](https://www.moguravr.com/vtuber-screen-design/)
- NovelAI: [DEV Community: V5 on Opus](https://dev.to/ilan_kim/novelai-v5-on-opus-usage-limits-the-2026-09-21-subscription-anlas-reset-and-the-apinovelainet-567l),
  [note (イツキ): recovers 11% per day](https://note.com/itsuki_ailab/n/nc7a9c09e6096?hl=en),
  [NovelAI journal: Opus usage limit](https://journal.novelai.net/opus-usage-limit-explained/) (search extract)
