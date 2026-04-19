## MediaLens v1.1.29

### Summary

This release fixes a false local AI install error that could appear after the runtime was created when model files were already present. MediaLens now skips model download when the required files are already on disk and confirms the model as installed.

### Highlights

- Existing local AI model files are detected before MediaLens tries to download them again.
- Install can finish cleanly after creating the runtime when the model files are already present.
- A failed preload/download no longer leaves a false error if the required model files are confirmed on disk.

### Notes

- Local AI model files and dependencies are still installed only when selected. They are not bundled into the main installer.
- Full changelog: <https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md>
