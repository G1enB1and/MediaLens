## MediaLens v1.5.3

### Summary

MediaLens can now find meaningfully related images across your entire library, not just duplicates or edits. This update combines local DINOv2 visual matching with improved edited-version, tag, duplicate, reverse lookup, and People workflows.

### Highlights

- Find visually similar images using optional local DINOv2 analysis, with cached results and consistent five-level thresholds.
- Compare visually similar files, edited versions, similar tags, and exact duplicates from separately configurable Details Panel sections.
- Use the redesigned reverse image lookup workspace with visual evidence, optional Google Cloud Vision results, and local AI page analysis.
- Open detected people's galleries and similarity results without losing the original file, gallery scope, or page when you go Back.

### Notes

- DINOv2 remains an optional Local AI install and is not bundled into the main MediaLens installer.
- The first DINOv2 scan of a scope takes longer; unchanged results are cached, and later scans only process new or modified files.
- Installed builds now use WebEngine hardware acceleration by default for smoother animated GIF playback, with software compatibility mode still available.

Full Changelog:
https://github.com/G1enB1and/MediaLens/blob/main/CHANGELOG.md
