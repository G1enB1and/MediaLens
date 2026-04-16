## MediaLens v1.1.20

### Summary

This release makes MediaLens easier to support on more machines with safer debugging-log bundles, clearer failure details, and more self-contained video tooling.

### Highlights

- **Safer Support Logs:** MediaLens now creates sanitized debugging-log bundles that exclude private app data such as databases, settings, thumbnails, recycle-bin files, and media files.
- **Optional Log Submission:** A new Help menu flow can submit debugging logs after user consent once a support endpoint is configured.
- **More Reliable Video Support:** Packaged builds now include FFmpeg and FFprobe, so video thumbnails and probing no longer depend on tools already installed on the user's PC.

### Notes

- Debugging logs now live under `%APPDATA%\MediaLens\debugging-logs\`.
- Existing root-level app logs, faulthandler logs, and crash reports are moved into the new debugging-log folder automatically.
- The included DreamHost support endpoint template is a starter for future low-cost support-log uploads.

Full Changelog:
https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md
