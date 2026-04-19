---
description: How to build the MediaLens setup installer
---

This workflow describes how to build the standalone executable and the Windows setup installer for MediaLens.

Canonical human-facing copy: `docs/workflows/build-installer.md`

// turbo

1. Run the build script, which uses the project `.venv` PyInstaller and then compiles the installer:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\build_installer.ps1"
   ```

2. Verify that the script reports a successful bundle path under `.pyinstaller-dist/<build-id>/MediaLens`.

3. Verify that the final installer was created in the repo root as `MediaLens_Setup.exe`.

Notes:
- The build script intentionally uses `.\.venv\Scripts\pyinstaller.exe` so packaged builds include the project's installed dependencies instead of whatever happens to be in a global Python or Conda environment.
- The build script intentionally writes PyInstaller output to a unique directory under `.pyinstaller-dist` so builds do not fail when an older `dist/MediaLens` folder is locked by Explorer, antivirus, or a running app.
- The build script intentionally reuses `.pyinstaller-temp/MediaLens` so normal rebuilds can reuse PyInstaller analysis cache. Use `-Clean` only when a full PyInstaller rebuild is needed.
- If `.venv` is missing required packages, install from `requirements.txt` before running the build.
- Local AI model dependencies and model weights are intentionally not bundled into the installer. The installer includes only the lightweight local AI worker source files and the per-model requirement files (`requirements-local-ai-wd-swinv2.txt`, `requirements-local-ai-internlm-xcomposer2.txt`, and `requirements-local-ai-gemma.txt`).
- In installed builds, per-model local AI virtual environments should live under `%APPDATA%\MediaLens\ai-runtimes` by default. This keeps optional model runtimes writable for the current user and prevents one model's dependency stack from affecting the app or another model.
- The installer does not prompt for or download optional AI runtimes during setup. MediaLens shows Local AI Models setup after install/update and also exposes model installation from Settings > AI. Adding an embedded Python bootstrap should be handled as an app-side downloader/bootstrapper concern, not as a larger setup bundle.
- If the AI worker source files or per-model requirement files are missing from the PyInstaller bundle, `scripts\build_installer.ps1` must fail before compiling the installer.
- If heavyweight local AI runtime packages such as Torch, Transformers, ONNX Runtime, or Hugging Face Hub are found inside the PyInstaller bundle, `scripts\build_installer.ps1` must fail; those packages belong in the per-model virtual environments instead.
