"""fal video jobs for the OC PV (MiniMax H3 first). Auth is injected by the environment proxy for *.fal.run /
*.fal.ai - never add, print or store keys here.

usage:
  fal_video.py run --model minimax/h3/image-to-video --image first.jpg [--end last.jpg] --prompt P
                   [--duration 5 --resolution 768P --seed S] --out clip.mp4
  fal_video.py quote --model M --duration 5 --resolution 768P
Every finished job appends model / prompt / inputs / seed / request id / cost estimate to manifest.jsonl next to
the output (AI disclosure, reproducibility, spend tracking).
"""
import argparse
import base64
import json
import mimetypes
import time
import urllib.error
import urllib.request
from pathlib import Path

QUEUE = "https://queue.fal.run"
# USD per output second (fal model pages, 2026-10-23)
PRICE = {"minimax/h3/image-to-video": {"480P": 0.05, "768P": 0.06, "2K": 0.13, "4K": 0.16},
         "minimax/h3-max/image-to-video": {"480P": 0.0325, "768P": 0.052, "1080P": 0.104}}


def req(url, payload=None, method=None):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(url, data=data, method=method or ("POST" if data else "GET"),
                               headers={"Content-Type": "application/json"} if data else {})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(r, timeout=120) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read()[:600].decode(errors="replace")
            if e.code in (429, 502, 503) and attempt < 5:
                time.sleep(5 * (attempt + 1))
                continue
            raise SystemExit(f"HTTP {e.code} {url}: {body}")


def data_uri(path):
    mt = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    return f"data:{mt};base64," + base64.b64encode(Path(path).read_bytes()).decode()


def quote(model, duration, resolution):
    return round(PRICE[model][resolution] * duration, 4)


def run(a):
    body = {"prompt": a.prompt, "duration": a.duration, "resolution": a.resolution,
            "prompt_expansion_mode": a.expansion, "enable_safety_checker": True}
    if a.image:
        body["image_url"] = data_uri(a.image)
    if a.end:
        body["end_image_url"] = data_uri(a.end)
    if a.seed is not None:
        body["seed"] = a.seed
    sub = req(f"{QUEUE}/{a.model}", body)
    rid = sub["request_id"]
    status_url, resp_url = sub["status_url"], sub["response_url"]
    print("submitted", rid, "est. $", quote(a.model, a.duration, a.resolution), flush=True)
    t0 = time.time()
    while True:
        st = req(status_url + "?logs=0")
        if st.get("status") == "COMPLETED":
            break
        if time.time() - t0 > 1800:
            raise SystemExit(f"timeout waiting for {rid}")
        time.sleep(8)
    res = req(resp_url)
    url = res["video"]["url"]
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=300) as r:
        out.write_bytes(r.read())
    rec = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": a.model, "prompt": a.prompt, "image": a.image,
           "end_image": a.end, "duration": a.duration, "resolution": a.resolution, "seed": a.seed,
           "expansion": a.expansion, "expanded_prompt": res.get("expanded_prompt"), "request_id": rid,
           "cost_usd_est": quote(a.model, a.duration, a.resolution), "seconds": round(time.time() - t0), "out": str(out)}
    with open(out.parent / "manifest.jsonl", "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("saved", out, f"({rec['seconds']} s, est. ${rec['cost_usd_est']})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "quote"])
    ap.add_argument("--model", default="minimax/h3/image-to-video")
    ap.add_argument("--image")
    ap.add_argument("--end")
    ap.add_argument("--prompt", default="")
    ap.add_argument("--duration", type=int, default=5)
    ap.add_argument("--resolution", default="768P")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--expansion", default="disabled", help="prompt_expansion_mode: disabled keeps the prompt as written")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.cmd == "quote":
        print("est. $", quote(a.model, a.duration, a.resolution))
        return
    run(a)


if __name__ == "__main__":
    main()
