"""Remove white artifacts from the side-view avatar sprites (sprites4/ -> sprites4c/).

The N5 pixel drawings use one palette white (248,250,255) for everything light. In the game some of it read as white
specks or wrong colours (owner, 2026-11-02: "no unwanted white artifacts"):
- background seen through a gap between hair strands (opaque white)        -> transparent
- pure-white hair shines (2-20 px specks on the hair)                      -> the palette's light hair blue
- the white sailor-collar line, chest mark and sock band (her design: light-blue stripes)  -> light blue
- a white face / thighs on the punch and air-swipe poses (the run master is peach) -> her skin tones
Kept: ear fur, eye whites, boot laces. Every change is listed per sprite below (seed points in sprite pixels), so
nothing else is touched.

usage: python3 spriteclean.py            (writes sprites4c/*.png and a before/after sheet to argv[1] if given)
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).parent
SRC, DST = HERE / "sprites4", HERE / "sprites4c"
HAIR_LIGHT = (118, 146, 214)
STRIPE = (130, 175, 245)          # light-blue stripe (already in the palette)
SKIN = (255, 236, 226)
SKIN_SHADE = (240, 196, 186)

# Components are named by the top-left corner of their bounding box (sprite pixels), as listed by
# `python3 spriteclean.py --list`. keep: (x0, y0, x1, y1) boxes never changed (eye whites).
PLAN = {
    "a01_run_9803": dict(
        clear=[(29, 56)],
        shine=[(103, 37), (72, 38), (93, 38), (80, 39)],
        stripe=[(59, 79), (83, 80), (91, 83), (57, 86), (55, 87), (90, 87), (51, 88), (48, 89), (87, 109), (90, 109)],
        skin=[], keep=[]),
    "a02_punch_9811": dict(
        clear=[],
        shine=[(26, 65), (20, 95)],
        stripe=[(55, 78), (56, 79), (47, 80), (64, 80), (73, 103), (76, 104), (74, 105), (51, 163), (56, 165)],
        skin=[(62, 45), (51, 146)], keep=[(63, 54, 77, 64)]),
    "a03_airswipe_9821": dict(
        clear=[(9, 61), (13, 80), (31, 96)],
        shine=[(94, 17), (102, 60), (89, 6), (50, 85)],
        stripe=[(67, 68), (90, 69), (89, 73), (63, 76), (62, 77), (60, 78), (58, 81), (55, 82), (52, 83), (55, 85),
                (98, 92), (93, 93), (95, 94)],
        skin=[(81, 36), (78, 48), (65, 133), (73, 148), (73, 154), (74, 155), (65, 158), (63, 159)],
        keep=[(76, 47, 93, 58)]),
}


def light_components(a):
    light = (a[..., 3] > 0) & (a[..., :3].min(-1) > 215)
    return ndimage.label(light)


def clean(name):
    a = np.asarray(Image.open(SRC / f"{name}.png").convert("RGBA")).copy()
    plan = PLAN.get(name, {})
    lab, _ = light_components(a)
    keep = np.zeros(a.shape[:2], bool)
    for x0, y0, x1, y1 in plan.get("keep", []):
        keep[y0:y1, x0:x1] = True
    log = []
    origin = {(sl[1].start, sl[0].start): k for k, sl in enumerate(ndimage.find_objects(lab), start=1)}
    for kind in ("clear", "shine", "stripe", "skin"):
        for x, y in plan.get(kind, []):
            k = origin.get((x, y))
            if not k:
                raise SystemExit(f"{name}: no light component starts at {(x, y)} ({kind})")
            m = (lab == k) & ~keep
            if kind == "clear":
                a[m] = 0
            elif kind == "shine":
                a[m, :3] = HAIR_LIGHT
            elif kind == "stripe":
                a[m, :3] = STRIPE
            else:
                # keep the drawing's light / shade structure: lighter whites -> skin, the rest -> skin shade
                lum = a[..., :3].mean(-1)
                a[m & (lum >= 244), :3] = SKIN
                a[m & (lum < 244), :3] = SKIN_SHADE
            log.append((kind, (x, y), int(m.sum())))
    return Image.fromarray(a, "RGBA"), log


def list_components():
    for name in PLAN:
        a = np.asarray(Image.open(SRC / f"{name}.png").convert("RGBA")).astype(int)
        lab, _ = light_components(a)
        for k, sl in enumerate(ndimage.find_objects(lab), start=1):
            print(name, (sl[1].start, sl[0].start), int((lab[sl] == k).sum()))


def main():
    if sys.argv[1:] == ["--list"]:
        return list_components()
    DST.mkdir(exist_ok=True)
    pairs = []
    for f in sorted(SRC.glob("*.png")):
        name = f.stem
        if name in PLAN:
            im, log = clean(name)
            print(name, log)
        else:
            im = Image.open(f).convert("RGBA")
        im.save(DST / f.name)
        pairs.append((Image.open(f).convert("RGBA"), im))
    if len(sys.argv) > 1:
        z = 3
        w = sum(p[0].width * z + 10 for p in pairs)
        h = max(p[0].height * z for p in pairs)
        sheet = Image.new("RGB", (w, 2 * h + 10), (255, 120, 200))
        x = 0
        for before, after in pairs:
            for row, im in enumerate((before, after)):
                big = im.resize((im.width * z, im.height * z), Image.Resampling.NEAREST)
                sheet.paste(big, (x, row * (h + 10)), big)
            x += before.width * z + 10
        sheet.save(sys.argv[1])


if __name__ == "__main__":
    main()
