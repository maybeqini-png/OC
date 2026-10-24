"""Mora-level lyric timing from the separated vocal (replaces the per-character part of pv4/retime.py, whose
interpolation put e.g. よ at 68.46 and そ at 69.80).

usage: syllables.py <vocals.wav> <out.json> [t0 t1]
Phrase onsets are fixed (PHRASES below: checked on the vocal spectrogram; SFX-anchored ones from README).
Inside each phrase, the morae are placed on sung-note boundaries:
- candidates: loudness dips (>= 2 dB below both neighbours within 70 ms), consonant bursts (3-8 kHz flux peaks),
  pitch steps (>= 0.8 semitone, stable 40 ms on both sides); strength = sum of normalised cues;
- dynamic programming picks n-1 boundaries in order, maximising strength minus a rhythm cost: note lengths
  close to multiples of a 16th note (local beat / 4) are preferred, notes shorter than 70 ms are not allowed;
- the phrase's last mora ends where the voice ends (loudness falls below the phrase median - 18 dB).
Output: [{line, phrases:[{text, t, morae:[{kana, t, end}], chars:[t]}]}]
"""
import json
import sys
from pathlib import Path

import librosa
import numpy as np
import pykakasi

HERE = Path(__file__).resolve().parent
SR, HOP = 22050, 128
SMALL = set("ゃゅょぁぃぅぇぉゎャュョァィゥェォヮ")
KKS = pykakasi.kakasi()

# (line text with full-width spaces, [phrase onsets in s]) - only the lines currently in production
PHRASES = [
    ("笑ったでしょ　めっ　もういっかい", [64.40, 66.72, 67.05]),
    ("よそ見しないで　見ててよね", [68.50, 71.20]),
    ("強がりだって　本気だもん", [72.62, 75.55]),
    ("この声で　キメちゃうよ", [76.50, 79.30]),
]

# Mora times checked by eye on the vocal spectrogram + pitch + loudness, and against ReazonSpeech token times, where
# the automatic placement was implausible (2026-10-23). Keys: (line index, phrase index) -> mora onsets.
OVERRIDES = {
    (0, 0): [64.40, 64.92, 65.13, 65.18, 65.98, 66.34],       # わ ら っ た で しょ (っ = the stop at 65.13)
    (0, 2): [67.05, 67.30, 67.50, 67.62, 67.69, 67.96],       # も う い っ か い (held い to 68.45)
    (1, 1): [71.20, 71.50, 72.17, 72.30, 72.42],              # み て | て よ ね (breath gap 71.8-72.15)
    (2, 0): [72.62, 73.03, 74.15, 74.39, 74.62, 74.73, 74.85],  # つ よ が り だ っ て
    (3, 0): [76.50, 76.71, 77.36, 77.65, 78.35],              # こ の こ え で (で held 78.35-79.2)
    (3, 1): [79.30, 80.08, 80.68, 80.85, 81.22],              # キ メ ちゃ う よ (よ held to 83.0)
}
END_OVERRIDES = {(3, 1): 83.02}


def morae_of(text):
    """[(kana, char_index)] with small kana joined to the previous mora; kanji spread their reading."""
    out, pos = [], 0
    for item in KKS.convert(text):
        orig, hira = item["orig"], item["hira"]
        if not orig:
            continue
        ms = []
        for ch in hira:
            if ch in SMALL and ms:
                ms[-1] += ch
            elif ch.strip():
                ms.append(ch)
        n = len(orig)
        for k, m in enumerate(ms):
            out.append((m, pos + min(int(k * n / max(len(ms), 1)), n - 1)))
        pos += n
    return out


def features(y):
    S = np.abs(librosa.stft(y, n_fft=1024, hop_length=HOP))
    t = librosa.frames_to_time(np.arange(S.shape[1]), sr=SR, hop_length=HOP)
    rms = np.sqrt((S ** 2).mean(axis=0))
    db = 20 * np.log10(rms + 1e-6)
    db = np.convolve(db, np.ones(3) / 3, mode="same")
    freqs = librosa.fft_frequencies(sr=SR, n_fft=1024)
    hb = S[(freqs > 3000) & (freqs < 8000)]
    flux = np.maximum(np.diff(np.log1p(hb), axis=1, prepend=np.log1p(hb[:, :1])), 0).sum(axis=0)
    f0, vf, _ = librosa.pyin(y, fmin=170, fmax=1050, sr=SR, hop_length=HOP, frame_length=2048)
    st = 12 * np.log2(np.where(vf, f0, np.nan) / 440)
    return t, db, flux, st


