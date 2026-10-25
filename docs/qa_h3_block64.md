# Frame-by-frame QA: MiniMax H3 clips for block 64.4-84.6 s

Date 2026-10-23. Every clip was inspected on 6 fps contact sheets (every 4th frame) and every drawing that
appears on screen (on 2s) was inspected on tight crops of face, hands and tail. Automatic checks ran on every
frame: silhouette parts / pops / outline jumps (`pv4/qa_frames.py`, isnet-anime matte), jaw-line wobble and
left/right asymmetry (`pv4/qa_face.py`), hair / eye colour drift and boil (`pv4/qa_clip.py`), cadence
(scratchpad `cadence2.py`). Evidence: **observed** = seen on the crops; **measured** = numbers.

## Verdicts

| Clip | Model / res | Verdict | Why (observed unless marked) |
|---|---|---|---|
| `h3_d01_close_tease` | H3 768P | **USE frames 4-110** | Face, clip, ears stable; jaw line stable (measured wobble ≤ 3.3 %, the 3 flags = mouth opening into a grin, checked on crops). No hands/tail in frame. |
| `h3_p02b_me_poke` | H3 768P | **USE frames 96-112 only** | Gentle poke, finger + sleeve correct in the used range; face stable (wobble ≤ 1.6 %). |
| `h3_p02_me_boop` | H3 768P | REJECT | Fist hits the lens with radial speed lines and a full background change (measured jump 85/255) - reads as an effect, not her acting. |
| `h3_p04_yosomi` | H3 768P | **USE frames 26-88 only** | Frames 10-22: the outstretched arm/hand is malformed (smeared fingers, sleeve morph) - excluded. Frames 88-94: finger elongates when lowering - excluded. Used range: hand at eye, face stable (wobble ≤ 0.8 %). |
| `h3_p04b_yosomi_anchor` | H3 768P | REJECT | A thin black tail appears from the frame edge at f8 that is not attached to her (the waist-up first frame has no tail). |
| `h3_p05_tsuyogari` | H3 768P | REJECT | Tail jumps from her left side to her right side (f42-f52) and detaches. |
| `h3_p05b_tsuyogari_anchor` | H3 768P | REJECT | Tail switches sides again (f56-f80). |
| `h3_p05c_tsuyogari_nt` | H3 768P | backup | Tail-free first frame: no tail invented, hands correct; face soft at this size. |
| `h3max_p05d_tsuyogari_nt_1080` | H3 Max 1080P | see below | |
| `h3_p07_konokoe` | H3 768P | REJECT | Strong boil on the moon/sea (measured boil median 5.9 vs ≤ 1.5 elsewhere); hand sits on the reflection. |
| `h3_p07b_konokoe_full` | H3 768P | REJECT | f4-f8: the tail detaches and floats beside her knee; f8-f12: malformed hand while lifting the arm. |
| `h3_p07c_konokoe_anchor` | H3 768P | REJECT | Tail disappears and reappears (f96-f136); eyes closed for most of the sung part. |
| `h3_p07d_konokoe_nt` | H3 768P | backup | No tail invented, hand on chest correct; face only ~88 px tall -> soft, mushy eyes on some frames (an AI tell at full-HD). |
| `h3max_p07e_konokoe_nt_1080` | H3 Max 1080P | **USE all** | Native 1080P: face, eyes, clip and patch crisp in every 4th-frame check (f0-f188); hand on chest correct; no tail invented; ripples and particles stay on the water. |
| `h3_s01`, `h3_s02`, `h3_a01`, `h3_p29` | H3 768P | tests | Sheet-background tests / not in this block. |

## Findings that changed the method
1. **The tail is the weakest part of generated video**: in 4 of 6 full-body clips it detached, switched sides or
   vanished. Fix: full-body first frames are rendered without the tail and the sheet's own tail is composited
   back (`pv4/tail.py`): hip-tracked, swaying on 2s, behind her legs, mirrored in the water. Confirmed: in both
   tail-free clips the model did not invent a tail.
2. **Arms in big swings** produce malformed hands (p04 f10-22, p07b f8-12). Fix: prompts keep hands close to the
   body and the edit uses only QA-passed frame ranges.
3. **Small faces at 768P smear** (eyes and mouth lose their lines when the face is < 100 px). Fix: H3 Max at native
   1080P for full-body shots; 768P only for close-ups (face > 300 px).
4. **Start + end on the same on-model frame** keeps the design stable over 8 s but encourages "closed eyes"
   holding patterns; prompt the action and its return explicitly.

## Jaw / face measurement (pv4/qa_face.py)
The face mask is split from the neck shadow by a two-cluster threshold on skin lightness, the jaw line is the
lower edge of the largest face blob, and its change is measured against the previous drawing after removing
shift and tilt. Results on the drawings used in the block: d01 max 3.3 % (mouth opening), p02b 1.6 %, p04 0.8 %,
p05c 1.8 %, p07d 1.4 % of face height; no left/right asymmetry above 3.5 %. All flagged drawings were opened on
crops and are expression changes, not distortions.

## Final-output review (rendered block, every 6th frame + full-res crops)
- Hook word 笑ったでしょ: first version re-flowed per character and was half hidden by her head; now set once with
  real kerning, wiped in per syllable, in the left third, only the last kana tucked behind her ear (intended depth).
- よそ見 -> 強がり: the 6-frame dissolve showed two moons at once (different framings) -> replaced by a straight cut.
- Composited tail checked at 72.8-75.8 s and 77-83 s on full-res crops: attached behind the left leg in every frame,
  sways on 2s, correct upside down in the inverted world; no doubled tail (the tail-free clips contain none).
- Lip-sync: mouth openness measured per source frame (checked on crops: closed = 0, open = 1) and matched to the
  separated vocal; in この声で 80 different drawings are used over 8.3 s, the mouth closes in the gaps of the line.
- Not fixed in this block: the 768P close-ups (笑ったでしょ, めっ) are slightly softer than the 1080P shots.

## v4.1 (code-rendered from the sheet, no generated pixels) - frame review
- Contact sheets every 4th frame of the whole block and full-res crops of faces (S1 tilts/squint, punch-ins, waist
  wink, inverted reflection face, held-note eyes) and full figures (S4, S6, S8): on-model in every checked frame (the
  drawing is the sheet); no jaw seam (the puppet is one deformation field, no layers); hands are the sheet's hands;
  the tail is the sheet's tail, attached and swaying.
- Fixed in review: water rings were drawn over her boots (now behind them, on the water surface above the reflection);
  a gap between the soles and their mirror image (now placed on the lowest opaque row, soles meet the reflection);
  lyric columns over the moon in white (moved to dark sky).
- Cuts vs morae: all 11 cuts are on mora onsets (by construction); offset to the nearest beat -4.9..+4.4 frames
  (the voice is not always on the beat; the picture follows the voice).

## Mouth proportion fix (2026-10-25, owner: "the only issue is the mouth being out of proper proportion")
The owner prefers the fal (H3) version of the block; the generated mouths were too big. No new generation (0 fal spend).
- Measured with one detector (`pv4/mouthfix.segment`: the largest non-skin hole enclosed by skin in the lower face; checked
  on crops of every used drawing). Widths as a share of the face box:
  - XIYIN's sheet smile: 0.103.
  - H3 open mouths: median 0.12-0.14, up to 0.18 wide and 0.12 high, so wider than her own smile.
  - Hand-drawn small-girl references while talking: 0.05-0.09 (UTOPIA, NGNL ED, Dragon Maid, Takagi); see
    `docs/research_xiyin_refs.md` §2.
- Fix (`pv4/mouthfix.py`, applied to each source frame before compositing in `pv4/block_64.py`):
  - sizes up to 0.07 x 0.05 stay as drawn; the excess above is compressed to 35 %, so the mouth still opens and closes
    with the voice;
  - the mouth is scaled about its top-centre, so it stays under the nose;
  - the original mouth and its pink lip shading are removed and filled with a plane fit of the surrounding skin;
  - the ink line is thickened before the shrink so it keeps the face's line weight;
  - the scale is median-smoothed over 5 source frames.
- Result on the used drawings:
  - d01: 14 of 20 changed (k 0.69-0.74);
  - p02b: 5 of 8;
  - p04: 11 of 23 (k 0.64-0.68);
  - p07e: 57 of 80 (k 0.62-0.70);
  - p05d: 0 (closed mouths only).
- QA:
  - before/after crops of every used drawing (scratchpad `qa/mfix/ba_*.jpg`) and of the rendered block every 6th frame,
    including the inverted この声で shot (`qa/mfix/final_*.jpg`);
  - full-resolution zooms of the strongest cases.
- Found and fixed during QA:
  - inpainting from the border smeared the lip shading back as a pink blot (p04 f37), so the fill is now a plane fit;
  - the shrunk line art was thinner and paler than the face's other lines, so it is now thickened first;
  - the thin centre of a teeth grin vanished (p04 f29), so thin strokes are detected by black-hat as well.
- Not changed: half-closed mouths below the threshold (e.g. p07e f159-161) and closed mouths; the 768P close-ups are still
  softer than the 1080P shots.
- Face boxes: `python mouthfix.py <lbpcascade_animeface.xml> <clip>...` (needs OpenCV 4) rebuilds
  `pv4/.cache/faceboxes_<clip>.npy`.
