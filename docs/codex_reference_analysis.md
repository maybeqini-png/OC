# Codex reference video — analysis and tool plan

Source: `full_story_proxy_v15.mp4` (made by the owner with Codex, sent 2026-10-28). 36.2 s, 640×360, 30 fps,
AAC 48 kHz. It is a different song from 「余裕だもん」. Evidence level: **measured** on this proxy unless
marked otherwise. Layout board: 14 layouts with times (rendered for the owner in chat, not committed).

## 1. What it is
A pastel lyric video (歌詞動画). The lyrics are the main visual. One or two illustrations of the OC
(headphones + cat plush; a hand-on-chin bust in the vertical cards) are reused in every layout. Nothing is
character-animated: all motion is layout, typography, masks and transitions.

## 2. Measured properties
| Property | Value | How measured |
|---|---|---|
| Layouts | 14 in 36 s, median ≈2.4 s each | contact sheets at 1 and 4 fps |
| Visual change events | 84 (median gap 0.20 s, mean 0.39 s) | peaks of mean frame difference |
| Fully still stretches ≥0.4 s | 9; the longest is the ending, 33.3–36.1 s | frame difference < 0.5 |
| Palette (share of pixels) | white #F6F8FC 56 %, periwinkle #9FB8E5 10 %, lavender #DADBF0 10 %, #8090C0 8 %, pink #F38DCC 7 %, cobalt #6899E7 5 %, grey-navy #6D7295 3 %, hot pink #EB166E 0.8 % | k-means (8) on all frames |
| Tempo | ambiguous, 103.4 or 152 BPM | librosa beat tracker, autocorrelation |
| Sync of picture changes to the music | **not measurable**: cross-correlation of picture change vs. onset strength peaks at 0.089, below the 95th percentile of a shuffled null (0.094); 38 % of changes fall within 50 ms of an 8th-note grid vs. 35 % for random times | librosa onsets + OpenCV |

Not measured: whether text appears on the sung syllables (would need vocal separation + ASR).

## 3. Why it works (the transferable rules)
1. **Typography is the picture.** Every phrase gets a new text treatment: tiles, vertical text, a word
   column, a ring around a circle mask, caption bars, an English text wall.
2. **A layout library, not shots.** Recurring devices: cards, checkerboards, circle/CD masks, OS windows,
   grids, HUD micro-labels, floating icons. Each layout lives ≈2 s and keeps moving inside.
3. **The screen almost never rests.** Something changes every ≈0.2–0.4 s.
4. **Strict palette.** A white base (56 %), two cool hues, one pink, a tiny hot-pink accent (<1 %).
   Her navy design reads clearly on the light base.
5. **Repetition is fine when designed.** Same drawing, different frame every time.

## 4. Weak points (what a better version fixes)
- Not locked to the beat (section 2), so the motion feels busy rather than musical.
- The character never moves.
- 32.0–36.2 s is effectively a frozen frame.
- 8.4–12.4 s: lyric tiles cover her face.
- Proxy resolution only.

## 5. Gap to our 「余裕だもん」 work
| | Codex reference | Ours (pv3/pv4) |
|---|---|---|
| Main visual | lyrics + layouts | character clips |
| Cutting | ≈2 s layouts, constant inner motion | 5 s clips, one action each |
| Palette | light base | dark navy base (her navy sweater sinks into it) |
| On-screen lyrics | everywhere | none |
| Character motion | none | yes (generated clips, lip flaps) |
| Timing data | not beat-locked | beat grid (136 BPM, 0.4411 s) + per-mora lyric times in `pv3/lyrics_timed.json` |

Decision for the owner: README §3 sets a dark navy room as the base. The reference shows a light base reads
better with her navy design. Switch to light, or keep dark with cobalt rim light?

## 6. Tools
| Job | Tool | Status here |
|---|---|---|
| Motion graphics, kinetic type, layouts, masks, transitions, edit timeline (the After Effects role) | **Remotion 4.0.539** (React → frames via headless Chromium) | installed, test render passed |
| 2.5D camera: layered cutouts in 3D, push-ins, depth of field, glow (AE 3D camera + Lens Blur + Glow role) | **Blender 5.2.3** (`bpy`, headless, CPU) | see section 7 |
| Beat grid, onsets, QA of sync | librosa, `pv3/lyrics_timed.json` | installed |
| Frame QA (contact sheets, motion, palette) | OpenCV, ffmpeg | installed |
| Final encode, audio mux | ffmpeg | installed |
| New drawings | NovelAI V5 (`oc-gen` skill) | available |
| Short motion accents (optional) | fal.ai video models | available (proxy key) |
| Not usable | After Effects (no Linux build, GUI only), Live2D Cubism (GUI only) | — |

Licenses: Remotion is free for individuals including commercial use (Remotion License, Free tier; company
licence needed above 3 employees). Blender is GPL (rendered output is the owner's). Add both to `LICENSES.md`
before any release.

## 7. Tool tests in this container (2026-10-28)
- **Remotion**: 48-frame 1280×720 kinetic-type test rendered with the pre-installed headless Chromium
  (`--browser-executable`). Works.
- **Blender** (`pip install bpy==5.2.3`, ≈400 MB): three image planes (stage, character sticker, foreground
  sticker) at different depths, keyframed camera push-in, animated focus. Parallax and depth of field work.
  - EEVEE does **not** run (no GPU / no `libEGL`). Cycles on CPU works: ≈4 s per frame at 960×540,
    32 samples, 4 cores. Estimate ≈15 s per 1080p frame, so use Blender only for camera shots, not the whole PV.
  - Glow through Blender's compositor is not tested yet (the compositor API changed in 5.x); glow can also
    be done in Remotion with CSS filters.

## 8. Proposed next step (needs the owner's go-ahead)
Rebuild one section of 「余裕だもん」 in the reference's lyric-video grammar, with what the reference lacks:
every layout change on the beat grid and every lyric mora on its sung time. Candidate: 42.6–64.4 s
(stumble → chorus). Acceptance tests:
1. Every layout change lands within ±1 frame (24 fps) of a beat or half-beat; measured, not eyeballed.
2. Every mora appears within ±1 frame of its time in `pv3/lyrics_timed.json`.
3. No fully still stretch longer than one beat (0.44 s) except deliberate freezes (えっ at 42.6 s).
4. Her face is never covered by text (face boxes from `pv3/detect_faces.py`).
5. 1920×1080, 24 fps, audio from `audio/t2_optimized_full.mp3` unchanged.
6. Side-by-side contact sheet against the Codex video for the owner to judge.
