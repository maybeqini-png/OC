"""XIYIN's faces harmonised with N5 (owner 2026-11-03: "pay attention to how the mouth and other facial features fit
the face shape ... use N5 together with the code").

Pipeline per game drawing (the project's proven face method, .claude/skills/oc-gen/SKILL.md):
1. guide = drawing in the sheet's colours (mdrecolor) with the one canonical eye pasted in (mdeyes);
2. V5 img2img of the whole guide at low strength, the same seed and the same OC prompt for every drawing, so N5
   redraws eyes, brows, mouth and cheeks together on that head's angle (features sit on the face shape) while the
   canonical eye design and the composition carry through;
3. only the face (feathered ellipse FACES) of the redraw is transplanted back onto the guide, so hair, outfit, hands
   and the weapon grip stay exactly as they were; the transplanted face is snapped to the guide's skin colour.
Redraws are cached in art/generated/md_style/face/ (prompts and seeds in that folder's prompts.sh / manifest.jsonl).

usage: python3 mdface.py guides            # write the guide images for prompts.sh
       python3 mdface.py check out.png [names...]
"""
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import mdeyes as EY
import mdrecolor as RC

DIR = Path(__file__).parent.parent / "art/generated/md_style/face"
STRENGTH = "0.35"   # 0.50 redesigns the eye (gold iris, new lashes); 0.35 keeps it and fits it to the face
SEED = 61001
# per-drawing seed picks (61001 gave a pale pupil-less eye / muddy rims on these; see face/prompts.sh)
SEEDS = {"v3_upper_49702": 61003, "v3_airslam_49701": 61003, "v3_airslam_49702": 61003}

# face ellipse (drawing px): forehead below the bangs, both eyes, cheeks, mouth, chin
FACES = {
    "z_run_49102": (535, 255, 668, 418),
    "z_punch_49113": (438, 258, 562, 412),
    "z_air_49123": (438, 298, 578, 424),
    "v3_windup_49701": (392, 368, 522, 482),
    "v3_smash_49702": (546, 636, 662, 778),
    "v3_upper_49701": (388, 362, 497, 468),
    "v3_upper_49702": (403, 432, 547, 562),
    "v3_airslam_49701": (366, 440, 508, 582),
    "v3_airslam_49702": (388, 478, 542, 612),
}


def guide(name):
    src = RC.recolor_pose(name) if name in RC.POSE_SEEDS else RC.recolor(name)
    return EY.fix(name, src)


def redraw_path(name, strength=STRENGTH, seed=SEED):
    return DIR / f"{name}_{strength}_{seed}.png"


@lru_cache(None)
def fix(name, strength=STRENGTH, seed=None):
    """RGB drawing: guide with the N5-harmonised face transplanted (guide alone if no redraw exists yet)."""
    g = guide(name)
    seed = seed or SEEDS.get(name, SEED)
    p = redraw_path(name, strength, seed)
    if name not in FACES or not p.exists():
        return g
    r = Image.open(p).convert("RGB").resize(g.size, Image.Resampling.LANCZOS)
    m = Image.new("L", g.size, 0)
    ImageDraw.Draw(m).ellipse(FACES[name], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(7))
    # keep the guide's skin tone: shift the redraw's skin pixels by the median skin difference inside the face
    ga, ra = np.asarray(g).astype(np.float32), np.asarray(r).astype(np.float32)
    inside = np.asarray(m) > 128
    skin = inside & (ga[..., 0] > 230) & (ga[..., 0] > ga[..., 2] + 6) & (ra[..., 0] > 220)
    if skin.sum() > 50:
        ra[skin] += np.median(ga[skin] - ra[skin], 0)
    # irises: every blue pixel that is not hair in the guide takes the canonical iris ramp by its lightness, so N5's
    # redraw can move the eye to fit the face but never changes its colours between frames
    hair_g = EY._hair(ga.astype(np.uint8)) & (ga.mean(-1) < 175)
    blue = inside & ~hair_g & (ra[..., 2] > ra[..., 0] + 40) & (ra.mean(-1) < 200)
    if blue.any():
        lum = ra[blue].mean(-1)
        ramp = np.array([EY.IRIS_LINE, EY.IRIS_TOP, EY.IRIS_MID, EY.IRIS_LOW], np.float32)
        stops = np.array([30, 60, 105, 175], np.float32)
        t = np.clip(np.interp(lum, stops, np.arange(4)), 0, 3)
        i0 = np.floor(t).astype(int).clip(0, 2)
        f = (t - i0)[:, None]
        ra[blue] = ramp[i0] * (1 - f) + ramp[i0 + 1] * f
    r = Image.fromarray(ra.clip(0, 255).astype(np.uint8), "RGB")
    return Image.composite(r, g, m)


if __name__ == "__main__" and sys.argv[1] == "guides":
    DIR.mkdir(parents=True, exist_ok=True)
    for n in FACES:
        guide(n).save(DIR / f"guide_{n}.png")
elif __name__ == "__main__" and sys.argv[1] == "check":
    names = sys.argv[3:] or list(FACES)
    strengths = [STRENGTH]
    tiles = []
    for n in names:
        x0, y0, x1, y1 = FACES[n]
        cx, cy, r = (x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0) * 0.85
        box = (int(cx - r), int(cy - r), int(cx + r), int(cy + r))
        row = [guide(n).crop(box).resize((360, 360))]
        for s in strengths:
            row.append(fix(n, s).crop(box).resize((360, 360)))
        tiles.append(row)
    S = Image.new("RGB", (360 * max(len(r) for r in tiles), 360 * len(tiles)), "white")
    for j, row in enumerate(tiles):
        for i, t in enumerate(row):
            S.paste(t, (360 * i, 360 * j))
    S.save(sys.argv[2])
