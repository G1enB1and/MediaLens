# Change Log

## v1.1.26 (Current)

### Summary

This release makes local AI model support much more dependable and flexible. MediaLens now isolates each AI model in its own worker process and runtime, so adding or testing new models is less likely to break models that already work.

### Highlights

- Gemma 4, InternLM XComposer2, and WD SwinV2 can now work side by side without sharing fragile dependency stacks.
- Description prompts now behave more naturally, with tags and starter text included only through prompt instructions instead of being forced onto the final response.
- Local AI failures and long-running generation are handled more clearly, with safer subprocess cleanup when the app closes.

### Added

- Added Gemma 4 E2B Instruct as an optional local AI model for tags and descriptions.
- Added a local AI model registry so each model can define its own worker module, runtime folder, and user-facing dropdown label.
- Added separate worker subprocess entry points for WD SwinV2 tag generation and InternLM XComposer2 description generation.
- Added separate optional dependency files for WD SwinV2, InternLM XComposer2, and Gemma 4 runtimes.
- Added AI settings status for the selected tag and description models, including an install action when the model runtime is missing.
- Added a Local AI Models setup dialog that appears after installing or updating MediaLens and shows install status for each optional model runtime.
- Added a managed Python bootstrap for local AI model installs so MediaLens can create per-model runtimes without requiring users to install Python themselves.
- Added clearer local AI model download size estimates based on the actual model files and major runtime packages.
- Added a View menu action to open Local AI Models and Status at any time.
- Added `{starter}` support for description prompts so users can place the starter text exactly where they want it.

### Changed

- Changed local AI execution so each model can run in its own virtual environment instead of sharing one dependency set.
- Changed installed builds to store optional local AI runtimes under `%APPDATA%\MediaLens\ai-runtimes` instead of the app install folder.
- Changed Generate Tags and Generate Description to open Local AI Models setup when the selected model runtime is not installed.
- Changed AI Settings model status details into separate Description, Size, Status, and Location rows.
- Changed description prompt handling so `{tags}` is opt-in; tags are only inserted when the prompt includes the `{tags}` placeholder.
- Changed `Start Description With` so it is passed to the model as an instruction instead of being prepended to the generated response.
- Changed InternLM XComposer2 loading back to the working legacy path after the Gemma integration work showed it requires a different runtime approach.
- Changed local AI progress and error handling to give clearer in-app updates during long-running generation and failures.
- Changed app shutdown handling so active local AI worker subprocesses are canceled and terminated more safely.

---

## v1.1.25

### Summary

This release introduces local AI-powered tagging and description generation directly into MediaLens, turning your library into something you can understand, search, and organize automatically. It also improves gallery stability and behavior during everyday workflows, making browsing, sorting, and cleanup feel more consistent and reliable.

### Highlights

- Local AI can now generate tags and descriptions into the MediaLens database, with separate controls for each workflow.
- Randomized galleries now keep the same session order after refreshes, deletes, hides, and metadata updates.
- Masonry view is more reliable when deleting, hiding, and displaying older JPG files with EXIF orientation.

### Added

- Added local AI tag generation using the local WD SwinV2 tagger model.
- Added local AI description generation that uses existing tags as context, producing more accurate and relevant descriptions.
- Added separate Generate Tags and Generate Description actions in the Details panel.
- Added AI settings groups for Tags and Descriptions, with separate prompts and generation settings for each workflow.
- Added Union Merge as the default tag write mode so generated tags append without duplicates.
- Added a scrollable multiline Tags editor in the Details panel.

### Changed

- Changed random sorting to assign each media path a session-stable random rank that resets only when the app starts or randomize is enabled again.
- Changed delete and hide handling in masonry view to return near the previous scroll position instead of jumping to the top.
- Changed masonry sizing to account for JPG EXIF orientation when reading image dimensions.
- Changed gallery refreshes to skip unnecessary DOM rebuilds when the visible gallery signature has not changed, reducing fast flashes during background updates.
- Changed lightbox video rendering to reduce expensive per-frame styling and improve playback performance.
- Changed AI prompt inputs in Settings to match the same input styling as the rest of the settings controls.

---

## v1.1.24

### Summary

This release fixes inconsistent Text Detection behavior and makes gallery filtering far more trustworthy and predictable. Manual scanner runs now perform real rescans, filters react instantly to overrides, and navigation controls feel more polished.

### Highlights

- Text Detection filters no longer treat weak text_likely signals as final results, relying instead on stronger and verified detection signals.
- Running Text Detection from Settings now performs a real rescan instead of finishing instantly from cached values.
- Gallery controls now behave more naturally, with pagination returning to the top and filter dropdowns collapsing when you click away.

### Added

- Added new SVG-based override switches for Text Detection and AI Detection, with clear on/off states across light and dark modes.

### Changed

- Changed effective Text Detection status to use manual overrides, verified text, and stronger text-detection signals instead of treating `text_likely` as source of truth.
- Changed Settings > Scanners > Text Detection > Run Now to rescan existing files and clear stale stronger auto text signals when rebuilding results.
- Changed Text Detection and OCR scanner eligibility so `text_likely` remains only a weak candidate signal, not a final positive result.
- Changed gallery refresh behavior so Text Detection and AI Detection manual override toggles immediately update active Text Detected, No Text Detected, AI, and Non-AI filters.
- Changed pagination so navigating to a different page scrolls the gallery back to the top.
- Changed the Filter By dropdown so it collapses when clicking or focusing outside of it.
- Changed text-filter scanning behavior to avoid the results/no-results blinking loop when filtering by Text Detected or No Text Detected.

---

## v1.1.23

### Summary

This release adds manual OCR text extraction, searchable detected text, and a new Scanners settings category, giving you much more control over text-related metadata tasks. With manual overrides, editable detected text, and background scanner controls, MediaLens makes it easier to find and manage media based on visible text.

### Highlights

- Manual OCR extraction lets you pull real text from images and videos on demand, then review or refine it in the Details panel.
- New Scanners settings provide visibility and control over background Text Detection and OCR schedules.
- Detected Text is now a searchable field in both search and the guided query builder.

### Added

- Added a Scanners settings category that shows real-time status, last-run times, and configurable intervals for background OCR and Text Detection.
- Added Run Now buttons and enable/disable toggles for each scanner service.
- Added a manual OCR button in the Details panel to trigger instant text extraction for the selected file.
- Added OCR support for video files using the existing preview image.
- Added an editable Detected Text field in the metadata panel with Save to DB support for manual corrections.
- Added Detected Text as a searchable field in the Advanced Search guided builder.
- Added manual override toggle buttons for Text / No Text and AI / Non-AI file classification.

---

## v1.1.22

### Summary

This release makes MediaLens more dependable when installing updates and playing videos in the lightbox. Update prompts now appear before the main window opens, while legacy install and app-data cleanup reduce confusion from old shortcuts and folders.

### Highlights

