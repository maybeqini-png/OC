# Block 64.4-84.6 s, v4.2: the fal clips repaired and refined (QA record, 2026-10-24)

Owner review of v4.1 (sheet puppet): the movements are stiff, the blinking eyes break the illusion, the result is far
behind video generation + editing. Request: repair and refine using the videos tested on fal; examine the
naturalness of the mouth during singing. Renderer: `pv4/block_64c.py`. Mouth: `pv4/mouth_layer.py`, QA tool
`pv4/qa_mouth.py`. Evidence labels: **measured** (numbers from the tools), **observed** (seen on crops / contact
sheets). No paid calls were made (fal: 0 new jobs; NovelAI: 0 Anlas).

## What changed

| Problem (owner / earlier QA) | v4.0 (H3 composite) | v4.1 (puppet) | v4.2 |
|---|---|---|---|
| Stiff motion | real H3 motion, but re-timed for lip-sync (body sped up / stalled) | sine-wave deformation of one drawing | H3 motion at its own speed, drawings on 2s, real holds; no re-ordering |
| Blinks | H3 blinks | code-drawn blink swaps | H3's own blinks only; no code blinks |
| Mouth during singing | frame selection by openness; stuck on H3's frozen "O" | 3 code-drawn shapes from loudness | mouth layer timed to the morae (below) |
| AI-look backgrounds | generated plates re-rendered by H3 | designed shapes | designed shapes laid out like each clip's own scene |
| Timing off the lyrics | phrase onsets only | mora-exact | mora-exact (v4.1 timing, type and story) |

## Mouth: what was wrong (measured, every frame, crop strips)
Mouth tracked from a hand-marked frame-0 point (`pv4/h3/mouth_marks.json`), openness = tallest column of mouth-interior
pixels / face width, normalised per clip on frames where nothing covers the mouth.
- `h3max_p07e` (この声で キメちゃうよ): one round "O" held for 66 frames (f94-160, 2.75 s) while the line moves through
  ちゃ う よ; shut for the last 30 frames while she still holds よ.
- `h3_p04` (よそ見しないで 見ててよね): mouth closed in 98 of 124 frames; open only f28-56.
- `h3max_p05d` (強がりだって): never opens.
- `h3_p02b`: the sleeve covers the mouth in f36-98 (occlusion test: non-skin > 12 % or navy > 8 % of the mouth window).
- **Dissolve frames**: the model fades between mouth shapes - a pale pink fill without an outline (observed at full
  resolution on `h3max_p07e` f106 and f160; flagged where non-skin area > 5 % and the darkest mouth pixel is lighter
  than L 0.47: p07e f39-41, f48-50, f90-92, f105-107, f159-161). No animator draws this; it reads as AI.

## Mouth: how it works now (`pv4/mouth_layer.py`)
1. **Chart**, per drawing on 2s, one frame ahead of the sound (an animator's mouth chart): the mora's vowel - あ open,
   お round, え い う half; each consonant-initial mora opens one step smaller on its first drawing if it lasts at
   least two drawings; lips shut just before and on ま/ば/ぱ-row morae, on っ, on ん before m/b/p or at a phrase end
   (otherwise ん is a half-open nasal); shut in rests (separated vocal below threshold, e.g. the breath 71.8-72.15)
   and after the phrase; one half-open drawing between shut and open. Loudness flicker of a single drawing is removed.
2. **Swap**: when the drawing's own mouth differs from the chart, the mouth is taken from another frame of the same
   clip with the wanted shape, nearest in time (<= 2.5 s), aligned by a shift/rotation search on the skin ring,
   colour-matched on that ring, pasted through a mask that covers both mouths (only pixels darker/redder than skin,
   or teeth). Refused when the face around the mouth does not line up (ring error > 140 after brightness match; 2x for
   a sister clip), when the mouth is occluded, or when no clean donor exists - then her own mouth stays.
3. `h3max_p05d` has no open mouths: donors come from `h3max_p07e` (same light, same model run), rescaled 58/67.

## Mouth: result per shot (measured with `pv4/qa_mouth.py` on the render's exact source ranges)
| Shot | Lyric | Clip, frames | Drawings | Shape = chart | Swapped | Notes |
|---|---|---|---|---|---|---|
| S1 | 笑ったでしょ | d01 from f4 | 28 | 28 | 20 | |
| S2 | めっ | p02b f104-107 | 4 | 4 | 0 | lips shut throughout (め is 70 ms, then っ); f102-103 / f110-112 have the finger over the mouth |
| S3 | もういっかい | p02b from f6 | 18 | 14 | 7 | っ shows half twice (laughing head pose, no donor lines up); last 2 drawings: sleeve over the mouth, under the white-out |
| S5 | (み)しないで 見ててよね | p04 f26 (6-frame hold) | 35 | 35 | 26 | し closes, な opens, breath before て shut, よ open, ね onset |
| S6 | 強がりだって | p05d from f56 | 35 | 35 | 28 | from f56: in f0-55 she looks down and no front-facing mouth lines up (ring error 630-750 vs 222) |
| S7 | 本気だもん | d01 from f84 | 10 | 10 | 8 | ほ half, ん half (nasal before き), き devoiced = shut, も lips |
| S8-9 | この声で キメちゃうよ | p07e from f0 | 80 | 80 | 45 | dissolve frames replaced; lips shut on め; held よ open; clean close after the phrase |
| total | | | 210 | 206 (98 %) | 134 | |
Open and round count as equal where the clip has only one of them (p07e has no wide-open あ).

Observed on full-resolution crops of S1, S5, S6, S8 and S9: no seam or colour step around pasted mouths, the mouth
stays in place on the face, the chin line is untouched.

## Other repairs on the clip pixels (`Actor.rgba` in `pv4/block_64c.py`)
- Cut-out with the isnet-anime matte (`pv4/matte.py`, temporally smoothed), tightened; edge colours de-contaminated by
  removing the old background estimated behind each edge pixel (no halo of the generated moon/stage).
- The model's sparkle dots over her removed (small spots much brighter than their 5x5 median).
- Full-body clips: the model's own water reflection under the soles is cut; her reflection is made from her cut-out;
  the sheet's tail is added behind her (`pv4/tail.py`), as in v4.0.
- 768P clips (7:4) scaled uniformly to 1920 wide (Lanczos + light unsharp) and centre-cropped to 16:9 (v4.0 squashed
  them 1.6 % vertically).
- Backgrounds: `pv4/bg_design.py` shapes with each clip's measured layout - p04 moon (1016, 419) r 250, horizon 679;
  p05d moon (987, 477) r 275, horizon 611; p07e moon (971, 427) r 231, horizon 601 (output px); stage spot at 0.58 W.

## Known limits (honest)
- The character pixels are still the model's: soft airbrushed hair shading and slight 768P softness remain (the
  earlier measurement of this, `docs/research_pv_language.md` §7, could not be re-run - its script was in an old
  scratchpad). The owner has now judged generated motion better than the puppet; the trade-off is accepted, not solved.
- S3 っ (2 drawings) and the punch-in colour fields: her stage light does not change with the field colour.
- S9 is a 1.42-1.56x punch-in on a 1080P clip: a little soft.
- Mouth timing is checked on the chart and on crops; it has not yet been reviewed by ear against the video by the owner.
