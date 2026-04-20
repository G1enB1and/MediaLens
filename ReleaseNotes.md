## MediaLens v1.1.30

### Summary

This release makes large folders feel significantly faster and more responsive during scanning. MediaLens now avoids unnecessary work by detecting changes more efficiently, prioritizing visible content, and resuming scans more intelligently.

### Highlights

- Large folders now spend far less time checking for changes before the gallery becomes usable.
- Visible media is scanned first, so on-screen content loads and updates sooner.
- Scans resume more gracefully after interruptions, reducing wasted work.

### Notes

- This release also fixes scanner database threading issues that could surface as background scan errors during heavy activity.

- Full Changelog: <https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md>
