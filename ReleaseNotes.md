## MediaLens v1.1.28

### Summary

This release fixes a local AI setup failure in the v1.1.27 installer. Model installation can now proceed correctly, and setup errors show useful details in the Local AI Models window instead of only showing a generic error.

### Highlights

- Fixed local AI model installs failing immediately with an internal settings error.
- See install progress and error details directly in the Local AI Models window.
- Developer runs can now be pointed at the same installed local AI folders to avoid maintaining duplicate model copies.

### Notes

- Local AI model files and dependencies are still installed only when selected. They are not bundled into the main installer.
- Full changelog: <https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md>
