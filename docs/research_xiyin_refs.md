# Cheeky small-girl references for XIYIN (anime PVs + VTuber MVs)

Date: 2026-10-25. Owner's request: survey Japanese anime PVs and VTuber reference characters for video references
that fit XIYIN's archetype (cheeky young girl / loli). Mid-survey the owner added: *skipping references for this
type of character will make the result diverge from XIYIN's design* (said about the 「可愛くてごめん」 girl's teasing
faces). So nothing of this type is dropped for being "too cute" or "too teasing". The only exclusion is sexualised
framing, which XIYIN's design does not have either (README §1).
Complements `docs/research_pv_language.md` (PV language, composition, AI look) and `docs/reference_breakdown.md`.
References are for acting, timing, staging and graphics only. Never copy their designs, characters or assets.
XIYIN's own proportions always come from `art/reference/oc_reference_sheet.webp`.

## Method and evidence levels
- 19 new analysis copies (360p, Bilibili, scratchpad only, never committed or used in the PV), fetched with scratchpad
  `bili_dl.py`. For OP/ED compilations only the first page / first ~90 s was fetched, which is the OP.
- Per video, scratchpad `study_namaiki.py`:
  - shots from HSV-histogram cuts;
  - per shot the largest anime face (lbpcascade_animeface) and its framing (ECU / CU / MCU by face height);
  - the mouth on that face, measured with `pv4/mouthfix.segment` (the same detector as the mouth fix);
  - contact sheets (one mid-frame per shot, one face crop per shot) that I reviewed by eye.
- Labels: **observed** = seen on the contact sheets at the given time; **measured** = numbers from the script;
  **inferred** = my reading. Credits and studios were not checked in this pass.
- Mouth detector check: on 25 open-mouth crops, 3 were wrong (a fingernail, a hand, a neck shadow) and are excluded.
  Values are about ±0.02 of face-box width.
- Cut counts are approximate: graphic sections with continuous motion merge into one "shot", and flashes split shots.
- Not used: `BV14s411X7at` (searched as Kuroneko, but it is the anime BLACK CAT, a wrong video) and the Blue Archive
  anime NCOP `BV1Ax4y1h7Xy` (downloaded, measured 163 cuts in 90 s, not reviewed yet).

