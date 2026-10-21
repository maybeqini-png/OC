"""Prepare PV assets: cutouts, background plates, beat grid and vocal envelope.

usage: preprocess.py <vocal_stem.wav> <instrumental_stem.wav>
writes pv/assets/*.png and pv/assets/timing.json
"""
import json
import sys
from pathlib import Path

import librosa
import numpy as np
from PIL import Image, ImageFilter
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parent.parent
G = ROOT / "art/generated"
OUT = ROOT / "pv/assets"
OUT.mkdir(parents=True, exist_ok=True)
FPS = 30
DUR = 178.6
session = new_session("isnet-anime")


def cut(src):
    a = remove(Image.open(src).convert("RGB"), session=session).getchannel("A")
    return a.point(lambda v: 0 if v < 12 else min(255, int(v * 1.08)))  # trim faint halo, firm up interior


# bust family shares one alpha so swapping faces never changes the silhouette
base = G / "nai_test/a3_img2img_v5_s050.png"
alpha = cut(base)
bust = {"bust_base": base, "bust_blink": G / "nai_test/b_blink_v5.png", "bust_talk": G / "nai_test/c_mouth_v5.png",
        "e3_shocked": G / "expr/e3_shocked.png", "e4_flustered": G / "expr/e4_flustered.png",
        "e6_laughing": G / "expr/e6_laughing.png", "e7_honest": G / "expr/e7_honest.png"}
for name, src in bust.items():
    im = Image.open(src).convert("RGB")
    im.putalpha(alpha)
    im.save(OUT / f"{name}.png")

for src in [G / "expr/e5_meh_wink_closeup.png"] + sorted((G / "poses").glob("[pc][0-9]_*.png")):
    if src.stem.endswith("_v45"):
        continue
    im = Image.open(src).convert("RGB")
    im.putalpha(cut(src))
    im.save(OUT / f"{src.stem}.png")

for src in sorted((G / "bg").glob("*.png")):
    im = Image.open(src).convert("RGB").resize((2304, 1296), Image.LANCZOS)
    im.save(OUT / f"{src.stem}.png")
    im.filter(ImageFilter.GaussianBlur(7)).save(OUT / f"{src.stem}_blur.png")

# beats from the instrumental stem, vocal loudness per video frame for lip-sync
inst, sr = librosa.load(sys.argv[2], sr=22050)
_, bf = librosa.beat.beat_track(y=inst, sr=sr, hop_length=256)
beats = librosa.frames_to_time(bf, sr=sr, hop_length=256)
voc, _ = librosa.load(sys.argv[1], sr=22050)
hop = sr // FPS
rms = librosa.feature.rms(y=voc, frame_length=hop * 2, hop_length=hop)[0]
db = 20 * np.log10(rms + 1e-9)
db = np.clip((db - (db.max() - 40)) / 40, 0, 1)
n = int(DUR * FPS) + 1
env = np.zeros(n)
env[: min(n, len(db))] = db[:n]
json.dump({"beats": [round(float(b), 3) for b in beats], "vocal_env": [round(float(v), 3) for v in env]},
          open(OUT / "timing.json", "w"))
print("assets:", sorted(p.name for p in OUT.glob("*.png")))
print("beats:", len(beats), "| env frames:", n)
