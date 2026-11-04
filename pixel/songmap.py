"""The song's own rhythm, measured from the master (audio/t2_optimized_full.mp3), for the chart (pixel/stream.py).

librosa: harmonic / percussive split; on the percussive part, onset strength in a low band (kick, < 150 Hz) and a
high band (snare / clap / hats, > 1.5 kHz); on the harmonic part, onsets of the vocal band (300 Hz - 3 kHz). Each
onset is snapped to the song's sixteenth grid (stream.beat_t) and stored with its strength per band; RMS energy per
bar gives the section intensity. Written to data/songmap.json (deterministic; the chart reads only that file).

usage: python3 songmap.py
"""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent


def build():
    import librosa
    import stream as st
    y, sr = librosa.load(str(st.AUDIO), sr=22050, mono=True)
    yh, yp = librosa.effects.hpss(y)
    hop = 256
    S = np.abs(librosa.stft(yp, n_fft=1024, hop_length=hop))
    f = librosa.fft_frequencies(sr=sr, n_fft=1024)
    lo = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S[f < 150]), sr=sr, hop_length=hop)
    hi = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S[f > 1500]), sr=sr, hop_length=hop)
    Sh = np.abs(librosa.stft(yh, n_fft=1024, hop_length=hop))
    vo = librosa.onset.onset_strength(S=librosa.amplitude_to_db(Sh[(f > 300) & (f < 3000)]), sr=sr, hop_length=hop)
    times = librosa.times_like(lo, sr=sr, hop_length=hop)
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    # the song's own beats (the fixed-tempo grid in stream.py drifts by up to 0.2 s against the master): librosa beat
    # tracker on the percussive part, sixteenths interpolated between consecutive beats
    tempo, beats = librosa.beat.beat_track(y=yp, sr=sr, units="time", start_bpm=136, tightness=200)
    beats = np.asarray(beats)
    q = st.BEAT / 4
    sixteenths = []
    for b0, b1 in zip(beats, beats[1:]):
        sixteenths += [b0 + (b1 - b0) * j / 4 for j in range(4)]
    grid = []
    for k, t in enumerate(sixteenths):
        w = (times > t - q * 0.45) & (times < t + q * 0.45)
        if not w.any():
            continue
        grid.append(dict(t=round(float(t), 4), k=k, beat=k // 4, lo=float(lo[w].max()), hi=float(hi[w].max()),
                         vo=float(vo[w].max()), rms=float(rms[w].mean())))
    # normalise each band by its 95th percentile so thresholds are song-relative
    for key in ("lo", "hi", "vo", "rms"):
        p = np.percentile([g[key] for g in grid], 95) or 1.0
        for g in grid:
            g[key] = round(min(2.0, g[key] / p), 3)
    out = ROOT / "data/songmap.json"
    out.write_text(json.dumps(grid))
    return out


if __name__ == "__main__":
    print(build())
