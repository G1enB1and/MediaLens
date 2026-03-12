# AI Image Metadata Map

This document maps the embedded metadata found in `tests/AI_Images` and compares it to what MediaManagerX currently harvests.

## Reproducible extraction

Primary dump used for this document:

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts\inspect_ai_metadata.py tests\AI_Images > .tmp-tests\ai_metadata_report.json
python scripts\inspect_ai_metadata.py tests\AI_Images --summary > .tmp-tests\ai_metadata_summary.txt
```

Useful follow-up checks:

```powershell
rg -a -n "c2pa|GPT-4o|Google|trainedAlgorithmicMedia|softwareAgent|claim_generator_info" tests\AI_Images\ChatGPT-Red-Panda.png
rg -a -n "c2pa|Google|SynthID|Generative AI" tests\AI_Images\nanobana2-flash-aistudio-cat-dog-snuggle.png
rg -a -n "chara|public_id|personality|first_mes|scenario" tests\AI_Images\Silly-Tavern-Jarvis.png
python -c "import json,base64; d=json.load(open('.tmp-tests/ai_metadata_report.json', encoding='utf-16')); s=d['Silly-Tavern-Jarvis.png']['container']['text_chunks'][0]['text']; print(base64.b64decode(s).decode('utf-8', errors='replace'))"
```

Notes:

- PowerShell redirection created `.tmp-tests/ai_metadata_report.json` as UTF-16, so read it back with `encoding='utf-16'`.
- `comfyui-img-to-img-workflow.png` is chunk-parseable but Pillow cannot identify it. Do not rely only on Pillow for PNG metadata extraction.

## What MediaManagerX currently covers

Current metadata harvesting is partially aligned but still shallow for AI-image use cases.

- `native/mediamanagerx_app/main.py::_harvest_universal_metadata`
  - Reads `img.info` keys like `comment`, `description`, `parameters`, `software`, `hardware`, `tool`, `civitai metadata`, `keywords`, `tags`.
  - Parses XMP `dc:subject`, `dc:description`, `lr:hierarchicalSubject`.
  - Parses IPTC caption/title/keywords.
  - Parses EXIF `XPComment`, `UserComment`, `XPKeywords`, `Software`, `Artist`, `Make`, `Model`.
- `native/mediamanagerx_app/main.py::_harvest_windows_visible_metadata`
  - Reads PNG XMP / Windows-visible comment and tag locations.

Important gaps shown by these test files:

- No parser for PNG `caBX` / JUMBF / C2PA provenance.
- No source-specific parser for ComfyUI `prompt` / `workflow` JSON.
- No parser for SillyTavern `tEXt` keyword `chara` with base64 JSON.
- No deep parser that splits A1111 / Forge `parameters` into normalized fields like prompt, negative prompt, model, lora, CFG, scheduler, steps, upscaler.
- No fallback raw-chunk scanner for malformed-but-valid-enough PNGs.

## File-by-file map

### `ChatGPT-Red-Panda.png`

- Container path: PNG chunk `caBX` at offset `33`, length `67938`.
- Type: JUMBF / C2PA Content Credentials, not normal PNG `tEXt` / `iTXt`.
- Pillow view: no `info`, no EXIF.
- Embedded values found in the `caBX` payload:
  - `c2pa.actions.v2`
  - action `c2pa.created`
  - `softwareAgent.name = GPT-4o`
  - `digitalSourceType = http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia`
  - action `c2pa.converted`
  - `c2pa.claim.v2`
  - `claim_generator_info.name = ChatGPT`
  - `claim_generator_info` includes `org.contentauth.c2pa_rsf0.67.1`
  - `instanceID = xmp:iid:4d983c77-395b-4715-a13e-0f2af8e65dd4`
  - later manifest also includes `c2pa.ingredient.v3`, `c2pa.thumbnail.ingredient`, `c2pa.opened`, validation results, hashed URI/data hash records
- AI-generation fields recoverable from metadata:
  - Tool/source: `ChatGPT`
  - Model / software agent: `GPT-4o`
  - Provenance type: C2PA-generated AI media
- Not found in this sample:
  - Prompt
  - Negative prompt
  - CFG / steps / sampler
  - Checkpoint / LoRA

### `civitai-cute-kitten.png`

- Container path: PNG `tEXt` chunk at offset `33`, keyword `parameters`, length `1798`.
- Pillow view: `img.info["parameters"]` contains the same full text.
- Embedded payload shape: classic A1111/Stable Diffusion `parameters` block.
- Recovered fields:
  - Prompt: `no humans, In this ultra-detailed CG art, the adorable kitten...`
  - Negative prompt: starts with `FastNegativeV2,(bad-artist:1)...`
  - Steps: `28`
  - Sampler: `DPM++ 2M Karras`
  - CFG scale: `7`
  - Seed: `2520073901`
  - Size: `768x1152`
  - Model hash: `a5eeeecc79`
  - Model: `hellofantasytime_V1.22`
  - Denoising strength: `0`
  - Clip skip: `2`
  - Hires upscale: `1.5`
  - Hires steps: `10`
  - Hires upscaler: `R-ESRGAN 4x+`
  - Face editor fields:
    - `face_editor_enabled`
    - `face_editor_face_margin`
    - `face_editor_confidence`
    - `face_editor_strength1`
    - `face_editor_strength2`
    - `face_editor_max_face_count`
    - `face_editor_mask_size`
    - `face_editor_mask_blur`
    - `face_editor_prompt_for_face`
    - `face_editor_apply_inside_mask_only`
    - `face_editor_apply_scripts_to_faces`
    - `face_editor_face_size`
    - `face_editor_use_minimal_area`
    - `face_editor_ignore_larger_faces`
    - `face_editor_affected_areas`
    - `face_editor_workflow` containing nested JSON
    - `face_editor_upscaler`
  - Version: `v1.4.0`
- Best normalization target:
  - `raw_parameters_text`
  - `ai_prompt`
  - `ai_negative_prompt`
  - `steps`
  - `sampler`
  - `cfg_scale`
  - `seed`
  - `width`, `height`
  - `model_name`, `model_hash`
  - `hires_*`
  - `tool_version`
  - `source_extra_json.face_editor_workflow`

### `comfyui-flux2-klein-ninja-cat.png`

- Container paths:
  - PNG `tEXt` chunk at offset `33`, keyword `prompt`, length `7337`
  - PNG `tEXt` chunk at offset `7382`, keyword `workflow`, length `194383`
- Pillow view:
  - `img.info["prompt"]`
  - `img.info["workflow"]`
- Embedded payload shape:
  - `prompt` = ComfyUI execution graph JSON
  - `workflow` = full ComfyUI UI workflow JSON
- Recovered from `prompt` JSON:
  - Noise seed: `162862083665867`
  - Width: `1920`
  - Height: `1080`
  - Positive prompt text: `anthropomorphic cat ninja in black with throwing stars`
  - Additional text node: `add more details with DETAILER`
  - UNET model: `flux-2-klein-9b-fp8.safetensors`
  - VAE: `flux2-vae.safetensors`
  - Sampler: `euler`
  - CFG: `1.0`
  - Flux2Scheduler steps: `4`
  - Save filename prefix: `Flux2-Klein`
- Recovered from `workflow` JSON:
  - Workflow id: `d24b0b73-3ceb-4c8c-bb27-afa0a63a85b9`
  - Revision: `0`
  - `last_node_id = 516`
  - `last_link_id = 947`
  - Full node/link graph
  - Frontend/version data including `frontendVersion = 1.39.16`
- Best normalization target:
  - `raw_comfy_prompt_json`
  - `raw_comfy_workflow_json`
  - `ai_prompt`
  - `model_name`
  - `vae_name`
  - `sampler`
  - `cfg_scale`
  - `steps`
  - `seed`
  - `width`, `height`
  - `save_prefix`
  - `tool = ComfyUI`

### `comfyui-img-to-img-workflow.png`

- Container paths:
  - PNG `tEXt` chunk at offset `33`, keyword `prompt`, length `1540`
  - PNG `tEXt` chunk at offset `1585`, keyword `workflow`, length `4851`
- Pillow view: Pillow fails to identify the image, but raw PNG chunk parsing succeeds.
- Embedded payload shape:
  - `prompt` = ComfyUI execution graph JSON
  - `workflow` = ComfyUI workflow JSON
- Recovered from `prompt` JSON:
  - Checkpoint: `SD1.5\v1-5-pruned-emaonly.safetensors`
  - Positive prompt: `Use clouds to represent a woman's profile, which has a real sense of beauty.`
  - Negative prompt: `lowres, bad anatomy, bad hands, text, error...`
  - Seed: `72797062025567`
  - Steps: `15`
  - CFG: `8.0`
  - Sampler: `dpmpp_2m`
  - Scheduler: `normal`
  - Denoise: `0.87`
