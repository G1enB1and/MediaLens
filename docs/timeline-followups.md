# Timeline Follow-Ups

Potential future improvements for the gallery timeline if loading-time jitter still needs refinement:

- Preserve the active timeline rail during incremental infinite-scroll appends instead of rebuilding the rail on each appended batch.
- Add a stronger layout-settling mode so timeline target refresh waits for short scroll idle windows before reconnecting to live section offsets.
- Reserve more stable early card heights where possible so grouped section offsets move less while images are still loading.
- Consider direction-aware smoothing thresholds that adapt to loading churn intensity instead of using a fixed correction threshold.
- If needed, add a lightweight debug overlay or logging mode for timeline target maps and active snap targets to diagnose early-load scroll drift.
