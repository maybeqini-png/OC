"""Time every lyric character to the sung vocal, so text and cuts land when she actually sings.

usage: lyric_timing.py <vocal_stem.wav> <out.json>

For each lyric line (rough start/end known), vocal note onsets are detected on the separated vocal stem and
the line's morae are mapped onto them in order (1 mora per sung note; when the counts differ, morae are spread
along the onset sequence). Each display character gets the time of its first mora; phrases (split at the
full-width space) get the time of their first character. Output: [{line, start, end, phrases:[{text, t,
chars:[t...]}]}].
"""
import json
import sys

import librosa
import numpy as np
import pykakasi

from render import LYRICS

SMALL = set("ゃゅょぁぃぅぇぉゎャュョァィゥェォヮ")


def morae(hira):
    return sum(1 for ch in hira if ch not in SMALL and ch not in "　 ")


def char_morae(text, kks):
    """Mora count per display character (kanji compounds share their reading's morae)."""
    out = []
    for item in kks.convert(text):
        orig, hira = item["orig"], item["hira"]
        if not orig:
            continue
        m = morae(hira)
        n = len(orig)
        if orig.strip() == "":
            out += [0] * n
            continue
        base = [m // n] * n
        for i in range(m - sum(base)):
            base[i] += 1
        out += [max(b, 1 if c not in SMALL else 0) for b, c in zip(base, orig)]
    return out


def hira_of(text, kks):
    return "".join(i["hira"] for i in kks.convert(text))


def asr_kana_times(rec, audio, t0, kks):
    """ReazonSpeech token timestamps -> list of (kana, time)."""
    st = rec.create_stream()
    st.accept_waveform(16000, audio)
    rec.decode_stream(st)
    out = []
    for tok, ts in zip(st.result.tokens, st.result.timestamps):
        for k in hira_of(tok, kks):
            if k not in SMALL and k.strip():
                # the first emitted token is stamped at the window start, not where it is sung
                out.append((k, t0 + float(ts) if ts > 0.05 else float("nan")))
    return out


def main():
    import difflib
    import sherpa_onnx
    M = "/tmp/claude-0/-home-user/79528b42-f6d5-55a7-a812-a65ac1a1835e/scratchpad/models/sherpa-onnx-zipformer-ja-reazonspeech-2024-08-01"
    rec = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=f"{M}/encoder-epoch-99-avg-1.int8.onnx", decoder=f"{M}/decoder-epoch-99-avg-1.int8.onnx",
        joiner=f"{M}/joiner-epoch-99-avg-1.int8.onnx", tokens=f"{M}/tokens.txt", num_threads=4,
        sample_rate=16000, feature_dim=80, decoding_method="greedy_search")
    y, _ = librosa.load(sys.argv[1], sr=16000)
    rms = librosa.feature.rms(y=y, frame_length=800, hop_length=160)[0]
    rt = np.arange(len(rms)) * 0.01
    voiced = rms > np.percentile(rms, 60)
    kks = pykakasi.kakasi()
    out = []
    for a, b, text in LYRICS:
        w0, w1 = max(a - 0.5, 0), b + 0.4
        asr = asr_kana_times(rec, y[int(w0 * 16000):int(w1 * 16000)], w0, kks)
        cm = char_morae(text, kks)
        kana = [k for k in hira_of(text.replace("　", ""), kks) if k not in SMALL and k.strip()]
        n = len(kana)
        times = np.full(n, np.nan)
        sm = difflib.SequenceMatcher(a=kana, b=[k for k, _ in asr], autojunk=False)
        for blk in sm.get_matching_blocks():
            for j in range(blk.size):
                times[blk.a + j] = asr[blk.b + j][1]
        times[times < a - 0.3] = np.nan
        # anchor the ends on voiced audio, then fill gaps monotonically
        vz = rt[(rt >= a - 0.3) & (rt <= b + 0.2) & voiced[:len(rt)]]
        v0, v1 = (vz[0], vz[-1]) if len(vz) else (a, b)
        if np.isnan(times[0]):
            times[0] = v0
        if np.isnan(times[-1]):
            times[-1] = max(v1 - 0.25, times[0] + 0.1 * n)
        idx = np.arange(n)
        ok = ~np.isnan(times)
        times = np.interp(idx, idx[ok], times[ok])
        times = np.maximum.accumulate(times)
        chars, k = [], 0
        for c, m in zip(text, cm):
            chars.append(round(float(times[min(k, n - 1)]), 3))
            k += m
        phrases, i = [], 0
        for ph in text.split("　"):
            phrases.append({"text": ph, "t": chars[i], "chars": chars[i:i + len(ph)]})
            i += len(ph) + 1
        out.append({"line": text, "start": phrases[0]["t"], "end": b, "phrases": phrases,
                    "matched": int(ok.sum()), "n_kana": n})
    json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
    for l in out:
        print(f'{l["start"]:7.2f} {l["matched"]:3d}/{l["n_kana"]:3d}  ' + " | ".join(f'{p["t"]:.2f} {p["text"]}' for p in l["phrases"]))


if __name__ == "__main__":
    main()
