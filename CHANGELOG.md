# Change Log

## v1.4.6 (Current)

### Summary

This release is a broad polish and stability update across MediaLens, led by a much faster and more capable Image Editor. It also improves Settings, Bulk Editor refresh behavior, Action History stability, and native UI consistency so everyday workflows feel steadier across the app.

### Highlights

- Edit faster with accelerated blur, live brush strokes, drag-based Magic Wand selection, marching-ants outlines, and a new Lasso selection option.
- Work with text more reliably using scalable font handling, resizable on-canvas bounds, better toolbar size changes, remembered font choice, and improved zoom alignment.
- Use a cleaner native interface with more consistent Settings controls, better editor dropdowns, fixed Bulk Editor combo behavior, and steadier Action History row interaction.

### Added

- Added accelerated image-processing paths for Image Editor blur, brush, eraser, and Magic Wand operations using reusable NumPy and optional OpenCV-backed processing where available.
- Added live brush and eraser application during drag gestures so strokes are applied immediately instead of waiting for a delayed final pass.
- Added Photoshop-style Magic Wand drag sampling, selection-tool sizing, circle cursor feedback, and forced selection within the wand cursor size.
- Added animated marching-ants outlines for selection masks across selection tools.
- Added a Lasso selection tool with path-based selection support.
- Added add and subtract cursor markers for selection tools so the active selection mode is visible at the cursor.
- Added a live brush-tip preview that reflects opacity and edge softness values.
- Added direct on-canvas text transform bounds with move and resize handles for active text layers.
- Added safer font handling for text layers by blocking the problematic 8514oem font, normalizing legacy layers to scalable fonts, and remembering the last selected text font across sessions.
- Added a 1px grey border around Image Editor layer preview thumbnails.
- Added new Image Editor brush, eraser, fill, and text-alignment SVG assets, including dark-mode variants where needed.
- Added regression coverage for Image Editor live brush painting, Magic Wand dragging, selection outlines, text sizing, text bounds, font handling, toolbar focus behavior, and zoom-specific text overlay alignment.
- Added native Action History safeguards so dynamically created detail widgets and lower-table row clicks stay parented and routed correctly.

### Changed

- Changed Magic Wand selection cleanup so selected areas form more closed, filled regions instead of loose tolerance-only pixel islands.
- Changed the Magic Wand drag experience by removing the accented preview path line and using the selection outline itself as the main feedback.
- Changed Image Editor text sizing to render and measure with pixel-sized fonts so toolbar size values visibly scale text layers more predictably.
- Changed Image Editor text toolbar edits to target the intended text layer even when focus or active-layer state changes during editing.
- Changed Image Editor text selection behavior so toolbar edits preserve the previous highlighted or unhighlighted live text state instead of forcing a new state.
- Changed Image Editor text bounds so the editable transform box has more usable padding and aligns correctly across zoom levels.
- Changed Image Editor text color handling so the text tool follows the shared foreground color picker like the brush and fill tools.
- Changed live Image Editor brush, eraser, and Magic Wand drag updates to avoid full preview and tab-state refreshes during mouse movement, cache selection overlays, and keep accelerated operations feeling responsive.
- Changed Image Editor font and combo controls to use the shared themed combo path with fixed-height controls, predictable popup height, stable row sizing, and better closed-control alignment.
- Changed Image Editor alignment controls to use themed SVG menu buttons with corrected light and dark mode rendering.
- Changed Settings controls to use shared themed combos, spin boxes, buttons, tabs, and text inputs more consistently across light and dark mode.
- Changed Settings tab geometry, AI page tabs, Background Processes tabs, and scanner/OCR control styling so native settings pages align more consistently and avoid clipped or disconnected tab chrome.
- Changed shared native control heights and spacing so settings, editor toolbar controls, buttons, combos, line edits, and numeric inputs align more consistently.
- Changed Bulk Editor metadata settings so visibility changes made in Settings refresh live without requiring deselecting and reselecting files.
- Changed bulk metadata and bulk rename dropdowns back to the single-chevron custom combo path so duplicate arrows do not return.
- Changed Action History details so normal row clicks no longer fall through embedded action-cell widgets or create transient popup windows.
- Changed Image Editor opening from large gallery selections to prefer the current file and avoid expensive selection scanning.

### Removed

- Removed obsolete Image Editor text editing paths that could create phantom boxes, stale geometry, or unreliable resize behavior.
- Removed the old Magic Wand drag path preview line in favor of the cleaner selection-outline feedback.

---

## v1.4.5

### Summary

This release makes MediaLens much better at recognizing near-identical images with color filters or color shifts, while also tightening People review, bulk editing, and comparison behavior so labels and navigation stay more predictable.

### Highlights

- Detect filtered, recolored, and color-shifted versions of the same image more reliably in Similar Files.
- Review similar and duplicate groups with more trustworthy guidance thanks to smarter Best Overall handling that backs off when MediaLens cannot safely auto-pick a winner.
- Move through People galleries more smoothly with better review fallbacks, safer navigation behavior, improved bulk-tab persistence, and cleaner face-focused profile crops.

### Added

- Added colorhash-based color-shift detection so Similar Files can better group images that match structurally but differ mainly by applied color filters.
- Added a Color Shifted Pairs preference rule under Settings > Similar File Rules with Keep Both and Keep Newest options, defaulting to Keep Both.
- Added action-history-backed edited-image labeling so similar groups can identify MediaLens-edited files and use stronger original-versus-edited hints when provenance is reliable.

### Changed

- Changed Similar Files grouping at high and very high thresholds to stop missing close matches because of overly restrictive prefix bucketing.
- Changed similar-group labels to distinguish color-shifted matches more clearly and downgrade weak pixel-only matches to a neutral Color-shifted pair label when edit provenance is not strong enough.
- Changed duplicate and similar review auto-resolution so Best Overall is suppressed when keep-both rules apply or when MediaLens does not automatically mark any item for deletion.
- Changed the bottom comparison panel to follow the same no-best logic as the review gallery so color-shifted and other keep-both pairs no longer show a conflicting Best in Comparison label.
- Changed People card review entry behavior to open Review All automatically when Review Unconfirmed has nothing left to review.
- Changed People bulk-editor tab behavior so file-backed People views keep the last used tab across Review and Show All transitions, while the top-level People Gallery still stays locked to the People-only workflow where file tabs are not applicable.
- Changed People header navigation controls to avoid unpredictable folder-history behavior while People galleries or People review surfaces are active.
- Changed People profile-circle face crops and unnamed-face review thumbnails to use a gentler face zoom that keeps a bit more of the image in frame.
- Changed image-editor opening from gallery selections to prefer the current file and avoid expensive large-selection scanning that could stall the UI.

---

## v1.4.4

### Summary

This release expands MediaLens People workflows with a more complete gallery and review experience, stronger bulk editing, improved duplicate-face handling, and more polished People-specific controls throughout the app.

### Highlights

- Review one person across every image they appear in with new Show All, Review All, and Review Unconfirmed modes, plus faster bulk editing that stays centered on the People tab while still unlocking the other bulk tools when files are in scope.
- Manage people more directly with cleaner person-only context menus, a themed Manage dialog, custom profile pictures, hidden people and hidden groups, and better People-gallery status and navigation controls.
- Eliminate repeated cloned face entries across People review, bulk People summaries, and single-image People details by deduplicating duplicate face records at the shared data layer.

### Added

- Added Show All, Review All, and Review Unconfirmed person-gallery modes with sticky header controls for switching between People review states.
- Added a themed Manage dialog for People cards and person review headers with rename, group, favorite, ignore, visibility, and profile-picture actions.
- Added support for custom People profile pictures with built-in profile image switching controls.
- Added hide and show support for individual people and custom People groups, including filtering that respects the existing Show Hidden setting.
- Added a sticky header close button in person review views that returns directly to the normal gallery.
- Added a sticky People Gallery header with All, Unnamed, and Unconfirmed tabs, plus Scan for Faces and close controls that keep People navigation available without relying on the main header control.
- Added a People Show All folder-scope toggle so person-specific normal-gallery results can either use the person's complete image set or be limited to the current folder when needed.

### Changed

- Changed the header People control from a dropdown into a direct People button with inactive gray icon styling and active light or dark mode icons.
- Changed People Show All to use the normal gallery renderer and the user’s current gallery view, such as Masonry or Grid, instead of custom People face cards with bounding boxes.
- Changed People Show All scoping to use exact person-id filtering and a People-derived image scope by default, so results do not disappear when the current folder does not contain that person’s images.
- Changed People Show All refresh behavior so paging, infinite scroll, lightbox page changes, view changes, filters, sorting, and metadata-sensitive refreshes preserve the active person scope.
- Changed live search to render the first matching batch quickly and continue loading additional matching batches in the background for better responsiveness in large galleries.
- Changed People review and Show All bulk selection so the same bulk People editor used by the main People gallery opens by default, auto-loads the relevant files, and still allows switching to metadata, tags, OCR, captions, and rename tabs when files are selected.
- Changed People review bulk counts so the People section stays scoped to the currently selected files instead of the full person group.
- Changed People review galleries and related summaries to automatically deduplicate repeated face detections, preventing duplicate cards, inflated counts, and repeated names.
- Changed People card actions, person review context menus, and person-gallery header controls to focus on person workflows instead of generic image actions.
- Changed People card styling with circular profile images, a hover-only profile-picture switcher, stronger accent-aware hover states, and bolded person names.
- Changed People review presentation so Show All and review modes are separated cleanly, Confirm All hides when it is not relevant, and Review Unconfirmed hides when a person has nothing left to review.
- Changed the People gallery footer count chip to show named and unnamed people totals instead of a misleading file count.
- Changed the Include Nested Files header toggle to use the new custom file-tree SVG icon set.

