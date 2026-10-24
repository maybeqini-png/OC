"""Per-frame character matte for video clips (isnet-anime ONNX, the rembg anime model), temporally smoothed.

usage: matte.py <clip.mp4> <model.onnx> <out.npz>   (alpha as uint8 [frames, h, w] at the clip's size)
Used to put type and light *behind* her in a generated clip: out = (frame + layer) * (1 - a) + frame * a.
Temporal smoothing: per-pixel exponential moving average with a motion gate, so static edges do not flicker
while moving edges follow without lag.
"""
import sys

import cv2
import numpy as np
import onnxruntime as ort

MEAN = np.array([0.485, 0.456, 0.406], np.float32)


class Matter:
    def __init__(self, model):
        self.s = ort.InferenceSession(model, providers=["CPUExecutionProvider"])
        self.inp = self.s.get_inputs()[0].name

    def __call__(self, bgr):
        h, w = bgr.shape[:2]
        x = cv2.resize(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), (1024, 1024), interpolation=cv2.INTER_AREA)
        x = (x.astype(np.float32) / 255 - MEAN).transpose(2, 0, 1)[None]
        p = self.s.run(None, {self.inp: x})[0][0, 0]
        p = (p - p.min()) / (p.max() - p.min() + 1e-6)
        return cv2.resize(p, (w, h), interpolation=cv2.INTER_LINEAR)


def clip_matte(path, model):
    m = Matter(model)
    cap = cv2.VideoCapture(path)
    out, prev, prev_g = [], None, None
    while True:
        ok, f = cap.read()
        if not ok:
            break
        a = m(f)
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
        if prev is not None:
            motion = cv2.GaussianBlur(np.abs(g - prev_g), (0, 0), 3)
            k = np.clip(motion * 25, 0.35, 1.0)  # still pixels: heavy smoothing; moving pixels: follow now
            a = prev * (1 - k) + a * k
        prev, prev_g = a, g
        out.append((np.clip(a, 0, 1) * 255).astype(np.uint8))
    cap.release()
    return np.stack(out)


if __name__ == "__main__":
    al = clip_matte(sys.argv[1], sys.argv[2])
    np.savez_compressed(sys.argv[3], alpha=al)
    print(sys.argv[3], al.shape)
