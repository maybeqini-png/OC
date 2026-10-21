"""Measure one track: technical quality, musical structure, and vocal performance.

usage: analyze.py <track>   (expects wav/<track>.wav and stems/<track>_vocals.wav)
writes json/<track>.json, json/<track>_f0.npz and img/<track>_overview.png
"""
import json
import sys

import librosa
import matplotlib
import numpy as np
import pyloudnorm as pyln
import scipy.signal as sps
import soundfile as sf

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

W = "/tmp/claude-0/-home-user/79528b42-f6d5-55a7-a812-a65ac1a1835e/scratchpad/oc_audio"
SR = 22050
HOP = 256
FPS = SR / HOP
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def r(x, n=2):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), n)


def technical(k):
    x, sr = sf.read(f"{W}/wav/{k}.wav", always_2d=True)
    meter = pyln.Meter(sr)
    lufs = meter.integrated_loudness(x)
    # short-term loudness (3 s windows, 1 s hop) -> loudness range approximation
    st = [meter.integrated_loudness(x[i:i + 3 * sr]) for i in range(0, len(x) - 3 * sr, sr)]
    st = np.array([v for v in st if np.isfinite(v) and v > -70])
    up = sps.resample_poly(x, 4, 1, axis=0)
    mono = x.mean(1)
    spec = np.abs(librosa.stft(mono.astype(np.float32), n_fft=4096, hop_length=2048)).mean(1)
    sdb = 20 * np.log10(spec + 1e-12)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=4096)
    above = np.where(sdb > sdb.max() - 70)[0]
    env = librosa.feature.rms(y=mono.astype(np.float32), frame_length=4096, hop_length=1024)[0]
    edb = 20 * np.log10(env + 1e-9)
    te = librosa.times_like(env, sr=sr, hop_length=1024)
    lead = te[np.argmax(edb > edb.max() - 40)]
    loud = np.where(edb > edb.max() - 40)[0]
    tail = te[-1] - te[loud.max()]
    last_audible = te[loud.max()]
    fade = edb[(te > last_audible - 3) & (te <= last_audible)]
    clipped = np.abs(x) >= 0.999
    return {
        "duration_s": r(len(x) / sr),
        "integrated_lufs": r(lufs, 1),
        "short_term_lufs_p10_p95": [r(np.percentile(st, 10), 1), r(np.percentile(st, 95), 1)],
        "loudness_range_lu": r(np.percentile(st, 95) - np.percentile(st, 10), 1),
        "sample_peak_dbfs": r(20 * np.log10(np.abs(x).max()), 2),
        "true_peak_dbtp_approx": r(20 * np.log10(np.abs(up).max()), 2),
        "clipped_samples": int(clipped.sum()),
        "dc_offset": [r(v, 5) for v in x.mean(0)],
        "crest_factor_db": r(20 * np.log10(np.abs(x).max() / np.sqrt((x ** 2).mean())), 1),
        "stereo_correlation": r(np.corrcoef(x[:, 0], x[:, 1])[0, 1], 3),
        "bandwidth_hz_at_-70db": r(freqs[above.max()], 0),
        "leading_silence_s": r(lead),
        "trailing_silence_s": r(tail),
        "last_audible_s": r(last_audible),
        "final_3s_level_drop_db": r(fade[0] - fade[-1], 1) if len(fade) else None,
    }


def key_of(y):
    chroma = librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=1024).mean(1)
    best = None
    for i in range(12):
        for mode, prof in (("major", MAJOR), ("minor", MINOR)):
            c = np.corrcoef(np.roll(prof, i), chroma)[0, 1]
            if best is None or c > best[0]:
                best = (c, f"{NOTE_NAMES[i]} {mode}")
    return best[1], r(best[0], 3)


