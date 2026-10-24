"""Mouth QA for one shot: body frames as planned, mouth targets from the morae, swaps applied; writes a crop strip
(every drawing: time, sung kana, vocal loudness, target -> shown shape, donor) and prints agreement numbers.

usage: qa_mouth.py <clip> <src_start[:hold[:src_end]]> <t0> <t1> <out.jpg> [donor clips...]
  body = clip frames from src_start at real time after holding the first drawing for `hold` frames, drawings on 2s
  (as pv4/block_64c.py src()); t0..t1 = song time of the shot.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mouth_layer as ML  # noqa: E402

FPS = 24


def vocal_env(t0, t1):
    import librosa
    y, sr = librosa.load(str(HERE / ".cache/vocals.wav"), sr=22050, mono=True, offset=t0 - 1, duration=t1 - t0 + 2)
    hop = int(sr / FPS)
    rms = np.array([np.sqrt(np.mean(y[i:i + hop] ** 2) + 1e-12) for i in range(0, len(y) - hop, hop)])
    db = 20 * np.log10(rms + 1e-6)
    return np.clip((db - (db.max() - 30)) / 24, 0, 1), t0 - 1


def phrases():
    return [p for line in json.load(open(HERE / "lyrics_block64.json")) for p in line["phrases"]]


def kana_at(t):
    for p in phrases():
        for k, m in enumerate(p["morae"]):
            end = p["morae"][k + 1]["t"] if k + 1 < len(p["morae"]) else p["end"]
            if m["t"] <= t < end:
                return m["kana"]
    return "-"


def main():
    clip, t0, t1, out = sys.argv[1], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
    parts = [int(x) for x in sys.argv[2].split(":")] + [0, 10 ** 6]
    s0, hold, s1 = parts[0], parts[1], parts[2] if len(parts) > 4 else 10 ** 6
    donors = sys.argv[6:]
    env, et0 = vocal_env(t0, t1)
    tl = ML.Timeline(phrases(), env, et0)
    sw = ML.MouthSwap(clip, donors)
    tr = ML.track(clip)
    fr = ML.frames(clip)
    fw = float(tr["fw"])
    tiles, agree, swaps, n = [], 0, 0, 0
    offs = list(range(0, int(round((t1 - t0) * FPS)), 2))
    plan = tl.plan([t0 + o / FPS for o in offs])
    for o, want in zip(offs, plan):
        t = t0 + o / FPS
        i = min(s0 + (max(o - hold, 0) // 2) * 2, s1, len(fr) - 1)
        f, donor = sw.apply(fr[i], i, want)
        shown = ML.track(donor[0])["cls"][donor[1]] if donor else tr["cls"][i]
        n += 1
        ok = shown == want or {shown, want} == {ML.OPEN, ML.ROUND}
        agree += int(ok)
        swaps += int(donor is not None)
        cx, cy = tr["pts"][i]
        s = int(fw * 0.42)
        c = f[max(int(cy - s), 0):int(cy + s), max(int(cx - s * 1.25), 0):int(cx + s * 1.25)]
        c = cv2.resize(c, (150, 120), interpolation=cv2.INTER_CUBIC)
        cv2.rectangle(c, (0, 0), (149, 119), (0, 200, 0) if ok else (0, 0, 255), 2)
        lab = f"{t:.2f} {ML.NAMES[want][:2]}>{ML.NAMES[shown][:2]}"
        cv2.putText(c, lab, (3, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        cv2.putText(c, f"e{tl.loud(t):.2f}" + (" sw" if donor else ""), (3, 116), cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                    (255, 255, 0), 1)
        tiles.append((c, kana_at(t + 1 / FPS)))
    # kana labels drawn with PIL (OpenCV has no Japanese glyphs)
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(str(HERE / "fonts/ZenKakuGothicNew-Bold.ttf"), 22)
    imgs = []
    for c, k in tiles:
        im = Image.fromarray(cv2.cvtColor(c, cv2.COLOR_BGR2RGB))
        ImageDraw.Draw(im).text((118, 88), k, font=font, fill=(255, 80, 120))
        imgs.append(np.array(im))
    while len(imgs) % 12:
        imgs.append(np.zeros_like(imgs[0]))
    sheet = np.vstack([np.hstack(imgs[k:k + 12]) for k in range(0, len(imgs), 12)])
    cv2.imwrite(out, cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f"{clip}: {n} drawings, shown == target {agree}/{n}, swapped {swaps}")


if __name__ == "__main__":
    main()
