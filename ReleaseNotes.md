## MediaLens v1.1.18

### Summary

This release improves reliability on installed Windows systems. MediaLens now uses a cleaner per-user app-data location and includes a safer gallery rendering path for machines that could show a black embedded gallery.

### Highlights

- Fixed installs where the gallery could render as a black surface even though media was still present underneath.
- Moved logs, settings, and database storage to `%APPDATA%\MediaLens\` instead of the old legacy naming.
- Existing installs automatically migrate forward so users keep their saved settings and library data.

### Notes

- Added deeper WebEngine logging to help diagnose any remaining machine-specific gallery rendering problems.

Full Changelog:
<https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md>
