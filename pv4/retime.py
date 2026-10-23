"""Re-time the lyrics to the sung vocal: every mora is placed on a detected note onset of the separated vocal.

usage: retime.py <vocals.wav> <reazonspeech_model_dir> <out.json>

Why: pv3/lyrics_timed.json interpolated between the few kana the ASR recognised, so whole phrases drifted
(強 72.70 -> が 74.18). Here the sung notes themselves are the time base:
1. note onsets on the vocal stem = energy onsets (spectral flux) + pitch steps (pyin f0 moving >= 0.8 semitone and
   holding >= 70 ms) + voicing starts, merged within 45 ms;
2. per line, morae (from the kana reading) are aligned to onsets with dynamic programming: each mora takes the
   next onset, ー / ん / っ / small vowels may share the previous note, spare onsets may be skipped; ASR token times
   (ReazonSpeech, sherpa-onnx) are soft anchors (cost grows with distance), never interpolated;
3. a char's time = its first mora; a phrase's time = its first char. Confidence per line = share of morae with an
   ASR anchor within 120 ms of the chosen onset.
"""
import json
import sys
from pathlib import Path

import librosa
import numpy as np
import pykakasi

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pv3"))
from render import LYRICS  # noqa: E402  (line text + rough windows)

SR, HOP = 22050, 256
SMALL = set("ゃゅょぁぃぅぇぉゎャュョァィゥェォヮ")
SHARE = set("ーんっンッ")  # morae that are often sung on the previous note
KKS = pykakasi.kakasi()


def kana_of(text):
    return "".join(i["hira"] for i in KKS.convert(text))


def morae_with_chars(text):
    """[(mora_kana, char_index)] for the display text (kanji compounds spread their reading over their chars)."""
    out = []
    pos = 0
    for item in KKS.convert(text):
        orig, hira = item["orig"], item["hira"]
        if not orig:
            continue
        ms = []
        for ch in hira:
            if ch in SMALL and ms:
                ms[-1] += ch
            elif ch.strip() and ch not in "　 ":
                ms.append(ch)
        n = len(orig)
        for k, m in enumerate(ms):
            out.append((m, pos + min(int(k * n / max(len(ms), 1)), n - 1)))
        pos += n
    return out


def onsets(y):
    flux = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
    on_e = librosa.onset.onset_detect(onset_envelope=flux, sr=SR, hop_length=HOP, backtrack=True, units="time",
                                      delta=0.06)
    f0, vflag, _ = librosa.pyin(y, fmin=150, fmax=1100, sr=SR, hop_length=HOP, frame_length=2048)
    t = librosa.times_like(f0, sr=SR, hop_length=HOP)
    st = 12 * np.log2(np.where(vflag, f0, np.nan) / 440.0)
    on_p, hold = [], int(0.07 * SR / HOP)
    k = 1
    while k < len(st) - hold:
        a, b = st[k - 1], np.nanmedian(st[k:k + hold])
        if np.isfinite(a) and np.isfinite(b) and abs(b - a) >= 0.8 and np.all(np.isfinite(st[k:k + hold])):
            on_p.append(t[k])
            k += hold
        else:
            k += 1
    on_v = [t[k] for k in range(1, len(vflag)) if vflag[k] and not vflag[k - 1]]
    allt = np.sort(np.concatenate([on_e, on_p, on_v]))
    merged = []
    for x in allt:
        if not merged or x - merged[-1] > 0.045:
            merged.append(float(x))
    strength = np.interp(merged, librosa.times_like(flux, sr=SR, hop_length=HOP), flux / (flux.max() + 1e-9))
    return np.array(merged), strength, (t, vflag)


def asr_anchors(rec, y16, t0):
    st = rec.create_stream()
    st.accept_waveform(16000, y16)
    rec.decode_stream(st)
    out = []
    for tok, ts in zip(st.result.tokens, st.result.timestamps):
        for ch in kana_of(tok):
            if ch.strip() and ch not in SMALL:
                out.append((ch, t0 + float(ts)))
    return out


