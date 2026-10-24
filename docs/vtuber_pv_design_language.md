# VTuber MVs and animated PVs: design language (research notes, 2026-10-24)

Why this exists: the owner reviewed the code-rendered PV (2026-10-24). The motion is stiff, the blinks break the
illusion, and the result is far behind what video generation plus editing gives. This file collects what the people
who make VTuber MVs actually do, and turns it into rules for this PV. It builds on `docs/reference_breakdown.md`
(storyboard-frame study of five MVs, 2026-10-22).

## 0. Method, evidence levels, limits
- Sources: web search plus the pages that could be opened from this environment. The network policy blocks most
  sites, and YouTube/Bilibili video downloads fail (bot check / CDN 403), so **no frame-level analysis of motion was
  possible this time**. Everything about timing comes from creators, press or fan analysis, not from counting frames.
- Labels used below:
  - **[read]** I opened the page this session and it says so. A creator's statement is still only the creator's claim.
  - **[search]** only seen through search-result summaries; the page itself was not opened. Treat as unverified.
  - **[own]** my analysis or general animation knowledge, not checked against a source this session.

## 1. What is wrong with our renders, in the field's terms

What the code does (read from the repo):
- Draft 1 (`pv/render.py`, 30 fps): a blink is a 4-frame swap to a *separately generated* closed-eye image, fired at
  random every 2.6-4.8 s, whatever the character is doing. The mouth is a binary swap driven by the audio envelope.
- v3 (`pv3/autorig.py`): every drawing is bent by one smooth displacement field: sine-wave head sway, a nod on each
  beat, sine breathing, sine hair swing. It updates every frame.

Why that reads as dead:
1. **No key poses, constant drift.** Japanese TV anime is mostly drawn on threes (8 drawings per second); staff on
   *THE FIRST SLAM DUNK* say full 24-drawing motion "moves too smoothly and looks wrong" [search]. The ビビデバ MV
   keeps its anime on threes and switches to twos as the story heats up [search, fan analysis]. Guilty Gear Xrd
   keyframes without inbetweens to look like anime at 60 fps [search]. Our warp is the opposite: a continuous
   sine motion on every frame with no hold, no snap, no change of pose. That is what reads as a puppet.
2. **Bending a finished drawing is not animation.** Live2D looks alive because the artwork is split into parts and
   every deformation is designed by hand, then keyed. Even there, hair looked stiff until the team gave the tips
   and the middle different timing [search: CGWORLD on the BanG Dream! Live2D work]. Warping one flat image cannot
   change the silhouette or produce a new pose; it only makes the picture wobble.
