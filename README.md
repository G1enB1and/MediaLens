# MediaLens

![MediaLens Logo](docs/Screenshots/MediaLens-Logo-1024.png)

**MediaLens helps you clean up duplicate and similar images with confidence, then becomes the fastest way to explore, understand, and organize your entire media library.**

If you’ve ever:

- Didn’t know which version to keep
- Ended up with multiple slightly different edits
- Struggled to find anything later

MediaLens is built for that entire experience, not just detection, but decision and long-term organization.

---

## Why MediaLens?

Most tools show duplicates.

**MediaLens shows what actually changed and helps you decide.**

- See differences like resolution, edits, format, text, and more
- Get clear “best version” recommendations based on your rules
- Review safely before anything is removed

No guesswork. No blind deletes.

---

## What it becomes after cleanup

Once your library is clean, MediaLens becomes your daily workspace:

- Fast search, filtering, and tagging
- Collections beyond folders
- Bulk editing across hundreds of files
- Timeline browsing by when things happened
- Deep metadata + AI understanding

---

## Built For

- AI image/video creators
- Photographers with large archives
- Video editors and content creators
- Dataset builders and researchers
- Anyone with messy, duplicate-heavy libraries

---

## Key Features

### Intelligent Duplicate & Similarity Cleanup

MediaLens doesn’t just detect duplicates, it understands variations.

#### Detect

- Exact duplicates (content hash)
- Visually similar images (perceptual hashing)
- Edited, resized, compressed variants
- Crops, grayscale, watermark/text changes

#### Understand

Each group is labeled with meaningful differences:

- Resolution, size, format
- Cropped vs full
- Text detected
- Metadata richness
- Folder priority

### Decide

- ★ Best overall recommendation
- Configurable rules for what “best” means
- Auto-resolve entire libraries safely
- Metadata merge before deletion

Always transparent. Always reversible.

![Similar Groups](docs/Screenshots/Screenshot-Similar-Groups-Puppy.png)

---

### Image Comparison

Evaluate two images without leaving your workflow.

- Side-by-side with reveal slider
- Synchronized zoom and pan
- “Best in comparison” suggestions
- Integrated keep/delete actions

Compare → decide → clean up.

![Comparison](docs/Screenshots/Screenshot-Comparison-Zoom.png)

---

### Bulk Editing Workspace

Tags, descriptions, and OCR, all in one place.

#### Tags

- Bulk edit across hundreds of files
- Common vs uncommon tag detection
- Tag lists with one-click apply

![Bulk Tag Editor](docs/Screenshots/Screenshot-Bulk-Tag-Editor.png)

#### Descriptions

- Edit or generate captions in bulk
- AI-assisted descriptions (local models)

![Bulk Description Editor](docs/Screenshots/Screenshot-Bulk-Description-Editor.png)

#### Text OCR (Fast + AI)

- Extract text from images and video previews
- Choose:
  - Fast OCR (quick)
  - AI OCR (higher accuracy)
- Mark files as “No Text”
- Save and edit results directly

![Bulk OCR Editor](docs/Screenshots/Screenshot-Bulk-OCR-Editor.png)

---

#### OCR Review

- Large preview with zoom + pan
- Compare Fast OCR vs AI OCR vs your edits
- Confirm best result per file
- Navigate quickly across files

![OCR Review](docs/Screenshots/Screenshot-OCR-Review-Zoom.png)

---

### Built-in AI (Local & Private)

MediaLens includes optional **local AI models** to help organize your media without sending your files to the cloud.

- Generate tags automatically
- Generate descriptions
- High-accuracy OCR
- Works with AI-generated images

#### Designed for control

- Models install on demand
- Run locally (GPU or CPU)
- Never overwrite your data without permission

![AI Descriptions Settings](docs/Screenshots/Screenshot-Settings-AI-Descriptions.png)

---

### Advanced Search

Find exactly what you're looking for without memorizing syntax.

- Visual query builder
- Combine tags, metadata, text, dates
- Save searches
- Sync between UI and raw search

![Guided Search](docs/Screenshots/Screenshot-Guided-Search-File-Date-Panda.png)

---

### Metadata System

Go beyond filenames.

- Extract:
  - AI prompts & workflows
  - EXIF / camera data
  - Embedded metadata
- Edit metadata in bulk
- Persistent tagging via file hashing
- Works even if files move or rename

![AI Detection](docs/Screenshots/Screenshot-AI-Detection-Google.png)

![AI Metadata](docs/Screenshots/Screenshot-Settings-Metadata-AI.png)

---

### Timeline Browsing

Explore your media by **when**, not just where.

- Group by day, month, year
- Smooth timeline scrubbing
- Jump instantly across large libraries

![Timeline](docs/Screenshots/Screenshot-Timeline-Grid.png)

---

### Automated Scanning

Keep your library up to date automatically.

- Scheduled scans (hourly, daily, weekly, or monthly)
- Folder-based monitoring
- Background processing
- Resume interrupted scans

![Scanners](docs/Screenshots/Screenshot-Settings-Scanners-Expanded.png)

---

### Backup & Restore

Your library is safe and portable.

- Export full library backups
- Restore fully or partially
- Merge or replace:
  - Metadata
  - Thumbnails
  - AI models
  - App data

Includes automatic safety backups before restore.

![Backup & Restore](docs/Screenshots/Screenshot-Export-Library-Backup.png)

---

### High-Performance Gallery

- Smooth browsing of images, GIFs, and videos
- Masonry, grid, and list views
- Infinite scroll where it matters
- Lightbox with zoom + pan

Built for thousands of files without slowing down.

---

### Smart Organization

- Collections independent of folders
- Drag-and-drop between folders
- Flexible filtering and sorting
- Clean, responsive UI

---

### Action History

Review and recover previous actions with persistent undo and redo history.

- Undo or redo deletes, moves, copies, renames, folder creation, metadata edits, rotations, and hidden-status changes
- Supports both bulk actions and single-file edits
- Clearly shows what can still be undone or redone
- Explains when recovery is no longer possible
- Works with MediaLens Retention and the Windows Recycle Bin

![Action History](docs/Screenshots/Screenshot-Action-History.png)

---

## Getting Started

### Windows Installer

Download the latest release:

[https://github.com/G1enB1and/MediaLens/releases](https://github.com/G1enB1and/MediaLens/releases)

- One-click install
- All dependencies included
- Ready to go

---

## Run from Source

git clone [https://github.com/G1enB1and/MediaLens.git](https://github.com/G1enB1and/MediaLens.git)  
cd MediaLens

python -m venv .venv  
..venv\Scripts\Activate.ps1

python -m pip install -U pip  
python -m pip install -e .

python scripts\setup.py  
python run.py

---

## Roadmap

MediaLens is evolving into a full intelligent media platform.

### Near-Term

- Batch rename engine
- Rating system
- Expanded filters (photo vs illustration, etc.)

### AI

- Prompt library tools
- “Chat with your images”
- Advanced similarity validation

### Ecosystem

- Cloud integrations (Drive, OneDrive, etc.)
- Cross-device sync
- Local-first sync options

### Advanced Tools

- Facial recognition
- Dataset creation workflows
- Bulk metadata generation

---

## License

MIT License

---

Created by Glen Bland
