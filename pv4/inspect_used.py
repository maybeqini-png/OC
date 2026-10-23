"""Inspection sheets of every drawing that appears on screen in a block (on 2s: every second source frame of
each used range), cropped tight to the character, frame numbers burned in.

usage: inspect_used.py <block module name> <out_dir>
"""
import importlib
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# character boxes in clip pixels (1344x768) per clip: x0, y0, x1, y1
BOX = {"h3_d01_close_tease": (484, 0, 1344, 768), "h3_p02b_me_poke": (420, 0, 1344, 768),
       "h3_p04_yosomi": (600, 0, 1344, 768), "h3_p05_tsuyogari": (760, 200, 1020, 720),
       "h3_p07b_konokoe_full": (540, 80, 810, 720)}


def main():
    B = importlib.import_module(sys.argv[1])
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for s0, s1, name, ss, _, _ in B.SHOTS:
        fr = B.clip(name)
        used = sorted({B.src_index(name, ss + (k / B.FPS)) for k in range(int(round((s1 - s0) * B.FPS)))})
        x0, y0, x1, y1 = BOX[name]
        th = 420
        tw = int(th * (x1 - x0) / (y1 - y0))
        cols = max(1, min(8, 2000 // tw))
        rows = 3
        per = cols * rows
        for p in range(0, len(used), per):
            grp = used[p:p + per]
            sheet = np.zeros((rows * (th + 22), cols * tw, 3), np.uint8)
            for j, fi in enumerate(grp):
                c = cv2.resize(fr[fi][y0:y1, x0:x1], (tw, th), interpolation=cv2.INTER_CUBIC)
                r, q = divmod(j, cols)
                sheet[r * (th + 22):r * (th + 22) + th, q * tw:(q + 1) * tw] = c
                cv2.putText(sheet, f"{name[3:12]} f{fi}", (q * tw + 4, r * (th + 22) + th + 16),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 230, 255), 1, cv2.LINE_AA)
            cv2.imwrite(str(out / f"{name}_used{p // per + 1:02d}.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
        print(name, "drawings on screen:", len(used), "frames", used[0], "-", used[-1])


if __name__ == "__main__":
    main()
