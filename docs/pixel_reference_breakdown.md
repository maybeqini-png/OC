# Pixel / game-UI reference breakdown (for the XIYIN pixel PV)

Fetched 2026-10-29. Evidence levels: **observed** = seen on frames extracted by the assistant; **stated** = the
uploader's own description or platform metadata (numbers are a snapshot); **reported** = third-party article.
Videos were analysed in the session scratchpad only; no frames or files from these works are stored in the repo.

## A. 一句话让opus烧40亿token做的爱丽丝mv — Bilibili BV11unF6fEmq
Stated: uploader 三千年夜, 2026-10-20, 3:33, 94.7K views / 27.4K likes / 11.8K favourites / 608 comments.
Song 「勇者アリスの大冒険！」 (Blue Archive, character 天童アリス); non-commercial fan work. Made with Claude Code +
Opus 5.5 and Remotion: 12,776 frames at 1080p60, about 80 sub-agents (art-direction proposals and reviews,
storyboard, component library, 15 sections, adversarial review), about 60% of a Max 20x weekly quota. Per-character
lyric timing: Demucs vocal separation + wav2vec2 forced alignment + manual correction. Pixel sprites (Alice and
friends, the demon king) were AI-generated images converted back to a pixel grid; official art only as
picture-in-picture windows, save cards, stickers and the end cover.
Observed (frames every 2 s, full-res crops; the 1080p30 stream, since 1080p60 needs a premium account):
- **One premise frames everything: a game session.** 「スイッチオン」 power-on → 「スタートです」 → a platformer
  world → command battles → idol stage → boss → finale → credits shown as a game room → 「スイッチオフで」 →
  「また明日」 → save-file card. Only 7 hard cuts in 213 s: the camera travels through one continuous world and
  scenes change by blocks assembling and scattering.
- **The lyrics are the level.** Key kanji (大冒険, 勇者, 伝説, 森, 敵, 世界, 山, 道, 仲間, 絆, 強大, 邪悪, 光) are
  built from beveled blocks with furigana as small key-cap tiles; kana hop in as tiles. Words become terrain: 山 is
  a hill she climbs, 道 a road, 橋 a bridge. A small Chinese subtitle line runs at the bottom.
- **Game grammar everywhere**: PRESS START, RPG コマンド window, LV counter, EXP bar, coins / 1UP, save-data
  screen, map, rock-paper-scissors, boss with HP.
- **Colour script by section**: sky-blue/green adventure → navy/purple command battles → pink idol → dark
  red/purple boss → pastel sunset → bright finale.
- **Not strict pixel art**: the world and letters are clean HD tiles (beveled, soft-shaded, anti-aliased). Only the
  characters are true pixel sprites, about 30-40 sprite pixels tall shown at about 5x; faint conversion noise is
  visible on the faces.

## B. [UT]人类……很高兴认识你，再见。Opus5.5 — Bilibili BV1PUHf6cEG6
Stated: uploader 可爱归归, 2026-10-06, 3:56, 265K views / 22.8K likes / 12.2K favourites / 728 comments. Undertale
Asgore fight (a series; an earlier episode did Mettaton). Opus 5.5 high to max, 1.55B tokens, most of them spent on
discarded brainstorming. The description quotes Claude's long reading of Asgore's character.
Observed (frames every 2 s, 79 detected cuts):
- A **faithful battle UI** (Chinese-localised 战斗/行动/物品/仁慈, LV/HP, the 「*」 narration box), Asgore as white
  line art, the six soul jars as coloured lanterns, ember particles.
- Intro: a long unbroken move through a 3D white corridor (0:00-0:41) before the battle box appears.
- **Mechanics as story beats**: Asgore destroys the MERCY button (~0:42); using an item triggers sepia memory
  flashbacks; low HP changes the mood; the ending is a quiet speech-bubble conversation.
- **Per-soul worlds**: each human soul gets its own 3D voxel scene and colour (kitchen, library where the bullets
  are words 困住/绝望/残忍/对不起, snow forest, western sunset, clock tower); the battle box tilts in perspective.
