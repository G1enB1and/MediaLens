---
description: How to build the MediaLens setup installer
---

This workflow describes how to build the standalone executable and the Windows setup installer for MediaLens.

// turbo

1. Run PyInstaller to bundle the application:

   ```powershell
   pyinstaller MediaLens.spec --noconfirm
   ```

2. Verify that the application bundle was created in `dist/MediaLens`.

// turbo
3. Compile the Inno Setup installer using the absolute path to `ISCC.exe`:

   ```powershell
   & "C:\Users\glenb\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer.iss
   ```

1. The final installer will be created in the root directory as `MediaLens_Setup.exe`.
