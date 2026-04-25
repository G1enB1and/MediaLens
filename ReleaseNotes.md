## MediaLens v1.1.36

### Summary

This release focuses on startup reliability and a clearer OCR setup experience. MediaLens now avoids a Windows startup path that could crash just after the splash screen, while OCR settings and model status are easier to understand and manage.

### Highlights

- Startup is more reliable on affected Windows installs that previously crashed just after the splash screen.
- OCR setup is easier to review with clearer Fast OCR, AI OCR, and Paddle runtime status.
- Review workflows now make it faster to generate OCR text and mark files as having no text.
- Paddle OCR now tries harder to use GPU first, then falls back to CPU with a clear reason when needed.

### Improvements

- Settings > AI opens more quickly because model status checks now run only when needed.
- Paddle OCR status now shows whether GPU is actually active.
- Review-window OCR generation updates in place without reloading and re-sorting the review list.
- Partial failed Paddle OCR runtimes no longer appear as installed.
- AI Models rows now keep their explicit expand or collapse state while installs run.
- Paddle CPU fallback can use PyPI if Paddle's CPU package index is unreachable.
- Paddle GPU installs now keep the selected GPU runtime as the final Paddle package after PaddleOCR dependency resolution.
- Paddle status no longer shows `GPU: CPU` while GPU detection is still unknown, installing, or failed before a valid CPU fallback exists.
- Paddle install from the AI Models status page now stays in the installing state instead of immediately refreshing back to not installed.
- Dev runs can use installed-build AI paths by setting `MEDIALENS_USE_INSTALLED_AI_PATHS=1`.
- Source runs through `python run.py` now use installed-build AI paths by default, so Paddle fixes can be tested without rebuilding.
- Paddle install now checks/repairs pip instead of upgrading pip itself on every install, avoiding a crash-prone package-updater step.
- AI Models status checks now show `Checking` instead of `Installing`, so opening the page does not look like it started an install.
- Paddle status now treats CPU-only Paddle on a detected NVIDIA GPU as a repairable GPU error instead of a clean installed state.

### Notes

- Windows builds now keep WebEngine's default page during startup unless diagnostic custom-page logging is explicitly enabled.
- Paddle OCR CPU fallback remains supported for systems without a usable NVIDIA GPU.

Full Changelog:
https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md
