## MediaLens v1.5.0

### Summary

This major update brings SAM 3-powered object segmentation into the Image Editor and makes object cutouts, masks, and selection editing much more capable. It also improves Local AI setup with guided Hugging Face access, background downloads, stronger GPU handling, clearer progress, and immediate cancellation.

### Highlights

- Automatically separate people, pets, and objects into editable layers and masks with Meta SAM 3, including better prompt control, generated image-specific prompts, and known-person naming from MediaLens People data.
- Edit selections and masks with more serious raster-editor tools, including Object Aware selection, layer masks, mask painting, refine brushes, lasso refinement, free transform, grow, shrink, feather, copy, cut, paste, and Select Pixels.
- Install and run SAM 3 more smoothly with a dedicated local runtime, early model downloads, Hugging Face token prompting, GPU fixes, live progress feedback, timeout recovery, and immediate cancel behavior.

### Notes

- This release carries forward the previously prepared v1.4.7 work and expands it into v1.5.0 because the Image Editor and SAM 3 changes are large enough for a major release step.
- SAM 3 remains an optional Local AI install and is not bundled into the main installer.

Full Changelog:
https://github.com/G1enB1and/MediaLens/blob/main/CHANGELOG.md
