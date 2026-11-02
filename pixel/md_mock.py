"""Game-scale mock-up of one monster family on its stage plate (1920x1080), for review before the video rebuild.

usage: python3 md_mock.py night out.png
Layout (docs/rhythm_game_style_reference.md): floor y 860, player ~250 px at x 420, air lane y ~420,
monsters 120-180 px; stage plate under a pastel haze so the flat sprites read on top.
"""
import sys

from PIL import Image, ImageDraw, ImageFilter

import mdsprites as MD
import scene as S

FAMILIES = {"night": ("n_ground", "n_air", "n_saw", (60, 40, 110), (120, 90, 190))}
FLOOR, AIR, PX = 860, 420, 420


def haze(im, tint, k=0.32):
    """Low-contrast pastel haze: soften, then lift toward a light stage tint."""
    im = im.convert("RGB").filter(ImageFilter.GaussianBlur(2))
    return Image.blend(im, Image.new("RGB", im.size, tint), k)


def put(c, spr, cx, bottom=None, cy=None):
    x = cx - spr.width // 2
    y = bottom - spr.height if bottom is not None else cy - spr.height // 2
    c.alpha_composite(spr, (x, y))


def mock(stage, out):
    g, a, s, floor_c, line_c = FAMILIES[stage]
    c = haze(S.plate_view(stage, 0.4), (200, 170, 235)).convert("RGBA")
    d = ImageDraw.Draw(c)
    d.rectangle((0, FLOOR, 1920, 1080), fill=floor_c + (255,))
    d.rectangle((0, FLOOR, 1920, FLOOR + 10), fill=line_c + (255,))
    for x in range(0, 1920, 120):
        d.rectangle((x, FLOOR + 40, x + 60, FLOOR + 48), fill=line_c + (255,))
    for y in (AIR, FLOOR - 75):                       # judgement rings
        d.ellipse((PX + 120 - 38, y - 38, PX + 120 + 38, y + 38), outline=(255, 255, 255, 230), width=5)
    put(c, MD.sprite("xiyin_run"), PX - 20, bottom=FLOOR + 8)
    gr = MD.sprite(g)
    put(c, gr, 900, bottom=FLOOR + 6)
    put(c, MD.sprite(a), 1280, cy=AIR)
    put(c, MD.sprite(s).rotate(18, Image.Resampling.BICUBIC, expand=True), 1500, bottom=FLOOR + 30)
    put(c, gr, 1780, bottom=FLOOR + 6)
    c.convert("RGB").save(out)


if __name__ == "__main__":
    mock(sys.argv[1], sys.argv[2])