- Recovered from `workflow` JSON:
  - Full node/link graph
  - Workflow `version = 0.4`
  - `models[0].name = v1-5-pruned-emaonly.safetensors`
  - `models[0].url = https://huggingface.co/Comfy-Org/stable-diffusion-v1-5-archive/...`
  - `models[0].directory = checkpoints`
- Best normalization target:
  - same ComfyUI fields as above
  - plus `checkpoint_url`
- Important parser note:
  - This sample proves you need a raw chunk parser fallback when image libraries reject the file.

### `forge-flux-dragon.png`

- Container path: PNG `iTXt` chunk at offset `33`, keyword `parameters`, length `899`.
- Pillow view: `img.info["parameters"]` contains the same full text.
- Embedded payload shape: A1111-like parameter string, but saved in `iTXt` instead of `tEXt`.
- Recovered fields:
  - Prompt: `An elegant grayscale fantasy scene with a majestic dragon...`
  - No explicit negative prompt found
  - Steps: `20`
  - Sampler: `Euler`
  - Schedule type: `Simple`
  - CFG scale: `1`
  - Distilled CFG Scale: `3.5`
  - Seed: `228895476`
  - Size: `1152x1152`
  - Model: `STOIQOAfroditeFLUXXL_F1DAlpha`
  - Tiling: `True`
  - Version: `f2.0.1v1.10.1-previous-665-gae278f79`
  - Diffusion in Low Bits: `float8-e5m2 (fp16 LoRA)`
  - Module 1: `ae`
  - Module 2: `clip_l`
  - Module 3: `t5xxl_fp16`
