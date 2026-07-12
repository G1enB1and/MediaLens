## MediaLens v1.5.2

### Summary

This release expands MediaLens local AI with stronger Gemma 4 GGUF vision support, and more reliable SAM 3 and InsightFace installers. It also polishes Image Editor object and mask workflows, improves Details panel AI feedback, and makes local model setup easier to inspect and repair.

### Highlights

- Use Gemma 4 and Gemma 4 Abliterated GGUF models more reliably for tags, descriptions, and AI OCR, with working multimodal projectors and automatic selection of installed models.
- Install and repair SAM 3 and InsightFace with clearer runtime diagnostics, better GPU fallback handling, saved Hugging Face token reuse, and more visible model-folder controls.
- Improved Image Editor with better Layer Mask workflow and better Object Aware Selection and masking. 

### Notes

- Flux Klein, SAM 3, InsightFace, and Gemma GGUF remain optional Local AI installs and are not bundled into the main MediaLens installer.
- Local model folder buttons now open the exact model-specific storage location, making it easier to add, remove, or reuse downloaded model files. 

Full Changelog:
https://github.com/G1enB1and/MediaLens/blob/main/CHANGELOG.md
