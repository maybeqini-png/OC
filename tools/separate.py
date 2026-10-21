"""MDX-Net vocal separation (UVR ONNX models) without torch.

usage: separate.py <model.onnx> <compensate> <in.wav> <out_vocals.wav> <out_inst.wav>
"""
import sys
import numpy as np
import librosa
import onnxruntime as ort
import soundfile as sf

N_FFT, HOP, DIM_F, DIM_T = 7680, 1024, 3072, 256
N_BINS = N_FFT // 2 + 1
CHUNK = HOP * (DIM_T - 1)
TRIM = N_FFT // 2
GEN = CHUNK - 2 * TRIM


def stft(chunk):  # chunk: [2, CHUNK] -> [1, 4, DIM_F, DIM_T]
    specs = []
    for ch in chunk:
        s = librosa.stft(ch, n_fft=N_FFT, hop_length=HOP, window="hann", center=True, pad_mode="reflect")
        specs += [s.real, s.imag]
    return np.stack(specs)[None, :, :DIM_F, :].astype(np.float32)


def istft(spec):  # [1, 4, DIM_F, DIM_T] -> [2, CHUNK]
    full = np.zeros((4, N_BINS, DIM_T), np.float32)
    full[:, :DIM_F] = spec[0]
    out = []
    for c in range(2):
        z = full[2 * c] + 1j * full[2 * c + 1]
        out.append(librosa.istft(z, hop_length=HOP, window="hann", center=True, length=CHUNK))
    return np.stack(out)


def main(model, comp, src, dst_v, dst_i):
    mix, sr = sf.read(src, always_2d=True)
    assert sr == 44100, sr
    mix = mix.T.astype(np.float32)
    n = mix.shape[1]
    pad = GEN - n % GEN
    padded = np.concatenate([np.zeros((2, TRIM), np.float32), mix, np.zeros((2, pad + TRIM), np.float32)], 1)
    sess = ort.InferenceSession(model, providers=["CPUExecutionProvider"])
    name = sess.get_inputs()[0].name
    outs = []
    for i in range(0, n + pad, GEN):
        spec = stft(padded[:, i:i + CHUNK])
        # UVR "denoise" trick: average model(spec) and -model(-spec)
        pred = 0.5 * (sess.run(None, {name: spec})[0] - sess.run(None, {name: -spec})[0])
        outs.append(istft(pred)[:, TRIM:-TRIM])
    voc = np.concatenate(outs, 1)[:, :n] * float(comp)
    sf.write(dst_v, voc.T, sr, subtype="FLOAT")
    sf.write(dst_i, (mix - voc).T, sr, subtype="FLOAT")
    print(src, "->", dst_v, f"chunks={len(outs)}")


if __name__ == "__main__":
    main(*sys.argv[1:6])
