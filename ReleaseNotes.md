## MediaLens v1.5.4

### Summary

This release turns FLUX.2 Klein into a practical, gallery-integrated image generation workspace while making everyday browsing feel faster and more dependable. Create and edit images with references, structural guidance, LoRAs, masks, and flexible canvases, then see new results appear in the gallery automatically.

### Highlights

- Generate or edit images locally with FLUX.2 Klein using up to four visual inputs, structural guides, LoRAs, inpainting, outpainting, and flexible canvas sizes.
- Work in a responsive three-column generator beneath the gallery, with progressive controls, painted masks, reference-based sizing, and automatic output refresh.
- Browse more smoothly with reliable double-click selection, preserved lightbox state, responsive Details loading, and steadier animated GIF playback.

### Notes

- ComfyUI and the selected Klein model begin loading when the generator opens, reducing the wait after Generate is clicked.
- ComfyUI sessions now shut down completely so old model processes do not consume GPU memory or stall later generations.
- Optional model runtimes and weights remain separate from the main MediaLens installer.

Full Changelog:
https://github.com/G1enB1and/MediaLens/blob/main/CHANGELOG.md
