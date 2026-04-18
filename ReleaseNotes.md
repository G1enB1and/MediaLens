## MediaLens v1.1.25

### Summary

This release introduces local AI-powered tagging and description generation directly into MediaLens, turning your library into something you can understand, search, and organize automatically. It also improves gallery stability and behavior during everyday workflows, making browsing, sorting, and cleanup feel more consistent and reliable.

### Highlights

- MediaLens can now generate tags and natural-language descriptions locally, using separate AI models and workflows designed for accuracy and control.
- AI-generated tags and descriptions integrate directly into search, filtering, and metadata workflows.
- Keep randomized galleries in the same order for the rest of the session, even after deletes, hides, refreshes, and metadata updates.
- Use masonry view with fewer jumps, flashes, and older JPG sizing problems.

### Notes

- Local AI models live outside the app package and are ignored by git, so they can remain available without bloating source control.
- Full changelog: <https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md>
