"""Transcribe the separated vocal with two Japanese-capable ASR models and score
intelligibility against the lyric sheet (character error rate on hiragana).

usage: asr.py <track> [lyrics_from_track]
"""
import json
import re
import sys

import librosa
import numpy as np
import pykakasi
import sherpa_onnx

W = "/tmp/claude-0/-home-user/79528b42-f6d5-55a7-a812-a65ac1a1835e/scratchpad/oc_audio"
M = "/tmp/claude-0/-home-user/79528b42-f6d5-55a7-a812-a65ac1a1835e/scratchpad/models"
KKS = pykakasi.kakasi()


def hira(s):
    s = re.sub(r"[♪\s、。！？!?,.・〜~ー…「」『』()（）]", "", s)
    return "".join(x["hira"] for x in KKS.convert(s))


def lyric_lines(src):
    blocks = open(f"{W}/srt/{src}.srt").read().strip().split("\n\n")
    lines = []
    for i, b in enumerate(blocks):
        rows = b.split("\n")
        start = rows[1].split(" --> ")[0]
        h, m, s = start.replace(",", ".").split(":")
        t = int(h) * 3600 + int(m) * 60 + float(s)
        text = [x.replace("♪", "").strip() for x in rows[2:]]
        cur = text[0] if i == 0 else (text[1] if len(text) >= 2 else text[-1])
        lines.append({"i": i + 1, "t_sheet": t, "text": cur})
    return lines


def recognizers():
    wd = f"{M}/sherpa-onnx-whisper-small"
    whisper = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=f"{wd}/small-encoder.int8.onnx", decoder=f"{wd}/small-decoder.int8.onnx",
        tokens=f"{wd}/small-tokens.txt", language="ja", task="transcribe", num_threads=4)
    rd = f"{M}/sherpa-onnx-zipformer-ja-reazonspeech-2024-08-01"
    reazon = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=f"{rd}/encoder-epoch-99-avg-1.int8.onnx", decoder=f"{rd}/decoder-epoch-99-avg-1.int8.onnx",
        joiner=f"{rd}/joiner-epoch-99-avg-1.int8.onnx", tokens=f"{rd}/tokens.txt", num_threads=4,
        sample_rate=16000, feature_dim=80, decoding_method="greedy_search")
    return {"whisper_small": whisper, "reazonspeech": reazon}


def run(rec, audio):
    st = rec.create_stream()
    st.accept_waveform(16000, audio)
    rec.decode_stream(st)
    return st.result.text.strip()


def align(hyp, ref):
    """Levenshtein alignment; returns per-ref-char error flags (sub/del) and insertion counts."""
    n, m = len(ref), len(hyp)
    D = np.zeros((n + 1, m + 1), np.int32)
    D[:, 0] = np.arange(n + 1)
    D[0, :] = np.arange(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i, j] = min(D[i - 1, j] + 1, D[i, j - 1] + 1, D[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]))
    err = np.zeros(n, int)
    ins = np.zeros(n + 1, int)
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and D[i, j] == D[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]):
            err[i - 1] = ref[i - 1] != hyp[j - 1]
            i, j = i - 1, j - 1
        elif i > 0 and D[i, j] == D[i - 1, j] + 1:
            err[i - 1] = 1
            i -= 1
        else:
            ins[i] += 1
            j -= 1
    return err, ins, int(D[n, m])


def main(k, lyr_src):
    d = json.load(open(f"{W}/json/{k}.json"))
    y, _ = librosa.load(f"{W}/stems/{k}_vocals.wav", sr=16000)
    # chunk phrases into <= 20 s windows
    chunks, cur = [], None
    for a, b in d["vocal"]["phrase_times"]:
        if cur and b - cur[0] <= 20 and a - cur[1] < 1.5:
            cur[1] = b
        else:
            if cur:
                chunks.append(cur)
            cur = [a, b]
    if cur:
        chunks.append(cur)
    recs = recognizers()
    out = {"track": k, "chunks": []}
    for a, b in chunks:
        seg = y[int(max(0, a - 0.15) * 16000): int((b + 0.15) * 16000)].astype(np.float32)
        row = {"start": a, "end": b, "whisper_small": run(recs["whisper_small"], seg)}
        # ReazonSpeech drops words on long inputs: decode each phrase (<= 8 s pieces) separately
        parts = []
        for pa, pb in d["vocal"]["phrase_times"]:
            if pa >= a - 0.01 and pb <= b + 0.01:
                for s0 in np.arange(pa, pb, 8.0):
                    s1 = min(pb, s0 + 8.0)
                    parts.append(run(recs["reazonspeech"], y[int(max(0, s0 - 0.15) * 16000): int((s1 + 0.15) * 16000)].astype(np.float32)))
        row["reazonspeech"] = "".join(parts)
        out["chunks"].append(row)
    if lyr_src:
        lines = lyric_lines(lyr_src)
        ref = "".join(hira(l["text"]) for l in lines)
        bounds = np.cumsum([0] + [len(hira(l["text"])) for l in lines])
        out["lyric_lines"] = []
        for name in recs:
            hyp = hira("".join(c[name] for c in out["chunks"]))
            err, ins, dist = align(hyp, ref)
            out[f"{name}_overall_cer"] = round(dist / len(ref), 3)
            for li, l in enumerate(lines):
                a, b = bounds[li], bounds[li + 1]
                e = int(err[a:b].sum() + ins[a + 1:b + 1].sum())
                if name == "whisper_small":
                    out["lyric_lines"].append({"i": l["i"], "text": l["text"], "len": int(b - a)})
                out["lyric_lines"][li][f"{name}_cer"] = round(e / max(1, b - a), 2)
        # opening line: transcribe just the first ~6 s after first vocal with both models
    fv = d["vocal"]["first_vocal_s"] or 0
    seg = y[int(max(0, fv - 0.2) * 16000): int((fv + 6.0) * 16000)].astype(np.float32)
    out["opening_6s"] = {n: run(rv, seg) for n, rv in recs.items()}
    json.dump(out, open(f"{W}/json/{k}_asr.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps({kk: vv for kk, vv in out.items() if kk not in ("chunks", "lyric_lines")}, ensure_ascii=False, indent=1))
    for c in out["chunks"][:4]:
        print(c)
    for l in out.get("lyric_lines", [])[:6]:
        print(l)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
