## MediaLens v1.0.22

### Summary
This release makes folder navigation feel much more capable and much less fragile. The header now behaves more like Windows Explorer, and several navigation paths were moved off the main UI thread to reduce freezing during browsing.

### Highlights
- Added a full Explorer-style address bar with clickable breadcrumbs, dropdown chevrons, editable path entry, and keyboard-friendly folder menus.
- Added a new hideable, resizable bottom panel with persisted size and visibility to reserve space for the upcoming AI chat experience.
- Moved several navigation-time folder and gallery lookups off the UI thread to improve responsiveness during folder changes.

### Notes
- The installer/build flow was also tightened up so stale packaged files are less likely to slip into a release.

---

Full Changelog:
https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md
