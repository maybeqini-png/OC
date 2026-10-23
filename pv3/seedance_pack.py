"""Build the Seedance 2.5 image-to-video pack for the PV: first/last frames on a green screen + prompts.

usage: seedance_pack.py            -> pv3/seedance/{frames/*.jpg, audio/*.m4a, prompts.md, prompts.json}

Each clip starts from one approved drawing (colour-locked to the reference sheet, white border removed),
placed on flat chroma green so the returned video can be keyed and composited into the v3 layouts.
Optional last frames turn two consecutive drawings into one continuous action.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from rembg import remove

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prep  # noqa: E402  (colour lock, rembg session)

ROOT = HERE.parent
OUT = HERE / "seedance"
GREEN = (0, 177, 64)  # broadcast chroma green: far from her navy/cobalt/skin colours
W, H = 1920, 1080
FACES = json.load(open(HERE / "stickers/faces.json"))

DESIGN = ("the same anime cat girl exactly as in @Image 1: long navy-blue hair with an ahoge, navy cat ears with pale pink inner fur, "
          "a light-blue cat-face hairclip, blue half-lidded eyes, oversized navy sweater with a navy sailor collar and cobalt stripes, "
          "short navy necktie, sleeves past her wrists, dark grey shorts, navy cat tail")
RULES = ("Keep her design, proportions, line art and colours identical to @Image 1 in every frame. 2D anime cel animation, "
         "clean lineart, flat cel shading, no 3D look, no realistic texture. Locked-off static camera, no zoom, no pan. "
         "Keep the flat solid green background unchanged, with no shadows on it, no props, no particles, no text and no other "
         "characters. Hair, ears and tail move with soft follow-through.")

# id: (song time s, first drawing, last drawing or None, framing, seconds, action beats)
CLIPS = {
    "v01_wake": (2.55, "d01_wake", None, "close", 4, "0-2 s: she rubs her eye with her sleeve and yawns. 2-4 s: she opens both eyes, looks at the viewer and gives a sly little smile; her ears twitch once."),
    "v02_peek": (4.02, "n01_peek", None, "full", 4, "She leans toward the viewer with her hands behind her back, tilts her head and smiles smugly with half-closed eyes; her tail swishes."),
    "v03_lookhere": (4.56, "d02_lookhere", None, "close", 4, "She points at the viewer with a cheeky grin, then wags the finger twice while leaning in slightly."),
    "v04_fufun": (7.63, "n02_fufun", "d03_stretch", "full", 4, "0-1.5 s: eyes closed, chin up, a smug 'hmph'. 1.5-4 s: she raises both arms into a big stretch, ending as @Image 2."),
    "v05_ikuyo": (9.92, "n03_ikuyo", None, "full", 4, "She points at the viewer and winks, with a small confident bounce on the beat."),
    "v06_jump": (11.05, "d04_jump", None, "full", 4, "She jumps with both arms up, hangs in the air for a moment and lands softly; hair and tail float and settle."),
    "v07_tensai": (17.75, "n04_tensai", None, "full", 4, "She holds a V sign over her eye and sways side to side to the music with a confident smile."),
    "v08_batchiri": (19.44, "n05_batchiri", None, "full", 4, "Holding a microphone, she flashes an OK sign and nods twice, pleased with herself."),
    "v09_kanpeki": (23.28, "n06_kanpeki", None, "full", 4, "Arms crossed, she nods smugly with her eyes closed, then opens one eye to check on the viewer."),
    "v10_zannen": (28.25, "n07_zannen", None, "full", 4, "Akanbe: she pulls down one eyelid, sticks out her tongue, then giggles."),
    "v11_yoyuu": (31.72, "n08_yoyuu", None, "full", 4, "Hands on hips, she puffs out her chest and sways confidently; her hair flutters."),
    "v12_kimeru": (37.22, "n10_kimeru", None, "full", 4, "A dynamic idol pose: she kicks one leg up, points to the sky and holds the pose while her hair blows."),
    "v13_trip": (42.6, "n11_trip", "n12_aitata", "full", 4, "0-1 s: she trips forward and flails her arms. 1-2.5 s: she tumbles down comically. 2.5-4 s: she sits on the floor holding her head, teary, ending as @Image 2."),
    "v14_matta": (44.08, "n13_matta", None, "full", 4, "Flustered, she holds her palm out toward the viewer ('wait!') and shakes her head quickly."),
    "v15_nocount": (46.24, "n14_nocount", None, "full", 4, "She crosses her arms in an X and shakes her head with her eyes shut: 'that doesn't count'."),
    "v16_niyake": (49.61, "n15_niyake", None, "full", 4, "She hides her blushing face behind her sleeves, peeks through, and squirms side to side."),
    "v17_breath": (53.48, "n16_shinkokyu", None, "full", 4, "Eyes closed, hand on her chest, she takes one slow deep breath in and out; her shoulders rise and fall."),
    "v18_seeno": (54.33, "d08_seeno", None, "close", 4, "She clenches her fists, her eyes sparkle with determination, and she opens her mouth to shout."),
    "v19_chorus": (55.58, "n17_sing", "d09_singpoint", "full", 4, "0-2 s: she sings into the microphone with her arm raised high. 2-4 s: still singing, she points at the viewer, ending as @Image 2."),
    "v20_fufun2": (59.35, "n18_fufun2", None, "full", 4, "She wags her index finger side to side and winks smugly."),
    "v21_sign": (61.86, "c05_sign", None, "full", 4, "She holds up the blank sign toward the viewer and bobs it on the beat, looking smug. The sign stays blank."),
    "v22_warauna": (64.4, "n29_warauna", None, "full", 4, "Blushing and annoyed, she points at the viewer and stamps one foot."),
    "v23_me": (66.6, "n19_me", None, "close", 4, "She leans toward the camera and gives a little paw boop toward the lens with a scolding pout, then pulls back."),
    "v24_mouikkai": (67.48, "n20_mouikkai", None, "full", 4, "She raises one index finger ('one more time!') with a cheerful little bounce."),
    "v25_tsuyogari": (72.64, "n22_tsuyogari", None, "full", 4, "She clenches her fists and trembles slightly, teary-eyed but determined; she sniffs and looks up."),
    "v26_jumpmic": (79.64, "d14_jumpmic", None, "full", 4, "She jumps with the microphone raised high, then lands and keeps singing."),
    "v27_screenshot": (84.62, "n23_screenshot", None, "close", 4, "Flustered, she rushes both hands toward the camera to cover it, blushing."),
    "v28_pui": (98.84, "n25_pui", "d16_back", "full", 4, "0-1.5 s: she turns her head away with a pout ('hmph'). 1.5-4 s: she turns her back to the viewer and glances over her shoulder, ending as @Image 2."),
    "v29_laugh": (107.42, "n26_fukidasu", None, "full", 4, "She bursts out laughing, covering her mouth with her sleeve; her shoulders shake and tears of laughter appear."),
    "v30_kuyashii": (109.64, "n27_kuyashii", None, "full", 4, "She bites her lip and grips her sleeves; tears well up, she looks down, then lifts her chin."),
    "v31_angeldevil": (112.95, "d20_angel", "d21_devil", "full", 4, "0-2 s: an innocent angelic smile with hands together and a halo. 2-4 s: the halo vanishes and she switches to a mischievous grin with finger devil horns, ending as @Image 2."),
    "v32_step": (119.26, "n28_step", None, "full", 4, "Nervous little dance steps on tiptoe, arms out for balance, wobbling cutely."),
    "v33_shout": (123.09, "d23_shout", None, "close", 4, "She shouts 'don't laugh!' with fists up; her hair bounces."),
    "v34_skypoint": (124.52, "d25_skypoint", None, "full", 4, "She points at the sky with confidence while wind blows her hair and sweater."),
    "v35_misebajan": (132.28, "n30_misebajan", None, "full", 4, "She flashes a peace sign with a big grin and winks."),
    "v36_reach": (145.9, "d29_reach", None, "close", 4, "She reaches her hand toward the viewer with an inviting smile."),
    "v37_powersing": (150.48, "d30_powersing", None, "full", 4, "She sings powerfully with the microphone held up and her eyes closed, swaying with the music."),
    "v38_wink": (154.41, "d31_wink", None, "full", 4, "Hands on hips, she winks triumphantly and grins."),
    "v39_matakite": (163.26, "n33_matakite", None, "full", 4, "She waves goodbye gently with a soft smile and tilts her head."),
    "v40_sleep": (170.0, "c01_sleep", None, "full", 4, "Curled up asleep, she breathes slowly; one ear twitches and her tail flicks once."),
}


def cut(aid):
    im = np.asarray(Image.open(ROOT / f"art/generated/pv3/{aid}.png").convert("RGB"))
    a = np.asarray(remove(Image.fromarray(im), session=prep.SESSION).getchannel("A")).astype(np.float32) / 255
    a = np.clip((a - 0.05) / 0.9, 0, 1)
    locked, _ = prep.lock(im, a > 0.5, REF)
    return locked, a


def frame(aid, framing):
    rgb, a = cut(aid)
    h0, w0 = a.shape
    if framing == "close" and FACES.get(aid):
        fx, fy, fw, fh = FACES[aid]          # sticker coords: the sticker adds a 42 px border pad
        k = h0 / 1216
        s = float(np.clip((0.34 * H) / (fh * k), 0.95, 2.0))
        cx, cy = (fx + fw / 2 - 42) * k, (fy + fh / 2 - 42) * k
        ox, oy = W / 2 - cx * s, H * 0.44 - cy * s
    else:
        s = 1040 / h0
        ox, oy = (W - w0 * s) / 2, H - h0 * s
    rgbi = Image.fromarray(rgb).resize((int(w0 * s), int(h0 * s)), Image.LANCZOS)
    ai = Image.fromarray((a * 255).astype(np.uint8)).resize(rgbi.size, Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), GREEN)
    canvas.paste(rgbi, (int(ox), int(oy)), ai)
    return canvas


def main():
    global REF
    REF = prep.ref_stats()
    (OUT / "frames").mkdir(parents=True, exist_ok=True)
    (OUT / "audio").mkdir(parents=True, exist_ok=True)
    rows = []
    for cid, (t, first, last, framing, dur, beats) in CLIPS.items():
        f1 = OUT / f"frames/{cid}_first.jpg"
        frame(first, framing).save(f1, quality=95)
        imgs = [f1.name]
        if last:
            f2 = OUT / f"frames/{cid}_last.jpg"
            frame(last, framing).save(f2, quality=95)
            imgs.append(f2.name)
        aud = OUT / f"audio/{cid}.m4a"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-t", str(dur), "-i",
                        str(ROOT / "audio/t2_optimized_full.mp3"), "-c:a", "aac", "-b:a", "192k", str(aud)], check=True)
        frames_line = "@Image 1 is the first frame." + (" @Image 2 is the last frame." if last else "")
        prompt = f"{frames_line} {DESIGN}. {beats} {RULES}"
        rows.append({"id": cid, "song_time": t, "duration_s": dur, "first_frame": f"frames/{f1.name}",
                     "last_frame": f"frames/{cid}_last.jpg" if last else None, "audio_ref": f"audio/{cid}.m4a",
                     "aspect_ratio": "16:9", "resolution": "1080p", "fps": 24, "generate_audio": False, "prompt": prompt})
        print(cid, "ok", flush=True)
    json.dump(rows, open(OUT / "prompts.json", "w"), ensure_ascii=False, indent=1)
    md = ["# Seedance 2.5 clip pack — 「余裕だもん」 PV v3", "",
          "Settings for every clip: image-to-video, 16:9, 1080p (720p is fine), 24 fps, audio OFF, duration as listed.",
          "Upload `first` as the first frame (@Image 1); when a `last` frame is listed, upload it as the last frame (@Image 2).",
          "The audio file is only the matching song section for your reference; do not add it to the video.",
          "Name each result exactly `<id>.mp4` and send them back — they are keyed (green) and placed into the v3 layouts.",
          "Reject a take if her design changes (hair colour, ears, hairclip, collar, tie, tail), if the green background",
          "changes or gets shadows, or if text appears.", ""]
    for r in rows:
        md += [f"## {r['id']}  (song {r['song_time']:.2f} s, {r['duration_s']} s)",
               f"- first: `pv3/seedance/{r['first_frame']}`" + (f"  ·  last: `pv3/seedance/{r['last_frame']}`" if r['last_frame'] else ""),
               "", "```", r["prompt"], "```", ""]
    (OUT / "prompts.md").write_text("\n".join(md), encoding="utf-8")


if __name__ == "__main__":
    main()
