# Next Session Plan

This file is the working handoff for future coding sessions.

Use these status markers:

- `[ ]` Not started
- `[~]` In progress
- `[x]` Done
- `[!]` Blocked on user decision

## Resume Goal

Continue the project improvements in a structured order without needing to rediscover context each session.

Priority themes:

1. Clarify and formalize the metadata model
2. Separate embedded metadata from AI metadata cleanly
3. Refactor large UI/business logic out of `main.py`
4. Add regression fixtures and tests
5. Improve UI consistency and performance incrementally

---

## Codex Will Do

These are implementation tasks that can be driven with minimal user input.

### Phase 1: Metadata Model

- [ ] Create a field-by-field metadata ownership map
- [ ] Inventory all metadata shown in the details panel
- [ ] Inventory all metadata persisted in `media_metadata`
- [ ] Inventory all metadata persisted in `media_ai_metadata`
- [ ] Document which fields are:
  - embedded/in-file
  - MediaLens DB-only
  - AI/inferred
  - editable
  - read-only
- [ ] Find and remove remaining places where embedded metadata is still mixed into AI summaries or AI storage paths
- [ ] Centralize file-write/embed support rules by format
- [ ] Make sure unsupported formats cannot accidentally use raster embed paths

### Phase 2: Metadata Pipeline

- [ ] Extract metadata orchestration from UI/bridge code into a dedicated service layer
- [ ] Separate stages clearly:
  - extraction
  - detection
  - parsing
  - normalization
  - persistence
  - summary generation
- [ ] Add explicit parser/version refresh behavior
- [ ] Add clearer warning handling for metadata parse failures
- [ ] Reduce noisy log output for expected unsupported cases

### Phase 3: Refactor `main.py`

- [ ] Extract metadata sidebar rendering/population into its own module
- [ ] Extract gallery sorting/filtering into its own module
- [ ] Extract preview/thumbnail/background-hint logic into its own module
- [ ] Extract duplicate/similar review logic into its own module
- [ ] Extract bridge metadata helpers into smaller bridge/service modules

### Phase 4: Tests And Fixtures

- [ ] Create a regression fixture folder for representative files
- [ ] Add parser tests for embedded metadata extraction
- [ ] Add persistence tests for metadata routing and version refresh
- [ ] Add sort/filter tests
- [ ] Add smoke checks for details-panel metadata rendering where practical

### Phase 5: UI Consistency

- [ ] Audit metadata terminology across settings, details, and actions
- [ ] Standardize labels for embedded vs AI vs DB-only metadata
- [ ] Reduce any remaining web/native duplicate behavior where practical
- [ ] Tighten the metadata panel structure for clarity

### Phase 6: Performance

- [ ] Audit repeated background work
- [ ] Add clearer invalidation rules for reprocessing
- [ ] Reduce duplicate scans/hashes/poster work
- [ ] Add lightweight instrumentation for slow operations

---

## User Decisions Needed

These are product choices where user input is needed before finalizing behavior.

### Metadata Terminology

- [ ] Decide final wording for:
  - `Embedded Metadata`
  - `AI Metadata`
  - `In File`
  - `In MediaLens DB`
  - `Inferred`
- [ ] Decide whether `Windows ctime` should be renamed in the UI
- [ ] Decide whether `Date Acquired` is the final label for metadata date

### Metadata Display Policy

- [ ] Decide which metadata sections should be visible by default for:
  - images
  - SVGs
  - animated GIFs
  - videos
- [ ] Decide how much catch-all embedded metadata should be shown inline
- [ ] Decide whether large embedded metadata should use:
  - a compact preview
  - expandable section
  - separate dialog

### Editability Rules

- [ ] Decide which fields should be editable vs read-only by media type
- [ ] Decide whether some metadata should be DB-only even when embedded versions exist
- [ ] Decide whether any SVG fields should ever be writable in-file later

### Duplicate Review Product Rules

- [ ] Decide preferred file type ranking for duplicates
- [ ] Decide how aggressive metadata merge behavior should be by default
- [ ] Decide whether duplicate review should show more technical reasoning or stay compact

### UI Product Choices

- [ ] Decide how explicit source labeling should be in the details panel
- [ ] Decide whether metadata source badges/labels should be always visible or only on hover/expand
- [ ] Decide whether advanced metadata belongs in the main sidebar or a secondary inspector

---

## Recommended Next Session Order

Start here next session:

1. [ ] Build the metadata ownership map
2. [ ] Identify every remaining embedded-vs-AI crossover
3. [ ] Present only the product decisions that block Phase 1
4. [ ] Complete the remaining metadata separation work
5. [ ] Start extracting the metadata pipeline/service layer

---

## Known Recent Decisions

- [x] Native Qt settings dialog is the preferred direction
- [x] SVG should have its own media filter and metadata mode
- [x] SVG should not keep a full AI settings section
- [x] Generic XMP/RDF catch-all metadata should live under general embedded metadata, not AI metadata
- [x] Transparent PNG thumbnails should use the same high-contrast background approach as SVG when needed
- [x] Sort by file type should exist

---

## Useful Future Checkpoints

When resuming work, first verify:

- [ ] Details panel still reads embedded metadata from general metadata storage
- [ ] AI summaries do not include generic embedded metadata noise
- [ ] SVG mode in settings only exposes the intended groups
- [ ] Sort/filter behavior still works in masonry, grid, details, duplicates, and similar views

---

## Session Notes Template

Add notes below this line in future sessions.

### Next Notes

- Last completed area:
- Current blocker:
- Next concrete implementation step:
- User decision needed:
