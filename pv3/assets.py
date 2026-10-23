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
    # v3: one drawing per sung phrase (see pv3/storyboard_v3.py)
    "d01_wake": ("upper", "close-up, waking up, sleepy, rubbing eye with sleeve, one eye open, yawning"),
    "d02_lookhere": ("upper", "close-up, pointing at viewer, cheeky smile, half-closed eyes, leaning forward"),
    "d03_stretch": ("cowboy", "stretching, arms up, interlocked fingers, one eye closed, getting ready"),
    "d04_jump": ("full", "jumping, arms up, energetic, open mouth, happy, " + LEGS),
    "d05_proud": ("upper", "hand on own chest, proud, eyes closed, chin up, smug"),
    "d06_hairflip": ("upper", "hair flip, hand in hair, cool, half-closed eyes, smirk"),
    "d07_hotcheeks": ("upper", "close-up, hands on own cheeks, heavy blush, steam, embarrassed, wavy mouth"),
    "d08_seeno": ("upper", "clenched fists, determined, sparkling eyes, open mouth, ready"),
    "d09_singpoint": ("cowboy", "singing, pointing at viewer, big smile, holding microphone"),
    "d10_turnaway": ("cowboy", "turning away, looking back over shoulder, smug, eyes closed, hand on hip"),
    "d11_gentle": ("upper", "close-up, face focus, gentle smug smile, half-closed eyes, looking at viewer, head tilt"),
    "d12_serious": ("upper", "close-up, serious, determined, wind, hair blowing, looking at viewer"),
    "d13_singclose": ("upper", "close-up, singing into microphone, eyes closed, both hands on microphone"),
    "d14_jumpmic": ("full", "jumping, holding microphone up, dynamic pose, open mouth, " + LEGS),
    "d15_flustered": ("upper", "waving both hands, flustered, blush, sweatdrop, open mouth"),
    "d16_back": ("cowboy", "from behind, back view, looking over shoulder, pout, tail"),
    "d17_peek": ("upper", "from side, peeking, one eye open, curious, hiding behind sleeve"),
    "d18_eyes": ("upper", "extreme close-up, eyes focus, surprised, sparkling eyes, blush"),
    "d19_wipetear": ("upper", "wiping tears with sleeve, determined smile, teary eyes"),
    "d20_angel": ("upper", "own hands together, innocent, angelic smile, eyes closed, halo, sparkles"),
    "d21_devil": ("upper", "fingers as horns on head, mischievous grin, tongue out, fang"),
    "d22_tiptoe": ("full", "close-up of legs, standing on tiptoes, trembling legs, boots, navy kneehighs, lower body"),
    "d23_shout": ("upper", "shouting, angry, blush, fists up, open mouth, close-up"),
    "d24_sleeves": ("cowboy", "rolling up sleeves, determined grin, confident"),
    "d25_skypoint": ("full", "pointing at sky, confident, wind, hair blowing, " + LEGS),
    "d26_tease": ("upper", "pointing at viewer, laughing, teasing, one eye closed"),
    "d27_frame": ("upper", "close-up, hands framing own face, look at me, smile, blush"),
    "d28_shh": ("upper", "close-up, index finger on lips, wink, smug"),
    "d29_reach": ("upper", "reaching hand toward viewer, foreshortening, inviting, smile"),
    "d30_powersing": ("full", "singing, holding microphone up, powerful, eyes closed, " + LEGS),
    "d31_wink": ("cowboy", "hands on hips, wink, triumphant, grin"),
    "d32_nod": ("upper", "arms crossed, eyes closed, nodding, smug, satisfied"),
    "d33_chin": ("upper", "close-up, chin on hand, smug smile, half-closed eyes, head tilt"),
    "d34_shy": ("upper", "shy smile, looking away, slight blush, fidgeting, sleeves"),
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