3. **The blink is a different picture.** Two AI images never match outside the eyes: line weight, strands and
   colour differ, so for 4 frames the whole face pops. Anime blinks are designed drawings: the basic one is a single
   closed frame between open frames; a careful one adds a half-closed frame; a three-frame half-closed-half reads as
   slow, deliberate acting [search: Aoike Ryosuke's Flash-animation column]. Cel-era anime mostly used just open and
   closed, and visible half-blinks became common with 3DCG and Live2D [search: blog essay]. With large eyes, a bit of
   pupil stays visible during the blink so the face never goes "dead", and the blink takes longer [search: design guide].
4. **Blinks with no reason.** Animators place blinks on a gaze shift or a head turn ("glancing down") [search: Aoike];
   many short MV cuts have no blink at all, and the ビビデバ dance chorus deliberately shows blink-free, mask-like anime
   faces [read: MoguLive review]. A blink every 3-4 s at random is a screensaver rule, not acting.
5. **Half-measures sit in the uncanny zone** [own]. A confident still with camera and graphics reads as design (anime
   uses held stills, 止め絵, for poses, gags and punch lines [search]). Real acting reads as alive. A still that
   "breathes" and swaps eyes is neither.

## 2. How VTuber MVs are made: production tiers

| Tier | What it is | Cost / team | Examples | How it moves |
|---|---|---|---|---|
| T0 | One illustration + lyrics (歌ってみた) | ¥3,000-8,000 [search: BOOTH/coconala price lists] | most covers | camera drift, particles, lyric motion |
| T1 | Layered illustration moved in AE or Live2D | ¥20,000+; +¥10,000 to split parts, +¥10,000 for lyric motion [search: coconala] | most indie originals | parts deformation, text carries rhythm |
| T2 | Full Live2D MV with a rig made for the MV | individual creators / Live2D JUKU | Live2D JUKU 『棄てられた惑星で』 (2026, all Live2D) [search]; 瀬兎一也's talk on choosing hand-drawn vs Live2D shots and making loops look natural [search] | keyed parameters, physics |
| T3 | Hand-drawn indie animation | 1-3 people | 粛聖!! ロリ神レクイエム☆ (illustration & animation ががめ, movie 鬼灯わらべ); 兎田ぺこら 「ぺこぺこ!! チキンフィーバー☆」 (animator ひとびと) [search]; 「まいたけダンス」 (ばかくん三世, from a stream ad-lib, 2-head chibi that "moves smoothly", 10M+ views, Shorts parodies) [search] | real drawings, holds, chibi gags |
| T4 | Small elite team, hybrid 3D/2D/live action | 2-3 core people, up to 20-40 per job [read: CGWORLD on 擬態するメタ] | 「ひっひっふー」 (Hurray!, 3 people, all Blender Eevee) [read/search]; 「ビビデバ」 (擬態するメタ: 360° camera + rotoscope, Clio Music 2025 bronze) [read] | frame rate used as storytelling |
| T5 | Studio, TV-anime quality | studio | Studio KAI (「Seishun Archive」, Marine 「幽霊船戦」 [read]); Qzil.la (Watame 「My song」); RIRI Yamashita (Miko 「Cherry Message」, 「Midnight Mission」); Wit Studio (Calliope 「Go-Getters」) [search]; Toei Zukun (Calliope 「Die For You」: mocap + live action, ~2 months) [read] | full character acting |

Observation [own]: the biggest hits are not the most expensive. The MV reported as the first VTuber original past 100M views is
the T3 ロリ神レクイエム (Sept 2023; 10M in 17 days) [search]; ビビデバ (T4) also passed 100M and is listed first in MoguLive's 2024
fan poll, where voters praised the MV's quality and its live-action + animation dance [read]. What the hits share: one
clear concept, a copyable motif (dance, pose, catchphrase), and editing locked to the music.

## 3. The design language

### 3.1 Concept first, then the method
- ビビデバ: the brief was "cross the making-of and the main film"; adding the constraint of a 360° camera made it
  possible within budget, shot as one take that shows front and back [read: CGWORLD]. The premise borrows *Who Framed
  Roger Rabbit*: anime characters "live in this world" and the film just records them [read: MoguLive review].
- ひっひっふー: she asked Hurray! directly; it is framed through her PC monitor to show her "unaware of the camera",
  and the song is about the joys and pains of making things [search: ぽぷりか's FANBOX/Video Salon summary].
- 擬態するメタ decide what is "面白い" first and design the workflow later; the two directors always do the planning,
  the offline edit and the final online edit themselves [read: CGWORLD].
- Kameyama Yohei (Calliope 「LET'S JUST CRASH」): "an MV is footage to lift the music, so the focus differs from an
  anime"; he built a beginning-development-turn-ending with an unexpected payoff [read: Real Sound].

### 3.2 A character version designed for the MV
- ひっひっふー used a character model made for the MV, adapting her delicate illustration style to the pop world of
  the video [search: Video Salon summary].
- ビビデバ gives Suisei an older, big-eyed design (Heisei/Y2K revival) instead of her current look, and shows it as a
  flat "toon" that stays separate from the live action [read: MoguLive review]. The face was kept out of the rotoscope
  and drawn by different animators from the body [read: same review, citing the making-of].
- Studio MVs redraw the talent in TV-anime model sheets [own, from the studio examples above].
- Lesson [own]: the illustration sheet is not an animation sheet. Animated MVs simplify the design for motion.

### 3.3 Timing: holds, snaps and frame rate as meaning
- Base on threes (8 drawings/s), ones and twos for accents; full smooth motion only where it is the point [search:
  SLAM DUNK staff; Endless Mode on twos; Nakamura Takashi drew a film on twos and only the water on ones].
- Frame-rate switching as a story device: in ビビデバ live action is 24 fps and anime 8 fps, anime goes to 12 fps when
  she throws the shoe, live action drops to 12 fps at the selfie and the two worlds meet, then the dance is 8 fps
  for both [search: fan frame analysis on Scrapbox].
- In ひっひっふー a clock's digital ticking turns into smooth continuous motion as the artist falls into flow: time
  feels continuous while creating and discrete in hindsight [read: CHE BUNBUN critique].
- Smooth motion is fine when it is real full animation of a simple design: the まいたけダンス chibi "moves smoothly"
  and that is part of its appeal [search].

### 3.4 Faces carry the performance
- "In motion, the most important thing is not the body but the face" [read: 八ツ橋まろん's note on 3D MVs].
- Kameyama: "even if you don't understand the language, you can roughly tell what's happening from the
  expressions"; Calliope praises his "cartoon-like" expressions [read: Real Sound].
- Physics is judged as a penalty system: clipping or stiff hair costs points, excellent physics earns a little
  [read: 八ツ橋まろん]. Our sine hair swing is exactly the kind of physics that loses points.

### 3.5 Eyes and blinks: working rules for this PV
From §1 [search] plus [own] where marked:
1. No blink in cuts shorter than ~2 s, unless the blink is the acting.
2. Blinks are motivated: on a gaze shift, a head turn, the start of a line, a change of mind.
3. Closed and half-closed eyes are designed drawings of the same image (same lines, same hair), not new generations:
   only the eye region may change.
4. Default: open, one closed drawing, open (the closed drawing held 2 frames at 24 fps) [own timing]. Slow, deliberate blink: half, closed (held), half.
5. Keep a sliver of pupil in the half-closed frame; the brows and upper lids move with the blink [own].
6. Signature idea [own]: a cat "slow blink" (a sign of trust in cats) on her smug beats, timed to the music. It
   turns the blink from a technical tic into character acting.

### 3.6 Typography is a main visual
- (From the earlier breakdown) ロリ神レクイエム: giant text walls, kanji stickers, chat-like small text.
- ひっひっふー: different fonts appear in sync with the drawing hand, one per technique [read: CHE BUNBUN]; まごつき
  hand-drew lyric text assets [search: Video Salon summary].
- えむ's lyric-video taxonomy: lyrics shown to be *looked at* (映像先行型, image-led) vs lyrics shown to be *read*
  (楽曲先行型, song-led); placement (fixed, bottom centre, full screen), decoration and motion follow from that choice
  [search]. Our v3 single karaoke line at the bottom is the song-led type; the hook lines want the image-led type.

### 3.7 Density, montage and gags from stream culture
- ひっひっふー packs a scrapbook-like opening montage (a date, a fast coder, a tired office worker) before her desk;
  the critic singles out the "exhilaration of layered effects and shots" [read: CHE BUNBUN]; KAI-YOU calls the
  2:44 MV impossibly dense [read].
- In-jokes reward fans: a blue screen reading 「あなたのPCは《めっちゃおつかれモード》」 parodies her stream-start
  screen, and the error code BADFOOD recalls a food-poisoning episode [read: CHE BUNBUN].
- Our equivalents already exist: chat as the crowd, the ノーカン counter, the sleeping-cat patch. They should be
  treated as the main visual system, not decoration [own].

### 3.8 Camera has a point of view
- Mostly conventional moves (horizontal pans, slight shake); save unusual moves for key moments; constant drone-like
  motion is discouraged [read: 八ツ橋まろん].
- Fisheye as a signature: Hurray! faked it in Eevee by distorting every object as seen from the camera [search:
  ぽぷりか's post on X].
- ビビデバ: mechanical pans "like a surveillance camera" give a cold, observing tone [read: MoguLive review].
- Our v3 rule "every shot has a camera move" goes against this [own].

### 3.9 撮影: compositing is what makes layers one picture
In anime, 撮影 (compositing) merges cels and backgrounds into one image and adds light, glow, blur and grain
[search: Natalie, Real Sound on ufotable/Shinkai]. Lighting is planned at the drawing stage to match the background
[search]. This is the layer where code is genuinely strong and where our pipeline should keep investing [own].

### 3.10 VTuber character design norms
- Most VTuber designs are "maximalist" (wild hair, horns, ears, complex outfits) so the persona reads at a glance;
  because a model is rigged once, detail is cheap there. Restrained designs such as ReGLOSS stand out [search:
  OGIUEMANIAX].
- A design has to hold up in motion, across expressions and angles that a single illustration never shows; sharp
  shapes read confident, round shapes gentle [search: design guide].
- Debut teasers often build the world and theme before showing faces (hololive EN's 2023 teaser hid all five
  members) and use silhouette reveals [search]. Evidence on debut-PV structure is thin.

### 3.11 Audience view of AI (risk)
- 2026 backlashes: Neverness to Everness (AI art after a no-AI promise; VTuber Ironmouse ended her sponsorship),
  the AGF 2026 AI teaser, the Stellar Blade AI MV with duplicated extras and garbled signs [search].
- Lesson [own]: disclose AI use plainly (already the plan), never imply hand-made, and reject any take with visible
  AI artefacts (garbled text, duplicates, design drift). Fans punish broken promises and artefacts more than the AI.

### 3.12 What AI-video MV makers do (state of practice, 2026)
- Keyframe first: approve cheap stills, then pay for video; fixing a face in the still is far cheaper than
  re-rolling a clip [search: Atlas Cloud guide, vendor].
- First frame + optional last frame per clip, the same reference pack every time; remove a flawed reference before
  regenerating, or the error comes back [search, vendor].
- Generate one cut at a time with the character and background separated [search: DomoAI guide].
- A storyboard grid image can drive a multi-cut 2D clip in one Seedance 2.0 run [read: npaka's note].
- Seedance 2.0 mini can lip-sync to an audio reference; 15 s per run is about 8 bars at 126 BPM [search].
- Nobody in these sources converts the 24 fps output to anime timing; that is an open opportunity [own].

## 4. What this means for 「余裕だもん」 (proposal, needs the owner's OK)
1. **Stop procedural "life".** Retire the autorig sine warps, the breathing and the image-swap blinks/mouths. Code
   keeps typography, layouts, chat, counter, 撮影 (light, glow, grain), and camera moves on purpose-held stills.
2. **Acting comes from video generation**, judged by the rules above, and post-timed to anime: re-time each clip to
   twos/threes with real holds (ones only for fast camera or effects), snap key poses to beats.
3. **Every still is a 止め絵 by choice**: no wobble, one deliberate camera move or none, and graphics doing the rhythm.
4. **Blink policy from §3.5**, including the slow-blink signature.
5. **One concept sentence for the PV** before more assets. Candidate [own]: "her stream is her stage, and the chat
   sees everything she would rather it did not".
6. **An MV model sheet** for the OC: simplified lines and sweater pattern, designed closed/half eyes, a real chibi
   variant. Simpler designs drift less in video generation [own].

Proposed first check (cheap, no paid calls): take one returned Seedance clip and render three versions of the same
~8 s section: (a) raw 24 fps, (b) re-timed to twos/threes with holds on beats, (c) the current v3 code render. The
owner picks by eye; measure flicker and design drift on each.

## 5. Gaps and next research steps
- Frame-level study (blink and mouth timing, cut lengths per bar) needs video access: the owner can download a few
  MVs and drop them in a local folder, or allow YouTube downloads for this environment.
- Paywalled or unreachable primaries: Video Salon's ひっひっふー article, KAI-YOU Premium interview with ぽぷりか,
  ぽぷりか's FANBOX making-of, 瀬兎一也's Live2D JUKU EX 2026 talk, the blink chapter of *The Animator's Survival Kit*.
- Credits for REFLECT: Siliconera names art by Mochizuki Mochi and movie by Nebiru [search]; not cross-checked.

## Sources
Opened this session [read]:
- CGWORLD, 擬態するメタ special: https://cgworld.jp/special-feature/2604-mimicrymeta.html
- CGWORLD, Mori Calliope 「Die For You」 part 1: https://cgworld.jp/article/202608-calliope-1.html
- Real Sound, Mori Calliope × 亀山陽平 talk: https://realsound.jp/2026/02/post-2299015_1.html
- KAI-YOU, ビビデバ Clio award: https://kai-you.net/article/91810
- KAI-YOU, ひっひっふー: https://kai-you.net/article/92911
- CHE BUNBUN, ひっひっふー critique: https://note.com/chebunbun/n/n5b845e2e1322
- MoguLive, ビビデバ MV review: https://www.moguravr.com/bibideba-mv-review/
- MoguLive, VTuber Award 2024 music: https://www.moguravr.com/mogulive-vtuber-award-2024-music/
- MoguLive, 幽霊船戦: https://www.moguravr.com/?p=254982
- 八ツ橋まろん, six elements of a VTuber 3D MV: https://note.com/maron_vtuber/n/n9924b36eb2a5
- npaka, GPT Images 2.0 + Seedance 2.0 storyboard test: https://note.com/npaka/n/nc374d622b000

Seen through search only [search]:
- SLAM DUNK on threes: https://press.moviewalker.jp/news/article/1133272/p2/
- ビビデバ frame-rate analysis (fan): https://scrapbox.io/uesYn/%E3%83%93%E3%83%93%E3%83%87%E3%83%90_%2F_%E6%98%9F%E8%A1%97%E3%81%99%E3%81%84%E3%81%9B%E3%81%84(official)
- Video Salon, ひっひっふー: https://videosalon.jp/premium/vsw307_t1/
- ぽぷりか on X (Eevee, fisheye): https://x.com/POPREQ/status/1944350444228391120
- Aoike Ryosuke on blinks (Mynavi): https://news.mynavi.jp/techplus/article/kurieita-21/ and mouth flaps: https://news.mynavi.jp/techplus/article/kurieita-22/
- Half-closed eyes in cel vs 3DCG (blog): https://scrapbox.io/frog96/%E5%8D%8A%E7%9B%AEbot%E3%81%A8%E5%86%99%E7%9C%9F%E3%81%AE%E5%86%8D%E7%99%BA%E6%98%8E
- Blink types and pupil visibility: https://www.creativebloq.com/how-to/how-to-design-an-animated-hero
- Endless Mode on 60 fps upscales: https://www.endlessmode.com/article/ai-brained-sickos-who-upscale-anime-to-60-fps-need-to-be-stopped
- Guilty Gear Xrd keyframing: https://steamcommunity.com/app/376300/discussions/0/487877107130580768
- CGWORLD, BanG Dream! Live2D motion: https://cgworld.jp/feature/201709-cgw230HS-bang-2.html
- Live2D eye-blink tutorial: https://docs.live2d.com/en/cubism-editor-tutorials/eye-blink/
- Live2D JUKU MV: https://prtimes.jp/main/html/rd/p/000000151.000024818.html
- 瀬兎一也 talk: https://cgworld.jp/special/live2d-juku-ex-2026/seto.html
- MV commission prices: https://booth.pm/ja/items/3025451 , https://coconala.com/services/3357728
- ロリ神 credits and 100M: https://news.allabout.co.jp/articles/o/81328/ , https://www.appbank.net/2023/09/27/vtuber/2576021.php
- ぺこら チキンフィーバー: https://kai-you.net/article/94224
- まいたけダンス: https://dic.nicovideo.jp/a/%E3%81%BE%E3%81%84%E3%81%9F%E3%81%91%E3%83%80%E3%83%B3%E3%82%B9 , https://kai-you.net/article/90875
- hololive MV credits: https://animecorner.me/hololive-summer-seishun-archive-gets-animated-music-video-by-studio-kai/ , https://www.anitrendz.com/news/2024/10/04/sakura-mikos-cherry-message-anime-music-video-imagines-hololive-gen-0-as-schoolmates , https://www.anitrendz.com/news/2023/10/25/hoshimachi-suisei-dances-in-the-night-in-midnight-grand-orchestras-midnight-mission-anime-music-video , https://www-d.animenewsnetwork.com/interest/2022-01-07/hololive-tsunomaki-watame-gets-movie-quality-anime-music-video/.181302
- Calliope × Wit Studio / Kameyama: https://www.siliconera.com/?p=1051421 , https://kai-you.net/article/93776
- REFLECT credits: https://www.siliconera.com/gawr-gura-reflect-music-video-released-includes-lyrics/
- 止め絵: https://dic.nicovideo.jp/t/a/%E6%AD%A2%E3%82%81%E7%B5%B5
- 撮影: https://natalie.mu/comic/news/624561 , https://realsound.jp/movie/2020/12/post-677025_4.html
- Lyric-video taxonomy (えむ): https://scrapbox.io/uesYn/%E3%83%AA%E3%83%AA%E3%83%83%E3%82%AF%E3%83%93%E3%83%87%E3%82%AA%E3%82%92%E8%A7%A3%E5%89%96%E3%81%99%E3%82%8B%EF%BC%88%E5%89%8D%EF%BC%89Text_by_%E3%81%88%E3%82%80
- VTuber design maximalism: https://ogiuemaniax.com/2023/09/06/hololives-regloss-features-refreshingly-simple-character-designs/
- hololive EN teaser: https://www.siliconera.com/new-hololive-english-vtuber-generation-teased/
- AI backlash: https://nteguide.com/en/blog/nte-ai-art-controversy-timeline/ , https://www.invenglobal.com/articles/26883/after-promising-a-human-centered-festival-agf-sparks-fan-backlash-with-ai-generated-teaser-video , https://www.dexerto.com/gaming/stellar-blade-fans-dumbfounded-by-ai-slop-music-video-for-blood-rain-3393628/
- AI MV workflow: https://www.atlascloud.ai/blog/guides/seedream-seedance-mv-workflow , https://www.domoai.app/ja/blog/panel-comic-animation-seedance-guide , https://tokiha-music.com/seedance-lipsync/