### Removed

- Removed generic image-focused actions from People card context menus and person-group review menus where those actions did not match People workflows.

---

## v1.4.3

### Summary

This release refines the new MediaLens People workflows with stronger bulk-review behavior, better deduplication, per-person group management, and much better responsiveness when reviewing people with large image sets.

### Highlights

- Review people from the Bulk Editor more reliably with deduplicated face cards, cleaner per-image summaries, and counts that stay scoped to the files you are actually working on.
- Work through large people libraries more smoothly thanks to async loading, lazy thumbnail updates, cached people-per-image mappings, and better default splitter behavior.
- Manage group membership directly from each detected person card in the bulk People editor using the same custom typed dropdown workflow as People naming and renaming.
- Use a more polished bulk People image list with improved layout, clearer People summaries, per-image Ignore, and better thumbnail and button behavior in both wide and narrow panel sizes.
- Keep Review People, bulk People, and per-image summaries in sync with matching deduplication logic so duplicate bridge rows no longer create repeated cards or repeated names.

### Added

- Added per-person Rename and Ignore actions plus a collapsible Groups section to bulk People detected cards, including per-group remove actions and a custom typed Add to Group workflow.
- Added Ignore Unnamed support to the bulk People detected section when unnamed detections are present.
- Added per-image Ignore actions to bulk People selected-image cards alongside Scan for People and Review.
- Added context-aware bulk People image-source labeling so person-driven workflows clearly show image sets such as Images Containing Amy Rollins.

### Changed

- Changed single-person People Gallery selection to open the bulk People workflow, auto-populate Selected Images from that person or face selection, and reuse scoped caches for faster review setup.
- Changed bulk People image rows to use a more compact layout with People summaries, responsive button placement, and taller thumbnails aligned to the action stack.
- Changed bulk People selected-image summaries to show the full deduplicated People list for each image so the image list stays consistent with Review People.
- Changed Review People and related People surfaces to deduplicate repeated face records using face identifiers and bounding-box signatures so identical people no longer appear multiple times.
- Changed bulk People loading to populate large image sets asynchronously in batches, lazy-load visible thumbnails on scroll, and recenter the splitter when a new People context opens unless the user already resized it.
- Changed the bulk People bottom section label from Detected People to People for clearer wording across load states and refreshes.

### Removed

- Removed the old shared bulk People footer group actions in favor of per-person group controls inside each detected person card.

---

## v1.4.2

### Summary

This release significantly expands MediaLens People workflows with a redesigned Review People experience, broader bulk editing capabilities, and a shared naming system that makes organizing faces faster and more reliable.

### Highlights

- Review everyone found in one image from a dedicated Review People workspace with bounding boxes, face actions, and image-to-image navigation.
- Manage detected people directly from normal image selections in the Bulk Editor, including scan, rename, ignore, and group-management workflows scoped to the files you selected.
- Name and rename people anywhere in MediaLens using a shared picker that combines typing, dropdown selection, autocomplete suggestions, and Tab completion.
- Use more consistent People buttons, dropdowns, hover states, and accent styling across review panels, bulk editing, and details views.
- Review, name, confirm, ignore, and organize faces much faster thanks to a redesigned workflow that keeps everything in context without jumping between dialogs.

### Added

- Added a dedicated Review People workspace for single-image face review with pan and zoom preview, bounding-box overlays, label toggles, per-face actions, and Previous and Next navigation tied to bulk-selected images.
- Added bulk People support for normal image selections with a Selected Images review list, per-file Review and Scan for People actions, Scan All for People, and detected-people actions scoped only to the selected files.
- Added collapsible Selected Images and Detected People sections in the bulk People editor, including a persistent draggable splitter between them.
- Added per-person Rename and Ignore actions in the bulk People detected list plus Ignore Unnamed support when unnamed detections are present.
- Added a shared People name picker used throughout MediaLens with direct typing, known-name dropdowns, autocomplete suggestions, and Tab completion for faster naming workflows.
- Added per-group Remove from Group buttons on People cards and expanded multi-select support across People gallery, unconfirmed, and unnamed views.

### Changed

- Changed Review Faces in the details panel to open the native Review People workspace instead of a one-name popup so multiple faces in one image can be reviewed in context.
- Changed single-file and bulk People workflows to treat generated "Unnamed" identities consistently, ensuring the correct naming, ignore, and not-person actions are always available.
- Changed People scan refresh behavior so details, Review People, and bulk People views all update immediately after a scan completes.
- Changed bulk People counts, actions, and summaries to stay scoped to the currently selected files instead of the full People library.
- Changed People controls across details, bulk, and review surfaces to use the shared MediaLens themed button system, custom dropdown styling, accent-aware hover states, and light or dark mode contrast rules more consistently.
- Changed Review People face cards, separators, labels, and overlays for better contrast, cleaner spacing, stronger accent usage, and more predictable empty and no-scan states.
- Changed drag-preview behavior so drag overlays remain inside the MediaLens window for a more integrated experience.

### Removed

- Removed the old single-name Review Faces popup workflow from single-image People review.

---

## v1.4.1

### Summary

This release continues polishing the Image Editor toward a professional Photoshop-inspired editing experience while improving performance, consistency, and overall usability across nearly every editing workflow.

### Highlights

- Use the Image Editor with traditional desktop-style menus that no longer overlap or leave detached dropdowns behind.
- Adjust layer opacity and other editor values faster with unified drag, typing, and mouse-wheel numeric controls throughout the editor.
- Paint with smoother brush strokes, improved soft-edge behavior, and cleaner editor-only menus that stay focused on editing workflows.
- Edit text directly on the canvas with reopenable text layers, themed font selection, and improved live text-edit behavior that feels closer to a traditional raster editor.
- Work with a more polished Photoshop-inspired editor featuring rulers, foreground and background color wells, stronger active-tool highlighting, refined Layers controls, and clearer dirty-document feedback.
- Open Image Editor dialogs and filter popups with consistent theming, dedicated per-filter workflows, async filter processing, and faster preview behavior on larger images.

### Added

- Added reusable inline numeric controls across the Image Editor toolbar with direct typing, horizontal drag adjustment, and mouse-wheel support.
- Added expanded automated test coverage for Image Editor menu visibility and shared numeric input behavior.
- Added direct on-canvas text editing with support for reopening existing text layers instead of always creating new ones.
- Added a themed font picker for text layers with corrected preview sizing, accent-aware selection styling, and themed popup scrollbars.
- Added Photoshop-style foreground and background color wells with a dedicated swap control and shared editor color state for paint and fill tools.
- Added Photoshop-style rulers with a View menu toggle and improved cursor or document context readouts.
- Added expanded blend-mode support, persistent layer masks, improved compositing, unrestricted layer movement, and softer hardness-aware brush rendering within the editor document model.
- Added dedicated editor-only Selection, Layers, Image, and Filter menu workflows with popup dialogs for image sizing, layer properties, and filter operations.
- Added shared themed editor dialog controls for rename, layer properties, crop, resize, and filter windows with custom dropdowns, drag-wheel numeric inputs, and accent-aware checkbox styling.
- Added async filter preview and apply execution so expensive filter work runs off the main UI thread with safer stale-preview handling.

### Changed

- Changed top-level Image Editor menu visibility handling to use proper menubar behavior instead of popup-style widgets.
- Changed Image Editor menu behavior so only one top-level menu can be active at a time, preventing overlapping or detached menus.
- Changed Image Editor Edit and View menus to hide gallery-only actions while editing, keeping bulk editors, People review actions, gallery views, and unrelated panel toggles out of the editing workspace.
- Changed View > Show Right Panel in the Image Editor to correctly control the shared right panel when it is being used as the Layers panel.
- Changed brush and paint option controls to use the same inline numeric editing style as layer opacity for more consistent interactions.
- Changed brush hardness response and stroke interpolation so softer brushes produce more natural falloff and smoother curved strokes.
- Changed filter and image-size controls to remain in menus and dialogs instead of crowding the editor toolbars.
- Changed text editing from a separate apply-style flow to direct on-canvas editing with hidden underlying text-layer rendering during live edits, reopen support, and better initialization for new text layers.
- Changed dirty-document feedback in editor tabs to use a clearer high-contrast accent indicator beside the close control.
- Changed the editor toolbar chrome with clearer active-tool highlighting and better foreground or background color control placement and theming.
- Changed the Layers panel layout, tabs rail, row sizing, visibility controls, blend-mode chrome, top opacity controls, and drag-reorder behavior to better match the intended Photoshop-style editing model.
- Changed the layer opacity field from a spinbox to the shared scrub-type numeric control and applied the same editing model across brush, text, fill, filter, adjustment, and resize controls.
- Changed image editor font, blend-mode, selection-shape, fill-mode, and filter dialogs to standardize on themed custom combo boxes instead of stock Qt dropdowns.
- Changed filter dialogs so each menu action opens a dedicated filter workflow, shows immediately before preview work starts, and reports processing status inside the dialog.
- Changed filter preview and apply handling to run asynchronously, discard stale results safely, and avoid cloning the full layered document when only the active layer preview is needed.
- Changed canvas redraw behavior to cache composited editor output between invalidations and changed large filter previews to use downscaled proxy rendering for better responsiveness.
- Changed Image Editor runtime behavior to better tolerate lightweight shells and testing environments, preventing regressions when bridge settings are unavailable.

### Removed

- Removed gallery-only View modes and non-editor Edit menu actions from the Image Editor workspace.

---

## v1.4.0

### Summary

This release introduces the first beta of the new MediaLens Image Editor, bringing a Photoshop-inspired layered raster editing workspace directly into MediaLens. Crop, resize, paint, text, filters, adjustment layers, selection, project saving, and undo are now integrated into the existing media workflow.

### Highlights