def music(k):
    y, _ = librosa.load(f"{W}/wav/{k}.wav", sr=SR)
    tempo, beats = librosa.beat.beat_track(y=y, sr=SR, hop_length=HOP)
    bt = librosa.frames_to_time(beats, sr=SR, hop_length=HOP)
    ibi = np.diff(bt)
    key, kconf = key_of(y)
    # beat-synchronous features -> structural segmentation
    chroma = librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=HOP)
    mfcc = librosa.feature.mfcc(y=y, sr=SR, hop_length=HOP, n_mfcc=13)
    feat = librosa.util.sync(np.vstack([librosa.util.normalize(chroma), librosa.util.normalize(mfcc[1:])]), beats)
    nseg = 10
    bounds = librosa.segment.agglomerative(feat, nseg)
    bt_full = np.concatenate([[0.0], bt])
    seg_t = [float(bt_full[min(b, len(bt_full) - 1)]) for b in bounds] + [len(y) / SR]
    rms = librosa.feature.rms(y=y, hop_length=HOP)[0]
    tr = librosa.times_like(rms, sr=SR, hop_length=HOP)
    rdb = 20 * np.log10(rms + 1e-9)
    # chorus candidate: segment whose chroma profile repeats most + high energy
    cs = librosa.util.sync(chroma, beats)
    segs = []
    for i in range(len(seg_t) - 1):
        a, b = seg_t[i], seg_t[i + 1]
        m = (tr >= a) & (tr < b)
        segs.append({"start": r(a), "end": r(b), "mean_db": r(rdb[m].mean(), 1)})
    prof = []
    for s in segs:
        bi = (bt >= s["start"]) & (bt < s["end"])
        prof.append(cs[:, :len(bt)][:, bi[:cs.shape[1]]].mean(1) if bi.any() else np.zeros(12))
    prof = np.array(prof)
    sim = np.corrcoef(prof) if len(prof) > 1 else np.ones((1, 1))
    sim = np.nan_to_num(sim)
    for i, s in enumerate(segs):
        s["repeat_score"] = r((np.sort(sim[i])[-3:-1]).mean(), 3)
    energy_1s = [r(rdb[(tr >= t) & (tr < t + 1)].mean(), 1) for t in range(int(len(y) / SR))]
    onset_env = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
    onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=SR, hop_length=HOP, units="time")
    return {
        "tempo_bpm": r(np.atleast_1d(tempo)[0], 1),
        "beat_interval_std_ms": r(ibi.std() * 1000, 1),
        "key_estimate": key, "key_confidence": kconf,
        "sections": segs,
        "onsets_per_sec": r(len(onsets) / (len(y) / SR)),
        "energy_db_per_second": energy_1s,
    }, bt


def notes_from_f0(midi, voiced):
    """Split voiced runs into notes (stable pitch regions >= 100 ms)."""
    notes, i, n = [], 0, len(midi)
    while i < n:
        if not voiced[i]:
            i += 1
            continue
        j = i
        while j < n and voiced[j]:
            j += 1
        run = midi[i:j]
        s = 0
        for t in range(1, len(run) + 1):
            if t == len(run) or abs(run[t] - np.median(run[s:t])) > 0.7 and t - s >= 1:
                if t - s >= int(0.1 * FPS):
                    notes.append((i + s, i + t))
                s = t
        i = j
    return notes


def vibrato(cents):
    """Return (rate_hz, extent_cents_pp) of the dominant 3-10 Hz modulation, or (None, 0)."""
    c = sps.detrend(cents)
    if len(c) < int(0.35 * FPS):
        return None, 0.0
    f, p = sps.periodogram(c * np.hanning(len(c)), fs=FPS, nfft=1024)
    band = (f >= 3) & (f <= 10)
    if not band.any():
        return None, 0.0
    b, a = sps.butter(2, [3 / (FPS / 2), 10 / (FPS / 2)], btype="band")
    try:
        bp = sps.filtfilt(b, a, c)
    except ValueError:
        return None, 0.0
    extent = 2 * np.sqrt(2) * bp.std()
    share = p[band].sum() / (p[(f > 0.5)].sum() + 1e-12)
    return (float(f[band][np.argmax(p[band])]) if share > 0.35 else None), float(extent)