- Update prompts now appear earlier at startup, giving MediaLens a better chance to patch a broken build before the main app loads.
- Lightbox video playback is smoother after reducing expensive background and WebEngine rendering work.
- Installer cleanup now migrates legacy app data into `%APPDATA%\MediaLens\` and removes stale legacy shortcuts and folders.

### Changed

- Moved the update check to the earliest startup point and replaced the web toast update prompt with a native dialog.
- Changed lightbox video styling to avoid WebEngine paths that can force video rendering onto the CPU.
- Changed the gallery overflow behavior to prevent rare horizontal scrollbar flicker during resize.
- Changed installer migration to merge legacy app data into `%APPDATA%\MediaLens\`, remove old branded app-data folders after migration, and clean stale legacy shortcuts/install folders.

### Fixed

- Fixed stale current-user taskbar shortcuts that could continue opening an older legacy install after updating.

---

## v1.1.21

### Summary

This release improves overall UI polish, tag management, and playback performance. The tag workflow is smoother with better dropdowns and database handling, while the details panel and image comparison view are more polished and responsive. Video playback in the lightbox is also more stable with background tasks pausing automatically.

### Highlights

- Tag management is now smoother with the ability to hide list panels, improved dropdowns, and database entries that preserve capitalization.
- The Details panel and Image Comparison view feel more polished with smoother resizing, aligned buttons, and consistent margins.
- Video playback in the lightbox performs more consistently because it now automatically pauses background scanners and animated gifs.

### Added

- Added the ability to hide Tag lists to keep the workspace tidy.

### Changed

- Restyled the Tag Lists dropdown and updated the empty state UI when no lists exist.
- Changed tag database handling to preserve capitalization while intelligently ignoring duplicates with different capitalization.
- Changed Details panel resizing logic to a single shared calculation, keeping buttons and text inputs smoothly aligned while drag-resizing.
- Adjusted margins and padding in the Image Comparison panel for a cleaner look.
- Replaced the comparison close buttons with a symmetrical SVG icon featuring more consistent colors and hover effects.
- Improved lightbox video playback performance by automatically pausing background scanners and animated gifs while a video is playing.

### Fixed

- Fixed tag creation so adding a new tag from the list creates a database entry immediately even if scanning hasn't processed it yet.
- Fixed tag counts to correctly update when showing or hiding nested files and hidden files.

---

## v1.1.20

### Summary

This release makes MediaLens easier to support on more machines with safer debugging-log bundles, clearer failure details, and more self-contained video tooling. It also lays the groundwork for optional support-log submission when a support endpoint is configured.

### Highlights

- Support bundles are now safer to share because they exclude private app data and redact path-like details.
- Debugging logs can be submitted from the Help menu after user consent once an upload endpoint is configured.
- Video thumbnails and probing are more reliable because packaged builds now include FFmpeg and FFprobe.

### Added

- Added a `debugging-logs` folder under `%APPDATA%\MediaLens\` for app logs, faulthandler logs, and crash reports.
- Added startup migration for existing root-level `app.log`, `faulthandler.log`, and `crash-reports` into the new `debugging-logs` folder.
- Added `Help > Create Debugging Log Bundle`, which creates a sanitized zip bundle for support.
- Added `Help > Submit Debugging Logs...`, which creates the sanitized bundle and uploads it only when a support endpoint is configured.
- Added consent, optional contact email, and optional issue notes to the debugging-log submission flow.
- Added hidden upload configuration through `MEDIALENS_DEBUG_UPLOAD_URL`, `MEDIALENS_DEBUG_UPLOAD_TOKEN`, or the matching support settings keys.
- Added a DreamHost-ready PHP upload endpoint template under `support-server/dreamhost`.
- Added DreamHost deployment instructions for a low-cost support-log submission setup.
- Added bundled `ffmpeg.exe` and `ffprobe.exe` packaging during installer builds.

### Changed

- Changed crash reports and diagnostic bundles to redact path-like values where practical.
- Changed normal app logging to keep startup diagnostics and problem reports while dropping routine tree, page-load, and frontend chatter unless verbose logging is enabled.
- Changed video tooling lookup to prefer bundled FFmpeg and FFprobe before falling back to the system PATH.
- Changed video thumbnail, probing, preprocessing, and playback failures to produce more useful app-log entries.
- Changed debugging-log bundles to include only sanitized diagnostic text and recent crash reports, excluding databases, settings, thumbnails, recycle-bin files, and media files.

### Removed

- Removed the installed app's reliance on users having FFmpeg and FFprobe separately installed for video poster generation and probing.

---

## v1.1.19

### Summary

This release refines file scope and folder visibility settings, and updates several actions across the gallery and settings workflows.

### Highlights

- Added settings to easily toggle nested files and folder visibility in the gallery.
- Added new `Delete` and `Rename` actions directly inside Tag Lists for faster organization.
- Updated dialog styling for a more consistent appearance.

### Added

- Added `Include nested files in gallery` and `Show folders in gallery` settings.
- Added a convenient `Include nested files` toggle directly in the header for fast access.
- Added deduplication logic for move/copy operations when both a folder and its nested files are selected.
- Added `Delete` and `Rename` options to Tag Lists.

### Changed

- Changed `Select All` behavior to correctly exclude folders when `Include nested files` is enabled.
- Changed the masonry view to consistently hide folders regardless of the global show-folders setting.
- Changed the file count chip in the header to accurately ignore folders.
- Lowered the delay time for tooltip text and improved tooltip legibility.
- Themed the `Create`, `Rename`, and `Delete` dialog windows to match the app.
- Changed the default install folder to `MediaLens` and fixed database migration from older `MediaManagerX` versions.

### Fixed

- Fixed the `AttributeError: 'GalleryWebPage' object has no attribute 'view'` error that occurred during WebEngine console logging.

---

## v1.1.18

### Summary

This release makes installed Windows builds more dependable. MediaLens now uses a cleaner per-user app-data location and applies safer gallery rendering defaults on systems where the embedded gallery could appear black or fail to paint correctly.

### Highlights

- Fixed installed builds that could show a black gallery surface even while items were still clickable underneath.
- MediaLens now stores logs, settings, and database files under `%APPDATA%\MediaLens\` instead of the old legacy app-data naming.
- Existing installs migrate forward automatically so users keep their settings and library data.

### Added

- Added automatic migration from legacy `G1enB1and\MediaManagerX` and `G1enB1and\MediaLens` app-data folders into `%APPDATA%\MediaLens\`.
- Added automatic migration from the legacy `mediamanagerx.db` filename to `medialens.db`.
- Added extra WebEngine diagnostics to the app log so renderer failures and page-load issues are easier to diagnose on customer machines.

### Changed

- Changed runtime settings storage to use `%APPDATA%\MediaLens\settings.ini` so the installed app no longer depends on a publisher-name subfolder.
- Changed Windows frozen builds to prefer a safer software-rendered WebEngine path when needed, reducing black or non-painted gallery surfaces on affected systems.
- Updated theme and runtime helpers across the main window, recycle bin, and video overlay so all runtime components read from the same MediaLens app-data location.

### Removed

- Removed active use of the legacy `MediaManagerX` app-data namespace for new MediaLens runtime storage.

---

## v1.1.17

### Summary

This release makes duplicate cleanup easier to trust. MediaLens now keeps your review decisions consistent, improves how duplicate matches are identified, and introduces a built-in retention system for safer file cleanup and recovery.

### Highlights

- Duplicate and similar review now loads more smoothly, with clearer progress stages and more stable rendering.
- Selections, folder priorities, and copied tags now behave more consistently during cleanup.
- Exact image duplicates continue matching even after metadata-only edits.
- New built-in retention system gives you a safer alternative to the Recycle Bin, with restore and cleanup controls.

### Added

- Added a built-in MediaLens retention system as an alternative to the Windows Recycle Bin, with configurable retention, review, restore, and delete options.
- Added `Most metadata` to the duplicate priority order so metadata preference can be explicitly ranked alongside folder, format, and size rules.
- Added tag inheritance when copying files inside MediaLens so copied files keep the source file's app tags.

### Changed

- Moved duplicate and similar grouping, ranking, and rule logic out of `main.py` into `review_groups.py` for a cleaner review pipeline.
- Reworked duplicate and similar review rendering to build offscreen first, then reveal cards in a more stable, staged way.
- Improved duplicate and similar progress messaging so folder scanning, grouping, and rendering stages are easier to understand.
- Updated preferred folder persistence so folder priority order is retained more consistently across settings changes and scope changes.
- Changed image duplicate identity to use decoded image content instead of raw file bytes, so metadata-only image edits do not break exact duplicate grouping.

### Removed

- Removed the old in-class duplicate and similar logic copies from `main.py` after the extracted review module became the live implementation.

---

## v1.1.16

### ✨ Summary

This release expands Similar File Rules with preferred folder ranking, giving you more control over how MediaLens decides what to keep. It also improves gallery responsiveness during resizing, panel changes, and grouping transitions.

### 🔥 Highlights

- **Preferred Folder Ranking**  
    Rank folders directly instead of relying on depth-based assumptions when reviewing duplicates and similar files.
- **Folder Priorities Section**  
    A new drag-and-drop interface lets you choose which folders matter and how strongly they influence decisions.
- **Smoother Gallery Updates**  
    The gallery now redraws more proactively, reducing blank or stale areas during resizing, layout changes, and grouping transitions.

### ➕ Added

- Added a **Folder Priorities** section to Similar File Rules with:
  - `Use Preferred Folders` toggle
  - Available folder list based on active scope
  - Drag-and-drop prioritized folder order
- Added **Preferred Folders** to Rule Priorities so folder ranking can influence:
  - Best Overall decisions
  - Keep selections
  - Delete selections
- Added **All Other Folders** as a default grouping baseline, allowing:
  - Important folders to rank above it
  - Less important folders to be pushed below it

### 🔄 Changed

- Replaced folder-depth-based logic with **user-defined folder ranking** when evaluating file organization during duplicate and similar review.
- Updated Similar File Rules to source folders dynamically from the active scope and manage them through a dedicated drag-and-drop workflow.
- Improved gallery refresh behavior with a more proactive relayout system during:
  - Window resizing
  - Splitter adjustments
  - Panel toggles
  - `Group By` transitions

---

## v1.1.15

### Summary

This release significantly improves the Duplicate and Similar files workflow with manual override capabilities and UI refinements, along with important bug fixes for file visibility and bulk tagging.

### Highlights

- Exclude false positives directly from Duplicate and Similar file groups with a new "X" button that remembers your choice on future scans.
- Reorganized Similar File Rules into a streamlined single-page layout with a new button to reset group exclusions.
- Added Open/Close Tag List toggle directly within the Bulk Tag Editor for quicker access to your tags.

### Added

- Added an "X" button to Duplicates and Similar file cards to exclude files from a group (remembers the override for future scans).
- Added a "Reset Group Exclusions" button in Similar File Rules.
- Added "Open/Close Tag List" toggle button within the Bulk Tag Editor.

### Changed

- Moved the Bulk Tag Editor action from the View menu to the Edit menu.
- Reorganized Similar File Rules: Moved priorities from a separate tab to a single-page layout below file formats.
- Improved UI design for similar file cards and Similar File Rules settings.
- The "Group by similar" view now immediately clears the screen and informs you to wait for scanning when switching folders, rather than showing stale results.

### Fixed

- Fixed the "All" checkbox in metadata so it correctly toggles all checks.
- Fixed a bug where dates were occasionally not returned properly from a scan.
- Fixed multi-select hide/unhide logic so it correctly applies to all selected files at once.
- Fixed an issue to ensure all files inside a hidden folder remain hidden when the "show hidden files" setting is disabled.

---

## v1.1.14

### Summary

This release makes tag-heavy cleanup much faster and easier to trust. MediaLens adds a full Tag List workspace, a rebuilt Bulk Tag Editor, and smoother multi-file tagging workflows that keep gallery filtering, selection, and tag feedback aligned.

### Highlights

- Tag List now gives you a dedicated panel for saved tag groups, quick tag filtering, drag sorting, and one-click tagging actions.
- Bulk Tag Editor is now a true separate workspace with common tags, uncommon tags, and faster select-all workflows for editing many files at once.
- Tag filtering, gallery counts, and selection behavior are now much more consistent, so you can move between parent tags and sub-tags without losing context.

### Added

- Added a resizable Tag List panel beside the right sidebar with saved tag lists, sorting modes, drag-and-drop ordering, import-from-file, and quick open and close controls.
- Added tag count buttons and tag-row filtering so the gallery can be narrowed to files using a selected tag directly from the Tag List.
- Added a dedicated Bulk Tag Editor workspace with its own tag input, common tags, uncommon tags, and select-all actions for the current gallery scope.
- Added `View` menu actions for `Show Tag List` and `Bulk Tag Editor`.
- Added empty-state and bulk-editor `Select All` buttons to speed up multi-file tagging workflows.

### Changed

- Reworked the right sidebar so Details, Bulk Tag Editor, and Tag List behave as separate workspaces while still sharing the same panel visibility and resize behavior.
- Updated Tag List actions so adding tags writes to the database immediately in both single-file and bulk workflows.
- Improved tag filtering so temporary tag scope does not overwrite the underlying gallery scope, making it much easier to switch between tags quickly.
- Improved bulk tag feedback so common and uncommon tags stay aligned with the selected files and Tag List highlighting.
- Refined selection behavior so gallery selections remain visible while working in Details, Tag List, and Bulk Tag Editor, and plain clicks return multi-selection back to a single selected file.

---

## v1.1.13

### Summary

This release makes large libraries easier to slice down into manageable work. MediaLens adds Smart Collections and better stackable filters for common cleanup cases, while also improving AI detection so you can trust automatic results or override them when needed.

### Highlights

- Smart Collections now give you one-click views for recent files, missing metadata, and larger files that are worth reviewing.
- Filter By now supports AI / Non-AI, No Tags, No Descriptions, and None to clear all filters.
- AI detection is more consistent across scanning, filtering, and details, and you can now manually confirm AI status when automatic metadata detection is not enough.

### Added

- Added Smart Collections for files acquired or modified in the last 7, 14, or 30 days.
- Added Smart Collections for `No Tags`, `No Description`, and files larger than `3 MB`, `10 MB`, `25 MB`, `100 MB`, and `1 GB`.
- Added stackable `No Tags` and `No Description` filters under `Filter By` so metadata cleanup can be scoped alongside other filters.
- Added stackable `AI Generated` and `Non-AI` filters based on the stored AI detection decision.
- Added a `User Confirmed AI` override in the details panel so manual AI decisions can take priority over automatic detection when needed.

### Changed

- Changed AI filtering to rely on one canonical stored AI decision instead of re-inferring AI state separately in multiple places.
- Improved scanning and metadata persistence so supported files now get an explicit AI detection result saved instead of leaving the field blank.
- Improved AI metadata parsing so SillyTavern-style metadata is recognized more reliably and user comments no longer count as AI evidence by themselves.
- Updated the details panel so core AI metadata fields, including `AI Tool / Source`, can be edited and saved back to the database.
- Replaced the native file-menu settings cog with a themed SVG icon that stays black in light mode and white in dark mode.
- Simplified `Filter By` so a single `None` option clears all groups while empty groups continue to behave implicitly as no filter.
- Fixed the file tree `Collapse All` action so it no longer instantly re-expands.

### Removed

- Removed the old `Start Collapsed in Details Panel` metadata setting, since the details panel no longer supports that behavior.

---

## v1.1.12

### Summary

This release makes duplicate cleanup much easier to trust and much faster to review. MediaLens now applies your review rules more consistently, keeps duplicate and comparison decisions in sync, and gives you clearer signals about what is identical, what should be kept, and how much space you can recover.

### Highlights

- Duplicate and similar review now pre-fills Keep and Delete selections from your rules, so there is less manual cleanup before using Auto Resolve.
- The comparison panel now stays aligned with duplicate review decisions, including matching delete controls, clearer winner labels, and better handling for truly identical files.
- Review stats are easier to follow with live Keep, Delete, and Potential Savings cards that reflect the current cleanup plan.

### Added

- Added Delete checkboxes to duplicate and similar review cards so review choices can be adjusted before running Auto Resolve.
- Added rule-based preselection for Keep and Delete in similar-file review so duplicate cleanup can start from your preferred decisions.
- Added a sticky review message and live summary cards for Keep, Delete, and Potential Savings based on the current checked selections.
- Added matching trashcan actions and delete-state syncing in the comparison panel so review actions stay consistent across both workflows.

### Changed

- Changed exact duplicate review so `Identical` is shown in place of `Best Overall` across duplicate groups, mixed duplicate-and-similar groups, and the comparison panel.
- Improved comparison winner logic so `Best in Comparison` follows `Best Overall` when files are effectively tied, with clearer winner labels only when there is a real difference.
- Restored and aligned duplicate scoring labels such as `Most metadata` so they appear more consistently in duplicate review and comparison.
- Updated duplicate-review and comparison trash buttons to use matching icon styling, hover states, and theme-aware colors.
- Renamed and refined the duplicate-review stats cards for clearer wording and better responsive behavior at smaller window sizes.
- Fixed Advanced Search duration and file-size unit selectors.

---

## v1.1.11

### Summary

This release brings a major search upgrade to MediaLens while also expanding file support and polishing everyday browsing. It makes powerful search easier to use, adds first-class SVG support, and improves several core gallery workflows.

### Highlights

- Advanced Search now includes a guided builder that helps users create powerful searches without memorizing syntax.
- SVG files now have first-class support with filtering, metadata handling, and better visibility for transparent artwork.
- File browsing is more polished with Sort by File Type and clearer high-contrast backgrounds for transparent PNG files.

### Added

- Added a new Advanced Search guided query builder with a header toggle, visual query controls, saved searches, field-based search options, and synchronization with the existing search syntax.
- Added full SVG media support with dedicated filtering, metadata handling, and transparent-background visibility improvements.
- Added Sort by File Type to the gallery sort options.

### Changed

- Updated advanced search to behave like a compact inline builder instead of a large full-screen panel, with responsive single-line controls, clearer labels, and theme-aware custom dropdown styling.
- Improved transparent PNG visibility by using the same high-contrast background logic already used for SVG files.
- Refined startup and update flow so the auto-updater relaunches more reliably after install.
- Suppressed harmless DirectWrite legacy font fallback warnings in the console so real runtime issues are easier to spot.

### Removed

- Removed the older splash branding above pinned folders in favor of a cleaner left-panel presentation.

---

## v1.1.10

### Summary

This release makes MediaLens feel steadier and more polished during everyday browsing. It reduces screen flicker for many Windows setups, replaces the old web settings overlay with a cleaner native settings window, and gives you more control over header space when you want a roomier gallery view.

### Highlights

- Settings now open in a native Qt window with a standard title bar, improved layout, and more consistent controls.
- Panel toggles have moved into the File menu, and a new header toggle lets you hide the top header to free up screen space when needed.
- Accent color contrast has been improved across settings and the header address bar so selected text and toggles stay easier to read.
- Windows builds now use a more stable DPI awareness mode to reduce flicker on some displays.

### Added

- Added a native Qt settings dialog with dedicated pages for General, Appearance, Player, Metadata, Similar File Rules, and AI.
- Added drag-and-drop reordering for metadata groups, metadata fields, preferred duplicate formats, and duplicate scoring priorities in native settings.
- Added an editable accent hex input alongside the accent color picker in Appearance settings.
- Added DPI diagnostics to startup logs and crash reports to make packaging and display issues easier to investigate.

### Changed

- Changed Windows packaging to force system DPI awareness in the installed app to help reduce flicker on some screens.
- Moved the left, right, bottom, and top panel toggles into the File menu and added a dedicated option to hide the header so the gallery can use more vertical space.
- Updated the native settings window to follow light and dark theme changes, use the chosen accent color more consistently, and improve checkbox and selected-text contrast automatically.
- Refined the native settings layout with better category spacing, cleaner metadata file-type controls, stronger Similar File Rules dropdown styling, and more consistent native dialog behavior.
- Updated the web header address-bar editor so selected text now chooses black or white automatically based on accent contrast instead of always using white.

### Removed

- Removed the old web-based settings overlay from the main settings flow.

---

## v1.1.9

### Summary

This release makes everyday browsing feel more flexible and polished. It improves filtering, startup presentation, and several header and settings workflows so common actions take less effort.

### Highlights

- Filter By now supports independent media-type and text-detection groups, so you can combine filters without resetting the rest of your view.
- Startup now feels cleaner with an optional transparent splash screen and without the extra stray window before the full UI appears.
- Header, settings, and sidebar polish reduce visual friction during navigation, sorting, and folder review.

### Added

- Added grouped Filter By controls so media type and text detection can be filtered independently.
- Added a `No Text Detected` filter for quickly isolating images without detected text.
- Added a `Sort: None` option to return to the default order, including randomized order when that setting is enabled.
- Added an optional transparent startup splash screen with an Appearance setting to turn it on or off.

### Changed

- Widened and refined the Filter By control so grouped filters remain easier to scan and use.
- Updated the header layout by moving the search bar to the lower row, improving address-bar responsiveness, moving the file count next to search and pagination, and replacing the old Compare header button with the bottom-panel toggle.
- Replaced the gallery scroll-to-top and scroll-to-bottom header icons with cleaner themed SVG icons.
- Moved the MediaLens title and logo above Pinned Folders, added a matching separator, and aligned left-panel separator spacing and thickness more consistently.
- Updated settings layout and wording by moving Appearance above Player, moving the close control to the top right, and renaming duplicate-review rules to Similar File Rules.
- Restored accent styling for the active folder in the File Tree and removed the extra focus border from pinned folders.
- Changed the right details panel scrollbar to appear only when needed.
- Improved startup loading by fixing parentage for the main splitter panels so the app opens more cleanly.

### Removed

- Removed the standalone Compare button from the header.

---

## v1.1.8

### ✨ Summary

This release refines similar-image review and Image Comparison to feel more compact, consistent, and responsive across the app. It also fixes live light/dark theme switching so the interface updates correctly without restarting. These updates reduce friction during review, making it faster to compare, decide, and clean up similar images.

### 🔥 Highlights

- Similar Groups now uses a tighter sticky summary header and more compact image cards, so reviewing large groups takes less scrolling.
- The Image Comparison panel now includes improved controls, cleaner slot styling, smoother slider behavior, and more polished preview framing for a more focused comparison experience

### Added

#### Comparison Controls

- Added remove (`X`) controls for each comparison slot and a close button for the Image Comparison panel
- Added smart filename truncation in comparison slots so long names resize cleanly
- Added on-screen guidance beneath the comparison viewer for mouse-wheel zoom behavior

### Changed

#### Comparison Panel Polish

- Refined the Image Comparison panel layout, spacing, cursor feedback, and rounded preview framing for a more cohesive and responsive feel
- Improved the center comparison slider so it stays stable while zooming and respects the rounded preview bounds
- Updated comparison slot and center preview surfaces so light and dark themes now render consistently with the surrounding UI

#### Similar Group Review

- Converted the Similar Groups summary into a compact sticky header with tighter, more readable stats
- Tightened similar-group cards by removing wasted inner thumbnail spacing and adding cleaner bordered image styling
- Updated `Auto Resolve All` to visually match other similar-group actions for a more consistent workflow

#### Packaging spec

- Updated the Windows packaging spec to bundle scipy.special modules more explicitly and align hidden imports more closely with MediaLens’ actual SciPy usage.

### Removed

- Removed the extra outer border from the left and right comparison slot cards to simplify the panel chrome

---

## v1.1.7

### Summary

This release sharpens the Image Comparison workflow so it is easier to judge mismatched files at a glance and review near-duplicates with clearer visual cues. It also refreshes the README to better highlight duplicate and similar-image cleanup.

### Highlights

- Smaller images in the comparison viewer now scale up to match the larger image for more useful side-by-side inspection.
- The comparison panel now shows clearer status messages for upscaled images and aspect-ratio differences.
- Comparison review labels were clarified so Best Overall stays tied to the full similar-image group while the panel can separately identify the best image in the current comparison.

### Added

#### Comparison Guidance

- Added comparison status labels that call out when one side was upscaled to match the other and when the compared images use different aspect ratios

### Changed

#### Comparison Matching

- Updated the center comparison viewer so the smaller image is resized to match the larger image during direct A/B inspection
- Refined aspect-ratio detection so images with effectively matching proportions are not mislabeled because of small resolution differences

#### Comparison Review Controls

- Improved comparison `Keep` and `Best Overall` behavior so comparison selections stay aligned with similar-image review state more consistently
- Updated comparison labels so `Best Overall` remains reserved for the full similar-image group while the panel separately calls out `Best in Comparison`

#### Documentation

- Refreshed README positioning and screenshots to emphasize duplicate finding, similar image review, and the Image Comparison workflow more clearly

---

## v1.1.6

### Summary

This release introduces Image Comparison, a new workspace for evaluating two images in place without leaving the gallery. It integrates directly with duplicate and similarity review, making it faster to inspect differences, choose the better version, and clean up near-duplicates with confidence.

### Highlights

New Image Comparison panel with left and right image slots plus a central reveal slider for true in-place A/B review

Load images using drag and drop, browse buttons, or gallery context menu actions such as Compare Images and Compare With Left/Right

Synchronized zoom and pan keep both images aligned during close inspection, with hold-to-isolate preview on either side for quick single-image checks

Comparison cards preserve keep/best actions and recalculate smart labels specifically for the current two-image decision instead of reusing broader group context

### Added

#### Image Comparison Mode

- Added a new **Image Comparison** panel beneath the gallery with left and right image slots plus a central overlay viewer
- Added drag-and-drop, browse button, and gallery context menu entry points for loading images into comparison
- Added an in-place reveal slider that shows the left image on one side and the right image on the other for fast visual A/B review
- Added synchronized mouse-wheel zoom with cursor focus and shared pan behavior so both images stay aligned during close inspection
- Added hold-to-isolate preview so either image can be viewed alone temporarily without leaving comparison mode

#### Comparison Workflow Integration

- Added comparison actions that integrate with the existing duplicate and similarity review workflow, including `Keep`, `Mark as Best`, and `Delete`
- Added recalculated labels and best-overall suggestions for the current two-image comparison instead of reusing labels from a larger similarity group
- Added contextual gallery actions for `Compare Images`, `Compare Image`, `Compare With Left`, and `Compare With Right`

### Changed

#### Bottom Panel Usage

- Repurposed the existing bottom panel shell from the AI placeholder into the new **Image Comparison** workspace
- Opening **Settings** now temporarily hides the comparison panel so the settings window can use the full center height before restoring it afterward

#### Comparison Panel Polish

- Refined the comparison card layout so filename and metadata remain inside each image card while labels and actions stay below
- Improved thumbnail resizing to preserve aspect ratio without cropping or stretching while staying responsive as the panel is resized
- Improved slider behavior so it snaps fully to the loaded side when only one image is present, then auto-centers once when a second image is added
- Improved small-window behavior with scrollable comparison side columns, tighter card spacing, better control alignment, and settings-category scrolling
- Improved comparison accent styling so labels, controls, checkboxes, and image cards update correctly with theme accent changes

### Removed

- Removed the unused AI chat placeholder content from the bottom panel in favor of the new **Image Comparison** workspace

---

## v1.1.5

### Summary

This release improves duplicate cleanup workflows and media playback control while refining navigation and preview behavior for a smoother, more predictable experience. It also greatly improves text detection speed and accuracy.

### Highlights

- Flexible duplicate cleanup now supports both single “Best” selection and multi-file “Keep” workflows.
- New player controls allow independent GIF autoplay, video looping, and default mute behavior.
- Text detection is now significantly faster and more accurate.

### Added

#### Duplicate Review Controls

- Added a `Mark as Best` toggle, restored the `Keep Best` action, and introduced `Delete Unchecked Files`.  
- Multiple files can now be marked as `Keep`, with a separate `Best` designation.

#### Player Settings

- Added a dedicated `Player` settings category with controls for default mute behavior, gallery GIF autoplay, details preview GIF autoplay, video loop mode, and loop cutoff length.

### Changed

- **Animated GIF Behavior** - Split autoplay behavior between the gallery and details preview.  
- The gallery now uses still posters when autoplay is disabled.
- **Preview & Video Reliability** - Improved preview consistency by fixing GIF stretching and cropping in the preview-above-details area.  
- The preview player now consistently respects the mute-by-default setting.
- **Pinned Folder Visibility** - Pinned folders now follow the same hidden-folder logic as the file tree and gallery.
- **File Tree Navigation** - File tree now rebuilds and reselects correctly when navigating outside the current branch using Back or Up.
- **Preview Toggle Placement** - Removed the duplicate `Preview Image Above Details` entry from the native `View` menu.

### Fixed

- **FFmpeg Filename Crash** - Resolved crashes caused by special characters in filenames by using safe aliases for FFmpeg and FFprobe calls while preserving original filenames in the UI.
- **Text Detection** - Improved text detection speed and accuracy.

### Removed

- **View Menu Preview Toggle** - Removed the duplicate `Preview Image Above Details` toggle from the native `View` menu.

---

## v1.1.4

### Summary

This was a stabilization-focused release that improved video previews and file deletion safety.

After significant rework, video playback is now more stable, and file deletion has been redesigned to be safer, more predictable, and user-controlled.

This update also introduces pinned folders and several UI refinements that improve clarity and consistency.

### Highlights

- Video preview system rebuilt for stable playback, consistent behavior, and reliable interaction.
- File deletion is now safer and more predictable with recycle bin support and configurable behavior.
- Pinned folders and UI refinements improve navigation clarity and overall usability.

### Added

- **Recycle Bin Delete Workflow** - Added recycle-bin delete as the default behavior, a `Shift+Delete` permanent delete shortcut with confirmation, and a new setting to control recycle-bin usage.
- **Pinned Folders Sidebar** - Added pinned folders in the left sidebar with right-click add/remove actions and drag-and-drop support.

### Changed

- **Video Preview Reliability** - Rebuilt the preview-above-details video pipeline to restore metadata, static posters, explicit in-place playback, lightbox double-click, and stable delete behavior without the earlier crashes.
- **Accent Contrast** - Improved accent-color readability in lower-contrast situations by dynamically increasing contrast where needed.
- **File Tree Visual Polish** - Refined tree and pinned-folder styling so selected folders use bold accent text without tinting icons, and chevrons only render when folders actually have children.
- **Header Branding** - Replaced the header logo.

---

## v1.1.3

### Added

- **Sidebar Video Player** - In-place video playback directly above the metadata panel.
- **Text Detection Filter** - 3-stage text detection system (Likely, More Likely, Verified) powered by OpenCV and OCR.

### Changed

- **Video Playback Stability** - Improved async teardown of video pipelines to prevent UI freezes and crashes during navigation.
- **Preview Toggle UX** - Moved preview toggle beside the header using a dedicated outline icon, keeping the header consistently visible.
- **Video Controls UI** - Refined controls with clean borders, frosted glass backgrounds, and high-contrast white icons.
- **Documentation** - Updated README and screenshots to reflect duplicate grouping, resolution workflows, and settings.
- **Branding** - Updated app icon and logo.

---

## v1.1.2

### Added

- **Auto Resolve Settings Panel**: Added a dedicated Duplicate and Similarity Auto Resolve Rules settings section with Rules and Priorities tabs for review behavior.
- **Variant Detection Labels**: Added color/grayscale, cropped/full-frame, file-size, and preferred-format labels to duplicate and similar review cards.

### Changed

- **Duplicate and Similar Ranking**: Refined keep-best scoring so visible category winners align better with the overall recommendation and user-configurable priority order.
- **Similarity Detection Stability**: Fixed pHash backfill, review grouping, and duplicate/similar counting regressions that were causing empty results in real folders.
- **Review Workflow Reliability**: Restored scan-driven duplicate and similar results, preserved review positioning more reliably after delete actions, and kept the duplicate/similar experience responsive.

---

## v1.1.1

### Added

- **Duplicate Review Modes**: Added `Duplicates`, `Duplicates and Similar`, and `Similar` gallery review modes in both the header controls and native `View` menu.
- **Perceptual Similarity Grouping**: Added perceptual-hash based grouping for visually similar images, alongside the existing exact duplicate grouping by content hash.
- **Duplicate Workflow Actions**: Added duplicate/similar group summary cards, keep-target selection, auto resolve, per-file delete, and group-level metadata merge actions.

### Changed

- **Keep Candidate Scoring**: Added richer keep-best reasoning based on metadata richness, folder organization, file size, resolution, and newest edit to make duplicate cleanup more trustworthy.
- **Similarity Threshold Controls**: Added user-selectable similarity threshold levels and split exact duplicate review from near-duplicate review for easier tuning.
- **Header Layout Polish**: Refined header wrapping, select sizing, breadcrumb behavior, and selected-folder responsiveness so the new review controls fit cleanly in the main UI.

---

## v1.0.23

### Added

- **MediaLens Brand Assets**: Added the new MediaLens logo set and multi-resolution ICO packaging assets for the app, installer, taskbar, and Start menu.

### Changed

- **MediaLens Rebrand**: Updated the app name across the header, window title, About dialog, DevTools window, installer, and packaged release outputs so shipped builds consistently present MediaLens.
- **Theme-Aware Header Branding**: Swapped the header logo to the new MediaLens light and dark variants while preserving theme-aware sidebar toggle behavior.
- **Release Packaging Names**: Renamed the build spec, packaged executable, installer output, and related workflow/docs references to the MediaLens naming scheme.
- **Update and Repo Links**: Pointed in-app update checks, installer downloads, Help menu links, and release documentation to the renamed G1enB1and/MediaLens GitHub repository.

---

## v1.0.22

### Added

- **Bottom AI Panel Shell**: Added a new hideable and resizable bottom panel with persisted visibility and size so the upcoming AI chat area has a dedicated place in the layout.
- **Explorer-Style Address Bar**: Replaced the simple selected-folder label with a full Windows Explorer-style address bar that shows the full path as clickable breadcrumbs.
- **Breadcrumb Folder Menus**: Added dropdown chevrons between breadcrumb segments and at the end of the current path so nearby folders can be opened directly from the address bar.

### Changed

- **Navigation Responsiveness**: Moved breadcrumb folder enumeration, gallery counts, and gallery listing requests off the UI thread so folder navigation is less likely to freeze the app.
- **Tree Sync Scheduling**: Changed native tree synchronization so folder navigation updates the selected folder first and coalesces heavier tree sync work behind a deferred timer instead of doing it immediately on every navigation.
- **Address Bar Interaction**: Added editable-path mode plus keyboard navigation and lazy-expanding flyout menus so the address bar behaves much closer to Windows Explorer.
- **Header Wrapping**: Updated the header layout so pagination drops below the address bar on narrower widths instead of overlapping it.
- **Release Build Safety**: Hardened the release build flow to catch stale packaged artifacts before producing an installer and kept `setup.cfg` versioning in sync during version bumps.

---

## v1.0.21

### Added

- **Explorer-Style Folder Navigation**: Added `Back`, `Up`, `Forward`, and `Refresh` controls beside the selected-folder readout for faster folder browsing.

### Changed

- **Context Menu Placement**: Refined right-click menu positioning so menus stay fully visible on screen instead of getting clipped near the bottom or edges.
- **Native Drag Preview Overhaul**: Replaced the Windows shell drag preview with a native in-app drag stack that keeps original aspect ratios, supports larger previews, and positions the preview/tooltip stack cleanly beside the cursor.
- **Multi-Item Drag Stacks**: Multi-select drags now show overlapping preview thumbnails so stacked drags communicate that multiple files are moving or copying.
- **Left Tree Navigation Behavior**: Restored the file tree so normal folder navigation highlights subfolders without re-rooting the tree unexpectedly.

---

## v1.0.20

### Added

- **Metadata Detail Group Headings**: Added `General`, `Camera`, and `AI` section headings to the single-item metadata details panel so dense metadata is easier to scan.

### Changed

- **Gallery Folder Drag and Drop**: Fixed dragging files from the gallery into folder cards shown inside the gallery, while preserving cancel behavior when dropping back on the same item or gallery background.
- **Timeline Polish Pass**: Added active/visible/dim anchor emphasis, corrected the bottom-of-gallery anchor edge case, made the timeline resize against the visible gallery viewport, improved its final positioning, and cleaned up the rounded shell rendering.
- **Metadata Panel Cleanup**: Removed unwanted Qt label indentation/left rules from metadata labels and headings, kept detail-only group headers out of bulk/empty states, and restyled `Clear Tags From DB` to match the other bulk tag editor actions.
- **Glassmorphism Removal**: Removed the appearance toggle and remaining blur/translucency paths so the header, lightbox, and other surfaces render fully opaque without flicker around animated GIFs and videos.
- **Sidebar Divider Stability**: Refined the native sidebar splitter/divider rendering so borders and resize hover states render crisply instead of appearing too thin or flickering.

### Removed

- **Glassmorphism Setting**: Removed the `Enable glassmorphism` appearance option and its remaining runtime wiring.

---

## v1.0.19

### Added

- **What's New Release Notes**: The `What's New` dialog now shows the polished `ReleaseNotes.md` summary first, followed by the full bundled changelog for users who want the detailed breakdown.
- **Timeline Navigation Arrows**: Added dedicated up/down controls to the timeline rail so dense timelines more clearly communicate that extra dates are available above or below the current viewport.

