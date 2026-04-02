## MediaLens v1.1.6

### Summary

This release adds Image Comparison, a new workspace for judging two images in place without leaving the gallery. It plugs directly into duplicate and similarity review, making it much faster to inspect differences, choose a winner, and clean up near-duplicates with confidence.

### Highlights

- New Image Comparison panel with left and right image slots and a central reveal slider for true in-place A/B review
- Load images by drag and drop, browse buttons, or gallery right-click actions like `Compare Images` and `Compare With Left/Right`
- Synchronized zoom and pan keep both images aligned during close inspection, with quick hold-to-isolate preview on either side
- Comparison cards carry over keep/best actions and recalculate smart labels for the current two-image decision instead of reusing the larger group context

### Notes

- The former bottom AI placeholder area now hosts Image Comparison.
- Opening Settings temporarily hides the comparison panel so the settings window can use the full center height.
- Settings categories now scroll when the settings window is made smaller.

---

Full Changelog:
https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md
