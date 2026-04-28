## MediaLens v1.2.6

### Summary

This release makes MediaLens safer to open on a wider range of Windows PCs. It avoids surprise full-drive scanning on startup, keeps large scans more responsive, improves drive browsing, and strengthens Local AI setup behavior.

### Highlights

- MediaLens now starts with no folder open by default, so users can adjust settings before choosing what to scan.
- The folder tree can browse other Windows drives, making photo libraries on secondary or external drives easier to open.
- Paddle OCR repair now performs clearer GPU package checks and avoids quietly falling back to CPU on compatible NVIDIA systems.

### Notes

- Existing startup options are still available in Settings > General if you prefer reopening the last folder or always opening a specific folder.
- Local AI recommended settings choose a profile but wait for an explicit install or download click before downloading files.

Full Changelog:
<https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md>
