## MediaLens v1.1.37

### Summary

This release improves Paddle OCR setup and status reporting, especially for systems with NVIDIA GPUs. It also makes source testing match installed builds more closely, reducing the need to rebuild while debugging OCR runtime issues.

### Highlights

- Paddle OCR status now clearly shows GPU success, CPU fallback, or a repairable GPU runtime problem.
- AI Models status checks now show as checks, not installs, until you explicitly click Install.
- Source runs now use the same AppData AI runtime paths as installed builds by default.

### Improvements

- Paddle installation keeps the final selected GPU runtime from being replaced by dependency resolution.
- Paddle setup checks and repairs pip without upgrading pip on every install.
- NVIDIA detection tries direct `nvidia-smi` paths and reports clearer detection details.
- AI Models expand and collapse arrows now use the existing themed SVG assets.
- Model install progress no longer expands unrelated model rows.
- The gallery loading message no longer shows encoded text.

### Notes

- CPU fallback remains supported for systems without a usable NVIDIA GPU.
- If an NVIDIA GPU is detected but only CPU Paddle is installed, MediaLens now shows a repairable GPU error instead of treating it as a clean install.

Full Changelog:
https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md
