## MediaLens v1.2.2

### Summary

This release makes MediaLens easier to repair, reinstall, and move safely. It adds library backup and restore tools, gives uninstall a real cleanup choice, and improves the startup updater path used to recover from broken builds.

### Highlights

- Export and import a MediaLens library backup from the File menu.
- Choose whether imported recycle-bin files, thumbnails, local AI models, and AI runtimes merge with or replace what is already installed.
- Uninstall can now remove selected app-data categories, including legacy leftovers, for a cleaner reinstall.

### Notes

- Startup update dialogs are now parented to the splash screen, reducing stray window flashes before the main app opens.
- Library backups intentionally exclude old MediaManagerX legacy files.

Full Changelog:
https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md