### Changed

- **Timeline Navigation Overhaul**: Rebuilt the grouped-date timeline to use one anchor per real date header, unified tooltip behavior, smoother drag and wheel scrubbing, a hybrid viewported anchor rail for dense timelines, and granularity-specific sizing for day, month, and year modes.
- **Infinite Scroll Policy**: Switched grouped-date non-masonry views plus `List`, `Details`, `Content`, `Small Grid`, and `Medium Grid` to infinite scroll so timeline navigation and long-form browsing are no longer broken up by pagination.
- **Header Responsiveness**: Moved the panel toggle and settings buttons beside Search and reworked the header layout so the controls wrap more cleanly on narrower widths instead of clipping off the right edge.
- **Bundled Help Content**: Packaged `SEARCH_SYNTAX.md` and `ReleaseNotes.md` with installed builds so help/release dialogs work outside the raw development environment.
- **Startup Folder Settings**: Corrected startup-folder settings state so the Browse button and related controls stay enabled/disabled based on the real `restore_last` setting.

---

## v1.0.18

### Changed

- **Details Header Layout**: Refined regular and grouped Details header spacing, sticky positioning, separator styling, and scroll-state behavior so both modes align cleanly without visible jumps or header gaps.
- **Grouped Details Columns**: Fixed grouped-by-date Details mode so the shared resizable header stays aligned with filenames, folders, sizes, and other row data below it while resizing.
- **Sidebar Width Persistence**: Corrected sidebar state persistence so reopening panels restores their previous usable widths instead of saving and restoring zero-width sidebars.
- **WebEngine Startup Stability**: Deferred the initial WebEngine background-color setup until after the event loop starts, avoiding native startup aborts seen on some installed Windows machines.

