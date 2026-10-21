"""Build the optimized t2 (A2-based) master and Short cuts.

Edits (times in seconds, measured on the t2 stems):
  - stumble: instrumental muffled + dipped from 「えっ」 (42.606) until 「ちょっと待った」 (44.18); synthesized thud at 43.05
  - 「めっ」 boop at 66.821 and 137.358; camera-shutter click at 「スクショ」 84.645
  - final chorus vocal +1.5 dB (125.5-153.95, ramps inside vocal gaps)
  - trailing silence trimmed (end 178.6 s), whole track gained to -1 dBTP
All SFX are synthesized here (no third-party audio).
"""
import numpy as np
import librosa
import pyloudnorm as pyln
import scipy.signal as sps
import soundfile as sf

W = "/tmp/claude-0/-home-user/79528b42-f6d5-55a7-a812-a65ac1a1835e/scratchpad/oc_audio"
OUT = f"{W}/deliver"
SR = 44100

a2, _ = sf.read(f"{W}/agents/opening/t2_fixA2_no_whoop_soft_breath.wav", always_2d=True)
inst, _ = sf.read(f"{W}/stems/t2_inst.wav", always_2d=True)
voc = a2 - inst  # A2 vocal (exact: A2 = inst + edited vocal)
t = np.arange(len(a2)) / SR


def ramp(t0, t1, v0, v1):
    """Gain curve: v0 before t0, raised-cosine to v1 at t1, v1 after."""
    x = np.clip((t - t0) / (t1 - t0), 0, 1)
    return v0 + (v1 - v0) * (0.5 - 0.5 * np.cos(np.pi * x))


# 1) stumble: muffle + dip the instrumental (STFT low-pass whose cutoff dives and recovers)
def muffle(x, t_in, t_hold_end, t_out, fc_low=350.0, dip_db=-5.0):
    a, b = int((t_in - 0.5) * SR), int((t_out + 0.5) * SR)
    seg = x[a:b]
    n_fft, hop = 2048, 256
    f = librosa.fft_frequencies(sr=SR, n_fft=n_fft)
    out = []
    for ch in seg.T:
        Z = librosa.stft(ch, n_fft=n_fft, hop_length=hop)
        tf = librosa.frames_to_time(np.arange(Z.shape[1]), sr=SR, hop_length=hop) + a / SR
        depth = np.interp(tf, [t_in, t_in + 0.06, t_hold_end, t_out], [0, 1, 1, 0])  # 0 = untouched, 1 = full muffle
        fc = 20000.0 * (fc_low / 20000.0) ** depth
        lp = 1.0 / np.sqrt(1.0 + (f[:, None] / fc[None, :]) ** 4)  # ~12 dB/oct roll-off
        g = lp * 10 ** (dip_db * depth / 20)[None, :]
        out.append(librosa.istft(Z * g, hop_length=hop, length=len(ch)))
    y = x.copy()
    edited = np.stack(out, 1)
    w = np.clip(np.minimum(np.arange(len(seg)), len(seg) - 1 - np.arange(len(seg))) / (0.05 * SR), 0, 1)[:, None]
    y[a:b] = w * edited + (1 - w) * seg  # crossfade at the outer edges (where depth is 0 anyway)
    return y


inst2 = muffle(inst, 42.58, 44.06, 44.18)

# 2) final chorus vocal lift +1.5 dB, ramps inside the vocal gaps
g = ramp(125.50, 125.75, 1.0, 10 ** (1.5 / 20)) * ramp(153.60, 153.95, 1.0, 10 ** (-1.5 / 20))
voc2 = voc * g[:, None]

mix = inst2 + voc2


# 3) synthesized SFX
def place(sig, at, gain_db, pan=0.0):
    s = sig * 10 ** (gain_db / 20) / (np.abs(sig).max() + 1e-12)
    i = int(at * SR)
    L, R = np.sqrt(0.5 - pan / 2), np.sqrt(0.5 + pan / 2)
    mix[i:i + len(s), 0] += s[: len(mix) - i] * L * np.sqrt(2)
    mix[i:i + len(s), 1] += s[: len(mix) - i] * R * np.sqrt(2)


