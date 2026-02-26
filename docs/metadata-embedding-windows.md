# Windows Metadata Embedding Notes (PNG/JPG)

Last validated: 2026-02-26

## Purpose

This document records the current metadata behavior and constraints so future edits do not re-break PNG embedding/import.

## UI/Data Contracts (Do Not Blur These)

- `Save Changes to Database` = UI DB fields -> database only
- `Import Metadata` = file -> Embedded UI fields only (must not read DB)
- `Embed Data in File` = Embedded UI fields -> file only (must not read DB)

### Database fields (editable, persisted in SQLite)

- `Tags` (DB tags)
- `Description`
- `Notes`
- `AI Prompt`
- `AI Negative Prompt`
- `AI Parameters`

### File-embedded fields (editable for file writing)

- `Embedded Tags`
- `Embedded Comments`
- `Embedded Tool Metadata` (display/import only; not the main DB fields)

## Why PNG Is Different (Windows)

`JPG` metadata is generally visible in Windows Explorer when written to EXIF (`XPComment`, `XPKeywords`, etc.).

`PNG` is inconsistent:

- Writing only PNG `tEXt` chunks (`Comment`, `Keywords`) was readable by Pillow, but not by Windows Explorer on this machine.
- Writing only EXIF `XP*` tags inside PNG also did not show in Windows Explorer on this machine.
- Writing PNG XMP (`XML:com.adobe.xmp`) with `dc:subject` *does* show tags in Windows Explorer (`System.Keywords`) on this machine.

## Current PNG Embed Strategy (Required)

When embedding PNG metadata, write **all** of the following:

- PNG text chunks (`tEXt`) for compatibility with tools:
  - `Comment`, `Comments`, `Description`, `Subject`, `Title`
  - `Keywords`, `Tags`
- PNG XMP (`XML:com.adobe.xmp`) for Windows Explorer compatibility:
  - `dc:subject` (tags)
  - `dc:description` (comment)
  - `dc:title` (comment duplicate/fallback)
  - `exif:UserComment` (comment fallback)
- PNG EXIF fallback (`XPComment`, `XPKeywords`, etc.) for tool compatibility

Do not remove the XMP write path from `native/mediamanagerx_app/main.py` (`_save_to_exif_cmd`) unless you re-test Windows PNG behavior.

## Current Import Strategy (Required)

`Import Metadata` must read from the file only and replace Embedded UI fields.

For Windows-visible PNG data, the import harvester must check:

1. PNG text chunk keys (`Comment`, `Comments`, `Description`, `Keywords`, `Tags`)
2. PNG XMP (`xmp` / `XML:com.adobe.xmp`) fields:
   - `dc:subject` -> Embedded Tags
   - `exif:UserComment` / `dc:description` / `dc:title` -> Embedded Comments (first match wins)
3. EXIF fallback (`XPComment`, `XPKeywords`, `ImageDescription`, `UserComment`)

## Important Observed Limitation (Windows PNG Comments)

On this Windows machine (tested via `Shell.Application` property API), PNG comment text written in XMP may appear as `System.Title` rather than `System.Comment`.

What was empirically confirmed:

- PNG tags from XMP `dc:subject` were visible in `System.Keywords`
- PNG comment text was not visible in `System.Comment` with the tested PNG write methods
- The same comment text appeared in `System.Title` when written to XMP `dc:description` / `dc:title`

This means Windows PNG "comment" display can vary by handler/version and is less reliable than JPG.

## Code Paths To Preserve

- `native/mediamanagerx_app/main.py:_save_to_exif_cmd`
- `native/mediamanagerx_app/main.py:_harvest_windows_visible_metadata`
- `native/mediamanagerx_app/main.py:_import_exif_to_db`
- `native/mediamanagerx_app/main.py:_show_metadata_for_path`

## Regression Checklist (PNG)

After changing metadata code:

1. Test a fresh `.png` and a fresh `.jpg`
2. In app, set `Embedded Tags` / `Embedded Comments`, click `Embed Data in File`
3. In Windows Explorer Properties -> Details:
   - Verify JPG tags/comments
   - Verify PNG tags at minimum
   - Check PNG `Title` as well if "Comments" appears blank
4. Back in app, click `Import Metadata`
5. Confirm only Embedded fields change (DB fields should not be overwritten)

