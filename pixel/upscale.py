"""Sharp upscaling of N5 anime plates with Real-ESRGAN (ncnn, CPU, tiled).

Model files come from the official realesrgan-ncnn-vulkan release (github.com/xinntao/Real-ESRGAN, v0.2.5.0,
BSD-3-Clause); they are not stored in the repo. Default: realesr-animevideov3-x2 (flat anime art, fast).

usage:  upscale.py in.png out.png --models DIR [--model realesr-animevideov3-x2] [--scale 2] [--height 1080]
"""
import argparse

import ncnn
import numpy as np
from PIL import Image

TILE, PAD = 192, 12


def upscale(im, models, model="realesr-animevideov3-x2", scale=2):
    net = ncnn.Net()
    net.opt.use_vulkan_compute = False
    net.opt.num_threads = 4
    net.load_param(f"{models}/{model}.param")
    net.load_model(f"{models}/{model}.bin")
    a = np.asarray(im.convert("RGB")).astype(np.float32) / 255
    h, w = a.shape[:2]
    out = np.zeros((h * scale, w * scale, 3), np.float32)
    for y0 in range(0, h, TILE):
        for x0 in range(0, w, TILE):
            ya, xa = max(0, y0 - PAD), max(0, x0 - PAD)
            yb, xb = min(h, y0 + TILE + PAD), min(w, x0 + TILE + PAD)
            tile = np.ascontiguousarray(a[ya:yb, xa:xb].transpose(2, 0, 1))
            ex = net.create_extractor()
            ex.input("data", ncnn.Mat(tile))
            _, o = ex.extract("output")
            o = np.array(o).transpose(1, 2, 0)
            cy, cx = (y0 - ya) * scale, (x0 - xa) * scale
            th, tw = (min(h, y0 + TILE) - y0) * scale, (min(w, x0 + TILE) - x0) * scale
            out[y0 * scale:y0 * scale + th, x0 * scale:x0 * scale + tw] = o[cy:cy + th, cx:cx + tw]
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--models", required=True)
    ap.add_argument("--model", default="realesr-animevideov3-x2")
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--height", type=int, default=1080, help="final height (Lanczos down from the x2 result)")
    a = ap.parse_args()
    big = upscale(Image.open(a.src), a.models, a.model, a.scale)
    if a.height:
        big = big.resize((round(big.width * a.height / big.height), a.height), Image.Resampling.LANCZOS)
    big.save(a.out)
