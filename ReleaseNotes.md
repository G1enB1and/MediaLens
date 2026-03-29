## MediaLens v1.1.4

### ✨ Summary

This was a stabilization-focused release that improved video previews and file deletion safety.

After significant rework, video playback is now more stable, and file deletion has been redesigned to be safer, more predictable, and user-controlled.

This update also introduces pinned folders and several UI refinements that improve clarity and consistency.

---

### 🔥 Highlights

- **Video Preview System Rebuilt**  
  The entire preview-above-details video pipeline was reworked to eliminate crashes and inconsistent behavior.  
  Metadata, static previews, in-place playback, and lightbox playback are now all functioning reliably again.

- **Safer Delete Workflow (Finally Feels Right)**  
  - `Del` → Sends files to Recycle Bin (default)  
  - `Shift+Delete` → Permanent delete with confirmation  
  - New setting allows full control over delete behavior  

  This resolves prior instability and makes deletion predictable and safe.

- **Pinned Folders Sidebar**  
  Quickly access important locations:
  - Right-click to pin/unpin folders  
  - Drag & drop support  
  - Clean integration with existing file tree  

---

### 🎨 UX & Visual Refinements

- **File Tree Improvements**
  - Selected folders now use bold accent text (no more muddy tinting)
  - Icons remain clean and readable
  - Chevrons only appear when folders actually have children

- **Adaptive Accent Contrast**
  Accent colors now dynamically adjust for readability in low-contrast situations

- **Updated Header Branding**
  Refreshed logo for improved visual consistency

---

📄 Full Changelog:
https://github.com/G1enB1and/MediaLens/blob/dev/native/mediamanagerx_app/CHANGELOG.md
