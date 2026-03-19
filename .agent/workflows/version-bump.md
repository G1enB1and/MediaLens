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

3. **Create ReleaseNotes.md**:
    * Overwrite `ReleaseNotes.md` in the repo root on every version bump.
    * Base it only on the newest version section from `native/mediamanagerx_app/CHANGELOG.md`.
    * Write it for less technical readers than the changelog.
    * Keep it short, polished, and GitHub-release friendly.
    * Use this general structure:

        ```markdown
        ## MediaManagerX v<new_version>

        ### ✨ Summary
        <1-2 sentence plain-English overview of why this release matters>

        ### 🔥 Highlights
        - <highest-value user-facing improvement>
        - <second most noticeable improvement>

        ### 🛠 Notes
        - <important packaging, compatibility, or implementation note if relevant>

        ---

        📄 Full Changelog:
        https://github.com/G1enB1and/MediaManagerX/blob/dev/native/mediamanagerx_app/CHANGELOG.md

        ---
        ```

    * When appropriate, prefer friendly headings and labels such as:
        * `🚀 New Features`
        * `⚡ Improvements`
        * `🐛 Fixes`
    * Focus on benefits, polish, and user-facing outcomes rather than deep implementation detail.

4. **Verify**:
    * Verify all version references in `VERSION`, `main.py`, `installer.iss`, and `pyproject.toml` are consistent.
    * Verify `ReleaseNotes.md` matches the newest changelog version and was written to the repo root.
