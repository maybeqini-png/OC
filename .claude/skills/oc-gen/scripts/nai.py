"""NovelAI image generation / inpainting for the OC PV.

Auth is injected by the environment proxy (network secret for *.novelai.net) - never add keys here.

usage:
  nai.py balance
  nai.py generate --model M --prompt P [--negative N] [--w 1024 --h 1024 --seed S --steps 28 --scale 5] --out file.png
  nai.py img2img  --model M --image in.png --prompt P [--strength 0.5] --out file.png
  nai.py infill   --model M --image in.png --mask mask.png --prompt P [--negative N] [--seed S --strength 1.0] --out file.png
Every successful call appends a record (model, prompt, seed, Anlas before/after) to the manifest next to the output.
"""
import argparse
import base64
import io
import json
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

BASE = "https://image.novelai.net"
DEFAULT_NEG = "lowres, bad anatomy, bad hands, text, watermark, signature, jpeg artifacts, multiple views, extra ears, human ears"


def call(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/124.0 Safari/537.36",  # the default Python agent is blocked (Cloudflare 1010)
               "Origin": "https://novelai.net", "Referer": "https://novelai.net/"}
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, method="POST" if data else "GET", headers=headers)
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read(), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            body = e.read()[:400].decode(errors="replace")
            if e.code == 429 and attempt < 7:  # one generation at a time per account (e.g. web UI busy)
                time.sleep(5 * (attempt + 1))
                continue
            raise SystemExit(f"HTTP {e.code}: {body}")


def anlas():
    d = json.loads(call("/user/subscription")[0])
    t = d.get("trainingStepsLeft") or {}
    return t.get("fixedTrainingStepsLeft", 0) + t.get("purchasedTrainingSteps", 0)


def params(a, extra=None):
    p = {
        "params_version": 3, "width": a.w, "height": a.h, "scale": a.scale, "sampler": "k_euler_ancestral",
        "steps": a.steps, "n_samples": 1, "ucPreset": 0, "qualityToggle": True, "dynamic_thresholding": False,
        "controlnet_strength": 1, "legacy": False, "add_original_image": True, "cfg_rescale": 0,
        "noise_schedule": "karras", "legacy_v3_extend": False, "skip_cfg_above_sigma": None, "use_coords": False,
        "legacy_uc": False, "normalize_reference_strength_multiple": True, "seed": a.seed, "characterPrompts": [],
        "v4_prompt": {"caption": {"base_caption": a.prompt, "char_captions": []}, "use_coords": False, "use_order": True},
        "v4_negative_prompt": {"caption": {"base_caption": a.negative, "char_captions": []}, "legacy_uc": False},
        "negative_prompt": a.negative, "deliberate_euler_ancestral_bug": False, "prefer_brownian": True,
    }
    if getattr(a, "charref", None):
        # NovelAI "Precise Reference" (V4.5 only): image must be 1024x1536, 1536x1024 or 1472x1472 (black padding)
        from PIL import Image
        im = Image.open(a.charref).convert("RGB")
        W, H = min(((1024, 1536), (1536, 1024), (1472, 1472)), key=lambda s: abs(s[0] / s[1] - im.width / im.height))
        sc = min(W / im.width, H / im.height)
        im = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
        canvas = Image.new("RGB", (W, H), "black")
        canvas.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
        buf = io.BytesIO()
        canvas.save(buf, "PNG")
        p.update({
            "director_reference_images": [base64.b64encode(buf.getvalue()).decode()],
            "director_reference_descriptions": [{"caption": {"base_caption": a.charref_mode, "char_captions": []},
                                                 "legacy_uc": False}],
            "director_reference_information_extracted": [1],
            "director_reference_strength_values": [a.charref_strength],
            "director_reference_secondary_strength_values": [a.charref_fidelity],
        })
        for k in ("normalize_reference_strength_multiple",):
            p.pop(k, None)
    p.update(extra or {})
    return p


def b64(path):
    return base64.b64encode(Path(path).read_bytes()).decode()


def save(raw, ctype, out):
    if "zip" in ctype or raw[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            raw = z.read(z.namelist()[0])
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["balance", "generate", "infill", "img2img"])
    ap.add_argument("--model")
    ap.add_argument("--prompt", default="")
    ap.add_argument("--negative", default=DEFAULT_NEG)
    ap.add_argument("--w", type=int, default=1024)
    ap.add_argument("--h", type=int, default=1024)
    ap.add_argument("--seed", type=int, default=20261021)
    ap.add_argument("--steps", type=int, default=28)
    ap.add_argument("--scale", type=float, default=5.0)
    ap.add_argument("--image")
    ap.add_argument("--mask")
    ap.add_argument("--strength", type=float, default=1.0)
    ap.add_argument("--out")
    ap.add_argument("--charref", help="Precise Reference image (V4.5 models only)")
    ap.add_argument("--charref-mode", default="character", choices=["character", "character&style"])
    ap.add_argument("--charref-strength", type=float, default=1.0)
    ap.add_argument("--charref-fidelity", type=float, default=1.0)
    a = ap.parse_args()
    if a.cmd == "balance":
        print("Anlas:", anlas())
        return
    before = anlas()
    if a.cmd == "generate":
        body = {"input": a.prompt, "model": a.model, "action": "generate", "parameters": params(a)}
    elif a.cmd == "img2img":
        body = {"input": a.prompt, "model": a.model, "action": "img2img",
                "parameters": params(a, {"image": b64(a.image), "strength": a.strength, "noise": 0,
                                         "extra_noise_seed": a.seed})}
    else:
        body = {"input": a.prompt, "model": a.model, "action": "infill",
                "parameters": params(a, {"image": b64(a.image), "mask": b64(a.mask), "strength": a.strength,
                                         "noise": 0, "extra_noise_seed": a.seed})}
    raw, ctype = call("/ai/generate-image", body)
    save(raw, ctype, a.out)
    after = anlas()
    rec = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "cmd": a.cmd, "model": a.model, "prompt": a.prompt,
           "negative": a.negative, "seed": a.seed, "steps": a.steps, "scale": a.scale, "size": [a.w, a.h],
           "source_image": a.image, "mask": a.mask, "charref": a.charref, "out": a.out, "anlas_before": before, "anlas_after": after}
    with open(Path(a.out).parent / "manifest.jsonl", "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"saved {a.out} | Anlas {before} -> {after} (cost {before - after})")


if __name__ == "__main__":
    main()
