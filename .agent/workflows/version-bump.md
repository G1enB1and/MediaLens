---
description: /version-bump - Bumps version in all files and updates CHANGELOG.md
---

This workflow automates the version release process.

1. **Calculate New Version**:
    * Read the current version from `VERSION`.
    * If an argument is provided (e.g., `/version-bump 1.0.5`), use that.
    * Otherwise, increment the patch version (e.g., `1.0.4` -> `1.0.5`).

// turbo
2.  **Sync Files**:
    *   Run the version bump script:
        ```powershell
        python scripts/version_bump.py <new_version>
        ```

1. **Fetch Git History**:
    * Retrieve the last 15 commits:

        ```powershell
        git log -15 --pretty=format:"* %s"
        ```

2. **Update CHANGELOG.md**:
    * Create a new section at the TOP of `native/mediamanagerx_app/CHANGELOG.md` for the new version.
    * Format: `## v<new_version> (Current)` (and change the old "Current" to just the version number).
    * Categorize all bullets into subheadings: `### Added`, `### Changed`, or `### Removed`.
    * **CRITICAL**: Do NOT change any existing version information below the new section.

3. **Verify**:
    * Verify all version references in `VERSION`, `main.py`, `installer.iss`, and `pyproject.toml` are consistent.