---

## v1.0.17

### Added

- **Crash Diagnostics**: Added local crash-report generation, `faulthandler` logging, and Help menu actions to create a diagnostic report or open the crash-report folder for troubleshooting installed builds on other machines.

### Changed

- **Packaged Runtime Stability**: Hardened packaged startup/runtime behavior by normalizing AI metadata values before JSON persistence, preventing scan-time failures from non-serializable EXIF values like Pillow `IFDRational`.
- **Details Panel States**: Updated the right sidebar so it shows a true empty-state prompt when nothing is selected and switches to a dedicated bulk tag editor when multiple files are selected.
- **Bulk Tag Editing**: Refined bulk tag save/embed behavior so entered tags append to existing DB and embedded file tags instead of replacing them.

---

## v1.0.16

### Changed

- **Grouped Details View**: Fixed grouped Details mode so only one sticky column header appears at the top, date groups collapse correctly, sticky date headers sit beneath the Details header, and the header seam no longer exposes scrolling content behind it.
- **List Context Menu**: Refined list-view context menu layering so the custom right-click menu reliably appears above gallery rows instead of being visually overlapped by list items.
- **Fresh Install Bootstrap**: Updated the packaged database initialization flow to bundle and load the SQL schema correctly in installed builds, preventing first-run launch failures caused by missing `app\\mediamanager\\db` resources.

