## MediaLens v1.1.2

### Summary
This release makes duplicate and similar-image cleanup more reliable and transparent. MediaLens now explains why files are recommended, gives you control over how decisions are made, and ensures real-world libraries produce consistent, trustworthy results.

### Highlights
- Added Duplicate and Similarity Auto Resolve Rules settings with configurable rules and ranking priorities.
- Added clearer variant labels such as color vs grayscale, cropped vs full frame, largest vs smallest file, and preferred format.
- Fixed duplicate and similar review so large real-world folders populate results again after scan and pHash backfill.

### Notes
- Similar-image detection still depends on perceptual hashes for images, while exact duplicate detection continues to use content hashes.
- This release focused on making duplicate/similar review trustworthy and stable before expanding deeper auto-resolve policies.

---

Full Changelog:
https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md