- Open the new Image Editor directly inside MediaLens with layered editing, a Photoshop-style workspace, and document tabs.
- Edit images with crop, resize, selections, paint tools, text layers, fills, gradients, filters, and non-destructive adjustment layers without leaving MediaLens.
- Save layered work to the new `.mlimage` project format or export flattened images back to standard image files.
- Undo saved image overwrites more safely with dedicated image-edit retention and `Image Edited` Action History support.

### Added

- Added a new beta Image Editor mode with direct `Edit Image` entry points from the main Edit menu and image context menus.
- Added an image editor workspace with a left tool rail, top options ribbon, central canvas, right Layers panel, document tabs, and bottom status bar.
- Added layer-based editing with active layer selection, reordering, renaming, duplication, visibility, opacity, and flattened image export.
- Added interactive crop and resize workflows with on-canvas crop handles, top-bar resize controls, aspect-ratio lock, and editor-only undo support.
- Added rectangle, oval, lasso, and magic-wand selection tools with replace, add, subtract, tolerance, and crop or resize-aware selection-mask behavior.
- Added Brush, Eraser, Fill, and Gradient tools with active-layer editing, selection-aware behavior, brush preview, and foreground/background color controls.
- Added editable text layers with direct on-canvas text entry, later re-editing, font family selection, text sizing, text width controls, and themed text highlight styling.
- Added Gaussian Blur, Bokeh Blur, and initial color-look filters with live preview support.
- Added editable non-destructive filter layers and adjustment layers for brightness, contrast, saturation, hue, temperature, tint, Levels, and Color Balance.
- Added a new `.mlimage` layered project format with project save and reopen support for layers, text, selections, filters, adjustments, and editor metadata.
- Added dedicated image-edit retention support and saved-edit `Image Edited` Action History entries so overwritten images can be restored after save.
- Added focused automated tests and offscreen editor runtime QA coverage for editor workflows, project round-tripping, filter preview behavior, and core editing interactions.

### Changed

- Expanded MediaLens beyond organization and review workflows by adding integrated in-app image editing.
- Changed editor menus, layer controls, blend mode presentation, rulers, status UI, dirty-document indicators, and toolbar styling to follow a more polished Photoshop-inspired editing model.
- Changed text editing behavior from a separate apply flow to direct on-canvas editing with better live preview, layer reopening, and themed font selection.
- Changed filter and adjustment workflows so MediaLens can support both destructive edits and more reusable non-destructive layer-based editing paths.
- Changed image-save handling so editor saves, Save As operations, and project saves use editor-specific routing instead of the regular gallery open and save flow.

---

## v1.3.5

### Summary

This release finishes a major round of Lightbox refinement. MediaLens now gives the slideshow player proper looping across paginated galleries, clearer playback controls, more stable fullscreen behavior, and more predictable control placement for both images and videos.

### Highlights

- Let Lightbox slideshows keep going across paginated galleries instead of stopping at the current page.
- Control slideshow looping directly from both Settings and a new shortcut, while keeping image, GIF, and video playback in one smoother flow.
- Use fixed-position Lightbox controls that no longer jump around as different media sizes load.
- Read video playback controls more clearly with distinct slideshow and video play or pause pills, plus better top-row layout in the native video overlay.

### Added

- Added a new `Settings > Player > Loop slideshow` setting, enabled by default.
- Added a new `Settings > Hotkey Shortcuts` entry for toggling slideshow loop with `Ctrl+L`.
- Added dedicated dark-theme `slideshow` and `video` SVG assets for the new native Lightbox playback pills.

### Changed

- Changed timed Lightbox slideshow playback to advance across paginated galleries, skip unsupported files between pages, and loop through the full result set instead of only the current page.
- Changed manual Lightbox next navigation to follow the same paginated cross-page behavior as autoplay slideshow advance.
- Changed Lightbox control anchoring so image, GIF, and video navigation buttons stay fixed to the viewer area instead of shifting with each file's rendered size.
- Changed image and GIF slideshow controls to match the native video slideshow pill styling while keeping the separate video play or pause control video-only.
- Changed native Lightbox video controls so slideshow, video play or pause, and mute or volume now sit together in a clearer top-left control row.
- Changed Lightbox playback pills and native mute or volume controls to use a squarer rounded-rectangle shape that better matches the rest of the viewer chrome.
- Changed native Lightbox video pointer activity handling so moving the mouse anywhere in the Lightbox, including outside the rendered video, can reveal controls again.

---

## v1.3.4

### Summary

This release overhauls the Lightbox viewing experience for images, GIFs, and videos. MediaLens now delivers a more unified slideshow workflow, cleaner controls, better theme behavior, more reliable mixed-media playback, dedicated fullscreen Lightbox mode that stays separate from the main app window state, and expanded Lightbox hotkey support.

### Highlights

- Use a more capable Lightbox with a real slideshow player that can move smoothly through images, GIFs, and videos in one flow.
- Navigate with redesigned Lightbox controls that auto-hide, stay aligned to the media itself, and behave more consistently in both light and dark mode.
- Open the Lightbox into its own dedicated fullscreen mode without changing the app window layout, side panels, or maximize state.
- Control the Lightbox more directly with shortcut support for mute or unmute, fullscreen, play or pause, escape, and previous or next navigation.
- Close, pause, mute, and move between items more reliably in the native video overlay with better theme syncing and fewer playback or tooltip issues.
- Enjoy cleaner Lightbox contrast and stability after removing the shadow-heavy control treatments that caused clipping, blinking, and inconsistent rendering.

### Added

- Added a true Lightbox slideshow player that can auto-advance through supported media using the configured Player interval and shared slideshow state across image, GIF, and video viewing.
- Added dedicated Lightbox close controls that remain accessible alongside the existing click-to-close behavior.
- Added dedicated fullscreen Lightbox controls for both the web image or GIF viewer and the native video overlay.
- Added a separate slideshow play or pause control at the center of the Lightbox while keeping independent video playback controls for videos.
- Added configurable Lightbox player shortcuts including Ctrl+M for mute or unmute and Ctrl+F for fullscreen toggle, alongside the existing spacebar, escape, and arrow key controls.

### Changed

- Changed Lightbox controls to auto-hide after pointer inactivity and reappear on movement, while remaining visible when the pointer rests over a control.
- Changed Lightbox fullscreen behavior to use a separate frameless fullscreen host so viewer fullscreen no longer changes the main MediaLens window state.
- Changed Lightbox previous and next controls into edge-aligned side tabs that stay attached to the displayed media bounds instead of drifting into the background.
- Changed Lightbox navigation to wrap back to the beginning and skip unsupported files so slideshow playback does not stall on invalid entries.
- Changed image, GIF, and video Lightbox controls to follow a more consistent theme-aware contrast model across light and dark mode.
- Changed Lightbox theme refresh behavior so open viewers update immediately when switching themes instead of waiting for the viewer to reopen.
- Changed native video overlay layout so mute, video play or pause, close, and slideshow controls align more consistently with the Lightbox chrome.
- Changed Lightbox icon and button treatment away from shadow-dependent rendering in favor of more stable high-contrast controls.
- Changed native video overlay tooltips and volume slider styling to better match the active theme.
- Changed Lightbox keyboard control support so both configurable shortcuts and built-in navigation keys work more consistently across image, GIF, and video viewing.

---

## v1.3.3

### Summary

This release focuses on faster large-library review workflows, a dedicated Bulk Metadata Editor, and expanded People organization tools. MediaLens is faster and more reliable when working through duplicates, similar files, metadata overrides, and growing People libraries, with additional polish across details and gallery menus.

### Highlights

- Use a dedicated Bulk Metadata Editor with independent layout settings to edit ratings, notes, collections, dates, and AI or text-detection overrides across many files from a single workspace.
- Review duplicates and similar files more reliably with persistent cache reuse, clearer real progress reporting, and better handling for very large folders.
- Organize People more easily with Favorite People, custom People groups, and profile-image actions directly from the gallery.
- Work more confidently in the Details panel and gallery menus with better themed dropdowns, clearer text-detection controls, and more consistent right-click grouping.

### Added

- Added a dedicated Bulk Metadata Editor with its own Metadata settings scope, separate single-file and bulk layout preferences, and bulk editing support for ratings, notes, collections, dates, and AI and text-detection overrides.
- Added persistent duplicate review caching that reuses completed review results across folder changes and app restarts.
- Added persistent similar review caching with automatic invalidation when underlying media changes.
- Added stable review signatures to safely determine when cached review results can be reused.
- Added native progress reporting for duplicate and similar review preparation, hashing, grouping, ranking, cache reuse, and result generation.
- Added Favorite People sections and favorite-star actions directly in the People gallery.
- Added custom People groups and group membership management.
- Added person profile image actions in the People gallery.
- Added favorite-star toggles directly on People cards so favorite organization can be managed without leaving the gallery.

### Changed

- Changed duplicate and similar review loading so usable review results appear before large scans fully complete.
- Changed similar-review grouping and ranking to scale better on large libraries through faster pHash neighbor search, safer cache reuse, and stale-result invalidation.
- Changed bulk metadata controls to focus on truly editable override-oriented fields instead of mixing in unrelated text-editing surfaces.
- Changed bulk and single-file override controls to use themed combo boxes that match MediaLens light mode, dark mode, and accent color behavior more consistently.
- Changed combo box wheel handling across the native UI so closed dropdowns no longer change values accidentally while the sidebar is being scrolled.
- Changed the Details panel text-detection override from a toggle to a clearer three-state dropdown that supports automatic detection, explicit text detected, and explicit no text detected.
- Changed People merge behavior so custom group memberships are preserved more reliably when people are consolidated.
- Changed gallery context menus to group related actions more consistently and improve scanning and predictability.

---

## v1.3.2