---

## v1.0.15

### Added

- **Date Grouping**: Added `Group By Date` across gallery views with date headers, collapsible sections, and a right-side jump/scrub timeline.
- **Date Metadata Fields**: Added `Date Taken`, `Date Acquired`, `Date Created`, and `Date Modified` to metadata settings and the Details sidebar for images, GIFs, and videos.

### Changed

- **Timeline UI**: Refined the timeline scrubber layout, spacing, padding, coloring, and docked sizing so it no longer overlaps the gallery and behaves predictably while resizing.
- **Metadata Dates**: Updated scanning, import, save, and embed flows to extract and persist filesystem dates plus EXIF/XMP-style taken/acquired dates, and made `Date Taken` and `Date Acquired` editable in the sidebar.
- **Date Labels**: Renamed date labels throughout the app for consistency with Windows Properties and the Details/settings panels.

---

## v1.0.14

### Changed

- **Installer Build**: Updated the packaged Windows app so background media scanning and related `ffmpeg`/`ffprobe` work no longer opens console windows while scanning folders.

---

## v1.0.13

### Added in v1.0.13

- **AVIF Support**: Introduced support for AVIF image files.
- **New Gallery Views**: Added several new view modes including List, Details, Content, and multiple Grid sizes (Small, Medium, Large, Extra Large) alongside the default Masonry layout.
- **Sidebar Preview Section**: Added a new preview panel at the top of the right sidebar that displays a thumbnail of the selected item above the metadata details.
- **View Menu**: Added a new "View" menu to toggle panels and switch between different gallery view modes.

