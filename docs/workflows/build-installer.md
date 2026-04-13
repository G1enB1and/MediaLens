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
- The build script intentionally uses `.\.venv\Scripts\pyinstaller.exe` so packaged builds include the project’s installed dependencies instead of whatever happens to be in a global Python or Conda environment.
- The build script intentionally writes PyInstaller output to a unique temporary directory under `.pyinstaller-dist` so builds do not fail when an older `dist/MediaLens` folder is locked by Explorer, antivirus, or a running app.
- If `.venv` is missing required packages, install from `requirements.txt` before running the build.