| # | Work (upload) | Who / archetype | Measured | Fit to XIYIN |
|---|---|---|---|---|
| X1 | HoneyWorks 「可愛くてごめん」 feat. かぴ MV ([BV1yx4y1F78Z](https://www.bilibili.com/video/BV1yx4y1F78Z), fan upload with subs) | long dark hair, blunt bangs, confident teasing poses | 81 shots, median 1.73 s, ECU+CU 69 % of time | archetype core (owner) |
| X2 | Blue Archive Kazusa character PV ([BV1Rd4y1w7Mn](https://www.bilibili.com/video/BV1Rd4y1w7Mn), 17 s) | dark hair, cat ears, oversized dark top; cool → sweet | 14 shots, median 0.52 s | closest design + "cool her vs real her" |
| X3 | 『干物妹！うまるちゃん』 OP1 ([BV1Ys411w7gp](https://www.bilibili.com/video/BV1Ys411w7gp)) | perfect girl outside / chibi gremlin inside | 47 shots, median 1.33 s | story device |
| X4 | Kobo Kanaeru 「HELP!!」 MV (official, [BV1if421Q7mL](https://www.bilibili.com/video/BV1if421Q7mL)) | bratty kid persona, oversized hoodie | continuous dance shots (median 16 s) | persona + staging |
| X5 | 『ガヴリールドロップアウト』 OP ([BV1Ys411w7M8](https://www.bilibili.com/video/BV1Ys411w7M8)) | smug lazy angel; fall | 42 shots, median 1.42 s, ECU 31 % | fall beat, smug face |
| X6 | 『かぐや様は告らせたい』 S1 OP ([BV1Li4y1Z7T3](https://www.bilibili.com/video/BV1Li4y1Z7T3), CN subs) | long black hair, elegant smug → flustered | 42 shots, median 1.73 s | smug → collapse; type |
| X7 | 『化物語』 OP 「帰り道」 (Mayoi) ([BV15x411H7GK](https://www.bilibili.com/video/BV15x411H7GK)) | cheeky small girl with fang grin | 67 shots, median 0.79 s | type, motif, moon |
| X8 | 『からかい上手の高木さん3』 OP 「まっすぐ」 ([BV1Qm4y1D7Rd](https://www.bilibili.com/video/BV1Qm4y1D7Rd), 60 fps upload) | the teaser who wins by waiting | 26 shots, median 2.75 s | tease timing |
| X9 | Nekomata Okayu 「もぐもぐYUMMY！」 (official, [BV1kp421S7sv](https://www.bilibili.com/video/BV1kp421S7sv)) | cat girl, oversized hoodie | 38 shots, median 3.46 s | cat girl, gag cards |
| X10 | 『まちカドまぞく』 OP 「町かどタンジェント」 ([BV1Xa4y1h7cx](https://www.bilibili.com/video/BV1Xa4y1h7cx)) | self-declared villain who always loses | 48 shots, median 1.21 s | game-UI gag, bad loser |
| X11 | 『小林さんちのメイドラゴン』 S1 OP (inferred: first page of [BV1vv411772t](https://www.bilibili.com/video/BV1vv411772t)) | Kanna (deadpan small girl) and cast | 52 shots, median 1.04 s | graphics: patterns, logo |
| X12 | Priconne Karyl 「Absolute secret」 ([BV1d5411x7Jb](https://www.bilibili.com/video/BV1d5411x7Jb), first 76 s) + Priconne OP ([BV1yq4y1N7Mr](https://www.bilibili.com/video/BV1yq4y1N7Mr)) | dark-haired cat girl, tsundere | 30 / 79 shots | night lighting of dark hair |
| X13 | Murasaki Shion 「メイジ・オブ・ヴァイオレット」 ([BV1oh411i75e](https://www.bilibili.com/video/BV1oh411i75e), fan upload) | bratty little witch persona | one held illustration + glitch cuts | cheap but on-brand |
| X14 | 『SPY×FAMILY』 OP (inferred OP1, first page of [BV1mT421a7in](https://www.bilibili.com/video/BV1mT421a7in)) | Anya (cheeky child) | 83 shots, median 0.83 s | peek staging, light |
| X15 | Yukopi 「強風オールバック」 ([BV1yL411X7dM](https://www.bilibili.com/video/BV1yL411X7dM), fan upload) | deadpan schoolgirl in a gale | 18 shots, median 5.1 s | deadpan + bold type |
| X16 | 『ヒナまつり』 (first 92 s of [BV1ag4y1q7ac](https://www.bilibili.com/video/BV1ag4y1q7ac)) | deadpan psychic girl | 37 shots, median 1.88 s | minor: deadpan, prop |

Already studied before (still part of the set): 『りゅうおうのおしごと！』 OP/ED (Ai, Ten), 『ノーゲーム・ノーライフ』
OP/ED (Shiro), 天使うと 「UTOPIA」, Gawr Gura 「REFLECT」 (research_pv_language.md), しぐれうい 「粛聖!! ロリ神
レクイエム☆」 (reference_breakdown.md).

## 1. Findings per work (observed unless marked)
- **X1 可愛くてごめん.**
  - Her teasing is a fixed *pose vocabulary*, held as ECU/CU on the beat: finger to lips (45.6, 48.7 s), wink with
    tongue (45.6 s), both hands pointing at camera (60.7 s), hands at cheeks / chin (79.4, 158.9 s), peace sign at the
    eye (186.7 s).
  - The same "Chu!" heart-frame shot returns on every hook (42.5, 48.6, 54.6, 60.6, 117.6, 123.6, 129.6 s): a
    recurring signature shot.
  - Pink kinetic katakana sits on the face layer. A UI gag (ranking bar chart, 21.3 s) does the job our chat does.
- **X2 Kazusa PV.** Cool face eating (1.8 s) → sweet closed-eye smile with fang (2.7 s) within one second, then a
  character card (6.2-14 s). The switch is instant and the design is unchanged; only the expression flips.
- **X3 Umaru OP.** One character in two drawing registers:
  - the "perfect" register: realistic proportions, small closed mouth, pastel light, holds of 2-6 s (4.0, 44.7-50.9 s);
  - the "real" register: chibi with a huge mouth and star eyes, cuts of 0.2-0.9 s (51.6-75 s).
  - An army of chibi clones (2.3, 15.1, 79.6 s) and flat patterned wallpapers of her motif (59-78 s).
- **X4 HELP!!.**
  - Flat two-tone fields (teal / crimson); thin Mincho lyric lines placed small beside her.
  - A dark shadow-double behind her acts on its own (7.1, 56.8, 87.9, 143.8, 160.9 s).
  - She is shown upside down (125.1, 133.3, 160.9 s), with afterimage trails on fast moves (73.6, 133.9 s).
- **X5 Gabriel DropOut OP.**
  - Opens with a fall from the sky (2.6-8.9 s).
  - Costume-detail inserts on consecutive beats, 0.4-0.8 s each: hand, zipper, skirt, bow (59.9-62.3 s).
  - Smug half-lidded ECU (70.1 s); upside-down character over the title letters (11.0, 51.5 s); flat graphic arrows
    and stripes instead of painted backgrounds (25-47 s).
- **X6 Kaguya OP.**
  - Thin Mincho title with one red kanji (告), held 7.4 s (15.0 s).
  - A white void with sparse red hearts and a tiny figure (3.5-7.1, 72.1 s).
  - Mirrored kaleidoscope copies of a dancer (62.1-63.0 s); split eye-ECUs of the two rivals (74.7 / 76.5 s).
- **X7 帰り道.**
  - Her name tag is the title card (8.8-9.3 s).
  - An eye ECU blinks every 0.2-0.5 s on the beat (11.0-13.1 s).
  - Frame-filling Mincho credits (13.8-15.7 s); a tiny figure against a huge full moon (54.3, 70.1 s).
  - She hangs upside down from a bar (73.4 s). Her identity motif (the snail) appears in many scenes (40.2, 71.9 s).
- **X8 Takagi S3 OP.** Long holds (median 2.75 s, the slowest here). Closed-mouth smiles and a sideways look carry the
  tease; the beat lands on the held look, not on motion. Ends on a sunset with small figures (64-85 s).
- **X9 もぐもぐYUMMY！**
  - Food plates as title cards on the beat (1.0-6.3 s); tiny chibi sprites hidden in big scenes.
  - "GAME OVER" cards (48.2, 123.5 s).
  - One deliberately serious, realistic shot as a tonal gag (149.5 s).
- **X10 Machikado OP.** An RPG battle-menu screen as a gag (54.6-55.3 s); the title built from road-sign shapes
  (11.5 s); a split screen (13.5 s); two single white flash frames as a cut (50.7 s).
- **X11 Dragon Maid OP.**
  - Giant brush-type kanji fill the frame (0.7-8.1 s).
  - Each character gets her own pattern panel: gingham, dots, stripes (24.8-29.2 s).
  - The logo's "o" is a flower that changes every 0.1-0.5 s on the beat (15.2-19.2 s).
  - Film-leader countdown with one portrait per number (33.5-36.9 s); a wall of repeated text (45.4-47.7 s).
- **X12 Karyl.**
  - A dark-haired cat girl kept readable at night: cool white/blue rim light on the hair against pale sky
    (22.2, 32.5 s).
  - Red is the only accent (roses, 43-60 s); glowing-eye ECU (44.6 s).
- **X13 Mage of Violet.**
  - One key illustration held for long stretches, with vertical lyrics in its negative space (58.3, 117.3, 163.2 s).
  - Mosaic-pixel glitch transitions (43.5-43.9, 102.4-102.9 s).
  - A recoloured "dark" variant of the same illustration (47.9, 106.9 s).
- **X14 SPY×FAMILY OP.** Anya peeking through flowers at the frame bottom (8.8, 46.8 s); light-flare whites as
  transitions (11.8, 47.0 s); painterly, backlit.
- **X15 強風オールバック.** A flat yellow field, 2-3 drawing loops, deadpan face, bold katakana title over her; holds
  of 5 s or more. The exact timing carries it.

## 2. Mouth size by character type (measured)
Open-mouth or smile width as a share of the face box, with the same detector as `pv4/mouthfix.py`:

| Type | Values |
|---|---|
| Small-girl designs, calm / teasing / talking | Uto 0.06-0.08, Kanna 0.08, Tohru 0.06, Shiro 0.09, Takagi 0.05 |
| 可愛くてごめん girl, teasing smiles (closed) | 0.20-0.29: her design draws a long smile line with lip tint |
| Shouts / gag faces | Machikado cast incl. Shamiko 0.17-0.24; Anya 0.29 |
| **XIYIN sheet**, closed smile | **0.103** |
| H3 clips, open, before the fix | 0.12-0.18 (wider than her own smile) |
| H3 clips, after the fix | ≤ ~0.10 |

Reading:
- Mouth width belongs to each character's design, not to the archetype. The 可愛くてごめん girl's wide smiles are
  on-model *for her*.
- The H3 mouths were wrong because they were wider and taller than **XIYIN's own** smile on calm, teasing lines. The
  fix (`pv4/mouthfix.py`) brings them back to her sheet.
- From the references, the rule for XIYIN:
  - teasing / singing lines keep her mouth within her sheet's smile width;
  - wide gag shapes are for gag beats only (えっ 42.6 s, あいたたた, ちょっと待った, わらうな 122.8 s), drawn as
    clear shapes.
  - The tease itself lives in the pose and the eyes (X1, X2, X8), not in a bigger mouth.

## 3. What to take for XIYIN (inferred from the above)
1. **Cool her vs real her by register, design unchanged** (X2, X3, X4, X13). The "real her" moments:
   - flip the expression instantly (X2);
   - change the tempo: holds for cool, fast cuts for the gag (X3);
   - give her a shadow-double or a recoloured double (X4, X13).
   This is the README story device, now backed by four references.
2. **A pose vocabulary for teasing** (X1, X8, X5): finger to lips, wink, pointing at the camera, hands at cheeks,
   half-lidded smug look, lean-in hold. Use one pose per lyric beat, held on 2s, with her own sheet's face.
3. **A signature hook shot that returns** on every 余裕だもん (X1 "Chu!" frame; X11's logo letter swap): the same
   framing each chorus, with one detail changed each time (the ノーカン counter, the patch's eye).
4. **Her identity motif everywhere** (X7 snail, X9 food, X3 hood pattern): the sleeping-cat patch and paw prints as
   wallpaper patterns, sign shapes and hidden sprites.
5. **Costume-detail inserts on beats** (X5): paw cuffs, tie emblem, cat clip, boots in 0.4-0.8 s cuts. This shows
   her design and keeps her on-model, because each insert is a crop of the sheet.
6. **Game-UI gags for the fails** (X9 GAME OVER, X10 RPG menu): matches the planned MISS! / NO COUNT pop-ups.
7. **Upside-down XIYIN** is a staple of the type (X4, X5, X7, X9) and fits the MIRROR SEA's inverted world.
8. **Flat graphic fields** for the comedic sections (X4, X5, X11, X15). They measured as hand-made-looking
   (research_pv_language.md §7: flat share), and they do not need generated plates.
9. **Typography:**
   - thin Mincho with one accent-colour character (X6; coral for her feelings);
   - frame-filling Mincho cards (X7);
   - bold kinetic type behind her (X15);
   - vertical lyrics in negative space (X13).
10. **Night lighting for navy hair** (X12): a cool rim light and a pale sky behind her head, so the dark hair never
    merges with the night.

## 4. Proposed mapping onto 「余裕だもん」 (for the owner to approve; times from README §2)
| Time | Lyric | Reference beat |
|---|---|---|
| 3.7 | ねえねえ | X8 held close look, closed-mouth smirk, slight lean-in |
| 7.6 | ふふん | X5 / X6 half-lidded smug ECU (small mouth) |
| 14.2 | 今日の私は だいてんさい | X7 / X11 frame-filling type; X5 costume inserts on 4 beats |
| ≈27.8, 55.6, 125.8 | 余裕だもん (hooks) | X1 recurring signature shot, one detail changed per chorus |
| 42.6-44.2 | えっ / あいたたた / ちょっと待った | X3 register switch to the gag; X10 / X9 game-UI card; gag mouth allowed |
| 45.8 | いまのは カウントに はいりません | X15 / X16 deadpan hold on a flat field |
| 49.2 | あーもう にやけないでよ | X1 hands-at-cheeks blush pose |
| 64.4 | 笑ったでしょ | X8 lean-in hold (current block, d01) |
| 66.82 | めっ | X1 finger pose / X14 cheeky child (current block, p02b) |
| 69.4 | よそ見しないで | X6 split eye ECU option |
| 96.2 | ぷいって | X10 bad-loser turn-away |
| 116.2 | 震えるつま先で | X4 shadow-double: the honest her |
| 122.8 | わらうな | gag mouth allowed |
| 163-172.5 | また来てよね | X8 sunset hold, small figures; restraint, never needy |

## 5. Not taken
- Sexualised framing of any kind (none of X1-X16 relies on it).
- Their designs, colours as a whole, characters, logos or assets.
- AI-upscaled / frame-interpolated uploads for timing work: X8 and X12 are 60 fps uploads, so they are used for
  staging only, not for cadence.