### Summary

This release focuses on workflow polish across MediaLens, making everyday cleanup work feel faster, clearer, and more dependable. Details, Collections, Settings, menus, and Action History all receive usability improvements, while numerous UI regressions and interaction delays have been resolved.

### Highlights

- Use an improved Details panel with collapsible sections, collection controls, unsupported-file handling, and more convenient save button locations.
- Work faster with more responsive Action History and right-click menus, including visible loading feedback and less delay before menus or actions appear.
- Customize keyboard shortcuts from a new Hotkey Shortcuts settings page with conflict detection and persistent overrides.
- Navigate collections, pinned folders, and folder trees more predictably with right-click behavior that no longer changes the active gallery unexpectedly.
- Enjoy a more polished Settings experience with better scrolling, full theme switching coverage, and corrected themed controls across light and dark mode.

### Added

- Added collection membership controls to the Details panel, including a themed Add to Collection action, clickable collection names, and per-collection removal controls for explicit memberships.
- Added a dedicated unsupported-file Details state that keeps file identity visible while replacing media-only metadata sections with clear unsupported-file messaging.
- Added a clear-search trashcan action inside the main gallery search box using existing MediaLens SVG assets and theme-aware hover styling.
- Added new native menu entries for People Gallery, Unconfirmed People, and Unconfirmed Face Groups.
- Added a Hotkey Shortcuts settings page with editable shortcut bindings, conflict validation, and persistent shortcut overrides.
- Added a gallery context menu Duplicate action and active-collection removal support for both files and explicitly added folders.
- Added dedicated footer notifications for undoable actions so recent edits appear immediately without waiting for Action History refreshes.
- Added loading feedback in the Action History footer while history is being repopulated.
- Added standard menu accelerators.

### Changed

- Changed the Details panel to use session-only collapse state memory so sections stay consistent while you switch files during a session but reset to expanded on a fresh launch.
- Changed the Details panel layout, section rendering, and stabilization behavior to reduce blank space, improve grouped metadata organization, and better match the existing theme system.
- Changed Details panel action rows for tags and descriptions to use responsive side-by-side layouts that can stack cleanly when width is limited.
- Changed Settings > General to split startup options from gallery behavior, and changed all Settings pages to scroll within the dialog instead of forcing larger window sizes.
- Changed Settings page scrollbars, theme propagation, and wrapper styling so settings content switches cleanly between light and dark mode and uses the same MediaLens scrollbar visuals.
- Changed native menus to use standard Windows-style accelerators and visible shortcut labels, including Ctrl+O for Open Folder and clearer separators in the Edit menu.
- Changed right-click menu grouping so file, compare, clipboard, collection, people, management, selection, and view actions are easier to scan.
- Changed gallery and sidebar right-click behavior so folder trees and pinned folders no longer treat right-click as navigation or selection-changing input.
- Changed Action History opening behavior so the window appears faster, refreshes after it is shown, and gives visible progress feedback while entries load.
- Changed context menu responsiveness for duplicate, delete, paste, and remove-from-collection actions by closing the menu immediately and starting heavier work after the UI has a chance to repaint.
- Changed delete workflows to reuse cached settings when available and show progress feedback sooner.
- Changed People wording so Unconfirmed Review is now labeled Unconfirmed People in the People surfaces and menus.

---

## v1.3.1

### Summary

This release adds a new Bulk Rename workspace built for safe, preview-first file renaming. You can now build rename patterns with guided controls, review conflicts before anything changes, and rename matching sidecar files with clear visibility into the final result.

### Highlights

- Use the new Bulk Rename editor to build filename rules with tokens, guided controls, and a live preview before renaming files.
- Review rename conflicts, invalid names, sidecar matches, and no-change rows in a dedicated preview table and optional pop-out window.
- Work more comfortably in the bulk editor with smoother resizing, tabbed editor modes, sticky rename actions, and theme-matched controls.
- Rate files with a new five-star metadata system that now flows through the Details panel, filters, sorting, and search.
- Run or schedule background People scans from Settings and see clearer Local AI readiness guidance for People, tags, descriptions, and OCR.
- Use an improved Action History with date-grouped sections, better detail-pane behavior, copy-path support, and broader undo coverage for People actions.

### Added

- Added a fourth Bulk Editor mode for Rename with pattern-based batch renaming, live preview generation, validation, and execution only after explicit confirmation.
- Added a standalone batch rename engine with token parsing, rename plan generation, conflict detection, sidecar rename support, and safer execution flow.
- Added guided rename controls for filename, folder, date, counter, people, cleanup, conflict handling, missing values, and saved rename settings presets.
- Added a floating Preview Rename Table window so larger rename plans can be reviewed outside the right sidebar.
- Added five-star file rating metadata across the Details panel, metadata settings, gallery filters, sorting, and search.
- Added scheduled and on-demand Scan for People controls to Settings > Background Processes, including status, next run, and cancel support.
- Added date-grouped Action History sections, copy-path support, and expanded undo/redo coverage for People review actions.

### Changed

- Changed bulk editor mode switching from plain buttons to responsive tab-style controls that fit better in smaller sidebar widths.
- Changed bulk editor controls, popups, combo boxes, checkboxes, and preview surfaces to better match MediaLens light mode, dark mode, and accent theme styling.
- Changed bulk editor resize behavior to avoid the severe sidebar drag stalls that previously affected Tags, Descriptions, Text OCR, and Rename layouts.
- Changed Local AI recommended setup and status summaries to include InsightFace Buffalo for People and clearer task-based readiness reporting.
- Changed Background Processes scheduling controls from popup dropdowns to clearer radio-button selectors while eliminating the empty flashing helper windows they were causing.
- Changed guided search metadata ordering and chevron behavior for People and Rating to make those filters read more cleanly.
- Changed Action History detail and list behavior to reduce layout jumps, preserve selection better, and make date-section navigation easier to use.
- Changed startup and dialog theming behavior to reduce blank-window flashes and stale theme repaint issues across settings, Action History, and bulk editor surfaces.
- Changed animated GIF rotation handling so rotating and undoing animated GIFs preserves the full animation instead of flattening to a single frame.

---

## v1.3.0

### Summary

This release introduces People to MediaLens as a new local facial recognition and people-browsing workspace. You can now scan for faces, group appearances by person, review matches, and move between People views and the normal library without losing the rest of your workflow.

### Highlights

- Browse a new People Gallery with named and unnamed person groups, favorite people, and profile images.
- Scan folders for faces with background progress, pause and resume support, and faster rescans that can skip files already processed.
- Review detected faces with confirmation tools, face overlays, profile image selection, and direct access to the Details panel for zoomable inspection.

### Added

- Added the new People feature to MediaLens with People Gallery, unnamed face groups, unconfirmed review, person profile images, and favorite people sections.
- Added local face scanning with optional InsightFace runtime support through AI Models, including GPU-aware runtime detection, provider reporting, and scan progress in the footer.
- Added person-aware search support so `person:Name` can open matched files directly from the main gallery and guided search flow.
- Added People sections to the Details panel and metadata settings so detected people can be shown, hidden, reviewed, and rescanned alongside other file details.
- Added review tools for naming whole groups, confirming all faces in a group, moving or renaming single faces, rejecting wrong matches, ignoring faces, and choosing a person's profile image from review or person search results.
- Added face box and landmark overlays with People settings to control their visibility during review.
- Added face-scan persistence so MediaLens can remember previously scanned files, skip rescans by default, and force full rescans when needed.

### Changed

- Changed People navigation so the dropdown can cleanly enter and exit People mode without trapping the gallery in a People-only view.
- Changed People review cards to load the selected file into the normal Details panel, including larger preview support and wheel zoom for still images.
- Changed People thumbnails to use face-aware square crops that keep the detected face centered while preserving overlay alignment for face boxes and landmarks.
- Changed People review layout with sticky review headers, aligned action buttons, improved card spacing, themed dialogs, and better status feedback for profile image and favorite updates.
- Changed supported People media handling so unsupported files are skipped from scanning and People review instead of appearing with broken results.

---

## v1.2.15

### Summary

This release makes duplicate and similar review less disruptive by keeping large review loads interruptible when you switch folders or views. MediaLens also sharpens and cleans up the image comparison panel so the before-and-after workspace looks tighter and reads more clearly.

### Highlights

- Switch away from large duplicate or similar folders without waiting for the current review build to finish.
- Use a cleaner image comparison slider with a thinner handle and a proper horizontal resize cursor.
- See sharper comparison slot image edges and tighter spacing around the left and right comparison previews.

### Added

- Added interruptible duplicate and similar gallery request handling so stale review loads stop when you change folders or views.
- Added explicit cancellation checks across duplicate and similar hash backfill and grouping work to keep long review passes from monopolizing the active request.

### Changed

- Changed duplicate and similar review refreshes to clear stale pending gallery and count requests before starting a new load.
- Changed the image comparison reveal slider to use a thinner, shorter handle and a horizontal resize cursor while hovering and dragging.
- Changed the left and right comparison slot image layouts to remove extra bottom padding and margin.
- Changed comparison slot borders and rounded thumbnail overlay rendering to produce sharper visible edges in the comparison panel.
- Normalized scrollbars with matching size, color, and style for a more consistent modern look.

---

## v1.2.14

### Summary

This release improves the Background Processes experience by adding tabbed controls for text detection, OCR, and AI metadata workers. MediaLens gallery and bulk editor performance has also been heavily optimized to feel faster and more responsive during routine use.

### Highlights

- Schedule background text detection, OCR, and AI metadata worker passes directly from the Background Processes settings.
- Enjoy faster gallery rendering and bulk editor scrolling with new short-lived caching and smarter thumbnail loading.
- Filter out unsupported text and non-media files automatically during bulk actions.

### Added

