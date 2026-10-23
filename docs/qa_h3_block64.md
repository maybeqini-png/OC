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