def align(morae, ons, strength, anchors, start_prior, grid):
    """DP: morae i -> onset index (non-decreasing; equal only for SHARE morae)."""
    n, m = len(morae), len(ons)
    gdist = np.array([np.min(np.abs(grid - o)) if len(grid) else 0.0 for o in ons])
    INF = 1e9
    # anchor time per mora: first unmatched ASR kana equal to the mora's first char, in order
    at = [None] * n
    j = 0
    for i, (k, _) in enumerate(morae):
        for jj in range(j, min(j + 6, len(anchors))):
            if anchors[jj][0] == k[0]:
                at[i], j = anchors[jj][1], jj + 1
                break
    cost = np.full((n, m), INF)
    back = np.zeros((n, m), int)

    def local(i, jj):
        c = 0.35 * (1 - strength[jj]) + min(gdist[jj] / 0.04, 2.0) * 0.4
        if at[i] is not None:
            c += min(abs(ons[jj] - at[i]) / 0.12, 6.0)
        return c

    for jj in range(m):
        # the line starts near its known start (README / pv3 windows, checked by ear earlier), not on a breath
        cost[0, jj] = local(0, jj) + min(abs(ons[jj] - start_prior) / 0.25, 8.0)
    for i in range(1, n):
        share = morae[i][0][0] in SHARE
        best, arg = INF, -1
        for jj in range(m):
            # previous onset strictly earlier (new note), or the same onset when this mora may share it
            if jj > 0 and cost[i - 1, jj - 1] < best:
                best, arg = cost[i - 1, jj - 1], jj - 1
            cand = []
            if best < INF:
                gap_ok = ons[jj] - ons[arg] >= 0.06
                cand.append((best + local(i, jj) + (0 if gap_ok else 2.0) + 0.12 * max(0, jj - arg - 1), arg))
            if share and cost[i - 1, jj] < INF:
                cand.append((cost[i - 1, jj] + 0.25, jj))
            if cand:
                c, a = min(cand)
                cost[i, jj], back[i, jj] = c, a
        # allow skipping onsets between notes: already covered by best over all earlier jj (running minimum)
    if not np.isfinite(cost[-1]).any() or cost[-1].min() >= INF:
        return None, 0.0
    jj = int(np.argmin(cost[-1]))
    path = [jj]
    for i in range(n - 1, 0, -1):
        jj = back[i, jj]
        path.append(jj)
    path = path[::-1]
    conf = np.mean([at[i] is not None and abs(ons[p] - at[i]) < 0.12 for i, p in enumerate(path)])
    return [float(ons[p]) for p in path], float(conf)


def main():
    import sherpa_onnx
    voc, mdir, out = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    y, _ = librosa.load(voc, sr=SR, mono=True)
    y16 = librosa.resample(y, orig_sr=SR, target_sr=16000)
    ons, strength, (vt, vflag) = onsets(y)
    beats = np.array(json.load(open(Path(__file__).resolve().parent.parent / "pv/assets/timing.json"))["beats"])
    grid = np.concatenate([np.linspace(b0, b1, 4, endpoint=False) for b0, b1 in zip(beats[:-1], beats[1:])])
    voiced_at = lambda t: bool(vflag[min(int(np.searchsorted(vt, t)), len(vflag) - 1)])
    rec = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=str(mdir / "encoder-epoch-99-avg-1.int8.onnx"), decoder=str(mdir / "decoder-epoch-99-avg-1.int8.onnx"),
        joiner=str(mdir / "joiner-epoch-99-avg-1.int8.onnx"), tokens=str(mdir / "tokens.txt"), num_threads=4,
        sample_rate=16000, feature_dim=80, decoding_method="greedy_search")
    res = []
    for k, (a, b, text) in enumerate(LYRICS):
        nxt = LYRICS[k + 1][0] if k + 1 < len(LYRICS) else b + 1
        w0, w1 = max(a - 0.6, 0), min(b + 0.4, nxt + 0.2)
        sel = (ons >= w0) & (ons <= w1)
        o, s = ons[sel], strength[sel]
        # 16th-grid points inside voiced audio are extra (weak) candidates for legato notes the detector missed
        g = grid[(grid >= w0) & (grid <= w1)]
        g = np.array([x for x in g if voiced_at(x) and (len(o) == 0 or np.min(np.abs(o - x)) > 0.05)])
        if len(g):
            o = np.concatenate([o, g])
            s = np.concatenate([s, np.full(len(g), 0.05)])
            order = np.argsort(o)
            o, s = o[order], s[order]
        flat = text.replace("　", "")
        mor = morae_with_chars(flat)
        anchors = asr_anchors(rec, y16[int(w0 * 16000):int(w1 * 16000)], w0)
        times, conf = (None, 0.0) if len(o) < 2 else align(mor, o, s, anchors, a, grid)
        if times is None:
            times, conf = list(np.linspace(a, b - 0.3, len(mor))), 0.0
        chars = [None] * len(flat)
        for (m_, ci), tt in zip(mor, times):
            if chars[ci] is None:
                chars[ci] = round(tt, 3)
        for ci in range(len(chars)):  # chars without a mora of their own (punctuation) take the previous time
            if chars[ci] is None:
                chars[ci] = chars[ci - 1] if ci else round(times[0], 3)
        phrases, i = [], 0
        for ph in text.split("　"):
            phrases.append({"text": ph, "t": chars[i], "chars": chars[i:i + len(ph)]})
            i += len(ph)
        res.append({"line": text, "start": phrases[0]["t"], "end": round(times[-1] + 0.35, 3), "phrases": phrases,
                    "morae": len(mor), "onsets_in_window": int(sel.sum()), "asr_conf": round(conf, 2)})
        print(f"{phrases[0]['t']:7.2f}  conf {conf:.2f}  " + " | ".join(f"{p['t']:.2f} {p['text']}" for p in phrases),
              flush=True)
    json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