- Added tabbed worker settings for Text Detection, OCR, AI Tags, and AI Descriptions under Background Processes.
- Added scheduled and run-now controls for AI metadata workers.
- Added short-lived caching for gallery entry results and counts to speed up UI refreshes.
- Added focused performance logging for gallery entries.
- Added automatic queueing of remaining hash backfills for duplicate and similar review loading.

### Changed

- Changed the scanner settings page name to Background Processes.
- Changed scanner progress to use a shared footer status with a toast fallback.
- Changed the bulk editor to automatically filter out text and non-media files from selections.
- Changed bulk editor row input layout sync and thumbnail loading to work correctly while scrolling.
- Changed gallery stylesheet loading to use direct ordered links for more reliable parsing.
- Changed settings AI runtime status refreshes to debounce routine checks.
- Changed web and native clickable controls to use pointing-hand cursors.

---

## v1.2.13

### Summary

This release makes review and cleanup workflows easier to trust by improving Action History, scanner feedback, and duplicate comparison layout. MediaLens now gives clearer explanations for recent actions, handles multi-file context actions more consistently, and makes duplicate review controls less cluttered.

### Highlights

- Review recent edits in a clearer Action History window with plain-English details and scoped metadata before-and-after summaries.
- Delete, cut, or copy multiple selected gallery items from the right-click menu without falling back to only the clicked file.
- Use duplicate and similar comparison views with less footer clutter while the comparison panel is open.

### Added

- Added a Delete All Action History control with themed warning styling and confirmation.
- Added clearer Action History details that explain selected actions in plain language instead of exposing internal state labels.
- Added visible before-and-after description values to new metadata edit history entries, including AI description fallback values before a user overwrites them.

### Changed

- Changed Action History metadata summaries so description, tag, and OCR edits only describe the fields that were actually edited.
- Changed Action History item tables to use Item, Change, Status, and Action columns with user-facing state labels.
- Changed Action History undo and redo controls to use clearer labels, tooltips, cursor states, and disabled styling.
- Changed gallery right-click Delete, Cut, and Copy actions to respect the full multi-selection.
- Changed the scanner and scan status handling to avoid repeated visible-page scan work and stale scan messages after switching pinned folders.
- Changed duplicate and similar review views so the gallery footer hides while the comparison panel is open and returns when the panel closes or the view changes.

---

## v1.2.12

### Summary

This release polishes the gallery header, breadcrumb navigation, and grouped browsing behavior so everyday folder navigation takes less space and behaves more predictably. MediaLens now handles compact controls, address overflow, and date-grouped layouts more like a native file browser.

### Highlights

- Use a cleaner two-row gallery header with compact icon buttons for nested files, sorting, filtering, grouping, and date granularity.
- Navigate long folder paths more easily with a This PC breadcrumb entry, Explorer-style overflow, and better drive switching.
- Switch to Group By Date more reliably without group headers collapsing into masonry or grid columns.

### Added

- Added a This PC breadcrumb icon at the start of drive-based paths so Windows drives are easier to reach from the address bar.
- Added Explorer-style breadcrumb overflow that moves hidden path segments into a dropdown from left to right as space gets tight.
- Added compact SVG-only controls for Include nested files, Sort by, Filter by, Group by, and Group By Date granularity.
- Added light, dark, and inactive SVG variants for the new compact gallery header controls.

### Changed

- Changed the gallery header layout so compact controls and search share the second row, with the search box expanding or shrinking before controls wrap.
- Changed gallery header buttons, chips, search, and breadcrumbs to use more consistent heights, corners, spacing, and borders.
- Changed breadcrumb menu dismissal so address bar dropdowns close when clicking outside the gallery as well as inside it.
- Changed Group By Date rendering so grouped gallery headers keep the full-width grouped layout during refreshes and setting changes.
- Changed gallery rendering so refreshes requested during an active render are queued and replayed instead of being dropped.
- Changed the Guided Search Builder control heights and header spacing to better match the surrounding compact header controls.

---

## v1.2.11

### Summary

This release introduces persistent Action History with undo and redo across sessions, making large cleanup and metadata workflows safer, easier to review, and easier to recover from. MediaLens now tracks whether previous actions remain reversible, adds clearer history states, and improves workflow organization across editing and review tools.

### Highlights

- Review recent deletes, moves, copies, renames, metadata edits, hidden-status changes, and rotations in one Action History window.
- Undo and redo supported actions from keyboard shortcuts or Action History while MediaLens checks stale recovery paths only when needed.
- Use a cleaner Edit and View menu layout with themed history, backup, and local AI status windows.

### Added

- Added Action History with grouped rows, item-level details, search, filters, and undo/redo controls.
- Added undo and redo support for deletes, moves, copies, renames, folder creation, metadata edits, hidden status changes, and rotations.
- Added persistent history validation so recent undo and redo actions remain available across sessions as long as their files or retained copies are still recoverable.
- Added selective item undo and redo for grouped history actions.
- Added Bulk Description Editor to the Edit menu.

### Changed

- Changed redo shortcuts to support both Ctrl+Y and Ctrl+Shift+Z.
- Changed Action History validation so broad checks run when the history window opens, while keyboard shortcuts validate only the next undo or redo candidate.
- Changed partial group undo and redo history messages to report how many items were handled and skipped.
- Changed Action History item states to show clearer labels for active, undone, unavailable, and externally changed items.
- Changed Action History, Library Backup options, and related dialog styling to support light theme, dark theme, native title bars, and accent-aware controls.
- Changed the Edit menu so Action History sits directly below Redo, bulk editors are grouped there, and Local AI Models and Status is labeled as an edit action.
- Changed the View menu so Masonry appears first and duplicate/similar views are separated into their own group.
- Changed the Library Backup export note to use shorter wording without legacy app details.

---

## v1.2.10

### Summary

This release focuses on responsiveness in tag filtering, bulk editing, duplicate review, and comparison workflows. MediaLens now shows visible gallery updates sooner, avoids several unnecessary UI refresh passes, and recovers more reliably from panel resizing during review.

### Highlights

- Filter by tags with faster gallery updates and less blocking work from the tag list.
- Review duplicates and similar files without the gallery waiting indefinitely behind off-screen loading work.
- Use bulk tag and description editors with clearer per-file Save controls and more stable responsive row layouts.

### Added

- Added per-file Save Tags buttons in the bulk Tags editor.
- Added per-file Save buttons beside Generate Description in the bulk Descriptions editor.
- Added targeted performance logging around gallery refreshes, bulk editor rebuilds, metadata selection, and layout syncs.
- Added short-lived gallery count caching and local AI status caching so repeated refreshes can avoid expensive checks.

### Changed

- Changed typed tag edits so they save only when the user clicks Save instead of auto-saving after input debounce.
- Changed tag filtering so the gallery and bulk editor update before slower tag-list state refresh work.
- Changed tag scope counts to update in place and reuse cached scope data when the active scope has not changed.
- Changed bulk selected-file rows to avoid redundant full layout passes when width, row count, and orientation are unchanged.
- Changed bulk row action button sizing so longer labels keep enough space before shorter Save buttons borrow equal width.
- Changed bulk tag and description row buttons to use distinct object names and styling independent of single-file metadata visibility settings.
- Changed duplicate and similar review loading so review results render directly instead of waiting for detached staged cards.
- Changed comparison panel show and hide handling to notify the gallery after splitter resizing so WebEngine repaints without requiring a manual resize.
- Changed startup dark-mode handling so the gallery background is dark before the WebEngine page finishes loading.
- Changed settings, local AI status checks, scan cache invalidation, and settings-triggered gallery refreshes to do less broad repeated work.

---

## v1.2.9

### Summary

This release expands folder workflows, collection behavior, and file handling while making gallery video playback and sorting more dependable. MediaLens now handles more real-world library layouts with less unnecessary scanning, smoother playback behavior, and clearer fallback handling.

### Highlights

- Drag folders between the gallery, file tree, pinned folders, collections, and external destinations with clearer move, copy, and pin behavior.
- Keep collections live with folder sources, optional nested file inclusion, and MediaLens recycle bin recovery for deleted folders and file types.
- Browse and sort larger galleries more smoothly, including WebM playback fixes and lightweight display for non-media files when enabled.

### Added

- Added folder drag-and-drop support for gallery folders, file tree destinations, pinned folders, collections, and Windows File Explorer destinations.
- Added support for collections that include live folder sources instead of only copied file snapshots.
- Added MediaLens recycle bin support for deleted folders and all file types that MediaLens can delete.
- Added a General setting to switch between showing all file types and showing media files only, with lightweight icons for unsupported file types.
- Added Local AI Models VRAM fit indicators, recommended-model emphasis, and a fit message below the model list.

### Changed

- Changed drag-and-drop tooltips for folders, pinned folders, collections, invalid destinations, and same-destination copy behavior.
- Changed folder copy and move refresh handling to use narrower cache invalidation instead of broad app-wide cache clearing where possible.
- Changed collections so folder display and Include nested files behavior match normal gallery folder behavior.
- Changed unsupported file handling so non-media files avoid expensive metadata, thumbnail, OCR, and AI processing when shown.
- Changed the Local AI Models window so light mode styling covers the model list and related controls more consistently.
- Changed delete confirmation dialogs for folders and collections to use MediaLens themed titles, accent colors, and button styling.
- Changed the empty no-folder gallery message so it spans the gallery, uses bold text, and explains how to pick a folder.
- Changed in-place gallery video playback to clear stale frames when switching videos.
- Changed WebM handling so playback controls appear correctly, invalid tiny dimensions no longer collapse masonry cards, and in-place playback sizing is more stable.
- Changed sort-only gallery refreshes so they skip unnecessary scan and count work.

---

## v1.2.8

### Summary

