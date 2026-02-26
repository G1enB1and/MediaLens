# MediaManagerX

A powerful, local-first media asset manager designed for privacy, speed, and premium aesthetics.

## 🚀 Getting Started

### Recommended (Windows)

The easiest way to get started is to download the latest **MediaManagerX_Setup.exe** from the [Releases](https://github.com/G1enB1and/MediaManagerX/releases) page. This will handle all dependencies and create a desktop shortcut for you.

### Power Users (Run from Source)

If you prefer to run from source or contribute to development:

1. **Clone the Repo**

   ```bash
   git clone https://github.com/G1enB1and/MediaManagerX.git
   cd MediaManagerX
   ```

2. **Setup Environment**

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -U pip
   python -m pip install -e .
   python scripts\setup.py
   ```

3. **Launch**

   ```powershell
   python -m native.mediamanagerx_app.main
   ```

---

## ✨ Current Features

MediaManagerX is currently a fully functional media browser and metadata editor in its Phase 1 "Foundation" stage.

- **Immersive Viewing**: Browse Images, GIFs, and Videos in a high-performance gallery. Includes a smooth Lightbox mode for focused viewing.
- **Smart Organization**: Search, sort, and filter your entire library with ease.
- **Advanced Metadata Management**:
  - **Dual Logic**: Manage metadata in a local high-speed database or embed it directly into the files.
  - **Bulk Editing**: Multi-select files or folders to edit tags and notes in bulk.
  - **Custom Views**: Toggle and sort exactly which metadata fields you want to see.
- **Premium Aesthetics**:
  - Beautiful Light and Dark modes.
  - Dynamic Accent Color tinting.
  - Optional **Glassmorphism** effects for a modern, premium feel.
- **Privacy & Persistence**:
  - **Hidden Assets**: Quickly hide sensitive files and folders from the UI.
  - **File Hashing**: Metadata and tags stay persistent even if you rename or move files across your disk, thanks to unique file fingerprinting.

---

## 🗺️ Roadmap (Coming Soon)

We are rapidly expanding MediaManagerX with advanced AI and utility features:

- **Library Utilities**: Duplicate file finder and automated library cleanup.
- **Advanced Recognition**: Integrated Facial Recognition and person grouping.
- **AI Automation**:
  - Auto-tagging and AI-generated image descriptions.
  - AI Image editing and generation directly via chat.
- **Intelligent Interaction**: "Chat with your images" using advanced models (SAM 2, Nanobanana) for segmenting, box labeling, and deep visual understanding.

---

## 🧪 Tests / Validation

Run the test suite to ensure everything is working correctly:

```bash
python tests/dev_check.py
```

---

## License

MIT License

Created by Glen Bland.
