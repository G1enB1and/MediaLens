## MediaLens v1.1.32

### Summary

This release makes Local AI more dependable in everyday use, especially in the installed app. MediaLens now handles more image formats correctly for Gemma, keeps model selection more consistent, and smooths out several frustrating Local AI setup and runtime problems.

### Highlights

- Gemma 4 is more reliable in the installed build, with fixes for model selection, runtime launch behavior, and fallback handling.
- AVIF, HEIC, HEIF, TIFF, WebP, animated images, and video sources now go through preview-image conversion before being sent to Gemma.
- Local AI status and setup behavior is more consistent, making it easier to switch models and understand what MediaLens is actually using.

### Notes

- This release includes multiple Local AI reliability fixes focused on installed-build Gemma behavior and difficult image-format edge cases.

Full Changelog:
https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md