This release makes MediaLens feel more responsive during everyday browsing and editing. It also adds more direct controls for saving metadata, opening previews, and managing the left sidebar layout without unnecessary scrolling or waiting.

### Highlights

- Switch themes, open settings, toggle hidden files, and return from minimize with less visible lag.
- Save Tags, Descriptions, or Text OCR directly from their Details panel sections.
- Collapse sidebar sections and open bulk-editor thumbnails in the same lightbox used by the gallery.

### Added

- Added collapsible headers for Pinned Folders, Folders, Collections, and Smart Collections in the left sidebar.
- Added targeted Details panel save buttons for Tags, Descriptions, and Text OCR.
- Added a separator above the bottom Details panel save-all action.
- Added lightbox opening from preview thumbnails in the bulk Tags and Descriptions editors.
- Added placeholders for unsupported or corrupt images so blank gallery cards explain what happened.

### Changed

- Changed minimize and restore handling so resize, relayout, and thumbnail background work are coalesced instead of all resuming at once.
- Changed settings, theme switching, hidden-file toggles, and masonry pagination refresh paths to reduce apparent lag.
- Changed theme refresh sequencing so native widgets and the web gallery switch together instead of showing a mismatched intermediate state.
- Changed theme coverage for settings, comparison, OCR review, dialogs, context menus, selection colors, no-text icons, and bulk thumbnail borders.
- Changed sidebar section size restore so Pinned Folders keeps a usable height across sessions and is protected from being squeezed by the file tree.
- Changed Details panel tag edits to save through the tag-only path instead of the full save-all handler.
- Changed bulk editor mode buttons to use the pointing-hand cursor.
- Changed gallery handling for unsupported or corrupt image files so previews and cards show a clear unavailable state.

---

## v1.2.7

### Summary

This release focuses on making Paddle OCR setup recover cleanly when a previous install attempt failed. MediaLens now builds and verifies OCR runtimes in a clean staging folder before replacing the active runtime, giving GPU systems a more reliable repair path and better diagnostics if something still goes wrong.

### Highlights

- Repair Paddle OCR without leaving the live OCR runtime half-created after a failed install.
- Keep the Local AI setup page focused on active Paddle install progress instead of stale probe errors.
- Capture a dedicated Paddle install log so future setup failures are easier to diagnose.

### Added

- Added a dedicated Paddle OCR install log in the existing debugging logs folder.

### Changed

- Changed Paddle OCR install and repair to build a clean staging runtime, probe it, and only activate it after success.
- Changed Paddle OCR package installs and probes to run from the isolated OCR runtime folder without MediaLens bundle paths ahead of the runtime packages.
- Changed Paddle OCR GPU install targeting to prefer the current Paddle GPU package version.
- Changed Local AI setup status handling so background status refreshes do not overwrite active Paddle install progress with stale probe results.

---

## v1.2.6

### Summary

This release makes MediaLens easier to start on more Windows PCs without overwhelming the system. Startup now waits for the user to choose a folder, background scanning is less aggressive, other drives are easier to browse, and local AI setup is more deliberate about downloads and GPU OCR repair.

### Highlights

- Start MediaLens without automatically scanning the whole C drive on first launch.
- Browse other Windows drives from the folder tree, including external or secondary photo drives.
- Install and repair Paddle OCR with clearer GPU package checks on compatible NVIDIA systems.

### Added

- Added a Settings > General startup option to open no folder on startup, now used as the default.
- Added empty-gallery guidance telling users to use File > Open and where to change the startup behavior.
- Added support for browsing other Windows drives from the folder tree.
- Added Paddle OCR status details for CPU Paddle, GPU Paddle, PaddleOCR, and detected GPU device count.

### Changed

- Changed startup folder handling so new installs do not automatically open and scan a folder until the user chooses one.
- Changed Local AI recommended settings so they select the recommended Gemma profile without starting a model download.
- Changed Gemma recommendation logic so systems without detected NVIDIA VRAM choose the smallest profile instead of the largest profile.
- Changed background scanning to back off CPU usage so Windows and other apps remain more responsive during large scans.
- Changed Paddle OCR runtime repair to clear stale Paddle package files before GPU activation.
- Changed Paddle OCR GPU validation to use a focused Paddle core probe instead of a broader PaddleOCR import during install checks.
- Changed Paddle OCR repair so compatible NVIDIA systems with GPU preference do not silently settle on CPU fallback after a GPU install failure.
- Changed Paddle OCR worker startup so bundled NVIDIA package DLL folders are added to the runtime path before OCR starts.

---

## v1.2.5

### Summary

This release makes everyday navigation and setup feel cleaner in MediaLens. Pinned folders can now be reordered directly, settings opens without flashing helper windows, and OCR runtime repair is more resilient when a previous install is stale.

### Highlights

- Reorder Pinned Folders by dragging them into the order you prefer.
- Open Settings with fewer distracting helper-window flashes from AI runtime checks.
- Repair Paddle OCR runtimes more reliably when an old or broken install is in the way.

### Added

- Added drag-and-drop sorting for Pinned Folders in the left sidebar.

### Changed

- Changed the Pinned Folders drag preview to show the styled row background, border, folder icon, folder name, and pin icon.
- Changed AI runtime and GPU probe subprocesses so they start hidden on Windows when status checks run from Settings.
- Changed shutdown handling for async AI status, media listing, media count, and child-folder callbacks so late results do not touch a deleted Bridge object.
- Changed Paddle OCR reinstall behavior to recreate stale runtimes before reinstalling and retry GPU activation after a failed runtime probe.

---

## v1.2.4

### Summary

This release makes detailed image review easier in MediaLens. OCR Review and the main image lightbox now support pan and zoom, while comparison workflows keep context, actions, and layout more stable as you move through groups.

### Highlights

- OCR Review images now support cursor-centered zoom and drag panning for precise text inspection.
- Image lightbox viewing now supports the same scrollwheel zoom and drag panning workflow.
- Comparison review navigation keeps group context, action controls, and panel sizing more predictable.

### Added

- Added cursor-centered zoom and drag panning to OCR Review images.
- Added pan and zoom to image and GIF lightbox.
- Added dedicated single-group review cards for the comparison review flow.
- Added a Details panel entry point for opening Text OCR Review from the Text OCR group.

### Changed

- Changed OCR Review to show the pan and zoom guidance message when a review image is loaded, while still replacing it with OCR status after generate actions.
- Changed zoom-out behavior in OCR Review and the image lightbox to recenter the image when returning to fit.
- Changed single-group comparison review actions to stay on a bottom action row and remain clipped cleanly during resize.
- Changed comparison review navigation to preserve the comparison panel height and restore group scroll position after closing comparison.
- Changed comparison group navigation to account for the sticky stats header so selected groups land more consistently.
- Changed comparison panel image loading and browse text sizing to be more stable.

---

## v1.2.3

### Summary

This release keeps Fast OCR repairs from downgrading a working GPU runtime. MediaLens now preserves an active Paddle GPU setup during repair and gives clearer status when repair fails instead of making the runtime look uninstalled.

### Highlights

- Fast OCR repair now protects an already-working Paddle GPU runtime from being replaced by CPU fallback.
- Paddle OCR setup now reports when the runtime is still installed after a failed repair attempt.
- CPU fallback installation now tries the package source that works for current Paddle CPU wheels before trying Paddle's CPU index.

### Changed

- Changed Paddle OCR repair so an existing GPU-active runtime is not removed before the replacement GPU package is proven usable.
- Changed Paddle OCR repair so CPU fallback is skipped when it would downgrade an existing GPU-active runtime.
- Changed Paddle OCR install failure handling to re-check the existing runtime before reporting it as not installed.
- Changed Paddle CPU fallback install order to try PyPI before Paddle's CPU package index.

---

## v1.2.2

### Summary

This release makes MediaLens safer to repair, reinstall, and move between machines. It adds full library backup and restore tools, gives import and uninstall workflows category-level choices for app data, and improves startup update diagnostics for broken-install recovery.

### Highlights

- Library backup export and import are now available from the File menu.
- Import can merge or replace supported app-data categories independently, including recycle-bin retention files, thumbnails, downloaded AI models, and AI runtime environments.
- Uninstall now asks which MediaLens data categories to keep or delete and cleans up unselected app-data files, including legacy leftovers.

### Added

- Added File menu tools to export and import MediaLens library backups.
- Added backup support for the main database, recycle-bin retention system, settings, thumbnails, downloaded AI models, managed Python, Python bootstrap files, and AI runtime environments.
- Added timestamped safety backups before library import restores the main database.
- Added per-category import merge options for recycle-bin retention data, thumbnails, downloaded AI models, and AI runtime environments.
- Added installer uninstall prompts for database, settings, recycle-bin retention data, thumbnails, AI models, AI runtimes, debug logs, import backups, legacy files, and other app-data.
- Added startup update diagnostics before the app bridge initializes.

### Changed

- Changed startup update dialogs so they are parented to the splash screen instead of appearing as stray top-level windows.
- Changed startup update checks to log failures and fall back to the GitHub latest-release API when the raw version check fails.
- Changed update-check setting synchronization so changes apply immediately.
- Changed library import so the main database is restored as the selected backup while supported app-data categories can merge or replace independently.
- Changed interactive uninstall cleanup so app-data files are removed unless the user explicitly selects the matching category to keep.

### Removed

- Removed active carry-forward of old MediaManagerX legacy files from the library backup format.

---

## v1.2.1

### Summary

This release makes MediaLens’ bulk editing tools much more practical for everyday use. Tags, descriptions, and Text OCR now share a polished workflow with per-file and batch editing, generation, review, saving, and responsive layouts that scale to large selections.

### Highlights