rng = np.random.default_rng(7)
tt = np.arange(int(0.35 * SR)) / SR
f_th = 90 + 90 * np.exp(-tt / 0.04)  # 180 -> 90 Hz body: audible on phone speakers
thud = np.sin(2 * np.pi * np.cumsum(f_th) / SR) * np.exp(-tt / 0.08)
click = sps.lfilter(*sps.butter(2, [150 / (SR / 2), 1200 / (SR / 2)], btype="band"), rng.standard_normal(len(tt))) * np.exp(-tt / 0.02)
thud = thud + 0.8 * click / np.abs(click).max()
thud[: int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))

tb = np.arange(int(0.16 * SR)) / SR
f_b = 700 + 700 * np.exp(-tb / 0.025)  # 1400 -> 700 Hz pop
boop = (np.sin(2 * np.pi * np.cumsum(f_b) / SR) + 0.25 * np.sin(4 * np.pi * np.cumsum(f_b) / SR))
boop *= np.minimum(1, tb / 0.003) * np.exp(-tb / 0.045)

ts = np.arange(int(0.16 * SR)) / SR
bp = sps.butter(2, [1500 / (SR / 2), 9000 / (SR / 2)], btype="band")
shut = np.zeros_like(ts)
for off, amp in ((0.0, 1.0), (0.075, 0.6)):
    k = int(off * SR)
    burst = sps.lfilter(*bp, rng.standard_normal(len(ts) - k)) * np.exp(-np.arange(len(ts) - k) / SR / 0.018)
    shut[k:] += amp * burst / np.abs(burst).max()
shut += 0.3 * np.sin(2 * np.pi * 120 * ts) * np.exp(-ts / 0.015)

place(thud, 43.05, -4.0)
place(boop, 66.821, -14.0, pan=-0.15)
place(boop, 137.358, -14.0, pan=0.15)
place(shut, 84.645, -4.0)

# 4) trim trailing silence, short fade to zero, then peak-safe gain
end = int(178.6 * SR)
mix = mix[:end]
mix[-int(0.3 * SR):] *= np.linspace(1, 0, int(0.3 * SR))[:, None]
tp = np.abs(sps.resample_poly(mix, 4, 1, axis=0)).max()
mix *= 10 ** (-1.0 / 20) / tp
sf.write(f"{OUT}/t2_optimized_full.wav", mix, SR, subtype="PCM_24")

# checks
ref = a2[:end] * (10 ** (-1.0 / 20) / tp)
d = np.abs(mix - ref).max(1) > 10 ** (-60 / 20)
edges = np.flatnonzero(np.diff(np.concatenate([[0], d.astype(int), [0]])))
regions = [(round(edges[i] / SR, 2), round(edges[i + 1] / SR, 2)) for i in range(0, len(edges), 2)]
merged = []
for r0, r1 in regions:
    if merged and r0 - merged[-1][1] < 0.3:
        merged[-1] = (merged[-1][0], r1)
    else:
        merged.append((r0, r1))
print("regions differing from A2 by more than -60 dB:", merged)
print("LUFS %.1f, true peak %.2f dBTP" % (pyln.Meter(SR).integrated_loudness(mix), 20 * np.log10(np.abs(sps.resample_poly(mix, 4, 1, axis=0)).max())))

# 5) Short cuts (start on a beat, short fade-in, 0.25 s fade-out before the next word)
for name, s0, s1 in (("short30_cool_stumble_hook", 33.611, 64.35),
                     ("short16_stumble_teaser", 41.564, 58.00),
                     ("short16_meh_challenge", 53.035, 69.45)):
    c = mix[int(s0 * SR):int(s1 * SR)].copy()
    c[: int(0.005 * SR)] *= np.linspace(0, 1, int(0.005 * SR))[:, None]
    c[-int(0.25 * SR):] *= np.linspace(1, 0, int(0.25 * SR))[:, None]
    sf.write(f"{OUT}/t2_{name}.wav", c, SR, subtype="PCM_24")
    print(name, "%.2f s" % (len(c) / SR))