def vocal(k, bt):
    v, _ = librosa.load(f"{W}/stems/{k}_vocals.wav", sr=SR)
    rms = librosa.feature.rms(y=v, frame_length=2048, hop_length=HOP)[0]
    rdb = 20 * np.log10(rms + 1e-9)
    active = rdb > rdb.max() - 35
    f0, vflag, vprob = librosa.pyin(v, fmin=150, fmax=1400, sr=SR, frame_length=2048, hop_length=HOP)
    n = min(len(f0), len(active))
    f0, vflag, active, rdb = f0[:n], vflag[:n], active[:n], rdb[:n]
    voiced = vflag & active & np.isfinite(f0)
    midi = librosa.hz_to_midi(np.where(voiced, f0, np.nan))
    np.savez_compressed(f"{W}/json/{k}_f0.npz", midi=midi, rdb=rdb)
    t = np.arange(n) / FPS
    vm = midi[voiced]
    tuning = librosa.pitch_tuning(librosa.midi_to_hz(vm)) if len(vm) else 0.0
    # phrases: active regions separated by gaps >= 250 ms
    phrases, i = [], 0
    act = active.copy()
    while i < n:
        if act[i]:
            j = i
            while j < n and (act[j] or (j + int(0.25 * FPS) < n and act[j:j + int(0.25 * FPS)].any())):
                j += 1
            if j - i >= int(0.2 * FPS):
                phrases.append((i, j))
            i = j
        else:
            i += 1
    # notes
    notes = notes_from_f0(np.nan_to_num(midi), voiced)
    note_stats = []
    for a, b in notes:
        seg = midi[a:b]
        med = np.median(seg)
        cents = (seg - med) * 100
        center_dev = ((med - tuning) - np.round(med - tuning)) * 100
        rate, ext = vibrato(cents) if (b - a) >= int(0.35 * FPS) else (None, 0.0)
        head = seg[: max(2, int(0.06 * FPS))].mean()
        hp = cents - sps.medfilt(cents, 5) if len(cents) >= 5 else cents
        note_stats.append({
            "t": a / FPS, "dur": (b - a) / FPS, "midi": med, "center_dev": center_dev,
            "std_cents": float(np.std(sps.detrend(cents))) if len(cents) > 3 else 0.0,
            "within5": float((np.abs(cents) <= 5).mean()), "jitter": float(np.std(hp)),
            "onset_dev": float((head - med) * 100), "vib_rate": rate, "vib_ext": ext,
        })
    long_notes = [s for s in note_stats if s["dur"] >= 0.35]
    sustained = [s for s in note_stats if s["dur"] >= 0.15]
    wsum = sum(s["dur"] for s in sustained) or 1
    # glides: steep continuous pitch motion inside voiced runs
    dm = np.abs(np.diff(midi)) * FPS  # semitones / s
    dm_valid = np.isfinite(dm)
    glide_frac = float((dm[dm_valid] > 20).mean()) if dm_valid.any() else 0.0
    big_jumps = int((np.abs(np.diff(midi))[dm_valid] > 9).sum())
    big_glides = []
    for a, b in phrases:
        seg = midi[a:b]
        fin = np.where(np.isfinite(seg))[0]
        for s0 in range(0, len(fin), max(1, int(0.25 * FPS))):
            win = fin[(fin >= fin[s0]) & (fin < fin[s0] + int(1.2 * FPS))]
            if len(win) > 10:
                vals = seg[win]
                # contiguous monotone-ish sweep
                span = vals.max() - vals.min()
                if span >= 7 and abs(np.corrcoef(np.arange(len(vals)), vals)[0, 1]) > 0.9:
                    big_glides.append((round((a + win[0]) / FPS, 2), round(float(span), 1)))
    dedup = []
    for g in big_glides:
        if not dedup or g[0] - dedup[-1][0] > 0.8:
            dedup.append(g)
    # breaths in gaps between phrases
    S = np.abs(librosa.stft(v, n_fft=2048, hop_length=HOP))[:, :n]
    freqs = librosa.fft_frequencies(sr=SR, n_fft=2048)
    band = (freqs >= 1500) & (freqs <= 8000)
    bdb = 20 * np.log10(S[band].mean(0) + 1e-9)
    floor = np.percentile(bdb, 5)
    flat = librosa.feature.spectral_flatness(S=S)[0][:n]
    breaths, gaps = 0, 0
    for (a0, b0), (a1, _) in zip(phrases[:-1], phrases[1:]):
        g0, g1 = b0, a1
        if g1 - g0 < int(0.12 * FPS):
            continue
        gaps += 1
        seg = (bdb[g0:g1] > floor + 12) & (flat[g0:g1] > 0.05) & ~np.nan_to_num(voiced[g0:g1]).astype(bool)
        if seg.sum() >= int(0.08 * FPS):
            breaths += 1
    # phrase dynamics
    ph_db = [float(np.percentile(rdb[a:b], 90)) for a, b in phrases]
    cen = librosa.feature.spectral_centroid(S=S, sr=SR)[0][:n]
    hf = S[freqs >= 5000].sum(0) / (S.sum(0) + 1e-9)
    # timing vs 16th-note grid
    on = librosa.onset.onset_detect(y=v, sr=SR, hop_length=HOP, units="time", backtrack=False)
    on = on[(on > bt[0]) & (on < bt[-1])]
    devs = []
    for o in on:
        i = np.searchsorted(bt, o) - 1
        if 0 <= i < len(bt) - 1:
            grid = bt[i] + np.arange(5) * (bt[i + 1] - bt[i]) / 4
            devs.append((o - grid[np.argmin(np.abs(grid - o))]) * 1000)
    devs = np.array(devs)
    first_onset = t[np.argmax(active)] if active.any() else None

    def summarize(ns, longs):
        ws = sum(s["dur"] for s in ns) or 1
        vib = [s for s in longs if s["vib_rate"] and s["vib_ext"] >= 20]
        return {
            "notes": len(ns),
            "intonation_mean_abs_cents_dev_from_semitone": r(sum(abs(s["center_dev"]) * s["dur"] for s in ns) / ws, 1),
            "within_note_pitch_std_cents": r(sum(s["std_cents"] * s["dur"] for s in ns) / ws, 1),
            "frac_frames_within_5c_of_note_center": r(sum(s["within5"] * s["dur"] for s in ns) / ws, 3),
            "micro_jitter_cents": r(sum(s["jitter"] * s["dur"] for s in ns) / ws, 1),
            "onset_deviation_cents_median": r(np.median([s["onset_dev"] for s in ns]) if ns else None, 1),
            "long_notes": len(longs),
            "long_notes_with_vibrato_frac": r(len(vib) / len(longs) if longs else 0, 2),
            "vibrato_rate_hz_mean": r(np.mean([s["vib_rate"] for s in vib]) if vib else None, 2),
            "vibrato_extent_cents_pp_mean": r(np.mean([s["vib_ext"] for s in vib]) if vib else None, 1),
        }

    opening = None
    if first_onset is not None:
        o_ns = [s for s in sustained if first_onset <= s["t"] < first_onset + 12]
        o_ln = [s for s in long_notes if first_onset <= s["t"] < first_onset + 12]
        om = midi[int(first_onset * FPS): int((first_onset + 12) * FPS)]
        od = np.abs(np.diff(om)) * FPS
        opening = summarize(o_ns, o_ln)
        opening["glide_frame_frac"] = r((od[np.isfinite(od)] > 20).mean() if np.isfinite(od).any() else 0, 3)
        opening["big_glides_(t,semitones)"] = [g for g in dedup if first_onset <= g[0] < first_onset + 12]
        opening["pitch_range_semitones"] = r(np.nanpercentile(om, 97) - np.nanpercentile(om, 3), 1)
    out = {
        "first_vocal_s": r(first_onset),
        "vocal_active_s": r(active.sum() / FPS, 1),
        "voiced_s": r(voiced.sum() / FPS, 1),
        "tuning_offset_semitones": r(tuning, 3),
        "median_pitch": librosa.midi_to_note(np.nanmedian(vm)) if len(vm) else None,
        "median_pitch_hz": r(librosa.midi_to_hz(np.nanmedian(vm)), 1) if len(vm) else None,
        "range_p5_p95_notes": [librosa.midi_to_note(np.nanpercentile(vm, 5)), librosa.midi_to_note(np.nanpercentile(vm, 95))] if len(vm) else None,
        "range_p5_p95_semitones": r(np.nanpercentile(vm, 95) - np.nanpercentile(vm, 5), 1) if len(vm) else None,
        "phrases": len(phrases),
        "phrase_loudness_std_db": r(np.std(ph_db), 2),
        "phrase_loudness_range_db": r(np.ptp(ph_db), 1) if ph_db else None,
        "breaths_detected": breaths, "inter_phrase_gaps": gaps,
        "breath_rate_per_gap": r(breaths / gaps if gaps else 0, 2),
        "glide_frame_frac_(>20st/s)": r(glide_frac, 3),
        "big_glides_(t,semitones)": dedup,
        "octave_like_jumps": big_jumps,
        "centroid_hz_voiced_median": r(np.median(cen[voiced]), 0) if voiced.any() else None,
        "hf_ratio_5k_plus_voiced_median": r(np.median(hf[voiced]), 3) if voiced.any() else None,
        "timing_dev_ms_median_abs": r(np.median(np.abs(devs)), 1) if len(devs) else None,
        "timing_dev_ms_iqr": r(np.subtract(*np.percentile(devs, [75, 25])), 1) if len(devs) else None,
        "whole_track": summarize(sustained, long_notes),
        "opening_12s": opening,
        "phrase_times": [[r(a / FPS), r(b / FPS)] for a, b in phrases],
    }
    return out, midi, rdb


def overview_png(k, m, midi, rdb, tech):
    y, _ = librosa.load(f"{W}/wav/{k}.wav", sr=SR)
    fig, ax = plt.subplots(3, 1, figsize=(18, 10), sharex=True)
    rms = librosa.feature.rms(y=y, hop_length=HOP)[0]
    tr = librosa.times_like(rms, sr=SR, hop_length=HOP)
    ax[0].plot(tr, 20 * np.log10(rms + 1e-9), lw=0.6, color="0.3", label="mix level (dB)")
    ax[0].plot(np.arange(len(rdb)) / FPS, rdb, lw=0.4, color="tab:blue", alpha=0.6, label="vocal level (dB)")
    for s in m["sections"]:
        ax[0].axvline(s["start"], color="r", lw=0.8, alpha=0.6)
    ax[0].set_ylim(-60, 0); ax[0].legend(loc="lower right")
    ax[0].set_title(f"{k}: {tech['duration_s']}s, {m['tempo_bpm']} BPM, {m['key_estimate']}, {tech['integrated_lufs']} LUFS  (red = section boundaries)")
    ax[1].plot(np.arange(len(midi)) / FPS, midi, lw=0.6)
    ax[1].set_ylabel("vocal MIDI"); ax[1].grid(alpha=0.3)
    S = librosa.amplitude_to_db(np.abs(librosa.stft(y, n_fft=2048, hop_length=1024)), ref=np.max)
    ax[2].imshow(S, origin="lower", aspect="auto", cmap="magma", vmin=-80, vmax=0,
                 extent=[0, len(y) / SR, 0, SR / 2])
    ax[2].set_ylabel("Hz (linear)"); ax[2].set_xlabel("time (s)")
    for a in ax:
        a.xaxis.set_major_locator(plt.MultipleLocator(10))
    plt.tight_layout(); plt.savefig(f"{W}/img/{k}_overview.png", dpi=70)


if __name__ == "__main__":
    k = sys.argv[1]
    tech = technical(k)
    m, bt = music(k)
    v, midi, rdb = vocal(k, bt)
    res = {"track": k, "technical": tech, "music": m, "vocal": v}
    json.dump(res, open(f"{W}/json/{k}.json", "w"), ensure_ascii=False, indent=1)
    overview_png(k, m, midi, rdb, tech)
    print(json.dumps({"track": k, "technical": tech, "music": {kk: vv for kk, vv in m.items() if kk != "energy_db_per_second"},
                      "vocal": {kk: vv for kk, vv in v.items() if kk != "phrase_times"}}, ensure_ascii=False, indent=1))
