## MediaLens v1.1.24

### Summary

This release makes gallery filtering more trustworthy and predictable, especially when working with Text Detection and AI Detection. Scanner runs, manual overrides, pagination, and filter dropdowns now behave more consistently.

### Highlights

- Text Detection filters no longer treat weak text_likely signals as final results, relying instead on stronger and verified detection signals.
- Running Text Detection from Settings now performs a real rescan instead of finishing instantly from cached values.
- Gallery controls now behave more naturally, with pagination returning to the top and filter dropdowns collapsing when you click away.

### Notes

- This update includes a database-safe behavior change for Text Detection status: `text_likely` remains available as a weak scanner candidate signal, but it no longer marks media as Text Detected by itself.

Full Changelog:
<https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md>
