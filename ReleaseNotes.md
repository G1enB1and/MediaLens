## MediaLens v1.2.7

### Summary

This release makes Paddle OCR repair safer and easier to diagnose. MediaLens now prepares a clean OCR runtime first, verifies it, and only replaces the active runtime after the new one is working.

### Highlights

- Paddle OCR repair is less likely to leave behind a broken partial runtime after a failed install.
- Local AI setup keeps showing active Paddle install progress instead of switching back to old probe errors mid-install.
- A dedicated Paddle install log now gives clearer details if OCR setup still fails on a specific PC.

### Notes

- This update is focused on Paddle OCR setup reliability, especially for Windows systems using GPU OCR support.

Full Changelog:
<https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md>
