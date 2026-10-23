"""Frame-by-frame character QA for generated clips.

usage: qa_frames.py <clip.mp4> <isnet-anime.onnx> <out_dir> [--step 4]

For EVERY frame:
- matte (pv4/matte.py, isnet-anime) -> silhouette;
- parts: connected components of the silhouette (area >= 0.15 % of the frame). The first frame is our on-model frame,
  so extra parts mean something came loose (broken tail, floating hand, stray hair blob); fewer parts can mean a
  limb merged or vanished;
- pop: silhouette area change against the previous frame (> 3 % = a limb or tail appeared/disappeared at once);
- extremities: the silhouette's convex-hull defects are counted per frame; jumps in that count point at hands and
  tail changing shape abruptly.
Then inspection sheets: every `step`-th frame (default 4 = 6 fps at 24 fps) cropped to the union box of the
character, 4 x 3 tiles per sheet, frame numbers burned in, flagged frames framed in red.
Writes <out_dir>/<clip>_qa.json and <clip>_sheetNN.jpg.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from matte import Matter  # noqa: E402


def analyse(path, model, out_dir, step=4):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = Path(path).stem
    cap = cv2.VideoCapture(path)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()
    cache = out_dir / f"{name}_alpha.npz"
    if cache.exists():
        alphas = list(np.load(cache)["alpha"].astype(np.float32) / 255)
    else:
        m = Matter(model)
        alphas = [m(f) for f in frames]
        np.savez_compressed(cache, alpha=(np.stack(alphas) * 255).astype(np.uint8))
    H, W = frames[0].shape[:2]
    min_area = 0.0015 * H * W
    rec = []
    prev_area = None
    for i, a in enumerate(alphas):
        sil = (a > 0.5).astype(np.uint8)
        sil = cv2.morphologyEx(sil, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(sil, connectivity=8)
        parts = [st[k] for k in range(1, n) if st[k, cv2.CC_STAT_AREA] >= min_area]
        area = float(sil.sum())
        cnts, _ = cv2.findContours(sil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        defects = 0
        if cnts:
            c = max(cnts, key=cv2.contourArea)
            hull = cv2.convexHull(c, returnPoints=False)
            if hull is not None and len(hull) > 3:
                d = cv2.convexityDefects(c, hull)
                if d is not None:
                    defects = int((d.reshape(-1, 4)[:, 3] / 256.0 > 0.02 * H).sum())
        pop = 0.0 if prev_area is None else abs(area - prev_area) / max(prev_area, 1)
        prev_area = area
        rec.append(dict(frame=i, parts=len(parts), area=round(area / (H * W), 4), pop=round(pop, 4), defects=defects,
                        boxes=[[int(p[0]), int(p[1]), int(p[2]), int(p[3])] for p in parts]))
    base_parts = rec[0]["parts"]
    base_def = int(np.median([r["defects"] for r in rec[:6]]))
    for r in rec:
        r["flag"] = []
        if r["parts"] > base_parts:
            r["flag"].append("detached part")
        if r["parts"] < base_parts:
            r["flag"].append("part merged/vanished")
        if r["pop"] > 0.03:
            r["flag"].append("silhouette pop")
        if abs(r["defects"] - base_def) >= 3:
            r["flag"].append("outline shape jump")
    # union box of the character over the clip
    allsil = np.max(np.stack([(a > 0.5) for a in alphas]), axis=0).astype(np.uint8)
    ys, xs = np.where(allsil)
    pad = 20
    x0, y0, x1, y1 = max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, W), min(ys.max() + pad, H)
    sel = list(range(0, len(frames), step))
    flagged = {r["frame"] for r in rec if r["flag"]}
    sel = sorted(set(sel) | flagged)
    tw = 470
    th = int(tw * (y1 - y0) / (x1 - x0))
    if th > 620:
        th = 620
        tw = int(th * (x1 - x0) / (y1 - y0))
    per = 12
    sheets = []
    for s in range(0, len(sel), per):
        group = sel[s:s + per]
        sheet = np.zeros((3 * (th + 26), 4 * tw, 3), np.uint8)
        for j, fi in enumerate(group):
            crop = cv2.resize(frames[fi][y0:y1, x0:x1], (tw, th), interpolation=cv2.INTER_AREA)
            if fi in flagged:
                cv2.rectangle(crop, (0, 0), (tw - 1, th - 1), (0, 0, 255), 4)
            r, c = j // 4, j % 4
            sheet[r * (th + 26):r * (th + 26) + th, c * tw:(c + 1) * tw] = crop
            label = f"f{fi} t{fi / 24:.2f}" + ("  " + ",".join(rec[fi]["flag"]) if fi in flagged else "")
            cv2.putText(sheet, label, (c * tw + 6, r * (th + 26) + th + 19), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (0, 0, 255) if fi in flagged else (0, 230, 255), 1, cv2.LINE_AA)
        p = out_dir / f"{name}_sheet{s // per + 1:02d}.jpg"
        cv2.imwrite(str(p), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
        sheets.append(str(p))
    summary = dict(clip=path, frames=len(frames), base_parts=base_parts, flagged_frames=len(flagged),
                   flags={k: sum(1 for r in rec if k in r["flag"]) for k in
                          ("detached part", "part merged/vanished", "silhouette pop", "outline shape jump")},
                   box=[int(x0), int(y0), int(x1), int(y1)], sheets=sheets)
    json.dump(dict(summary=summary, frames=rec), open(out_dir / f"{name}_qa.json", "w"), indent=1)
    return summary


if __name__ == "__main__":
    args = sys.argv[1:]
    step = 4
    if "--step" in args:
        step = int(args[args.index("--step") + 1])
        args = args[:args.index("--step")]
    print(json.dumps(analyse(args[0], args[1], args[2], step), ensure_ascii=False))