### Changed in v1.0.13

- **Video Controls**: Reduced the time video controls remain visible after mouse-over to 500ms for a more responsive feel.
- **Details Panel Responsiveness**: Improved the responsiveness of the metadata details panel.
- **Hidden Files Logic**: Updated hidden files, folders, and collections logic to use hidden status in database rather than filenames starting with a dot.

### Fixed in v1.0.13

- **File Tree**: Fixed a critical issue where the folder tree appeared empty in the installed application when the root was a drive path (e.g., `C:/Pictures`).
- **AVIF Previews**: Implemented FFmpeg-based fallback for AVIF sidebar previews, resolving the issue where native Qt support was missing.
- **AVIF Dimensions**: Added ffprobe-based dimension retrieval for AVIF files to ensure correct aspect ratios and details rendering.
- **Conflict Dialog**: Improved conflict detection and thumbnail rendering in the conflict dialog for AVIF files.

---

## v1.0.12

### Changed in v1.0.12

- **Video Loading Optimization**: Refined the video loading mechanism to significantly reduce delay, ensuring a smoother playback experience in the gallery.
- **Scanning Efficiency**: Optimized the file tree scanning process to ensure full scans only occur when necessary, improving overall application responsiveness.
- **Update Notification Enhancements**: Improved update notifications by replacing redundant native OS dialogues with stylized toasts for a more consistent and modern UI experience.

