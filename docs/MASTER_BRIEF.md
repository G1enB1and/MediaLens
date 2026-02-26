# MediaManager — Master Brief (Attempt #7)

## Purpose
Build a practical, AI-powered media asset manager first (organization, tagging, search, dedupe, bulk ops), with optional emotional/context features later.

## Non-negotiables
- Fast, stable viewer experience.
- Persistent metadata (tags/notes) must never be lost when folders are closed.
- Strong local-file workflow on Windows (no brittle sandbox workarounds).
- Neutral-by-default UX; emotional features are opt-in.

## Known failure patterns from prior attempts
1. Viewer performance bottlenecks (especially many GIF/video items).
2. Conflated persistence vs current workspace scope in data model.
3. Browser-sandbox friction for local filesystem access in web-first builds.
4. Rebuild fatigue due to missing written constraints and milestone gates.

## Architecture guardrails
- Keep **persistent catalog** separate from **workspace/view state** conceptually.
- File identity must not rely only on path (renames/moves happen).
- Viewer should only render/play what is in/near viewport.
- Design APIs and modules so MediaManager can integrate into PersonaSphere later.

## MVP (Phase 1)
1. Stable viewer (grid + lightbox) with smooth scrolling and reliable previews.
2. Folder ingest + thumbnail cache.
3. Persistent tags/notes attached to stable media IDs.
4. Search/filter over filename + tags + basic metadata.
5. Bulk tag operations.

## Out of scope for initial stabilization
- Advanced emotional mapping.
- Full semantic RAG integration.
- Complex inpainting/edit pipelines.

## Milestone gate to avoid another reset
Before adding major features, require:
- Viewer performance acceptable on real library sample.
- No tag-loss regression across open/close/reopen cycles.
- Basic search + bulk tagging confirmed stable.

## Immediate next step
Create `MediaManager/DECISIONS.md` with locked tech choices for attempt #7 (frontend/runtime, backend/service boundary, storage model, and preview strategy).