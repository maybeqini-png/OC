"""Character drawings for the PV, one per lyric beat, generated on a plain background so each can be checked
against the reference sheet and colour-locked before it is placed into a designed layout.

Pipeline per drawing: NAI V4.5 Precise Reference (owner's sheet or the reference board) -> NAI V5 img2img at
strength 0.2 (V5 finish, identity kept) -> art/generated/pv3/<id>.png. Existing files are skipped.

usage: assets.py [ids...]
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
NAI = ROOT / ".claude/skills/oc-gen/scripts/nai.py"
OUT = ROOT / "art/generated/pv3"
BOARD = ROOT / "art/reference/refboard_A.png"      # full body + enlarged face + detail crops
SHEET = ROOT / "art/reference/oc_reference_sheet.webp"

OC = ("1girl, solo, cat girl, cat ears, long hair, royal blue hair, ahoge, blue cat hairclip, hair ornament, blue eyes, "
      "oversized navy sweater, navy sailor collar, blue stripes, short navy necktie, sleeves past wrists, dark grey shorts, cat tail")
LEGS = "navy kneehighs, black boots"
Q = "white background, simple background, anime key visual, official art, clean lineart, cel shading, moe, masterpiece, best quality"
NEG = ("blunt bangs, hime cut, text, watermark, signature, logo, lowres, bad anatomy, bad hands, extra fingers, missing fingers, "
       "human ears, extra ears, cyan hair, purple hair, grey hair, belt, long necktie, {{multiple views}}, character sheet, "
       "reference sheet, nsfw, jpeg artifacts, blurry, shadow")

# id: (framing, pose/expression tags). framing picks the reference: full/chibi -> sheet (single figure), else board.
ASSETS = {
    "n01_peek": ("cowboy", "leaning forward, arms behind back, short necktie, smug, half-closed eyes, looking at viewer, head tilt"),
    "n02_fufun": ("cowboy", "hand on hip, eyes closed, smug, nose up, chin up, smirk"),
    "n03_ikuyo": ("upper", "pointing at viewer, one eye closed, wink, smirk"),
    "n04_tensai": ("upper", "v over eye, peace sign, confident smile, half-closed eyes"),
    "n05_batchiri": ("cowboy", "holding microphone, ok sign, confident smile"),
    "n06_kanpeki": ("cowboy", "arms crossed, smug, half-closed eyes, smirk, looking at viewer, head tilt"),
    "n07_zannen": ("upper", "akanbe, pulling down eyelid, tongue out, teasing, one eye closed"),
    "n08_yoyuu": ("full", "standing, hands on hips, chest out, smug, half-closed eyes, smirk, " + LEGS),
    "n09_smart": ("cowboy", "finger gun, pointing at viewer, cool, smirk, half-closed eyes"),
    "n10_kimeru": ("full", "dynamic pose, one leg up, pointing up, confident, open mouth, " + LEGS),
    "n11_trip": ("full", "tripping, stumbling forward, falling, surprised, open mouth, arms flailing, motion lines, " + LEGS),
    "n12_aitata": ("full", "sitting on floor, hand on own head, teary eyes, pout, " + LEGS),
    "n13_matta": ("upper", "hand up, stop gesture, palm toward viewer, flustered, sweatdrop, open mouth"),
    "n14_nocount": ("upper", "crossed arms x sign, eyes closed, serious, denial, sweatdrop"),
    "n15_niyake": ("upper", "covering face with sleeves, blush, embarrassed, peeking through fingers"),
    "n16_shinkokyu": ("upper", "eyes closed, hands on own chest, deep breath, calm, light blush"),
    "n17_sing": ("cowboy", "singing, holding microphone, arm raised, open mouth, happy, closed eyes"),
    "n18_fufun2": ("upper", "finger wag, index finger raised, smug, one eye closed, smirk"),
    "n19_me": ("upper", "leaning toward viewer, poking viewer, foreshortening, paw pose, pout, scolding, half-closed eyes"),
    "n20_mouikkai": ("upper", "index finger raised, one more, cheerful smile, open mouth"),
    "n21_yosomi": ("upper", "pointing at own eyes, look at me, pout, slight blush"),
    "n22_tsuyogari": ("upper", "clenched fists, determined, teary eyes, slight blush"),
    "n23_screenshot": ("upper", "hands covering camera, palms toward viewer, foreshortening, flustered, blush, open mouth"),
    "n24_namaiki": ("upper", "pout, puffed cheeks, arms crossed, annoyed, looking away"),
    "n25_pui": ("upper", "turning head away, pout, eyes closed, hmph, profile"),
    "n26_fukidasu": ("upper", "laughing, hand over mouth, tears of laughter, eyes closed"),
    "n27_kuyashii": ("upper", "biting lip, teary eyes, gripping sleeves, frustrated"),
    "n28_step": ("full", "dancing, on tiptoes, one leg raised, arms out, nervous smile, " + LEGS),
    "n29_warauna": ("upper", "pointing at viewer, angry, blush, open mouth, embarrassed"),
    "n30_misebajan": ("cowboy", "peace sign, big grin, bandaid on cheek, confident"),
    "n31_utaikiru": ("upper", "singing, eyes closed, hand on chest, passionate, open mouth"),
    "n32_honene": ("cowboy", "both hands on hips, triumphant, smug, closed eyes, smirk"),
    "n33_matakite": ("upper", "waving, gentle smile, half-closed eyes, head tilt"),
    "c01_sleep": ("chibi", "chibi, full body, sleeping, curled up, zzz"),
    "c02_fall": ("chibi", "chibi, full body, falling flat on face, comedic, dust cloud"),
    "c03_dizzy": ("chibi", "chibi, full body, dizzy, spiral eyes, sitting"),
    "c04_stomp": ("chibi", "chibi, full body, angry, stomping, puffed cheeks, steam"),
    "c05_sign": ("chibi", "chibi, full body, holding blank sign, smug"),
    "c06_boop": ("chibi", "chibi, full body, paw pose, booping, one eye closed"),
    "c07_cry": ("chibi", "chibi, full body, crying, waterfall tears, open mouth"),
    "c08_dance": ("chibi", "chibi, full body, dancing, happy, arms up, music notes"),
}


def run(args):
    r = subprocess.run([PY, str(NAI), *args], capture_output=True, text=True)
    print((r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "no output", flush=True)
    return r.returncode == 0


SEED = {"n01_peek": 8100, "n12_aitata": 8112}  # redraws after QA (long tie, odd bump)


def make(aid, seed):
    framing, pose = ASSETS[aid]
    raw, fin = OUT / f"{aid}_raw.png", OUT / f"{aid}.png"
    if fin.exists():
        return
    ref = SHEET if framing in ("full", "chibi") else BOARD
    prompt = f"{OC}, {pose}, {Q}" if framing != "chibi" else f"{OC}, {pose}, {LEGS}, {Q}"
    if framing in ("upper", "cowboy"):
        prompt = f"{framing.replace('upper', 'upper body').replace('cowboy', 'cowboy shot')}, " + prompt
    if not raw.exists():
        run(["generate", "--model", "nai-diffusion-4-5-full", "--w", "832", "--h", "1216", "--seed", str(seed),
             "--charref", str(ref), "--charref-mode", "character", "--prompt", prompt, "--negative", NEG, "--out", str(raw)])
    if raw.exists():
        run(["img2img", "--model", "nai-diffusion-5-full", "--w", "832", "--h", "1216", "--seed", str(seed), "--strength", "0.2",
             "--image", str(raw), "--prompt", prompt, "--negative", NEG, "--out", str(fin)])


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    ids = sys.argv[1:] or list(ASSETS)
    for i, aid in enumerate(ids):
        make(aid, SEED.get(aid, 8000 + list(ASSETS).index(aid)))