---

## v1.0.11

### Added in v1.0.11

- **Collections System**: Introduced a new system to organize media into collections. Collections appear in the left sidebar, are resizable, and persist across sessions.
- **Enhanced Search Syntax**: Overhauled the search engine to support collections, wildcards, mathematical expressions, exclusions, phrases, and complex operators (+ - ? * | OR).
- **Search Help**: Added a detailed search syntax guide accessible via the Help menu.
- **Collection Context Menu**: Added "Add to Collection..." to the gallery context menu, supporting both individual and bulk actions with the ability to create new collections on the fly.

### Changed in v1.0.11

- **Scanning Progress Bar**: The progress bar is now stationary at the bottom of the screen and hides completely when clicked.
- **Sidebar Resize Handles**: Refined the UI by reducing the sidebar resize handle width from 5px to 1px.

### Fixed in v1.0.11

- **Glass Morphism Persistence**: Fixed an issue where the glass morphism setting was not correctly restored on application launch.

---

## v1.0.10

---

## v1.0.9

### Added in v1.0.9

- **Enhanced Metadata Support**: Expanded metadata scraping to include tEXt, iTXt, zTXt, XMP, EXIF, chara, C2PA, JUMBF, caBX, IPTC, JFIF, and COM. The app now detects digital watermarks, ComfyUI workflows, character cards, AI prompts/parameters, and more.
- **Metadata Settings Tabs**: Added separate tabs in Settings for Image, Video, and GIF metadata configurations.
- **Metadata Grouping**: Grouped metadata into General, Camera, and AI sections that can be individually hidden or reordered.
- **Metadata Persistence**: Added a button to save hidden metadata into a visible comments field for easier access.

