---
description: /version-bump - Bumps version in all files and updates CHANGELOG.md
---

This workflow automates the version release process.

Formatting rules for all generated changelog and release-note content:

* Never use nested bullet lists.
* Always add a blank line below every header.
* Never use horizontal rules like `---` except between release versions in `CHANGELOG.md`, so version boundaries stay easy to skim.
* Never use emojis or mojibake.
* Never edit previous version sections. Only add or modify the current version being prepared; past versions are locked and must stay consistent with already published release history.

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
    * Add user-facing release messaging directly into the changelog section before the technical categories:

        ```markdown
        ## v<new_version> (Current)

        ### Summary
        <1-2 sentence plain-English overview of why this release matters>

        ### Highlights
        - <highest-value user-facing improvement>
        - <second most noticeable improvement>
        - <optional third user-facing improvement>

        ### Added
        ...
        ```

    * Keep `Summary` and `Highlights` concise and non-technical so users reading the in-app `What's New` view can quickly understand why they should care about the update.
    * Categorize all bullets into subheadings: `### Added`, `### Changed`, or `### Removed`.
    * **CRITICAL**: Do NOT change any existing version information below the new section.

3. **Create ReleaseNotes.md**:
    * Overwrite `ReleaseNotes.md` in the repo root on every version bump.
    * Base it only on the newest version section from `native/mediamanagerx_app/CHANGELOG.md`.
    * Write it for less technical readers than the changelog.
    * Keep it short, polished, and GitHub-release friendly.
    * Use this general structure:

        ```markdown
        ## MediaLens v<new_version>

        ### ✨ Summary
        <1-2 sentence plain-English overview of why this release matters>

        ### 🔥 Highlights
        - <highest-value user-facing improvement>
        - <second most noticeable improvement>

        ### 🛠 Notes
        - <important packaging, compatibility, or implementation note if relevant>

        ---

        📄 Full Changelog:
        https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md
        ```

    * Do not leave a trailing separator at the end of `ReleaseNotes.md`
    * When appropriate, prefer friendly headings and labels such as:
        * `🚀 New Features`
        * `⚡ Improvements`
        * `🐛 Fixes`
    * Focus on benefits, polish, and user-facing outcomes rather than deep implementation detail.

4. **Editorial Review Pass**:
    * After drafting both the new changelog section and `ReleaseNotes.md`, run a separate second-pass review/edit step in a fresh prompt or submission.
    * This review pass must be separate from the writing pass. Do not combine drafting and reviewing into one request.
    * In the review pass, pay attention to:
        * clear user-facing value, not just technical correctness
        * whether the `Summary` explains why the update matters
        * whether the `Highlights` are concise, non-repetitive, and focused on reasons to care
        * avoiding wording that simply repeats the `Added` / `Changed` / `Removed` bullets below
        * clarity, flow, grammar, and readability for casual users
        * consistent branding and naming, always using `MediaLens`
        * keeping tone polished and professional without sounding overhyped
        * making sure release notes and changelog entries stay aligned with the actual changes in the repo
        * preserving brevity, especially for in-app `What's New` display
        * catching awkward phrasing, redundancy, or vague statements that could be made more concrete
    * Apply worthwhile edits from that second-pass review before finalizing files.

5. **Verify**:
    * Verify all version references in `VERSION`, `main.py`, `installer.iss`, and `pyproject.toml` are consistent.
    * Verify `ReleaseNotes.md` matches the newest changelog version and was written to the repo root.