- Likely source family:
  - Forge / Flux pipeline
- Parser note:
  - Do not assume `parameters` always lives in `tEXt`; this sample uses `iTXt`.

### `grok-cat-dog-snuggle.jpg`

- Container path: JPEG segments only:
  - `APP0` JFIF at offset `2`
  - quantization / Huffman / frame / scan markers
- Pillow view:
  - `jfif`
  - `jfif_version`
  - `jfif_unit`
  - `jfif_density`
- Not found:
  - EXIF `APP1`
  - XMP `APP1`
  - IPTC `APP13`
  - COM comment segment
  - AI prompt / model / tool metadata
- Conclusion:
  - No embedded metadata beyond basic JPEG/JFIF container info.

### `nanobana2-flash-aistudio-cat-dog-snuggle.png`

- Container path: PNG chunk `caBX` at offset `33`, length `6014`.
- Type: JUMBF / C2PA Content Credentials.
- Pillow view: no `info`, no EXIF.
- Embedded values found in the `caBX` payload:
  - `c2pa.signature`
  - Google certificate chain:
    - `Google C2PA Media Services 1P ICA G3`
    - `Google C2PA Root CA G3`
    - OCSP / certificate URLs
  - `c2pa.claim.v2`
  - `claim_generator_info.name = Google C2PA Core Generator Library`
  - `claim_generator_info.version = 878472295:878472295`
  - `c2pa.actions.v2`
  - action description: `Created by Google Generative AI.`
  - action description: `Applied imperceptible SynthID watermark.`
  - `digitalSourceType = http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia`
- AI-generation fields recoverable from metadata:
  - Tool/source family: Google Generative AI / SynthID provenance
  - Provenance only; no prompt/model/checkpoint fields found in this sample
- Not found:
  - Prompt
  - Negative prompt
  - Steps / sampler / CFG
  - Explicit model name

### `Silly-Tavern-Character.png`

- Container path:
  - PNG `tIME` chunk at offset `33`, length `7`
- Pillow view: no `info`, no EXIF.
- Not found:
  - `tEXt`, `zTXt`, `iTXt`
  - XMP
  - EXIF
  - `chara`
- Conclusion:
  - No recoverable embedded character-card metadata in standard metadata containers in this sample.

### `Silly-Tavern-Jarvis.png`

- Container paths:
  - PNG `tEXt` chunk at offset `437747`, keyword `chara`, length `8758`
  - PNG `eXIf` chunk at offset `446517`, length `14`
- Pillow view:
  - `img.info["dpi"]`
  - no useful EXIF values surfaced
