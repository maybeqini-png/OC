"""Fix the stream-cam pout frame (owner 2026-11-05: "the colours on the face look off", 1:40): its closed eyes had
grey-blue smudges under them and dark grey lids. The face of a V5 img2img redraw (art/generated/vtuber3/fix,
pout_0.30_69002, same expression, clean pink blush) is transplanted back into final/pout.png with a feathered
ellipse, its colours matched to the frame's skin.

usage: python3 vtfix.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).parent.parent
FINAL = ROOT / "art/generated/vtuber3/final/pout.png"
FIX = ROOT / "art/generated/vtuber3/fix/pout_0.30_69002.png"
BOX = (560, 380)                     # crop origin in the 2048 frame (fix/pout_crop.png)
FACE = (90, 240, 900, 930)           # ellipse in crop px: eyes, cheeks, mouth


def build():
    base = Image.open(FINAL).convert("RGB")
    crop = base.crop((BOX[0], BOX[1], BOX[0] + 1024, BOX[1] + 1024))
    red = Image.open(FIX).convert("RGB").resize((1024, 1024))
    a, b = np.asarray(crop).astype(np.float32), np.asarray(red).astype(np.float32)
    skin = (a[..., 0] > 235) & (a[..., 0] > a[..., 2] + 15) & (b[..., 0] > 235)
    b[skin] += np.median(a[skin] - b[skin], 0) * 0.5         # half-way: keep the cleaner tone, no visible seam
    red = Image.fromarray(b.clip(0, 255).astype(np.uint8))
    m = Image.new("L", (1024, 1024), 0)
    ImageDraw.Draw(m).ellipse(FACE, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(28))
    out = base.copy()
    out.paste(Image.composite(red, crop, m), BOX)
    out.save(FINAL)
    return out


if __name__ == "__main__":
    build()
