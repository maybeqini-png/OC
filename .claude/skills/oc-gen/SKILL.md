---
name: oc-gen
description: Generate and edit artwork for the OC PV with NovelAI (V5) through the environment's injected API key; use for any new OC expression, pose, background or face-variant frame.
---
# oc-gen

Generates OC PV artwork with NovelAI. The NovelAI key is a network secret injected by the environment proxy for
`*.novelai.net`; never add, print or store keys. Base URL: `https://image.novelai.net` (the old api.novelai.net
endpoints are retired). One generation at a time per account (HTTP 429 is retried automatically).

## Commands (`scripts/nai.py`)
- `balance` - Anlas left. Normal-size (1024x1024, 28 steps) generations on the owner's Opus plan measured 0 Anlas.
- `generate --model nai-diffusion-5-full --prompt ... --out ...`
- `img2img --model nai-diffusion-5-full --image in.png --strength 0.5 --seed S --prompt ... --out ...`
- `infill --model nai-diffusion-5-full-inpainting --image in.png --mask mask.png ...` (API inpainting leaves grey
  rims at mask edges and can hallucinate text - avoid for face variants)
Each output appends model/prompt/seed/Anlas to `manifest.jsonl` next to it (for AI disclosure and reproducibility).

## Proven pipeline (tested 2026-10-21, see `art/generated/nai_test/`)
1. Design + framing from the OpenAI/ChatGPT image model (on-model; masked edits stay pixel-aligned).
2. Restyle each frame with V5 `img2img`, strength 0.5, the SAME seed, the full OC tag prompt (README section 1).
3. For face variants, transplant only the changed eye/mouth region of the restyled variant onto the restyled base
   (feathered ellipse, best-shift alignment) so everything else stays identical.
Tags-only V5 drifts off-model (blunt bangs, wide eyes); if used, add `messy bangs, hair between eyes,
half-closed eyes, smug` and negative `blunt bangs, hime cut, blush, wide-eyed, cyan, purple hair`.

## Rules
- Quote the expected cost and get the owner's OK before any batch that may cost Anlas or money.
- Never name real artists or VTubers in prompts. Plain light-grey background for character assets.
