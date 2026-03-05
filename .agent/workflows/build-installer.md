---
description: How to build the MediaManagerX setup installer
---

This workflow describes how to build the standalone executable and the Windows setup installer for MediaManagerX.

// turbo

1. Run PyInstaller to bundle the application:

   ```powershell
   pyinstaller MediaManagerX.spec --noconfirm
   ```

2. Verify that the application bundle was created in `dist/MediaManagerX`.

// turbo
3. Compile the Inno Setup installer using the absolute path to `ISCC.exe`:

   ```powershell
   & "C:\Users\glenb\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer.iss
   ```

1. The final installer will be created in the root directory as `MediaManagerX_Setup.exe`.
