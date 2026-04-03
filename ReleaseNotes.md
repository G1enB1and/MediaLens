## MediaLens v1.1.6

### Summary

This release introduces Image Comparison, a new workspace for evaluating two images in place without leaving the gallery. It integrates directly with duplicate and similarity review, making it faster to inspect differences, choose the better version, and clean up near-duplicates with confidence.

### Highlights

New Image Comparison panel with left and right image slots plus a central reveal slider for true in-place A/B review
Load images using drag and drop, browse buttons, or gallery context menu actions such as Compare Images and Compare With Left/Right
Synchronized zoom and pan keep both images aligned during close inspection, with hold-to-isolate preview on either side for quick single-image checks
Comparison cards preserve keep/best actions and recalculate smart labels specifically for the current two-image decision instead of reusing broader group context

### Notes

The former bottom AI placeholder area now hosts Image Comparison
Opening Settings temporarily hides the comparison panel so the settings window can use the full center height
Settings categories now scroll properly when the settings window is reduced in size

---

Full Changelog:
<https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md>