def candidates(t, db, flux, st, a, b):
    sel = np.where((t >= a) & (t <= b))[0]
    w = int(0.07 * SR / HOP)
    cand = {}
    fl = flux / (np.percentile(flux[sel], 95) + 1e-6)
    for i in sel[w:-w] if len(sel) > 2 * w else []:
        left, right = db[i - w:i].max(), db[i + 1:i + w + 1].max()
        dip = min(left, right) - db[i]
        s = 0.0
        if dip > 2.0 and db[i] == db[i - w:i + w + 1].min():
            s += min(dip / 8, 1.5)
        if fl[i] > 0.6 and fl[i] == fl[max(i - 3, 0):i + 4].max():
            s += min(fl[i], 1.5) * 0.8
        k = int(0.04 * SR / HOP)
        if i - k >= 0 and i + k < len(st):
            l_, r_ = np.nanmedian(st[i - k:i]), np.nanmedian(st[i:i + k])
            if np.isfinite(l_) and np.isfinite(r_) and abs(r_ - l_) >= 0.8:
                s += min(abs(r_ - l_) / 3, 1.0)
        if s > 0:
            cand[i] = s
    # merge candidates closer than 45 ms (keep the strongest)
    idx = sorted(cand)
    merged = []
    for i in idx:
        if merged and t[i] - t[merged[-1]] < 0.045:
            if cand[i] > cand[merged[-1]]:
                merged[-1] = i
        else:
            merged.append(i)
    return [(float(t[i]), cand[i]) for i in merged]


def place(n, start, end, cands, sixteenth):
    """Choose n-1 boundaries among cands (ordered) between start and end."""
    if n == 1:
        return [start]
    pts = [(start, 0.0)] + [c for c in cands if start + 0.07 <= c[0] <= end - 0.07]
    m = len(pts)
    INF = 1e9

    def rhythm(d):
        q = d / sixteenth
        return 0.6 * abs(q - round(q)) * (1 if q >= 0.8 else 3)

    cost = np.full((n, m), INF)
    back = np.zeros((n, m), int)
    cost[0, 0] = 0.0
    for k in range(1, n):
        for j in range(1, m):
            best, arg = INF, -1
            for i in range(j):
                if cost[k - 1, i] >= INF:
                    continue
                d = pts[j][0] - pts[i][0]
                if d < 0.07:
                    continue
                c = cost[k - 1, i] + rhythm(d) - pts[j][1]
                if c < best:
                    best, arg = c, i
            if arg >= 0:
                cost[k, j], back[k, j] = best, arg
    # the last note must fit before the end
    fin = [cost[n - 1, j] + rhythm(end - pts[j][0]) if end - pts[j][0] >= 0.07 else INF for j in range(m)]
    j = int(np.argmin(fin))
    if fin[j] >= INF:  # not enough candidates: spread evenly on the 16th grid
        step = max((end - start) / n, 0.07)
        return [start + k * step for k in range(n)]
    out = [j]
    for k in range(n - 1, 0, -1):
        j = back[k, j]
        out.append(j)
    return [pts[i][0] for i in out[::-1]]


def main():
    voc, out_path = sys.argv[1], sys.argv[2]
    t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 60.0
    t1 = float(sys.argv[4]) if len(sys.argv) > 4 else 90.0
    y, _ = librosa.load(voc, sr=SR, mono=True, offset=t0, duration=t1 - t0)
    t, db, flux, st = features(y)
    t = t + t0
    beats = np.array(json.load(open(HERE.parent / "pv/assets/timing.json"))["beats"])
    res = []
    for li, (line, onsets) in enumerate(PHRASES):
        texts = line.split("　")
        nxt_line = PHRASES[li + 1][1][0] if li + 1 < len(PHRASES) else onsets[-1] + 6
        phrases = []
        for k, (txt, on) in enumerate(zip(texts, onsets)):
            nxt = onsets[k + 1] if k + 1 < len(onsets) else nxt_line
            sel = (t >= on) & (t < nxt)
            med = np.median(db[sel])
            voiced = np.where(sel & (db > med - 18))[0]
            end = float(t[voiced[-1]]) if len(voiced) else nxt - 0.05
            end = min(end + 0.03, nxt - 0.02)
            bi = np.searchsorted(beats, on)
            beat = float(np.median(np.diff(beats[max(bi - 4, 0):bi + 4])))
            end = END_OVERRIDES.get((li, k), end)
            mor = morae_of(txt)
            if (li, k) in OVERRIDES:
                ts = OVERRIDES[(li, k)]
                assert len(ts) == len(mor), (txt, len(mor), len(ts))
            else:
                cands = candidates(t, db, flux, st, on, end)
                ts = place(len(mor), on, end, cands, beat / 4)
            ends = ts[1:] + [end]
            chars = [None] * len(txt)
            for (kana, ci), tt in zip(mor, ts):
                if chars[ci] is None:
                    chars[ci] = round(tt, 3)
            for ci in range(len(chars)):
                if chars[ci] is None:
                    chars[ci] = chars[ci - 1]
            phrases.append({"text": txt, "t": round(on, 3), "end": round(end, 3), "chars": chars,
                            "morae": [{"kana": m[0], "t": round(a, 3), "end": round(b, 3)} for m, a, b in zip(mor, ts, ends)]})
        res.append({"line": line, "start": phrases[0]["t"], "end": phrases[-1]["end"], "phrases": phrases})
        for p in phrases:
            print(f'{p["t"]:7.2f}-{p["end"]:6.2f} ' + " ".join(f'{m["kana"]}{m["t"]:.2f}' for m in p["morae"]))
    json.dump(res, open(out_path, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