- Embedded payload shape:
  - `chara` text chunk contains base64-encoded JSON
  - `eXIf` exists but is effectively empty / non-useful in this sample
- Decoded `chara` JSON fields:
  - `public_id`
  - `name = Jarvis`
  - `description`
  - `short_description`
  - `personality`
  - `first_mes`
  - `chat`
  - `mes_example`
  - `scenario`
  - `categories`
  - `create_date_online`
  - `edit_date_online`
  - `edit_date_local`
  - `add_date_local`
  - `last_action_date`
  - `nsfw`
- This is not image-generation metadata, but it is deeply embedded structured metadata that MediaManagerX does not currently parse.
- Best normalization target:
  - `raw_sillytavern_card_json`
  - `character_name`
  - `character_description`
  - `character_personality`
  - `character_scenario`
  - `character_first_message`
  - `character_examples`
  - timestamps / NSFW flag

### `stabile-diffusion-web-ui-glass-fox.png`

- Container path: PNG `tEXt` chunk at offset `33`, keyword `parameters`, length `1035`.
- Pillow view: `img.info["parameters"]` contains the same full text.
- Embedded payload shape: classic A1111 / Stable Diffusion WebUI parameter block.
- Recovered fields:
  - Prompt: `Made_of_pieces_broken_glass, solo, blurry, fox...`
  - Prompt also includes inline LoRA token: `<lora:Made_of_pieces_broken_glass-000001:0.8>`
  - Negative prompt: starts with `bad art, bad artist, blur...`
  - Steps: `30`
  - Sampler: `DPM++ 2M SDE Karras`
  - CFG scale: `4`
  - Seed: `3677823845`
  - Size: `768x432`
  - Model hash: `0f1b80cfe8`
  - Model: `dreamshaperXL10_alpha2Xl10`
  - Clip skip: `2`
  - LoRA hashes: `Made_of_pieces_broken_glass-000001: 9e22e1d72cfd`
  - Version: `v1.7.0`
- Best normalization target:
  - same A1111 fields as `civitai-cute-kitten.png`
  - plus `lora_tokens[]` and `lora_hashes[]`

## Source patterns to support

### A1111 / WebUI / Civitai / Forge-style `parameters`

- Look in PNG `tEXt` and `iTXt` with keyword `parameters`.
- Parse into:
  - prompt
  - negative prompt
  - steps
  - sampler
  - scheduler / schedule type
  - CFG
  - seed
  - size
  - model / checkpoint
  - model hash
  - clip skip
  - denoise
  - hires fields
  - upscaler
  - LoRA tokens in prompt
  - LoRA hashes
  - tool version
  - preserve unknown key/value tail

### ComfyUI

- Look for PNG `tEXt` keys `prompt` and `workflow`.
- Store both raw JSON blobs.
- Extract normalized values from nodes:
  - positive and negative text nodes
  - checkpoint / UNET / VAE / CLIP loaders
  - seed
  - steps
  - sampler
  - scheduler
  - CFG
  - width / height
  - denoise
  - save prefix
  - frontend / workflow version

### C2PA / JUMBF / `caBX`

- Look for PNG `caBX`.
- Parse JUMBF boxes and CBOR claims/assertions.
- Good normalization targets:
  - provenance format = `C2PA`
  - claim generator
  - software agent / model family if present
  - action list
  - digital source type
  - instance id
  - ingredient / thumbnail / signature presence
- Do not expect prompt fields here; these samples only expose provenance.

### SillyTavern cards

- Look for PNG `tEXt` keyword `chara`.
- Base64-decode value, then parse JSON.
- Treat as a different metadata family than image generation params.

## Recommended unified schema direction

At minimum, keep both normalized fields and raw source blobs:

- `source_format`
- `tool_name`
- `tool_version`
- `metadata_container`
- `metadata_path`
- `raw_text`
- `raw_json`
- `raw_cbor_or_jumbf`
- `ai_prompt`
- `ai_negative_prompt`
- `model_name`
- `model_hash`
- `checkpoint_name`
- `vae_name`
- `clip_name`
- `loras_json`
- `sampler`
- `scheduler`
- `cfg_scale`
- `steps`
- `seed`
- `width`
- `height`
- `denoise_strength`
- `upscaler`
- `hires_json`
- `provenance_json`
- `character_card_json`
- `unparsed_kv_json`

The raw blob matters. Several sources embed far more than the first-pass normalized fields, and those extra fields will keep changing.