- Bulk Editor now brings Tags, Descriptions, and Text OCR together in a single, consistent workspace.
- Text OCR Review now provides a large image view with side-by-side Fast OCR, AI OCR, and User Typed text, along with clear source confirmation and navigation.
- Scanner scheduling is more practical with saved folders, configurable intervals, and clearer schedule status.

### Added

- Added a Text OCR tab to the Bulk Editor with per-file No Text, Fast OCR, AI OCR, and Keep actions.
- Added bulk Text OCR bottom actions for Fast OCR, AI OCR, saving edited OCR text to the database, and clearing OCR text.
- Added a dedicated Text OCR Review workspace with a large preview image, side-by-side Fast OCR, AI OCR, and User Typed fields, Keep and Generate controls, Previous and Next navigation, status messaging, and close controls.
- Added No Text actions to both the Bulk OCR rows and the OCR Review workspace.
- Added visual confirmed-source indicators for OCR Review text fields and Keep buttons.
- Added bulk list synchronization for OCR Review so previous and next navigation scrolls to the reviewed file and highlights it with the accent color.
- Added per-file generate buttons below inputs in bulk tag and description rows.
- Added source folder lists for scheduled scanner runs instead of relying on the current gallery selection.
- Added scanner schedule options for hourly, daily, weekly, and monthly runs with time and day controls.
- Added Next Scheduled Run display when scheduling is enabled.
- Added an OCR action to copy all folders from the list above into the OCR scanner folder list.

### Changed

- Changed the Bulk Editor into a more usable multi-tool workspace with Tags, Descriptions, and Text OCR tabs.
- Changed bulk selected-file rows to load and resize more reliably across narrow and wide right-panel layouts.
- Changed bulk tag, description, and OCR rows so thumbnails, inputs, and action buttons align consistently and wrap cleanly at small widths.
- Changed OCR Review to occupy the main gallery workspace while preserving the existing gallery selection and returning quickly when closed.
- Changed OCR Keep actions so manually typed edits are saved before the source is confirmed.
- Changed No Text handling so files leave Text Detected filtered lists after being marked as no text, and OCR Review advances to the next file when appropriate.
- Changed Select All and bulk editor refresh behavior so large selections with the Tag List and Bulk Editor open no longer trigger the flashing popup-window crash.
- Changed the scanner page to be scrollable and to keep folder and schedule sections collapsed by default.
- Changed scanner scheduling so Run in background controls whether the scanner runs, without disabling the schedule and folder controls.
- Changed scanner status so enabling Run in background reports Scheduled when appropriate.
- Changed scanner labels and radio options for clearer wording.
- Changed scanner folder and schedule headers to use SVG disclosure icons and theme-aware styling.
- Changed Paddle Runtime install and repair access so the install path is kept in the AI Models Status window.
- Changed Paddle OCR probe failure output so noisy pip/network text is handled more cleanly.
- Changed several bulk editor and scanner controls to better match MediaLens light/dark theme, accent color, spacing, and SVG icon conventions.

### Removed

- Removed the duplicate Paddle Runtime Install/Repair button from Settings > AI > Text and OCR.

---

## v1.1.37

### Summary

This release makes Paddle OCR setup clearer and more reliable, especially on systems with NVIDIA GPUs. MediaLens now avoids misleading install/status states and gives developers a faster way to test installed-runtime behavior without rebuilding.

### Highlights

- Paddle OCR setup is more transparent about whether GPU is active, CPU fallback is in use, or repair is needed.
- AI Models status no longer looks like it starts installs while it is only checking runtimes.
- Source runs now use installed AI runtime paths by default, making Paddle fixes faster to test before packaging.

### Added

- Added installed-build AI runtime path behavior to `python run.py` dev launches.
- Added a `MEDIALENS_USE_INSTALLED_AI_PATHS=1` switch for source runs that should use AppData AI runtime and model paths.

### Changed

- Changed Paddle OCR installation so PaddleOCR dependency resolution cannot replace the final selected GPU runtime with CPU Paddle.
- Changed Paddle OCR installation to check and repair pip without upgrading pip itself on every install.
- Changed Paddle OCR GPU detection to try absolute `nvidia-smi` paths and report the attempted detection failures.
- Changed Paddle OCR status details to distinguish installing, checking, NVIDIA detected but inactive, valid CPU fallback, and runtime probe errors.
- Changed Paddle status so CPU-only Paddle on a detected NVIDIA GPU is shown as a repairable GPU error, not a clean install.
- Changed the Paddle install button on the AI Models status page to wait for install progress signals instead of immediately refreshing back to a not-installed probe result.
- Changed AI Models status refreshes to show `Checking` instead of `Installing` while probing runtimes.
- Changed the AI Models status expand and collapse controls to use theme-appropriate SVG arrows instead of text characters.
- Changed model install status updates so other model rows stay collapsed unless explicitly expanded.
- Changed the gallery loading message to remove encoded text.

### Removed

- Removed no user-facing features in this release.

---

## v1.1.36

### Summary

This release focuses on startup reliability and a clearer OCR setup experience. MediaLens now avoids a Windows WebEngine startup path that could crash just after the splash screen, while OCR settings and model status are easier to understand and manage.

### Highlights

- Startup is more reliable on affected Windows installs that previously crashed just after the splash screen.
- OCR setup is easier to review with clearer Fast OCR, AI OCR, and Paddle runtime status.
- Review workflows now make it faster to generate OCR text and mark files as having no text.
- Paddle OCR installation now tries multiple GPU package versions first, then falls back to CPU with a clear reason when GPU is unavailable or unusable.

### Added

- Added Paddle OCR to the Local AI Models status dialog with status, progress, install, uninstall, and delete-cache controls.
- Added OCR scanner scope options for processing either files marked as text detected or all files in scope.
- Added Fast OCR and AI OCR generate buttons to the OCR review workflow.
- Added a No Text review action that clears the selected OCR winner and marks the file as no text detected.
- Added startup diagnostics that log whether MediaLens is using the default or custom WebEngine page.

### Changed

- Changed Windows frozen builds to keep WebEngine's default page during startup, avoiding a native crash path seen on some installed systems.
- Changed splash startup handling to avoid forcing an immediate Qt event pass before the main window is built.
- Changed Settings > AI to refresh lazily so opening settings no longer runs expensive status checks for every page up front.
- Changed OCR settings into clearer Tags, Descriptions, and Text OCR tabs with model status and editable prompts.
- Changed Paddle OCR status reporting to show whether GPU is actually active instead of only showing the preferred mode.
- Changed review-window OCR generation to update the OCR cell in place without reloading and re-sorting the review list.
- Changed file-tree and pinned-folder hidden-state lookups to keep rendering if a database lookup fails instead of allowing a Qt model callback to terminate the app.
- Changed Paddle OCR installation to try multiple GPU package versions before falling back to CPU with the GPU failure reason.
- Changed Paddle OCR worker startup so `auto` with GPU preference actually passes the GPU device to PaddleOCR.
- Changed Paddle OCR status so partial failed runtimes no longer appear as installed, while valid CPU fallback runtimes still do.
- Changed Paddle CPU fallback to try PyPI if Paddle's CPU package index cannot be reached.

### Removed

- Removed OCR Accurate, leaving Fast OCR through Paddle and AI OCR through Gemma 4.

---

## v1.1.35

### Summary

This release makes duplicate and similar-image review smoother and faster. The comparison panel now opens directly into the right review context, adds practical image-by-image navigation, and bulk editors feel more responsive with large selections.

### Highlights

- The comparison panel now preloads review groups and lets you move through images and groups without leaving the panel.
- Bulk tag and caption editors open large selections faster by loading thumbnails lazily.
- Comparison labels now use live file sizes, so equal-size files are no longer shown as largest or smallest winners.

### Added

- Added Previous Image and Next Image controls for both comparison slots when reviewing duplicate or similar groups.
- Added startup and reopen handling so the comparison panel can preload the current duplicate or similar group when the bottom panel is already open.
- Added disabled tooltips for comparison navigation buttons so unavailable previous or next actions explain why they cannot run.

### Changed

- Changed comparison group navigation to remember the active review group while the bottom panel is closed and resume there when reopened.
- Changed duplicate and similar review comparison setup so opening the bottom panel seeds the active group without forcing the panel to reopen after it is closed.
- Changed comparison navigation button styling, disabled states, cursors, and SVG close icons to better match the rest of MediaLens.
- Changed comparison file-size ranking to use the live file size on disk instead of stale cached scan data.
- Changed bulk tag and bulk caption editors to lazy-load thumbnails so selected-file rows render faster.
- Changed bulk Select All handling to reduce duplicate metadata refresh work and batch selected-file database reads.

### Removed

- Removed stale auto-seeding paths that could force the bottom comparison panel open again after users closed it.

---

## v1.1.34

### Summary

This release makes MediaLens more dependable when working with SVGs, bulk selections, and the details panel. SVG files now behave better across previews and Local AI, while selection and empty-state behavior is cleaner and more predictable.

### Highlights

- SVG files now preview more cleanly and can be used with Local AI tagging through automatically generated preview images.
- The details panel now clears stale tags, descriptions, and AI fields when nothing is selected.
- Multi-select behavior is more dependable, including Ctrl-click deselection from an existing selected group.

### Added

- Added SVG poster generation for Local AI so SVG files are analyzed through a raster preview while tags and descriptions still save to the original SVG record.

### Changed

- Changed SVG rendering in the details panel so previews stay sharper when the right sidebar is resized.
- Changed SVG thumbnails in the bulk tag and caption editors to use high-contrast backgrounds.
- Changed Ctrl-click gallery selection so clicking an already selected item removes it from the current selection and updates the details panel with the reduced selection.
- Changed the details-panel empty state so stale tags, descriptions, embedded metadata, and AI fields are cleared and replaced with `Select file(s) to view details.`
- Changed bulk selected-file rows to guard against deleted Qt objects during teardown and layout updates.
- Changed corrupted text glyphs in native controls to use SVG icons or source-safe separators instead of fragile encoded characters.
- Changed `main.py`, `bridge.py`, `web/app.js`, `settings.py`, and the native window code into smaller task-focused modules while preserving the existing app behavior.
- Changed JavaScript bridge helpers to tolerate missing or non-array values in more gallery and settings flows.

