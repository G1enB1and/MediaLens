# MediaManager — Locked Decisions (Attempt #7)

## Architecture Direction (Locked)
Use a **hybrid app**:
- **Native shell:** Python + PySide6 (Windows desktop app)
- **Gallery renderer:** Embedded web view (HTML/CSS/JS) for high-performance media rendering

Rationale: PySide6 handles local desktop integration well, but web rendering is better for smooth masonry layout + simultaneous animated playback.

---

## Gallery Requirements (Locked)
The gallery must:
1. Use a **masonry/Pinterest-style** layout (not uniform grid)
2. Be **responsive** to window size
3. Support **simultaneous playback** of multiple animated GIFs/videos with minimal lag
4. Use **lazy loading**
5. **Precache near-viewport** media for smooth scrolling
6. Use **pagination** (~100 items per page)
7. GIF behavior:
   - autoplay + loop
8. Video behavior:
   - `< 1 minute`: autoplay + loop
   - `>= 1 minute`: do not autoplay, show first frame + controls
9. Clicking any image/video opens **shadowbox-style overlay** with larger view

---

## Implementation Constraints
- Keep local Windows-native workflow (no cloud dependency required for core usage)
- Prioritize memory-safe rendering and smooth scrolling over feature breadth
- Preserve future integration path into PersonaSphere via API/module boundary

---

## Embedded Web Strategy (Locked)
- Use **PySide6 QWebEngineView** as the embedded web renderer for Phase 1.

Rationale: first-party Qt integration, predictable desktop behavior on Windows, and clean path to iterate viewer performance before considering alternative wrappers.

## Next Build Target
Phase 1 implementation should focus on this gallery experience first, before advanced tagging/AI features.