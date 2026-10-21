"""Render mix + vocal-stem spectrograms with a pitch contour for a time window.

usage: plot_window.py <track> <start_s> <end_s> <out.png>
"""
import sys
import numpy as np
import librosa
import librosa.display
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

W = "/tmp/claude-0/-home-user/79528b42-f6d5-55a7-a812-a65ac1a1835e/scratchpad/oc_audio"
k, t0, t1, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
SR = 22050
mix, _ = librosa.load(f"{W}/wav/{k}.wav", sr=SR, offset=t0, duration=t1 - t0)
voc, _ = librosa.load(f"{W}/stems/{k}_vocals.wav", sr=SR, offset=t0, duration=t1 - t0)
f0, vflag, _ = librosa.pyin(voc, fmin=150, fmax=1400, sr=SR, frame_length=2048, hop_length=256)
tf = librosa.times_like(f0, sr=SR, hop_length=256) + t0

fig, ax = plt.subplots(4, 1, figsize=(16, 13), sharex=True, gridspec_kw={"height_ratios": [1, 3, 3, 2]})
tt = np.arange(len(mix)) / SR + t0
ax[0].plot(tt, mix, lw=0.3, color="0.3", label="mix")
ax[0].plot(tt, voc, lw=0.3, color="tab:blue", alpha=0.7, label="vocal stem")
ax[0].set_ylim(-1, 1); ax[0].legend(loc="upper right"); ax[0].set_title(f"{k}: waveform {t0:.1f}-{t1:.1f}s")
for a, y, title in ((ax[1], mix, "mix"), (ax[2], voc, "vocal stem")):
    S = librosa.amplitude_to_db(np.abs(librosa.stft(y, n_fft=2048, hop_length=256)), ref=np.max)
    librosa.display.specshow(S, sr=SR, hop_length=256, x_axis="time", y_axis="log", ax=a, cmap="magma", vmin=-80, vmax=0,
                             x_coords=librosa.times_like(S, sr=SR, hop_length=256) + t0)
    a.set_title(f"{title} spectrogram (log freq)")
ax[2].plot(tf, f0, color="cyan", lw=1.2)
midi = librosa.hz_to_midi(f0)
ax[3].plot(tf, midi, color="tab:blue", lw=1)
ax[3].set_ylabel("MIDI note"); ax[3].grid(True, alpha=0.3); ax[3].set_title("vocal pitch (pYIN)")
ax[3].set_xlabel("time (s)")
for a in ax:
    a.set_xlim(t0, t1)
    a.xaxis.set_major_locator(plt.MultipleLocator(1))
plt.tight_layout(); plt.savefig(out, dpi=80)
print(out)