- Action sections cut fast (median detected shot about 0.7 s); story sections hold long.

## C. 【像素崩铁】音游风银狼PV — Bilibili BV1xW4y197K9
Stated: uploader 苏帕帕瓦, 2023-06-10, 1:34, 1.02M views / 91.3K likes / 33.6K favourites. A traditional rhythm
game crossed with Muse Dash, edited in Premiere (crashed several times); art help from King_LIU樱律 and
可可爱爱当老板; BGM 「即兴演出 fReeStyLE」. Bilibili refused the video stream to us (HTTP 567), so this is from the
platform's 19 preview frames (one per 5 s): treat details as approximate.
Observed:
- **One fixed side-view layout for the whole video**: the chibi pixel sprite on the left, a two-lane track,
  enemies (HSR mechs; around 0:35-0:50 a second girl with a box and a laser beam, probably Herta given the title)
  entering from the right, a combo counter at the
  top centre (16 → 309), coloured key-lane flashes at the bottom, neon cyan/purple on navy.
- Ends on a **STAGE CLEAR result screen** (score 19951118, Combo 999, Excellent 999, Miss 0) with a high-res
  portrait.
- The style is in character: Silver Wolf is a gamer, and her official PV already used rhythm-game UI.

## D. Similar works (Japan / US)
| Work | Platform, stated numbers | What it shows |
|---|---|---|
| sasakure.UK 「＊ハロー、プラネット。」 dot PV (2009) | YouTube oVb6Gkf-IJM, 4.48M views | Game HUD (1UP, score, hearts, item box), chibi Miku sprite, lyrics as in-game text |
| m7kenji × TORIENA 「PULSE FIGHTER」 | YouTube SiTazCUPBGM, 344K views | 8-bit side-scroller MV with PRESS START; reported: one artist, about six months, Photoshop + Flash animated against the WAV (KAI-YOU, ICON) |
| ゆず 「ALWAYS」 (2022) | YouTube bc59wdtveCg, 886K views | Fully pixel-art MV by mae (Shibuya Pixel Art Contest 2020 winner), painterly landscapes rather than game UI (Billboard) |
| Muse Dash (PeroPeroGames) | game | The side-scrolling cute-character rhythm layout that C borrows |
| Opus 5.5 code-rendered MVs on Bilibili | e.g. 千本樱 / バケモノの唄 MV BV1ovpE66EPW, about 516K views | The current trend of code-drawn MVs (see A, B) |

## E. What carries over to XIYIN
1. **One game premise frames every shot** (A: a game session with power-on / save-file bookends; C: one rhythm
   stage with a result screen). For XIYIN: her stream is a rhythm-game run; LIVE on/off are the bookends; the end
   card is a result screen (the ノーカン counter becomes the MISS count that she paws back to 0).
2. **A fixed gameplay layout as the backbone** (C): verses and choruses run on one Muse Dash-like stage where notes
   come from the beat grid and `pv3/lyrics_timed.json`. Cheap, readable, and fully deterministic in code.
3. **「*」 narration for the gags** (B): the Undertale-style box gives deadpan comedy for the stumble
   (e.g. 「* XIYIN 假装什么都没发生。」 / 「* 这次不算。」).
4. **Block words only for the hooks** (A): 余裕, 大天才, ノーカン, めっ built from tiles; everything else in the one
   lyric line.
5. **Mixed resolution is fine** (A): HD UI and clean tiles around true pixel sprites, as long as each layer keeps
   its own grid and the sprites keep one pixel scale.
6. **Stay lean**: A used about 80 sub-agents; this project works inline (README), so reuse a few layout families and
   components instead of 15 bespoke sections.
7. **Borrowed attention**: A, B and C all ride an existing IP or song; XIYIN is original, so the premise has to come
   from her own story (smug → MISS → 「ノーカン!」 → めっ), which the rhythm-game framing supplies.
