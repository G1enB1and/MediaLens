# MediaManagerX

**A powerful, modern media manager built for large libraries, AI workflows, and deep metadata.**

MediaManagerX helps you explore, organize, and understand your media — not just store it.  
Browse thousands of files smoothly, navigate by time, and surface hidden metadata like AI prompts, EXIF data, and embedded comments.

---

## 🔥 Why MediaManagerX?

Most media managers treat files like static objects.

MediaManagerX treats them like **living data**.

- Navigate your library by **collections, time, or folders**
- Extract and edit **deep embedded metadata** (AI prompts, EXIF, workflows)
- Handle **massive collections** without losing performance
- Stay flexible with **database + embedded metadata dual storage**

---

## 🧭 Built For

MediaManagerX is designed for people who manage **large, complex, or AI-generated media libraries**:

- 🎨 AI artists (Stable Diffusion, ComfyUI, Midjourney workflows)
- 📸 Photographers with large photo archives
- 🎬 Video editors and content creators
- 🧠 Researchers building datasets or tagging systems
- 🗂️ Power users who want control over their files

---

## ✨ Key Features

### 🕰️ Timeline-Based Browsing (NEW)

Explore your media by **when it was created, modified, aqcuired, taken, or auto**.

- Group by **day, month, or year**
- Smooth timeline scrubbing with live feedback
- Active / visible context highlighting
- Infinite scrolling for continuous browsing
- Jump through large libraries instantly

This transforms browsing from “where is it?” → **“when did I make it?”**

---

### 🧠 Advanced Metadata System

Go beyond filenames.

- Extract:
  - AI prompts & generation parameters
  - EXIF & camera data
  - Embedded comments and tags
- Edit metadata in bulk across files or folders
- Choose your workflow:
  - ⚡ Fast local database
  - 📦 Embedded metadata in files
- Persistent tagging via file hashing (even after moving/renaming files)

---

### 🖼️ High-Performance Gallery

- Smooth browsing for images, GIFs, and videos
- Multiple view modes:
  - Masonry
  - Grid (various sizes)
  - List / Details / Content views
- Infinite scroll where it matters
- Lightbox for large focused viewing

---

### 🧩 Smart Organization

- Search, filter, and sort your entire library
- Collections for flexible grouping (independent of folders)
- Drag-and-drop between folders directly in the gallery, file tree, or explorer
- Clean, responsive UI designed for real work sessions

---

### 🧰 Built for Large Libraries

- Lazy loading and optimized scanning
- Hybrid pagination + infinite scroll strategy
- Timeline-aware navigation at scale
- Designed to handle **thousands of files without breaking flow**

---

### 🎨 Clean, Stable UI

- Dark and light themes with accent color of your choice
- Responsive layout that adapts to screen size
- Optimized rendering for multiple animated gifs and videos in a collage style masonry view with no stutter, lag, or flickering.
- Carefully tuned interactions for smooth, predictable behavior

---

## 🚀 Getting Started

### Recommended (Windows)

Download the latest installer:

👉 <https://github.com/G1enB1and/MediaManagerX/releases>

- One-click setup
- All dependencies included
- Desktop shortcut created automatically

---

## Power Users (Run from Source)

```
git clone https://github.com/G1enB1and/MediaManagerX.git
cd MediaManagerX
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
python scripts\setup.py
python -m native.mediamanagerx_app.main
```

---

## 🗺️ Roadmap

MediaManagerX is evolving into a full intelligent media platform.

### 🔜 Near-Term

- Duplicate finder with smart merge logic
- Compare mode (side-by-side / overlay)
- Video preview in metadata panel
- Batch rename engine
- Improved metadata automation and syncing

---

### 🤖 AI-Powered Features

- Auto-tagging and image descriptions
- Prompt extraction and management
- Prompt library and workflow tools
- “Chat with your images” (vision + LLM integration)
- Segment Anything (SAM) integration

---

### ☁️ Ecosystem & Sync

- Google Photos / Drive import
- OneDrive / Dropbox / cloud integrations
- Cross-device sync options
- Local-first + private cloud (NAS / Docker support)

---

### 🧪 Advanced Tools

- Facial recognition and grouping
- Dataset creation tools (AI training workflows)
- Bulk metadata generation and export
- Media analysis and filtering tools

---

## 🧪 Tests / Validation

`python tests/dev_check.py`

---

## 💬 Philosophy

MediaManagerX is built around a simple idea:

> Your media is more than files — it’s context, memory, and meaning.

This app is designed to help you navigate that meaning, not just store data.

---

## 📄 License

MIT License

---

Created by Glen Bland