### Removed

- Removed duplicate Qt bridge tooltip slots that caused ambiguous overload warnings in the terminal.

---

## v1.1.33

### Summary

This release makes MediaLens much faster and more practical when working with groups of files. Bulk editing is now more capable, selection stays stable while resizing the panel, and the new caption workflow makes it easier to manage descriptions separately from tags.

### Highlights

- Added a dedicated Bulk Captioning Editor alongside the upgraded Bulk Tag Editor.
- Bulk editing now shows selected files with thumbnails and per-file editable tag or caption fields.
- Multi-file gallery selections now stay visually selected while resizing the editor panel.

### Added

- Added a separate Bulk Captioning Editor with its own page, controls, per-file description fields, and View menu entry.
- Added a mode switch at the top of the Bulk Editor so you can quickly move between bulk tag editing and bulk caption editing.
- Added compact selected-file cards to bulk editing, including thumbnails and editable per-file fields for the active mode.

### Changed

- Changed the Bulk Tag Editor layout to better support large selections, including a more useful selected-files view and updated bulk generation controls.
- Changed bulk caption generation to use the existing MediaLens description pipeline while presenting it as captions in the bulk workflow.
- Changed bulk editor behavior during resize so selected files in the gallery keep their multi-selection state instead of collapsing visually to one file.
- Changed gallery selection updates with the tag list open to reduce unnecessary tag-list work and improve responsiveness when moving between files.

### Removed

- Removed Common and Uncommon sections, add-to-all input, and tag-list access from the caption workflow where they did not fit description editing.

---

## v1.1.32

### Summary

This release makes Local AI much more reliable in real-world use, especially in installed builds. MediaLens now handles more image formats correctly for Gemma, keeps model selection and status more consistent, and fixes several frustrating Local AI setup and runtime edge cases.

### Highlights

- Gemma 4 is more dependable in the installed app, with several fixes for model selection, runtime launch behavior, and fallback handling.
- Local AI now handles AVIF, HEIC, HEIF, TIFF, WebP, animated images, and video sources more safely by converting them to preview images before sending them to Gemma.
- The Local AI setup and status experience is clearer, with improved model syncing, copyable status text, and simpler advanced versus recommended flows.

### Added

- Added stronger Gemma launch diagnostics in worker logs to make installed-build failures easier to trace.
- Added broader retry and fallback handling for Gemma GGUF launches, including a true CPU-offload fallback path when GPU startup fails.
- Added more complete Gemma sub-model syncing between settings UI, status views, and active runtime payloads.

### Changed

- Changed Local AI source handling so Gemma uses generated preview images for AVIF, HEIC, HEIF, TIFF, WebP, animated images, and videos instead of sending unsupported originals to llama.cpp.
- Changed Gemma GGUF launch behavior in installed builds to better isolate subprocess state inherited from the packaged app.
- Changed Gemma profile selection so the selected downloaded sub-model consistently becomes the active runtime model instead of only updating UI state.
- Changed Local AI troubleshooting surfaces so important status and error text remains easier to copy and verify.
- Changed several Local AI model-management flows to behave more predictably when switching between downloaded Gemma variants.

### Removed

- Removed a parser-sensitive tag filter expression that could fail on stricter Python parsing paths.

---

## v1.1.31

### Summary

This release makes Local AI setup much easier to understand and much more practical to use. MediaLens now guides users toward a recommended Gemma 4 setup, makes model switching and downloads easier to manage, and greatly improves local captioning reliability on GPU systems.

### Highlights

- Gemma 4 now supports multiple downloadable model variants, so you can switch between installed versions without uninstalling and reinstalling each time.
- Local AI setup now has a simpler recommended flow for most users, while still keeping advanced controls available when needed.
- Gemma 4 descriptions are far more reliable again, with cleaner output and better handling for GGUF and BF16 model variants.

### Added

- Added a simplified Local AI Models onboarding flow with `Use Recommended models` and expandable advanced options.
- Added downloadable Gemma 4 sub-model management, including installed-model indicators, per-model download and delete actions, and easier switching between downloaded variants.
- Added recommended Gemma profile selection based on available VRAM, including larger options for high-VRAM GPUs.
- Added clearer Gemma profile and download progress presentation inside the Local AI Models window.

### Changed

- Changed Gemma 4 local inference from a single fixed Transformers setup to selectable llama.cpp-based model variants, including GGUF and BF16 options.
- Changed Gemma 4 prompting and cleanup so image descriptions return normal final paragraphs more reliably instead of reasoning or instruction text.
- Changed Local AI installation to overlap runtime preparation with model downloads for faster setup.
- Changed AI model status reporting to better distinguish simple user-facing status from advanced technical details.
- Changed the Settings `AI` page to use a simpler local AI status presentation and a cleaner handoff into the advanced Local AI Models window.
- Changed Local AI setup, runtime probing, and installer diagnostics to improve GPU detection, validation, and recovery when CUDA-backed runtimes are available.
- Changed Local AI status and error text surfaces so important messages are selectable and easier to copy when troubleshooting.

### Removed

- Removed older low-level Local AI controls from the main Settings `AI` page that no longer fit the new guided setup flow.

---

## v1.1.30

### Summary

This release makes large folders feel significantly faster and more responsive during scanning. MediaLens now avoids unnecessary work by detecting changes more efficiently, prioritizing visible content, and resuming scans more intelligently.

### Highlights

- Large folders now spend far less time checking for changes before the gallery becomes usable.
- Visible media is scanned first, so on-screen content loads and updates sooner.
- Scans resume more gracefully after interruptions, reducing wasted work.

### Added

- Added checkpoint-based scan resume so interrupted scans continue from prior progress instead of restarting.

### Changed

- Reworked scan evaluation to use a single-pass change detection instead of multiple full-folder checks.
- Optimized change detection by comparing against preloaded in-memory data instead of per-file database queries.
- Limited deep scanning to only files that actually changed instead of reprocessing entire folders.
- Prioritized currently visible gallery items during scanning.
- Switched to thread-local SQLite connections to eliminate cross-thread scanner errors.
- Improved animated GIF lightbox rendering to avoid CPU-heavy styling that could impact playback.

---

## v1.1.29

### Summary

This release fixes local AI install and preload failures in installed builds. MediaLens now launches each model worker from its own isolated runtime path, skips model downloads when required files are already present, repairs stale InternLM support paths, and reports clearer install errors when a preload really fails.

### Highlights

- Existing local AI model files are now detected before MediaLens tries to download them again.
- Install can finish cleanly after creating the runtime even when the model files were already present.
- Local AI workers no longer inherit the packaged app's internal Python package path, preventing installed-build dependency conflicts with per-model virtual environments.
- InternLM XComposer2 can recover when its local CLIP path was previously patched to an old development model folder.
- A failed preload/download now includes a clearer process exit code, and no longer leaves a false error if the required model files are confirmed on disk.

### Changed

- Changed local AI model installation to skip the preload/download step when model files are already installed.
- Changed local AI worker startup to launch direct worker scripts from the model runtime directory instead of importing through the packaged app bundle.
- Changed local AI install completion to re-check model files after preload failures before reporting an error.
- Changed InternLM XComposer2 path repair so stale local CLIP paths are replaced with the currently configured model folder.
- Changed local AI worker failure messages to include Windows exit-code details when available.

---

## v1.1.28

### Summary

This release fixes a local AI setup failure in the v1.1.27 installer. Model installation can now proceed correctly, and setup errors show useful details in the Local AI Models window instead of only showing a generic error.

### Highlights

- Fixed local AI model installs failing immediately with an internal settings error.
- Local AI Models now shows install progress and error details directly in the setup window.
- Added a developer-only script to point dev runs and installed runs at the same local AI model folders.

### Added

- Added `scripts/use_installed_local_ai_paths.ps1` for local development machines that should share installed MediaLens AI folders.
- Added a compact install progress/error message line to the Local AI Models window.

### Changed

- Changed local AI install preload settings so MediaLens copies the selected model into the worker payload instead of mutating immutable settings.

---

## v1.1.27

### Summary

This release makes local AI setup easier to understand and manage. MediaLens now gives clearer model install status, simpler setup wording, and direct install or uninstall controls without exposing backend details users do not need.

### Highlights

- Local AI Models and Status is now available from the View menu whenever you want to check model readiness.
- Each local AI model now has clearer status, size, purpose, install, and uninstall controls in one dedicated window.
- The Python bootstrap and model install checks are more reliable, so MediaLens only treats a model as installed when the needed files are actually present.

### Added

- Added an Uninstall action for installed local AI models in the Local AI Models window.
- Added clearer per-model Description, Size, and Status presentation in the Local AI Models window.
- Added hand cursors and tighter button sizing for Local AI Models actions.

### Changed

- Changed the Local AI Models window to follow the app's light or dark theme and accent color more closely.
- Changed installed model status to use a simple checkmark label instead of a bordered badge that looked too much like a button.
- Changed AI Settings to show simpler local AI model status and hide model size there, leaving size details in the Local AI Models window.
- Changed the Python bootstrap install path to use a verified NuGet Python package for more predictable first-run model setup.
- Changed model readiness checks so a runtime alone is not enough; required model files must also be present before the model appears installed.

### Removed

- Removed technical runtime, backend, and model-location wording from the user-facing AI setup surfaces.

---

## v1.1.26

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
