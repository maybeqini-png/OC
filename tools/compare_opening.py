"""Overlay the opening vocal pitch contour of every track, aligned at first vocal onset.

usage: compare_opening.py <seconds_after_onset> <out.png> <track> [<track> ...]
"""
import json
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

W = "/tmp/claude-0/-home-user/79528b42-f6d5-55a7-a812-a65ac1a1835e/scratchpad/oc_audio"
FPS = 22050 / 256
span, out, tracks = float(sys.argv[1]), sys.argv[2], sys.argv[3:]
fig, ax = plt.subplots(len(tracks), 1, figsize=(16, 3.2 * len(tracks)), sharex=True)
ax = np.atleast_1d(ax)
for a, k in zip(ax, tracks):
    d = json.load(open(f"{W}/json/{k}.json"))
    f = np.load(f"{W}/json/{k}_f0.npz")
    on = d["vocal"]["first_vocal_s"]
    i0, i1 = int(on * FPS), int((on + span) * FPS)
    t = np.arange(i0, i1) / FPS - on
    a.plot(t, f["midi"][i0:i1], lw=1.2)
    a2 = a.twinx()
    a2.plot(t, f["rdb"][i0:i1], color="0.6", lw=0.5)
    a2.set_ylim(-70, 0)
    a.set_ylim(50, 85)
    a.grid(alpha=0.3)
    a.set_ylabel("MIDI")
    a.set_title(f"{k}: vocal pitch from first vocal onset ({on:.2f}s in file)  [grey = vocal level dB]")
ax[-1].set_xlabel("seconds after first vocal onset")
ax[-1].xaxis.set_major_locator(plt.MultipleLocator(1))
plt.tight_layout()
plt.savefig(out, dpi=75)
print(out)
