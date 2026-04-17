## MediaLens v1.1.22

### Summary

This release makes MediaLens more dependable when installing updates and playing videos in the lightbox. Update prompts now appear earlier during startup, and legacy cleanup helps prevent old shortcuts or folders from opening the wrong version.

### Highlights

- Startup update checks now use a native dialog before the main app opens, improving the chance that an update can repair a broken build.
- Lightbox video playback is smoother after reducing background work and avoiding expensive video rendering paths.
- Installer cleanup now migrates old app data into `%APPDATA%\MediaLens\` and removes stale legacy shortcuts and folders.

### Notes

- Existing settings, databases, thumbnails, and recycle-bin data are preserved during migration whenever possible.
- If a legacy file conflicts with an existing file in `%APPDATA%\MediaLens\`, the current file is kept and the legacy copy is preserved with a `.legacy-N` name.

Full Changelog:
https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md
