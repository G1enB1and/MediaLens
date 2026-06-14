## MediaLens v1.4.3

### Summary

This release refines the new MediaLens People workflows with stronger bulk-review behavior, better deduplication, per-person group management, and much better responsiveness when reviewing people with large image sets.

### Highlights

- Review people from the Bulk Editor more reliably with deduplicated face cards, cleaner per-image summaries, and counts that stay scoped to the files you are actually working on.
- Work through large people libraries more smoothly thanks to async loading, lazy thumbnail updates, cached people-per-image mappings, and better default splitter behavior.
- Manage group membership directly from each detected person card in the bulk People editor using the same custom typed dropdown workflow as People naming and renaming.
- Use a more polished bulk People image list with improved layout, clearer People summaries, per-image Ignore, and better thumbnail and button behavior in both wide and narrow panel sizes.
- Keep Review People, bulk People, and per-image summaries in sync with matching deduplication logic so duplicate bridge rows no longer create repeated cards or repeated names.

### Notes

- This release also moves bulk People group actions into per-person cards, adds Ignore Unnamed support in bulk review, and renames the bulk editor bottom section from Detected People to People for clearer wording.

Full Changelog:
https://github.com/G1enB1and/MediaLens/blob/main/CHANGELOG.md
