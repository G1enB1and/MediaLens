## MediaLens v1.1.36

### Summary

This release focuses on startup reliability and a clearer OCR setup experience. MediaLens now avoids a Windows startup path that could crash just after the splash screen, while OCR settings and model status are easier to understand and manage.

### Highlights

- Startup is more reliable on affected Windows installs that previously crashed just after the splash screen.
- OCR setup is easier to review with clearer Fast OCR, AI OCR, and Paddle runtime status.
- Review workflows now make it faster to generate OCR text and mark files as having no text.

### Improvements

- Settings > AI opens more quickly because model status checks now run only when needed.
- Paddle OCR status now shows whether GPU is actually active.
- Review-window OCR generation updates in place without reloading and re-sorting the review list.

### Notes

- Windows builds now keep WebEngine's default page during startup unless diagnostic custom-page logging is explicitly enabled.

Full Changelog:
https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md
