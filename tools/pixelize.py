"""Convert aligned anime frames into pixel-art sprites with one shared palette.

usage: pixelize.py <out_dir> <height_px> <n_colors> <base.png> [<frame.png> ...]
The base frame defines the palette and the cutout; every frame uses the same grid and palette,
so regions that are identical in the sources stay identical in the sprites (no flicker).
"""
import sys

import numpy as np
from PIL import Image
from rembg import new_session, remove

out_dir, N, K = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
paths = sys.argv[4:]
src = [Image.open(p).convert("RGB") for p in paths]
W0 = src[0].size[0]
b = W0 // N                      # block size in source pixels
S = N * b                        # working resolution (multiple of block)

alpha = np.asarray(remove(src[0], session=new_session("isnet-anime")).getchannel("A").resize((S, S), Image.LANCZOS)) / 255.0


def boost(im):
    """Slight saturation/contrast lift so the palette keeps the OC's blues vivid."""
    a = np.asarray(im).astype(float) / 255
    g = a.mean(2, keepdims=True)
    a = np.clip(g + (a - g) * 1.15, 0, 1)
    a = np.clip((a - 0.5) * 1.08 + 0.5, 0, 1)
    return Image.fromarray((a * 255).round().astype(np.uint8))


work = [boost(im.resize((S, S), Image.LANCZOS)) for im in src]
# palette from the character only (background pixels excluded)
base = np.asarray(work[0])
fg = base[alpha > 0.5].reshape(-1, 1, 3)
pal_img = Image.fromarray(fg).quantize(colors=K, method=Image.Quantize.MEDIANCUT, kmeans=4)
pal = np.array(pal_img.getpalette()[: K * 3]).reshape(K, 3)
lum = pal @ np.array([0.299, 0.587, 0.114])
dark = np.argsort(lum)[: max(2, K // 8)]  # line colours
outline = int(np.argmin(lum))


def sprite(im):
    idx = np.asarray(im.quantize(palette=pal_img, dither=Image.Dither.NONE))
    blocks = idx.reshape(N, b, N, b).transpose(0, 2, 1, 3).reshape(N, N, b * b)
    out = np.zeros((N, N), int)
    for y in range(N):
        for x in range(N):
            cnt = np.bincount(blocks[y, x], minlength=K)
            mode = cnt.argmax()
            d = cnt[dark].max()
            # keep thin features: near-black lines, or any colour clearly darker than the block (mouth, lashes)
            local = np.where((lum < lum[mode] - 70) & (cnt >= 0.06 * b * b))[0]
            if d >= 0.22 * b * b:
                out[y, x] = dark[cnt[dark].argmax()]
            elif len(local):
                out[y, x] = local[np.argmax(cnt[local])]
            else:
                out[y, x] = mode
    opaque = alpha.reshape(N, b, N, b).mean((1, 3)) > 0.5
    # clean isolated single pixels (all 4 neighbours agree on another colour)
    o = out.copy()
    for y in range(1, N - 1):
        for x in range(1, N - 1):
            nb = [out[y - 1, x], out[y + 1, x], out[y, x - 1], out[y, x + 1]]
            if nb.count(nb[0]) == 4 and nb[0] != out[y, x] and out[y, x] not in dark:
                o[y, x] = nb[0]
    out = o
    # 1-px outline on the silhouette edge
    edge = opaque & ~(np.roll(opaque, 1, 0) & np.roll(opaque, -1, 0) & np.roll(opaque, 1, 1) & np.roll(opaque, -1, 1))
    out[edge] = outline
    rgba = np.zeros((N, N, 4), np.uint8)
    rgba[..., :3] = pal[out]
    rgba[..., 3] = opaque * 255
    return Image.fromarray(rgba, "RGBA")


sprites = [sprite(im) for im in work]
for p, s in zip(paths, sprites):
    name = p.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    s.save(f"{out_dir}/{name}_{N}px.png")
print(f"{N}px sprites, palette {K} colours, block {b}px:", [p.rsplit('/', 1)[-1] for p in paths])
