"""REJECTED EXPERIMENT (kept for the record, docs/research_pv_language.md §7): a cel pass meant to turn generated
character footage back into flat-painted, inked anime cels in the sheet's colours. Result: posterised, blotchy frames.

Measured problem (docs/research_pv_language.md §7): generated frames carry soft airbrushed gradients and micro
texture everywhere (character soft-share 0.16 vs sheet 0.05 / bust 0.01; palette 45 colours vs 24), which is what
reads as "AI". Hand-painted cels are flat fills with 1-2 hard shadow tones and an ink line.

Per frame (character pixels only, from the per-frame matte):
1. edge-preserving flattening (mean-shift on Lab) removes airbrush gradients and texture but keeps shapes;
2. every pixel is snapped to the PALETTE of the on-model first frame (k-means of the sheet figure as relit in that
   frame), so fills are exactly the sheet's colours and shading collapses to hard cel boundaries;
3. tiny islands are merged into their neighbours (majority filter), so no speckle boils between frames;
4. temporal hysteresis: a pixel keeps last drawing's palette index unless another index is clearly closer;
5. ink: thin dark structures of the source become solid line colour; the silhouette gets a crisp outer line.
"""
import cv2
import numpy as np


def to_lab(rgb):
    lab = cv2.cvtColor(np.clip(rgb, 0, 1).astype(np.float32), cv2.COLOR_RGB2LAB)
    return lab  # L 0..100, a/b ~ -127..127


def from_lab(lab):
    return np.clip(cv2.cvtColor(lab.astype(np.float32), cv2.COLOR_LAB2RGB), 0, 1)


class CelPass:
    def __init__(self, ref_rgb, ref_alpha, k=26, line_L=None):
        """ref_rgb/ref_alpha: the clip's on-model first frame (our relit sheet composite) and its character mask."""
        lab = to_lab(ref_rgb)
        m = ref_alpha > 0.6
        px = lab[m].reshape(-1, 3).astype(np.float32)
        rng = np.random.default_rng(0)
        px = px[rng.choice(len(px), min(len(px), 60000), replace=False)]
        crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.2)
        _, _, cen = cv2.kmeans(px, k, None, crit, 4, cv2.KMEANS_PP_CENTERS)
        cen = cen[np.argsort(cen[:, 0])]
        self.pal = cen.astype(np.float32)  # sorted dark -> light
        self.line_lab = self.pal[0].copy() if line_L is None else np.array([line_L, self.pal[0][1], self.pal[0][2]])
        self.line_lab[0] = min(self.line_lab[0], 18.0)
        self.prev_idx = None
        self.prev_gray = None

    def _assign(self, lab):
        d = ((lab[..., None, :] - self.pal[None, None]) ** 2 * np.array([1.4, 1.0, 1.0], np.float32)).sum(-1)
        return d

    def frame(self, rgb, alpha, outline_px=2):
        h, w = alpha.shape
        m = alpha > 0.5
        ys, xs = np.where(m)
        if len(ys) == 0:
            return rgb
        y0, y1 = max(ys.min() - 8, 0), min(ys.max() + 9, h)
        x0, x1 = max(xs.min() - 8, 0), min(xs.max() + 9, w)
        crop = rgb[y0:y1, x0:x1]
        mc = m[y0:y1, x0:x1]
        u8 = (np.clip(crop, 0, 1) * 255).astype(np.uint8)
        # 1. flatten: mean shift keeps edges, kills gradients and texture
        flat = cv2.pyrMeanShiftFiltering(cv2.cvtColor(u8, cv2.COLOR_RGB2BGR), sp=5, sr=14, maxLevel=1)
        flat = cv2.cvtColor(flat, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
        lab = to_lab(flat)
        # 2. snap to the on-model palette (with hysteresis against the previous drawing)
        d = self._assign(lab)
        idx = d.argmin(-1)
        g = cv2.cvtColor(u8, cv2.COLOR_RGB2GRAY)
        if self.prev_idx is not None and self.prev_idx.shape == idx.shape:
            flow = cv2.calcOpticalFlowFarneback(g, self.prev_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            hh, ww = idx.shape
            yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
            pidx = cv2.remap(self.prev_idx.astype(np.float32), xx + flow[..., 0], yy + flow[..., 1],
                             cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE).astype(int)
            pd = np.take_along_axis(d, pidx[..., None], -1)[..., 0]
            bd = np.take_along_axis(d, idx[..., None], -1)[..., 0]
            keep = pd < bd + 40.0  # only switch when the new colour is clearly closer
            idx = np.where(keep, pidx, idx)
        # 3. majority filter: remove islands smaller than ~3x3
        k = len(self.pal)
        votes = np.zeros(idx.shape + (k,), np.float32)
        for c in np.unique(idx[mc]):
            votes[..., c] = cv2.boxFilter((idx == c).astype(np.float32), -1, (5, 5))
        idx = np.where(mc, votes.argmax(-1), idx)
        self.prev_idx, self.prev_gray = idx, g
        out_lab = self.pal[idx]
        # 5a. ink: thin dark lines of the source (darker than surroundings, narrow)
        L = to_lab(crop)[..., 0]
        bg = cv2.blur(L, (9, 9))
        ink = ((L < bg - 9) & (L < 45)).astype(np.uint8)
        ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        ink = cv2.GaussianBlur(ink.astype(np.float32), (0, 0), 0.6)
        out = from_lab(out_lab)
        out = out * (1 - ink[..., None]) + from_lab(self.line_lab[None, None])[0, 0] * ink[..., None]
        # 5b. outer contour line on the silhouette
        a8 = (alpha[y0:y1, x0:x1] > 0.5).astype(np.uint8)
        edge = a8 - cv2.erode(a8, np.ones((outline_px * 2 + 1,) * 2, np.uint8))
        edge = cv2.GaussianBlur(edge.astype(np.float32), (0, 0), 0.7)
        out = out * (1 - edge[..., None]) + from_lab(self.line_lab[None, None])[0, 0] * edge[..., None]
        res = rgb.copy()
        res[y0:y1, x0:x1] = np.where(mc[..., None], out, crop)
        return res