### Changed in v1.0.9

- **Metadata Sidebar UI**: Redesigned the metadata sidebar to use vertically stacked buttons, ensuring elements fit correctly within the available width.

---

## v1.0.8

### Added in v1.0.8

- **Video Rotation**: Added context menu options to rotate video files 90 degrees CW and CCW.
- **Image Rotation**: Added context menu options to rotate image files 90 degrees CW and CCW.
- **External Editors**: Added Open with Photoshop and Open with Affinity right-click actions.

### Changed in v1.0.8

- **Pause Button**: Refined the pause button interaction and logic.

### Fixed in v1.0.8

- **Installer**: Fixed setup installer missing files and pathing bugs.

---

## v1.0.7

### Changed in v1.0.7

- **Video Player Sizing Fix**: Addressed a race condition that caused in-place gallery videos to occasionally play at an incorrect, minimized size.
- **Lightbox Styling Refinements**: Fixed an issue where hovering over the lightbox previous/next navigation buttons caused them to shift downward. They now scale up smoothly in place.
- **Mute Default Restored**: Fixed a bug where in-place videos would sometimes start with sound. Videos are properly muted by default again.
- **Previous and Next Buttons Changed**: Replaced the native video player's previous and next emoji buttons with custom SVG graphics to prevent the Windows OS from rendering them with colorful backgrounds.

### Removed in v1.0.7

- **Close Buttons Removed**: Completely removed both the native video player close button and the underlying web lightbox close button to eliminate visual ghosting and overlapping. Users can cleanly close the media overview by clicking anywhere outside the media content.

---

## v1.0.6

### Added in v1.0.6

- **In-Place Video Playback**: Videos can now play directly inside the gallery card, overlaid on the thumbnail, without opening a separate window.
- **Custom SVG Media Controls**: Play and Pause buttons now use custom SVG icons for a crisp, professional appearance that avoids OS emoji rendering issues on Windows.
- **Video Controls Overlay**: A translucent control bar with play/pause, mute, volume slider, and a seek bar is displayed while a video is playing in-place.

### Changed in v1.0.6

- **Accent Color on Video Sliders**: Volume and seek bar sliders in the video overlay now use the user's selected accent color from Settings.
- **Smart Lazy Loading**: Gallery images are now loaded on demand as you scroll, using a native `IntersectionObserver` bound to the scrollable container. Images one full screen below the visible area are preloaded before you scroll to them.
- **Poster Restoration**: Pausing or closing an in-place video now correctly restores the original thumbnail poster image.
- **Video Click Behavior**: Clicking the video frame no longer pauses playback; only the dedicated Pause button does.
- **Fixed What's New:** What's New now accurately reflects current Changelog.md.
- **Fixed Auto-Update:** Auto-Update now uses RedirectPolicyAttribute with NoLessSafeRedirectPolicy which properly follows the redirects that github uses for releases.

### Removed in v1.0.6

- **Removed Loading Media Dialog**: Removed the "Loading Media" progress dialogue because local files load faster than the dialog can meaningfully update, eliminating a visual stutter on every gallery update.

---

## v1.0.5

### Changed in v1.0.5

- **File Tree Fix**: Improved path normalization and initialization robustness to ensure the file tree is visible in the packaged installer environment.
- **Improved Logging**: Added detailed initialization logging to help diagnose environment-specific path issues.

---

## v1.0.4

### Added in v1.0.4

- **Gallery Drag & Drop**: Drag and drop files or folders from Windows File Explorer directly into the gallery area with the same behavior and styling as the file tree.
- **Conflict Comparison Dialog**: Added a popup dialog when copying or moving files to a destination containing an existing filename, allowing context comparison before resolving the conflict.

### Changed in v1.0.4

- **Cursor Feedback**: Cursor now changes to a hand pointer when hovering over clickable folders and files.
- **Conflict Dialog Improvements**:
  - Fixed SVG rendering for the **Apply to all** checkbox so the checkmark displays correctly in all themes.
  - Improved button hover effects for clearer interaction feedback.
  - Fixed vertical clipping of long filenames.
- **Drag & Drop Refinements**:
  - Improved handling of multi-file transfers between the gallery and file tree.
  - Adjusted tooltip offset and event handling to suppress duplicate Windows tooltips.
- **Gallery Context Menu**: Right-clicking empty gallery space now correctly opens the application menu.

---

## v1.0.3

### Added in v1.0.3

- **Keyboard Shortcuts**:
  - **Ctrl+C / Ctrl+X / Ctrl+V** - Copy, Cut, Paste files and folders
  - **Delete** - Delete selected items with confirmation
  - **F2** - Rename selected items (inline for folders, dialog for gallery)
  - **Ctrl+A** - Select all gallery items

### Changed in v1.0.3

- **Drag & Drop Improvements**:
  - Move or copy multiple selections simultaneously
  - Default action is **Move**, hold **Ctrl** to **Copy**
  - Dynamic tooltips showing destination folder
  - Drag thumbnails offset from cursor for better visibility
- **Selection & UI Stability**:
  - Fixed gallery items deselecting when opening context menus
  - Gallery now refreshes immediately after deletion
  - Keyboard shortcuts no longer trigger while typing in Tags or Description fields
- **Metadata Compatibility**: Fixed tag and comment embedding so metadata appears correctly in Windows File Properties.
- **Persistent Layout**: Sidebar widths are now remembered across sessions.
- **UI Improvements**:
  - Fixed inconsistent theme colors in metadata and bulk tagging sidebars
  - Adjusted scrollbar hover effects for better visual consistency
- **Bug Fix**: Resolved `AttributeError` in native shortcut handlers.

---

## v1.0.2

### Added in v1.0.2

- **Auto-Update System**: App now checks GitHub for updates on launch (manual check available).
- **Help Dialogs**: Added **Terms of Service** and **What's New** windows in the Help menu.

### Changed in v1.0.2

- **Media Loading**: Placeholders and borders remain hidden until metadata and dimensions are loaded.
- **Navigation Fix**: Scroll position now resets correctly when switching pages or search results.
- **Performance Optimization**: Removed real-time GIF pausing in the lightbox to reduce overhead.
- **UI Improvements**:
  - Help dialogs now use themed backgrounds matching light and dark modes
  - Fixed button contrast issues in light mode
  - Added native Markdown rendering for informational documents
- **About Window**: Expanded version and author information.
- **Masonry Layout Stability**: Prevented layout shifts by reserving space using correct aspect ratios.

---

## v1.0.1-alpha

### Added in v1.0.1-alpha

- Initial MediaLens project scaffold and Python package layout.
- SQLite schema bootstrap and initialization scripts.
- Windows path normalization utilities and scope validation.
- Folder scope query builder and selection state helpers.
- Core repositories for media ingest/query, metadata CRUD, and tag CRUD.
- Repository facade (`MediaRepository`) for native UI integration.
- Unit test suite for foundation modules.
- Development validation helper (`scripts/dev_check.py`).
- First-run database bootstrap helpers and automatic DB initialization.
- Repository hygiene configuration (`.gitignore`) for caches and runtime data.
- `Makefile` convenience commands (`setup`, `test`, `run`).
- CLI support for custom database paths via `--db-path`.
- Demo ingest script for quick ingestion and scoped listing tests.
- Initial container-first masonry layout helper and design documentation.

---
