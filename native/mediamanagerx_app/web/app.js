
// Globals for state
let gSearchQuery = '';
let gPage = 0;
const PAGE_SIZE = 100;
let gTotal = 0;
let gMedia = []; // Current page items
let gSelectedFolders = [];
let gActiveCollection = null;
let gBridge = null;
let gPosterRequested = new Set();
let gPosterObserver = null;
let gSort = 'name_asc';
let gFilter = 'all';
let gCurrentTargetFolderName = '';
let gExternalEditors = {};
let gCurrentDragCount = 0;
let gPlayingInplaceCard = null;
let gActiveMetadataMode = 'image';
let gUpdateToastTimer = null;
let gScanManuallyHidden = false;
let gGalleryViewMode = 'masonry';
let gGroupBy = 'none';
let gGroupDateGranularity = 'day';
let gCollapsedGroupKeys = new Set();
let gTimelineScrubActive = false;
let gTimelineScrubPointerId = null;
const TIMELINE_INSET_PX = 20;
const TIMELINE_THUMB_SIZE_PX = 14;
const TIMELINE_TOP_YEAR_TOP_PX = 20;
const TIMELINE_TOP_MONTH_TOP_PX = 35;
const TIMELINE_THUMB_OFFSET_PX = 8;

const GALLERY_VIEW_MODES = new Set(['masonry', 'grid_small', 'grid_medium', 'grid_large', 'grid_xlarge', 'list', 'content', 'details']);
const DETAILS_COLUMN_CONFIG = [
  { key: 'thumb', label: '', min: 72, width: 72, resizable: false },
  { key: 'name', label: 'File Name', min: 25, width: 260, resizable: true },
  { key: 'folder', label: 'Folder', min: 25, width: 280, resizable: true },
  { key: 'type', label: 'Type', min: 25, width: 120, resizable: true },
  { key: 'modified', label: 'Date modified', min: 25, width: 170, resizable: true },
  { key: 'size', label: 'Size', min: 25, width: 110, resizable: true },
];
let gDetailsColumnWidths = Object.fromEntries(DETAILS_COLUMN_CONFIG.map(col => [col.key, col.width]));

const METADATA_SETTINGS_CONFIG = {
  image: {
    groups: {
      general: {
        label: 'General',
        fields: [
          ['res', 'Resolution', true], ['size', 'File Size', true],
          ['exifdatetaken', 'EXIF Date Taken', false], ['metadatadate', 'Metadata Date', false],
          ['filecreateddate', 'File Created Date', false], ['filemodifieddate', 'File Modified Date', false],
          ['description', 'Description', true],
          ['tags', 'Tags', true], ['notes', 'Notes', true], ['embeddedtags', 'Embedded Tags', true],
          ['embeddedcomments', 'Embedded Comments', true],
        ],
      },
      camera: {
        label: 'Camera',
        fields: [
          ['camera', 'Camera Model', false], ['location', 'Location (GPS)', false], ['iso', 'ISO Speed', false],
          ['shutter', 'Shutter Speed', false], ['aperture', 'Aperture', false], ['software', 'Software / Editor', false],
          ['lens', 'Lens Info', false], ['dpi', 'DPI', false],
        ],
      },
      ai: {
        label: 'AI',
        fields: [
          ['aistatus', 'AI Detection', true], ['aisource', 'AI Tool / Source', true], ['aifamilies', 'AI Metadata Families', true],
          ['aidetectionreasons', 'AI Detection Reasons', false], ['ailoras', 'AI LoRAs', true], ['aimodel', 'AI Model', true],
          ['aicheckpoint', 'AI Checkpoint', false], ['aisampler', 'AI Sampler', true], ['aischeduler', 'AI Scheduler', true],
          ['aicfg', 'AI CFG', true], ['aisteps', 'AI Steps', true], ['aiseed', 'AI Seed', true],
          ['aiupscaler', 'AI Upscaler', false], ['aidenoise', 'AI Denoise', false], ['aiprompt', 'AI Prompt', true],
          ['ainegprompt', 'AI Negative Prompt', true], ['aiparams', 'AI Parameters', true], ['aiworkflows', 'AI Workflows', false],
          ['aiprovenance', 'AI Provenance', false], ['aicharcards', 'AI Character Cards', false], ['airawpaths', 'AI Metadata Paths', false],
        ],
      },
    },
    groupOrder: ['general', 'camera', 'ai'],
  },
  video: {
    groups: {
      general: {
        label: 'General',
        fields: [
          ['res', 'Resolution', true], ['size', 'File Size', true],
          ['exifdatetaken', 'EXIF Date Taken', false], ['metadatadate', 'Metadata Date', false],
          ['filecreateddate', 'File Created Date', false], ['filemodifieddate', 'File Modified Date', false],
          ['duration', 'Duration', true], ['fps', 'Frames Per Second', true],
          ['codec', 'Codec', true], ['audio', 'Audio', true], ['description', 'Description', true], ['tags', 'Tags', true], ['notes', 'Notes', true],
        ],
      },
      ai: {
        label: 'AI',
        fields: [
          ['aistatus', 'AI Detection', true], ['aisource', 'AI Tool / Source', true], ['aifamilies', 'AI Metadata Families', true],
          ['aimodel', 'AI Model', true], ['aicheckpoint', 'AI Checkpoint', false], ['aisampler', 'AI Sampler', true],
          ['aischeduler', 'AI Scheduler', true], ['aicfg', 'AI CFG', true], ['aisteps', 'AI Steps', true], ['aiseed', 'AI Seed', true],
          ['aiprompt', 'AI Prompt', true], ['ainegprompt', 'AI Negative Prompt', true], ['aiparams', 'AI Parameters', true],
          ['aiworkflows', 'AI Workflows', false], ['aiprovenance', 'AI Provenance', false], ['airawpaths', 'AI Metadata Paths', false],
        ],
      },
    },
    groupOrder: ['general', 'ai'],
  },
  gif: {
    groups: {
      general: {
        label: 'General',
        fields: [
          ['res', 'Resolution', true], ['size', 'File Size', true],
          ['exifdatetaken', 'EXIF Date Taken', false], ['metadatadate', 'Metadata Date', false],
          ['filecreateddate', 'File Created Date', false], ['filemodifieddate', 'File Modified Date', false],
          ['duration', 'Duration', true], ['fps', 'Frames Per Second', true],
          ['description', 'Description', true], ['tags', 'Tags', true], ['notes', 'Notes', true], ['embeddedtags', 'Embedded Tags', true],
          ['embeddedcomments', 'Embedded Comments', true],
        ],
      },
      ai: {
        label: 'AI',
        fields: [
          ['aistatus', 'AI Detection', true], ['aisource', 'AI Tool / Source', true], ['aifamilies', 'AI Metadata Families', true],
          ['aidetectionreasons', 'AI Detection Reasons', false], ['ailoras', 'AI LoRAs', true], ['aimodel', 'AI Model', true],
          ['aicheckpoint', 'AI Checkpoint', false], ['aisampler', 'AI Sampler', true], ['aischeduler', 'AI Scheduler', true],
          ['aicfg', 'AI CFG', true], ['aisteps', 'AI Steps', true], ['aiseed', 'AI Seed', true], ['aiupscaler', 'AI Upscaler', false],
          ['aidenoise', 'AI Denoise', false], ['aiprompt', 'AI Prompt', true], ['ainegprompt', 'AI Negative Prompt', true],
          ['aiparams', 'AI Parameters', true], ['aiworkflows', 'AI Workflows', false], ['aiprovenance', 'AI Provenance', false],
          ['aicharcards', 'AI Character Cards', false], ['airawpaths', 'AI Metadata Paths', false],
        ],
      },
    },
    groupOrder: ['general', 'ai'],
  },
};

// Loading progress tracking
let gTotalOnPage = 0;
let gLoadedOnPage = 0;
let gLoadingDismissed = false;

function setStatus(text) {
  const el = document.getElementById('status');
  if (el) el.textContent = text;
}

function setSelectedFolder(paths, activeCollection = null) {
  const el = document.getElementById('selectedFolder');
  if (!el) return;
  if (activeCollection && activeCollection.name) {
    el.textContent = activeCollection.name;
    return;
  }
  if (!paths || paths.length === 0) {
    el.textContent = '(none)';
    return;
  }
  if (paths.length === 1) {
    el.textContent = paths[0].split(/[/\\]/).pop();
  } else {
    el.textContent = `${paths.length} folders selected`;
  }
}

// Background queue for items not yet in the viewport
let gBackgroundQueue = [];
let gBackgroundIdleId = null;

function flushBackgroundQueue() {
  gBackgroundIdleId = null;
  if (gBackgroundQueue.length === 0) return;

  // Process in idle time: drain up to 5 items per idle slot
  const deadline = performance.now() + 8; // 8ms budget per batch
  while (gBackgroundQueue.length > 0 && performance.now() < deadline) {
    const item = gBackgroundQueue.shift();
    if (item.type === 'image') {
      loadImage(item.el, item.imgSrc);
    } else if (item.type === 'video') {
      loadVideoPoster(item.el, item.path);
      if (gBridge && gBridge.preload_video) {
        gBridge.preload_video(item.path, item.width || 0, item.height || 0);
      }
    }
  }

  // Schedule next batch if any remain
  if (gBackgroundQueue.length > 0) {
    scheduleBackgroundDrain();
  }
}

function scheduleBackgroundDrain() {
  if (gBackgroundIdleId) return;
  if (typeof requestIdleCallback !== 'undefined') {
    gBackgroundIdleId = requestIdleCallback(flushBackgroundQueue, { timeout: 500 });
  } else {
    gBackgroundIdleId = setTimeout(flushBackgroundQueue, 16);
  }
}

function loadImage(el, imgSrc) {
  if (gPosterRequested.has(el)) return;
  gPosterRequested.add(el);
  el.onload = () => {
    gLoadedOnPage++;
    el.style.opacity = '1';
    const card = el.closest('.card');
    if (card) { card.classList.remove('loading'); card.classList.add('ready'); }
  };
  el.onerror = () => {
    gLoadedOnPage++;
    el.style.opacity = '1';
    const card = el.closest('.card');
    if (card) { card.classList.remove('loading'); card.classList.add('ready'); }
  };
  el.style.opacity = '0';
  el.src = imgSrc;
}

function loadVideoPoster(el, path) {
  if (gPosterRequested.has(el)) return;
  gPosterRequested.add(el);
  // Hide immediately so the card's shimmer shows through until the poster arrives
  el.style.opacity = '0';
  if (gBridge && gBridge.get_video_poster) {
    gBridge.get_video_poster(path, function (posterUrl) {
      const card = el.closest('.card');
      if (posterUrl) {
        // Preload via tempImg so the browser caches it — then show instantly
        const tempImg = new Image();
        tempImg.onload = () => {
          el.src = posterUrl;
          gLoadedOnPage++;
          // Push opacity change one frame out so the CSS transition fires
          requestAnimationFrame(() => { el.style.opacity = '1'; });
          if (card) { card.classList.remove('loading'); card.classList.add('ready'); }
        };
        tempImg.onerror = () => {
          el.removeAttribute('src');
          gLoadedOnPage++;
          requestAnimationFrame(() => { el.style.opacity = '1'; });
          if (card) { card.classList.remove('loading'); card.classList.add('ready'); }
        };
        tempImg.src = posterUrl;
      } else {
        el.removeAttribute('src');
        gLoadedOnPage++;
        requestAnimationFrame(() => { el.style.opacity = '1'; });
        if (card) { card.classList.remove('loading'); card.classList.add('ready'); }
      }
    });
  }
}

function ensureMediaObserver() {
  if (gPosterObserver) return;
  gPosterObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const el = entry.target;
        if (gPosterRequested.has(el)) continue;

        const imgSrc = el.getAttribute('data-src');
        const path = el.getAttribute('data-video-path');

        gTotalOnPage++;
        gPosterObserver.unobserve(el);

        // Load immediately — no delay for items entering the viewport
        if (imgSrc) {
          loadImage(el, imgSrc);
        } else if (path) {
          loadVideoPoster(el, path);
          if (gBridge && gBridge.preload_video) {
            // Find the original item to get width/height
            const item = gMedia.find(m => m.path === path);
            if (item) {
              gBridge.preload_video(path, item.width || 0, item.height || 0);
            }
          }
        }
      }
    },
    {
      root: document.querySelector('main'),
      rootMargin: `0px 0px ${Math.round(window.innerHeight)}px 0px`,
      threshold: 0,
    }
  );
}

function resetMediaState() {
  gPosterRequested.clear();
  if (gPosterObserver) {
    gPosterObserver.disconnect();
    gPosterObserver = null;
  }
}

let gLoadingShownAt = 0;
const MIN_LOADING_MS = 1000;

let gLoadingHideTimer = null;

function setGlobalLoading(on, text = 'Loading…', pct = null) {
  const gl = document.getElementById('globalLoading');
  const t = document.getElementById('loadingText');
  const b = document.getElementById('loadingBar');
  if (!gl || !t || !b) return;

  if (on) {
    if (gLoadingHideTimer) {
      clearTimeout(gLoadingHideTimer);
      gLoadingHideTimer = null;
    }

    if (gl.hidden) {
      gLoadingShownAt = Date.now();
    }
    gl.hidden = false;
    t.textContent = text;

    if (pct != null) {
      const clamped = Math.max(0, Math.min(100, pct));
      b.style.width = `${clamped}%`;
    }
    return;
  }

  gLoadingDismissed = true;
  const elapsed = Date.now() - (gLoadingShownAt || Date.now());
  const wait = Math.max(0, MIN_LOADING_MS - elapsed);

  if (gLoadingHideTimer) clearTimeout(gLoadingHideTimer);
  gLoadingHideTimer = window.setTimeout(() => {
    gl.hidden = true;
    gLoadingHideTimer = null;
  }, wait);
}


// Enable clicking to hide the loading overlay if it gets stuck
document.addEventListener('DOMContentLoaded', () => {
  const gl = document.getElementById('globalLoading');
  if (gl) {
    gl.style.cursor = 'pointer';
    gl.onclick = () => {
      gLoadingDismissed = true;
      gl.hidden = true;
    };
  }
});

function wireScanIndicator() {
  const el = document.getElementById('scanIndicator');
  const file = document.getElementById('scanFile');
  const bar = document.getElementById('scanBar');
  if (!el || !file || !bar) return;

  el.onclick = () => {
    gScanManuallyHidden = true;
    el.hidden = true;
  };

  if (gBridge.scanProgress) {
    gBridge.scanProgress.connect((fileName, percent) => {
      if (gScanManuallyHidden) return;
      el.hidden = false;
      file.textContent = fileName;
      bar.style.width = `${percent}%`;
    });
  }

  if (gBridge.scanStarted) {
    gBridge.scanStarted.connect(() => {
      gScanManuallyHidden = false;
      el.hidden = false;
      bar.style.width = '0%';
      file.textContent = 'Initializing...';
    });
  }

  if (gBridge.scanFinished) {
    gBridge.scanFinished.connect(() => {
      // Keep it visible for a second then hide
      file.textContent = 'Finished';
      bar.style.width = '100%';
      setTimeout(() => {
        el.hidden = true;
      }, 2000);
    });
  }
}

let gCtxItem = null;
let gCtxIndex = -1;
let gCtxFromLightbox = false;

function hideCtx() {
  const ctx = document.getElementById('ctx');
  if (ctx) ctx.hidden = true;
  gCtxItem = null;
  gCtxIndex = -1;
  gCtxFromLightbox = false;
}
window.hideCtx = hideCtx;

// The locked card retains its selection border even when clicking elsewhere (e.g. metadata panel).
let gLockedCard = null;
let gSelectedPaths = new Set();
let gLastSelectionIdx = -1;
let gIsCtxMenuClick = false; // Guard for context menu clicks

function deselectAll() {
  if (gIsCtxMenuClick) {
    gIsCtxMenuClick = false;
    return;
  }
  document.querySelectorAll('.card.selected').forEach(c => c.classList.remove('selected'));
  gSelectedPaths.clear();
  gLockedCard = null;
  gLastSelectionIdx = -1;

  if (gPlayingInplaceCard) {
    gPlayingInplaceCard.classList.remove('playing-inplace', 'playing-inprogress', 'playing-confirmed');
    gPlayingInplaceCard.removeAttribute('data-paused');
    gPlayingInplaceCard = null;
    if (gBridge && gBridge.close_native_video) {
      gBridge.close_native_video(() => { });
    }
  }
}
window.deselectAll = deselectAll;

function selectAll() {
  gSelectedPaths.clear();
  document.querySelectorAll('.card').forEach(c => {
    c.classList.add('selected');
    const path = c.getAttribute('data-path');
    if (path) gSelectedPaths.add(path);
  });
  gIsCtxMenuClick = true; // Prevents the follow-up document click from deselecting
  syncMetadataToBridge();
}
window.selectAll = selectAll;

function triggerRename() {
  let path = null;
  if (gCtxItem && gCtxItem.path) {
    path = gCtxItem.path;
  } else if (gSelectedPaths.size > 0) {
    path = Array.from(gSelectedPaths)[0];
  }

  if (path && gBridge && gBridge.rename_path_async) {
    const curName = path.split(/[/\\]/).pop();
    const next = prompt('Rename to:', curName);
    if (next && next !== curName) {
      if (typeof closeLightbox === 'function') closeLightbox();
      setGlobalLoading(true, 'Renaming…', 25);
      gBridge.rename_path_async(path, next, () => { });
    }
  }
}
window.triggerRename = triggerRename;

function syncMetadataToBridge() {
  if (gBridge && gBridge.show_metadata) {
    const paths = Array.from(gSelectedPaths);
    gBridge.show_metadata(paths);
  }
}

function getItemName(item) {
  if (!item || !item.path) return '';
  const parts = item.path.split(/[/\\]/);
  return parts[parts.length - 1] || item.path;
}

function getItemFolder(item) {
  if (!item || !item.path) return '';
  const parts = item.path.split(/[/\\]/);
  parts.pop();
  return parts.join('\\');
}

function getItemFolderDisplay(item) {
  const folder = getItemFolder(item);
  if (!folder) return '';
  const parts = folder.split(/[/\\]/).filter(Boolean);
  const tail = parts.length > 0 ? parts[parts.length - 1] : folder;
  return `.../${tail}`;
}

function formatFileSize(bytes) {
  const value = Number(bytes || 0);
  if (!Number.isFinite(value) || value <= 0) return '';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = value;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  const digits = size >= 10 || unitIndex === 0 ? 0 : 1;
  return `${size.toFixed(digits)} ${units[unitIndex]}`;
}

function formatModifiedTime(value) {
  const ts = Number(value || 0);
  if (!Number.isFinite(ts) || ts <= 0) return '';
  const millis = ts > 1e12 ? Math.floor(ts / 1000000) : ts;
  try {
    return new Date(millis).toLocaleString();
  } catch (_) {
    return '';
  }
}

function getItemIndex(item, fallbackIdx = 0) {
  const candidate = Number(item && item.__galleryIndex);
  return Number.isInteger(candidate) && candidate >= 0 ? candidate : fallbackIdx;
}

function getGalleryContainerClasses(mode) {
  const nextMode = GALLERY_VIEW_MODES.has(mode) ? mode : 'masonry';
  if (nextMode === 'masonry') {
    return ['masonry'];
  }
  if (nextMode.startsWith('grid_')) {
    return ['gallery-grid', `view-${nextMode.replace('_', '-')}`];
  }
  if (nextMode === 'details') {
    return ['gallery-details'];
  }
  if (nextMode === 'content') {
    return ['gallery-content'];
  }
  return ['gallery-list'];
}

function applyGalleryClasses(el, mode) {
  if (!el) return;
  el.className = 'gallery';
  getGalleryContainerClasses(mode).forEach(cls => el.classList.add(cls));
}

function applyGalleryViewMode(mode) {
  const nextMode = GALLERY_VIEW_MODES.has(mode) ? mode : 'masonry';
  gGalleryViewMode = nextMode;
  const el = document.getElementById('mediaList');
  if (!el) return;
  applyGalleryClasses(el, nextMode);
}

function viewUsesThumbnails() {
  return gGalleryViewMode !== 'list';
}

function viewSupportsInlineVideoPlayback() {
  return gGalleryViewMode === 'masonry' || gGalleryViewMode === 'grid_large' || gGalleryViewMode === 'grid_xlarge';
}

function getDetailsColumnConfig(key) {
  return DETAILS_COLUMN_CONFIG.find(col => col.key === key) || null;
}

function fitDetailsColumnsToContainer(container) {
  if (!container) return;
  const availableWidth = Math.max(container.clientWidth - 24, 0);
  const fixedWidth = DETAILS_COLUMN_CONFIG.filter(col => !col.resizable).reduce((sum, col) => sum + col.width, 0);
  const gapsWidth = 14 * (DETAILS_COLUMN_CONFIG.length - 1);
  const targetWidth = Math.max(availableWidth - fixedWidth - gapsWidth, 0);
  const resizable = DETAILS_COLUMN_CONFIG.filter(col => col.resizable);
  const widths = Object.fromEntries(resizable.map(col => [col.key, Math.max(col.min, gDetailsColumnWidths[col.key] || col.width)]));
  const totalCurrent = Object.values(widths).reduce((sum, value) => sum + value, 0);
  const totalMin = resizable.reduce((sum, col) => sum + col.min, 0);

  if (targetWidth <= 0) {
    resizable.forEach(col => { gDetailsColumnWidths[col.key] = col.min; });
    return;
  }

  if (targetWidth >= totalCurrent) {
    return;
  }

  if (targetWidth <= totalMin) {
    resizable.forEach(col => { gDetailsColumnWidths[col.key] = col.min; });
    return;
  }

  let remainingShrink = totalCurrent - targetWidth;
  const nextWidths = { ...widths };
  let adjustable = resizable.filter(col => nextWidths[col.key] > col.min);
  while (remainingShrink > 0.5 && adjustable.length > 0) {
    const totalSlack = adjustable.reduce((sum, col) => sum + (nextWidths[col.key] - col.min), 0);
    if (totalSlack <= 0) break;
    adjustable.forEach(col => {
      const slack = nextWidths[col.key] - col.min;
      if (slack <= 0) return;
      const shrink = Math.min(slack, remainingShrink * (slack / totalSlack));
      nextWidths[col.key] -= shrink;
    });
    const achievedShrink = Object.keys(widths).reduce((sum, key) => sum + (widths[key] - nextWidths[key]), 0);
    remainingShrink = Math.max(0, (totalCurrent - targetWidth) - achievedShrink);
    adjustable = resizable.filter(col => nextWidths[col.key] > col.min + 0.5);
  }

  resizable.forEach(col => {
    gDetailsColumnWidths[col.key] = Math.round(Math.max(col.min, nextWidths[col.key]));
  });
}

function applyDetailsColumnWidths(container) {
  if (!container) return;
  fitDetailsColumnsToContainer(container);
  DETAILS_COLUMN_CONFIG.forEach(col => {
    const width = col.resizable ? (gDetailsColumnWidths[col.key] || col.width) : col.width;
    container.style.setProperty(`--details-col-${col.key}`, `${Math.round(width)}px`);
  });
}

function wireDetailsColumnResize(handle, container) {
  const key = handle.dataset.colKey;
  const config = getDetailsColumnConfig(key);
  if (!config || !config.resizable) return;

  handle.addEventListener('pointerdown', (event) => {
    event.preventDefault();
    event.stopPropagation();
    const startX = event.clientX;
    const startWidth = gDetailsColumnWidths[key] || config.width;

    const onMove = (moveEvent) => {
      const nextWidth = Math.max(config.min, Math.round(startWidth + (moveEvent.clientX - startX)));
      gDetailsColumnWidths[key] = nextWidth;
      applyDetailsColumnWidths(container);
    };

    const onUp = () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  });
}

function renderDetailsHeader(container) {
  const header = document.createElement('div');
  header.className = 'details-header';
  DETAILS_COLUMN_CONFIG.forEach(col => {
    const cell = document.createElement('div');
    cell.className = `details-header-cell${col.resizable ? ' is-resizable' : ''}`;
    cell.textContent = col.label;
    if (col.resizable) {
      const handle = document.createElement('div');
      handle.className = 'details-resize-handle';
      handle.dataset.colKey = col.key;
      cell.appendChild(handle);
      wireDetailsColumnResize(handle, container);
    }
    header.appendChild(cell);
  });
  container.appendChild(header);
}

function hasSelectedMediaCards() {
  return Array.from(document.querySelectorAll('.card.selected')).some(card => card.getAttribute('data-is-folder') !== 'true');
}

function updateCtxViewState() {
  document.querySelectorAll('.ctx-view-item').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.viewMode === gGalleryViewMode);
  });
}

function handleCardSelection(card, item, idx, e) {
  e.stopPropagation();
  const path = item.path || '';

  if (e.ctrlKey || e.metaKey) {
    if (card.classList.contains('selected')) {
      card.classList.remove('selected');
      gSelectedPaths.delete(path);
    } else {
      card.classList.add('selected');
      gSelectedPaths.add(path);
    }
    gLastSelectionIdx = idx;
  } else if (e.shiftKey && gLastSelectionIdx !== -1) {
    const start = Math.min(gLastSelectionIdx, idx);
    const end = Math.max(gLastSelectionIdx, idx);
    const cards = document.querySelectorAll('.card');
    for (let i = start; i <= end; i++) {
      const current = cards[i];
      const currentPath = current.getAttribute('data-path');
      current.classList.add('selected');
      if (currentPath) gSelectedPaths.add(currentPath);
    }
  } else {
    deselectAll();
    card.classList.add('selected');
    gSelectedPaths.add(path);
    gLastSelectionIdx = idx;
  }

  gLockedCard = card;
  syncMetadataToBridge();
}

function getDateFromItem(item) {
  const ts = Number(item && (item.auto_date || item.exif_date_taken || item.metadata_date || item.file_created_time || item.modified_time) || 0);
  if (!Number.isFinite(ts) || ts <= 0) return null;
  const millis = ts > 1e12 ? Math.floor(ts / 1000000) : ts;
  const date = new Date(millis);
  return Number.isNaN(date.getTime()) ? null : date;
}

function getDateGroupMeta(item) {
  const date = getDateFromItem(item);
  if (!date) {
    return {
      key: 'unknown',
      label: 'Unknown Date',
      timelineYear: 'Unknown',
      timelineLabel: 'Unknown',
      timelineTitle: 'Unknown Date',
      sortValue: -1,
    };
  }

  const year = date.getFullYear();
  const month = date.getMonth();
  const day = date.getDate();
  const monthLabel = date.toLocaleDateString(undefined, { month: 'short' });
  const monthLong = date.toLocaleDateString(undefined, { month: 'long' });

  if (gGroupDateGranularity === 'year') {
    return {
      key: `${year}`,
      label: `${year}`,
      timelineYear: `${year}`,
      timelineLabel: `${year}`,
      timelineTitle: `${year}`,
      sortValue: Date.UTC(year, 0, 1),
    };
  }

  if (gGroupDateGranularity === 'month') {
    return {
      key: `${year}-${String(month + 1).padStart(2, '0')}`,
      label: `${monthLong} ${year}`,
      timelineYear: `${year}`,
      timelineLabel: monthLabel,
      timelineTitle: `${monthLong} ${year}`,
      sortValue: Date.UTC(year, month, 1),
    };
  }

  return {
    key: `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`,
    label: date.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' }),
    timelineYear: `${year}`,
    timelineLabel: monthLabel,
    timelineTitle: `${monthLong} ${year}`,
    sortValue: Date.UTC(year, month, day),
  };
}

function buildGroupedItems(items) {
  const groups = [];
  const seen = new Map();
  items.forEach((item) => {
    const meta = getDateGroupMeta(item);
    let group = seen.get(meta.key);
    if (!group) {
      group = { ...meta, items: [] };
      seen.set(meta.key, group);
      groups.push(group);
    }
    group.items.push(item);
  });
  const ascending = gSort === 'date_asc';
  groups.sort((a, b) => {
    if (a.sortValue === b.sortValue) return a.label.localeCompare(b.label);
    if (a.sortValue < 0) return 1;
    if (b.sortValue < 0) return -1;
    return ascending ? a.sortValue - b.sortValue : b.sortValue - a.sortValue;
  });
  return groups;
}

function toggleGroupCollapsed(groupKey, forceCollapsed = null) {
  const shouldCollapse = forceCollapsed === null ? !gCollapsedGroupKeys.has(groupKey) : !!forceCollapsed;
  if (shouldCollapse) gCollapsedGroupKeys.add(groupKey);
  else gCollapsedGroupKeys.delete(groupKey);
  document.querySelectorAll(`.gallery-group[data-group-key="${CSS.escape(groupKey)}"]`).forEach(section => {
    const body = section.querySelector('.gallery-group-body');
    const toggle = section.querySelector('.gallery-group-toggle');
    const collapsed = gCollapsedGroupKeys.has(groupKey);
    section.classList.toggle('is-collapsed', collapsed);
    if (body) body.hidden = collapsed;
    if (toggle) toggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
  });
}

function setAllGroupsCollapsed(collapsed) {
  document.querySelectorAll('.gallery-group').forEach(section => {
    const key = section.dataset.groupKey;
    if (key) toggleGroupCollapsed(key, collapsed);
  });
}

function scrollToGroup(groupKey) {
  const target = document.querySelector(`.gallery-group[data-group-key="${CSS.escape(groupKey)}"]`);
  if (!target) return;
  target.scrollIntoView({ block: 'start', behavior: gTimelineScrubActive ? 'auto' : 'smooth' });
}

function updateTimelineThumb(index, total) {
  const thumb = document.querySelector('#timelineRail .timeline-scrubber-thumb');
  if (!thumb || total <= 0) return;
  const ratio = total <= 1 ? 0 : index / (total - 1);
  thumb.style.top = `calc(${TIMELINE_TOP_YEAR_TOP_PX + TIMELINE_THUMB_OFFSET_PX}px + ${Math.max(0, Math.min(1, ratio))} * (100% - ${TIMELINE_INSET_PX * 2}px) - ${TIMELINE_THUMB_SIZE_PX / 2}px)`;
}

function scrubTimelineAt(clientY) {
  const rail = document.getElementById('timelineRail');
  const track = rail && rail.querySelector('.timeline-scrubber-track');
  if (!rail || !track) return;
  const targets = Array.isArray(rail.__scrubGroups) ? rail.__scrubGroups : [];
  if (!targets.length) return;
  const rect = track.getBoundingClientRect();
  const rawRatio = rect.height <= 0 ? 0 : (clientY - rect.top) / rect.height;
  const ratio = Math.max(0, Math.min(1, rawRatio));
  const index = Math.max(0, Math.min(targets.length - 1, Math.round(ratio * (targets.length - 1))));
  const targetKey = targets[index];
  if (!targetKey) return;
  updateTimelineThumb(index, targets.length);
  scrollToGroup(targetKey);
}

function renderTimelineRail(groups) {
  const rail = document.getElementById('timelineRail');
  if (!rail) return;
  rail.innerHTML = '';
  rail.__scrubGroups = [];

  if (gGroupBy !== 'date' || !Array.isArray(groups) || groups.length === 0) {
    rail.hidden = true;
    return;
  }

  rail.__scrubGroups = groups.map(group => group.key);
  const scale = document.createElement('div');
  scale.className = 'timeline-scale';
  const entryPositions = [];
  const entryMarkers = [];

  const years = new Map();
  let lastMonthTitle = null;
  const toInsetTop = (ratio) => `calc(${TIMELINE_INSET_PX}px + ${Math.max(0, Math.min(1, ratio))} * (100% - ${TIMELINE_INSET_PX * 2}px))`;
  groups.forEach((group, groupIndex) => {
    const ratio = groups.length <= 1 ? 0 : groupIndex / (groups.length - 1);
    if (!years.has(group.timelineYear)) {
      years.set(group.timelineYear, { key: group.key, ratio });
    }
    const duplicateMonth = gGroupDateGranularity === 'day' && group.timelineTitle === lastMonthTitle;
    if (!duplicateMonth || gGroupDateGranularity !== 'day') {
      const marker = document.createElement('button');
      marker.type = 'button';
      marker.className = 'timeline-marker timeline-entry';
      marker.textContent = group.timelineLabel;
      marker.title = group.timelineTitle;
      marker.dataset.groupKey = group.key;
      marker.style.top = toInsetTop(ratio);
      marker.addEventListener('click', () => scrollToGroup(group.key));
      scale.appendChild(marker);
      entryPositions.push(ratio);
      entryMarkers.push({ key: group.key, ratio, marker });
      lastMonthTitle = group.timelineTitle;
    }
  });

  const firstEntryRatio = entryPositions.length ? Math.min(...entryPositions) : null;
  const lastEntryRatio = entryPositions.length ? Math.max(...entryPositions) : null;

  const findClearRatio = (ratio) => {
    const minGap = 0.055;
    let nextRatio = ratio;
    const nearby = entryPositions
      .filter(value => Math.abs(value - ratio) < minGap)
      .sort((a, b) => Math.abs(a - ratio) - Math.abs(b - ratio));
    nearby.forEach((value) => {
      if (Math.abs(nextRatio - value) < minGap) {
        if (value < 0.12) {
          nextRatio = Math.max(0.01, value - minGap);
        } else if (value <= 0.5) {
          nextRatio = Math.min(0.98, value + minGap);
        } else {
          nextRatio = Math.max(0.02, value - minGap);
        }
      }
    });
    return Math.max(0.01, Math.min(0.98, nextRatio));
  };

  const yearMarkers = [];
  years.forEach(({ key, ratio }, year) => {
    const yearBtn = document.createElement('button');
    yearBtn.type = 'button';
    yearBtn.className = 'timeline-marker timeline-year';
    yearBtn.textContent = year;
    yearBtn.dataset.groupKey = key;
    const resolvedRatio = findClearRatio(ratio);
    yearBtn.style.top = toInsetTop(resolvedRatio);
    if (lastEntryRatio !== null && Math.abs(ratio - lastEntryRatio) < 0.001) {
      yearBtn.classList.add('is-above');
      yearBtn.style.top = toInsetTop(lastEntryRatio);
    }
    yearBtn.addEventListener('click', () => scrollToGroup(key));
    scale.appendChild(yearBtn);
    yearMarkers.push({ key, ratio, marker: yearBtn });
  });

  const firstEntry = entryMarkers[0];
  const firstYear = yearMarkers[0];
  if (firstEntry && firstYear) {
    firstYear.marker.classList.remove('is-above');
    firstYear.marker.classList.add('is-top-year');
    firstYear.marker.style.top = `${TIMELINE_TOP_YEAR_TOP_PX}px`;
    firstEntry.marker.classList.add('is-top-month');
    firstEntry.marker.style.top = `${TIMELINE_TOP_MONTH_TOP_PX}px`;
  }

  const scrubber = document.createElement('div');
  scrubber.className = 'timeline-scrubber';
  scrubber.innerHTML = '<div class="timeline-scrubber-track"></div><div class="timeline-scrubber-thumb"></div>';
  scrubber.addEventListener('pointerdown', (e) => {
    gTimelineScrubActive = true;
    gTimelineScrubPointerId = e.pointerId;
    scrubTimelineAt(e.clientY);
  });
  scale.appendChild(scrubber);

  rail.appendChild(scale);
  updateTimelineThumb(0, rail.__scrubGroups.length);
  rail.hidden = !rail.childElementCount;
}

function setCustomSelectValue(selectId, value) {
  const el = document.getElementById(selectId);
  if (!el) return;
  const trigger = el.querySelector('.select-trigger');
  const option = el.querySelector(`[data-value="${CSS.escape(value)}"]`);
  if (!trigger || !option) return;
  trigger.textContent = option.textContent;
  el.querySelectorAll('.selected').forEach(node => node.classList.remove('selected'));
  option.classList.add('selected');
}

function syncGroupByUi() {
  const granularitySelect = document.getElementById('dateGranularitySelect');
  if (granularitySelect) {
    granularitySelect.hidden = gGroupBy !== 'date';
  }
}

function openFolderItem(path) {
  if (gBridge && gBridge.set_selected_folders && path) {
    deselectAll();
    gBridge.set_selected_folders([path]);
  }
}

function createStructuredCard(item, idx) {
  const mediaIdx = getItemIndex(item, idx);
  const card = document.createElement('div');
  const isFolder = !!item.is_folder;
  const usesThumbnails = viewUsesThumbnails();
  const supportsInlinePlayback = !isFolder && item.media_type === 'video' && viewSupportsInlineVideoPlayback();
  card.className = `card structured-card${isFolder ? ' folder-card ready' : ' loading'}`;
  card.tabIndex = 0;
  card.setAttribute('data-path', item.path || '');
  card.setAttribute('data-is-folder', isFolder ? 'true' : 'false');

  const thumbWrap = document.createElement('div');
  thumbWrap.className = 'structured-thumb';
  card.appendChild(thumbWrap);

  if (isFolder) {
    const folderThumb = document.createElement('div');
    folderThumb.className = 'folder-thumb';
    folderThumb.innerHTML = '<div class="folder-glyph"></div>';
    thumbWrap.appendChild(folderThumb);
  } else if (!usesThumbnails) {
    const icon = document.createElement('div');
    icon.className = `media-icon ${item.media_type === 'video' ? 'video-icon' : 'image-icon'}`;
    thumbWrap.appendChild(icon);
    card.classList.add('ready');
  } else if (item.media_type === 'image') {
    const img = document.createElement('img');
    img.className = 'thumb';
    img.setAttribute('data-src', item.url);
    img.alt = '';
    if (item.is_animated) {
      img.setAttribute('data-animated', 'true');
      img.setAttribute('data-path', item.path || '');
    }
    thumbWrap.appendChild(img);
    gPosterObserver.observe(img);
  } else {
    const img = document.createElement('img');
    img.className = 'thumb poster';
    img.alt = '';
    img.setAttribute('data-video-path', item.path || '');
    thumbWrap.appendChild(img);
    gPosterObserver.observe(img);

    if (supportsInlinePlayback) {
      const playIndicator = document.createElement('div');
      playIndicator.className = 'video-play-indicator';
      playIndicator.innerHTML = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='white'><path d='M8 5v14l11-7z'/></svg>`;
      thumbWrap.appendChild(playIndicator);
      playIndicator.addEventListener('click', (e) => {
        e.stopPropagation();
        const path = item.path || '';
        if (!path || !gBridge) return;
        if (gPlayingInplaceCard) {
          gPlayingInplaceCard.classList.remove('playing-inplace', 'playing-inprogress', 'playing-confirmed');
          gPlayingInplaceCard.removeAttribute('data-paused');
        }
        const rect = thumbWrap.getBoundingClientRect();
        if (gBridge.open_native_video_inplace) {
          card.classList.add('playing-inplace', 'playing-inprogress');
          gPlayingInplaceCard = card;
          const shouldLoop = (item.duration && item.duration < 60) || false;
          gBridge.open_native_video_inplace(path, rect.x, rect.y, rect.width, rect.height, true, shouldLoop, true, item.width || 0, item.height || 0);
        } else {
          gBridge.open_native_video(path, true, false, true, item.width || 0, item.height || 0);
        }
      });
    }
  }

  const content = document.createElement('div');
  content.className = 'structured-content';

  const title = document.createElement('div');
  title.className = 'entry-name';
  title.textContent = getItemName(item);
  title.title = getItemName(item);
  content.appendChild(title);

  const folder = document.createElement('div');
  folder.className = 'entry-folder';
  folder.textContent = getItemFolderDisplay(item);
  folder.title = getItemFolder(item);
  content.appendChild(folder);

  if (gGalleryViewMode === 'details') {
    const typeCell = document.createElement('div');
    typeCell.className = 'entry-detail';
    typeCell.textContent = isFolder ? 'Folder' : (item.media_type === 'video' ? 'Video' : 'Image');
    content.appendChild(typeCell);

    const modifiedCell = document.createElement('div');
    modifiedCell.className = 'entry-detail';
    modifiedCell.textContent = formatModifiedTime(item.modified_time);
    content.appendChild(modifiedCell);

    const sizeCell = document.createElement('div');
    sizeCell.className = 'entry-detail';
    sizeCell.textContent = isFolder ? '' : formatFileSize(item.file_size);
    content.appendChild(sizeCell);
  } else if (gGalleryViewMode === 'content') {
    const meta = document.createElement('div');
    meta.className = 'entry-detail';
    meta.textContent = isFolder ? 'Folder' : [item.media_type === 'video' ? 'Video' : 'Image', formatFileSize(item.file_size)].filter(Boolean).join(' • ');
    content.appendChild(meta);
  } else if (gGalleryViewMode === 'list') {
    folder.remove();
  }

  card.appendChild(content);

  card.addEventListener('click', (e) => handleCardSelection(card, item, mediaIdx, e));
  card.addEventListener('dblclick', () => {
    if (isFolder) openFolderItem(item.path);
    else openLightboxByIndex(mediaIdx);
  });
  card.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      if (isFolder) openFolderItem(item.path);
      else openLightboxByIndex(mediaIdx);
    }
  });
  card.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    showCtx(e.clientX, e.clientY, item, mediaIdx, false);
  });

  if (!isFolder) {
    card.draggable = true;
    card.addEventListener('dragstart', (e) => {
      const path = item.path || '';
      if (!path) return;
      const paths = gSelectedPaths.has(path) ? Array.from(gSelectedPaths) : [path];
      const urls = paths.map(p => 'file:///' + p.replace(/\\/g, '/'));
      const pathsJson = JSON.stringify(paths);
      e.dataTransfer.setData('text/uri-list', urls.join('\r\n'));
      e.dataTransfer.setData('text/plain', pathsJson);
      e.dataTransfer.setData('web/mmx-paths', pathsJson);
      e.dataTransfer.setData('application/x-mmx-type', 'file');
      if (window.qt && gBridge && gBridge.set_drag_paths) gBridge.set_drag_paths(paths);
      gCurrentDragCount = paths.length;
      e.dataTransfer.effectAllowed = 'copyMove';
    });
    card.addEventListener('drag', (e) => {
      if (gBridge && gBridge.update_drag_tooltip && e.clientX > 0 && e.clientY > 0) {
        const isCopy = e.ctrlKey || e.metaKey;
        const count = gCurrentDragCount || 1;
        gBridge.update_drag_tooltip(count, isCopy, gCurrentTargetFolderName);
      }
    });
    card.addEventListener('dragend', () => {
      if (gBridge && gBridge.hide_drag_tooltip) gBridge.hide_drag_tooltip();
      if (window.qt && gBridge && gBridge.set_drag_paths) gBridge.set_drag_paths([]);
      gCurrentDragCount = 0;
    });
  }

  return card;
}

function createMasonryCard(item, idx) {
  const mediaIdx = getItemIndex(item, idx);
  const card = document.createElement('div');
  card.className = 'card loading';
  card.tabIndex = 0;
  if (item.width && item.height) {
    card.style.aspectRatio = `${item.width} / ${item.height}`;
  }

  if (item.media_type === 'image') {
    const img = document.createElement('img');
    img.className = 'thumb';
    img.setAttribute('data-src', item.url);
    img.alt = '';
    if (item.is_animated) {
      img.setAttribute('data-animated', 'true');
      img.setAttribute('data-path', item.path || '');
    }
    card.appendChild(img);
    gPosterObserver.observe(img);

    card.setAttribute('data-path', item.path || '');

    card.addEventListener('click', (e) => handleCardSelection(card, item, mediaIdx, e));
    card.addEventListener('dblclick', () => openLightboxByIndex(mediaIdx));
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        openLightboxByIndex(mediaIdx);
      }
    });

    card.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      showCtx(e.clientX, e.clientY, item, mediaIdx, false);
    });

    card.draggable = true;
    card.addEventListener('dragstart', (e) => {
      const path = item.path || '';
      if (!path) return;

      let paths = [];
      if (gSelectedPaths.has(path)) {
        paths = Array.from(gSelectedPaths);
      } else {
        paths = [path];
      }

      if (window.qt && gBridge && gBridge.debug_log) {
        gBridge.debug_log("JS DragStart Image: SelectedCount=" + gSelectedPaths.size + " Dragging=" + path + " FinalCount=" + paths.length);
      }
      console.log("JS DragStart Image:", paths);

      const urls = paths.map(p => 'file:///' + p.replace(/\\/g, '/'));
      const pathsJson = JSON.stringify(paths);

      e.dataTransfer.setData('text/uri-list', urls.join('\r\n'));
      e.dataTransfer.setData('text/plain', pathsJson);
      e.dataTransfer.setData('web/mmx-paths', pathsJson);
      e.dataTransfer.setData('application/x-mmx-type', 'file');

      if (window.qt && gBridge && gBridge.set_drag_paths) {
        gBridge.set_drag_paths(paths);
      }
      gCurrentDragCount = paths.length;

      e.dataTransfer.effectAllowed = 'copyMove';

      const previewImg = card.querySelector('img');
      if (previewImg) {
        const canvas = document.createElement('canvas');
        canvas.width = 64;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(previewImg, 0, 0, 64, 64);
        e.dataTransfer.setDragImage(canvas, -10, -10);
      }
    });
    card.addEventListener('drag', (e) => {
      if (gBridge && gBridge.update_drag_tooltip && e.clientX > 0 && e.clientY > 0) {
        const isCopy = e.ctrlKey || e.metaKey;
        const count = gCurrentDragCount || 1;
        gBridge.update_drag_tooltip(count, isCopy, gCurrentTargetFolderName);
      }
    });
    card.addEventListener('dragend', (e) => {
      if (gBridge && gBridge.hide_drag_tooltip) {
        gBridge.hide_drag_tooltip();
      }
      if (window.qt && gBridge && gBridge.set_drag_paths) {
        gBridge.set_drag_paths([]);
      }
      gCurrentDragCount = 0;
      e.preventDefault();
    });
    return card;
  }

  const img = document.createElement('img');
  img.className = 'thumb poster';
  img.alt = '';
  img.setAttribute('data-video-path', item.path || '');
  card.appendChild(img);
  gPosterObserver.observe(img);

  const playIndicator = document.createElement('div');
  playIndicator.className = 'video-play-indicator';
  playIndicator.innerHTML = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='white'><path d='M8 5v14l11-7z'/></svg>`;
  card.appendChild(playIndicator);
  playIndicator.addEventListener('click', (e) => {
    e.stopPropagation();
    const path = item.path || '';
    if (!path || !gBridge) return;

    if (gPlayingInplaceCard) {
      gPlayingInplaceCard.classList.remove('playing-inplace', 'playing-inprogress', 'playing-confirmed');
      gPlayingInplaceCard.removeAttribute('data-paused');
    }

    const rect = card.getBoundingClientRect();
    if (gBridge.open_native_video_inplace) {
      card.classList.add('playing-inplace', 'playing-inprogress');
      gPlayingInplaceCard = card;
      const shouldLoop = (item.duration && item.duration < 60) || false;
      gBridge.open_native_video_inplace(path, rect.x, rect.y, rect.width, rect.height, true, shouldLoop, true, item.width || 0, item.height || 0);
    } else {
      gBridge.open_native_video(path, true, false, true, item.width || 0, item.height || 0);
    }
  });

  card.addEventListener('mouseenter', () => {
    if (gBridge && gBridge.preload_video && item.path) {
      gBridge.preload_video(item.path, item.width || 0, item.height || 0);
    }
  });

  card.setAttribute('data-path', item.path || '');

  card.addEventListener('click', (e) => handleCardSelection(card, item, mediaIdx, e));
  card.addEventListener('dblclick', () => openLightboxByIndex(mediaIdx));
  card.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      openLightboxByIndex(mediaIdx);
    }
  });
  card.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    showCtx(e.clientX, e.clientY, item, mediaIdx, false);
  });

  card.draggable = true;
  card.addEventListener('dragstart', (e) => {
    const path = item.path || '';
    if (!path) return;

    const paths = gSelectedPaths.has(path) ? Array.from(gSelectedPaths) : [path];
    const urls = paths.map(p => 'file:///' + p.replace(/\\/g, '/'));
    const pathsJson = JSON.stringify(paths);

    e.dataTransfer.setData('text/uri-list', urls.join('\r\n'));
    e.dataTransfer.setData('text/plain', pathsJson);
    e.dataTransfer.setData('web/mmx-paths', pathsJson);
    e.dataTransfer.setData('application/x-mmx-type', 'file');

    if (window.qt && gBridge && gBridge.set_drag_paths) {
      gBridge.set_drag_paths(paths);
    }
    gCurrentDragCount = paths.length;
    e.dataTransfer.effectAllowed = 'copyMove';
  });
  card.addEventListener('drag', (e) => {
    if (gBridge && gBridge.update_drag_tooltip && e.clientX > 0 && e.clientY > 0) {
      const isCopy = e.ctrlKey || e.metaKey;
      const count = gCurrentDragCount || 1;
      gBridge.update_drag_tooltip(count, isCopy, gCurrentTargetFolderName);
    }
  });
  card.addEventListener('dragend', () => {
    if (gBridge && gBridge.hide_drag_tooltip) {
      gBridge.hide_drag_tooltip();
    }
    if (window.qt && gBridge && gBridge.set_drag_paths) {
      gBridge.set_drag_paths([]);
    }
    gCurrentDragCount = 0;
  });

  return card;
}

function renderStructuredMediaList(el, items) {
  if (gGalleryViewMode === 'details') {
    applyDetailsColumnWidths(el);
    renderDetailsHeader(el);
  }

  items.forEach((item, idx) => {
    el.appendChild(createStructuredCard(item, idx));
  });

  requestAnimationFrame(() => {
    const unobserved = el.querySelectorAll('img[data-src]:not([src]), img[data-video-path]:not([src])');
    unobserved.forEach(img => {
      if (gPosterRequested.has(img)) return;
      const imgSrc = img.getAttribute('data-src');
      const path = img.getAttribute('data-video-path');
      const item = gMedia.find(m => m.path === path || m.url === imgSrc);
      if (imgSrc) {
        gBackgroundQueue.push({ type: 'image', el: img, imgSrc });
      } else if (path && item) {
        gBackgroundQueue.push({ type: 'video', el: img, path, width: item.width, height: item.height });
      }
    });
    scheduleBackgroundDrain();
  });
}

function renderGroupedMediaList(el, items) {
  const folderItems = items.filter(item => !!item.is_folder);
  const mediaItems = items.filter(item => !item.is_folder);
  const groups = buildGroupedItems(mediaItems);
  el.classList.add('gallery-grouped');

  if (folderItems.length > 0) {
    const prefix = document.createElement('div');
    prefix.className = 'gallery-group-prefix';
    applyGalleryClasses(prefix, gGalleryViewMode);
    if (gGalleryViewMode === 'masonry') {
      folderItems.forEach((item, idx) => prefix.appendChild(createMasonryCard(item, idx)));
    } else {
      renderStructuredMediaList(prefix, folderItems);
    }
    el.appendChild(prefix);
  }

  groups.forEach(group => {
    const section = document.createElement('section');
    section.className = 'gallery-group';
    section.dataset.groupKey = group.key;

    const header = document.createElement('div');
    header.className = 'gallery-group-header';

    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'gallery-group-toggle';
    toggle.innerHTML = `<span class="gallery-group-chevron" aria-hidden="true"></span><span class="gallery-group-title">${group.label}</span><span class="gallery-group-count">${group.items.length}</span>`;
    toggle.addEventListener('click', () => toggleGroupCollapsed(group.key));
    toggle.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      showCtx(e.clientX, e.clientY, null, -1, false);
    });
    header.appendChild(toggle);

    const body = document.createElement('div');
    applyGalleryClasses(body, gGalleryViewMode);
    body.classList.add('gallery-group-body');

    if (gGalleryViewMode === 'masonry') {
      group.items.forEach((item, idx) => body.appendChild(createMasonryCard(item, idx)));
    } else {
      renderStructuredMediaList(body, group.items);
    }

    section.appendChild(header);
    section.appendChild(body);
    el.appendChild(section);
    toggleGroupCollapsed(group.key, gCollapsedGroupKeys.has(group.key));
  });

  renderTimelineRail(groups);
  requestAnimationFrame(() => {
    const unobserved = el.querySelectorAll('img[data-src]:not([src]), img[data-video-path]:not([src])');
    unobserved.forEach(img => {
      if (gPosterRequested.has(img)) return;
      const imgSrc = img.getAttribute('data-src');
      const path = img.getAttribute('data-video-path');
      const item = gMedia.find(m => m.path === path || m.url === imgSrc);
      if (imgSrc) {
        gBackgroundQueue.push({ type: 'image', el: img, imgSrc });
      } else if (path && item) {
        gBackgroundQueue.push({ type: 'video', el: img, path, width: item.width, height: item.height });
      }
    });
    scheduleBackgroundDrain();
  });
}

function showCtx(x, y, item, idx, fromLightbox = false) {
  const ctx = document.getElementById('ctx');
  if (!ctx) return;

  gCtxItem = item;
  gCtxIndex = idx;
  gCtxFromLightbox = !!fromLightbox;

  const hideBtn = document.getElementById('ctxHide');
  const unhideBtn = document.getElementById('ctxUnhide');
  const renameBtn = document.getElementById('ctxRename');
  const addToCollectionBtn = document.getElementById('ctxAddToCollection');

  // Position clamped to viewport
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const rect = ctx.getBoundingClientRect();
  const w = rect.width || 200;
  const h = rect.height || 180;

  const left = Math.max(8, Math.min(vw - w - 8, x));
  const top = Math.max(8, Math.min(vh - h - 8, y));
  ctx.style.left = `${left}px`;
  ctx.style.top = `${top}px`;
  ctx.hidden = false;

  if (gBridge && gBridge.debug_log) {
    gBridge.debug_log(`showCtx: item=${item ? item.path : 'null'} idx=${idx}`);
  }

  // Enable/disable Paste
  const pasteBtn = document.getElementById('ctxPaste');
  if (pasteBtn && gBridge && gBridge.has_files_in_clipboard) {
    gBridge.has_files_in_clipboard(function (has) {
      pasteBtn.disabled = !has;
    });
  }

  // Show/hide per-item actions
  const hasItem = !!item;
  const isFolder = hasItem && !!item.is_folder;
  ['ctxHide', 'ctxUnhide', 'ctxRename', 'ctxDelete', 'ctxExplorer', 'ctxCut', 'ctxCopy'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = hasItem ? 'block' : 'none';
  });
  const metaBtn = document.getElementById('ctxMeta');
  if (metaBtn) metaBtn.style.display = hasItem && !isFolder ? 'block' : 'none';
  if (addToCollectionBtn) addToCollectionBtn.style.display = (hasItem && !isFolder) || (!hasItem && hasSelectedMediaCards()) ? 'block' : 'none';
  
  const isRotatable = hasItem && !isFolder && (item.media_type === 'image' || item.media_type === 'video');
  ['ctxRotCW', 'ctxRotCCW', 'ctxRotSep'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = isRotatable ? 'block' : 'none';
  });
  
  // External Editors
  const psBtn = document.getElementById('ctxPhotoshop');
  const affBtn = document.getElementById('ctxAffinity');
  const edSep = document.getElementById('ctxEditorSep');
  let hasEd = false;
  if (psBtn) {
      const showPs = hasItem && !isFolder && !!gExternalEditors.photoshop;
      psBtn.style.display = showPs ? 'block' : 'none';
      if (showPs) hasEd = true;
  }
  if (affBtn) {
      const showAff = hasItem && !isFolder && !!gExternalEditors.affinity;
      affBtn.style.display = showAff ? 'block' : 'none';
      if (showAff) hasEd = true;
  }
  if (edSep) {
      edSep.style.display = hasEd ? 'block' : 'none';
  }

  // Bulk actions
  const selectAllBtn = document.getElementById('ctxSelectAll');
  if (selectAllBtn) selectAllBtn.style.display = hasItem ? 'none' : 'block';
  const clearSelectionBtn = document.getElementById('ctxSelectNone');
  if (clearSelectionBtn) clearSelectionBtn.style.display = (gSelectedPaths.size > 0) ? 'block' : 'none';
  const collapseAllBtn = document.getElementById('ctxCollapseAll');
  const expandAllBtn = document.getElementById('ctxExpandAll');
  const showGroupActions = gGroupBy === 'date';
  if (collapseAllBtn) collapseAllBtn.style.display = showGroupActions ? 'block' : 'none';
  if (expandAllBtn) expandAllBtn.style.display = showGroupActions ? 'block' : 'none';

  // New folder is shown only when right-clicking background (no item)
  const newFolderBtn = document.getElementById('ctxNewFolder');
  if (newFolderBtn) newFolderBtn.style.display = hasItem ? 'none' : 'block';
  const viewSep = document.getElementById('ctxViewSep');
  if (viewSep) viewSep.style.display = hasItem ? 'none' : 'block';
  document.querySelectorAll('.ctx-view-item').forEach(btn => {
    btn.style.display = hasItem ? 'none' : 'block';
  });
  updateCtxViewState();

  // Refine Hide/Unhide display
  if (hasItem) {
    const isHidden = item && item.is_hidden;
    if (hideBtn) hideBtn.style.display = isHidden ? 'none' : 'block';
    if (unhideBtn) unhideBtn.style.display = isHidden ? 'block' : 'none';
  }
}

function wireCtxMenu() {
  const ctx = document.getElementById('ctx');
  if (!ctx) return;

  const selectAllBtn = document.getElementById('ctxSelectAll');
  if (selectAllBtn) selectAllBtn.addEventListener('click', () => {
    selectAll();
    hideCtx();
  });

  const clearSelectionBtn = document.getElementById('ctxSelectNone');
  if (clearSelectionBtn) clearSelectionBtn.addEventListener('click', () => {
    deselectAll();
    syncMetadataToBridge();
    hideCtx();
  });

  const cancelBtn = document.getElementById('ctxCancel');
  if (cancelBtn) cancelBtn.addEventListener('click', hideCtx);

  window.addEventListener('click', (e) => {
    if (ctx && !ctx.hidden && !ctx.contains(e.target)) hideCtx();
  });
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') hideCtx();
  });

  // Consolidated mousedown listener for all context menu items
  // Immediate response beats potential dismissal loops.
  ctx.addEventListener('mousedown', (e) => {
    const btn = e.target.closest('.ctx-item');
    if (!btn) return;

    e.preventDefault();
    e.stopPropagation();

    const item = gCtxItem;
    const fromLb = gCtxFromLightbox;

    const getTargetPaths = () => {
      if (item && item.path) {
        if (gSelectedPaths.has(item.path)) {
          return Array.from(gSelectedPaths);
        }
        return [item.path];
      }
      return Array.from(gSelectedPaths);
    };

    if (gBridge && gBridge.debug_log) {
      gBridge.debug_log(`ctx mousedown: id=${btn.id} path=${item ? item.path : 'null'}`);
    }

    if (btn.dataset.viewMode && gBridge && gBridge.set_setting_str) {
      applyGalleryViewMode(btn.dataset.viewMode);
      updateCtxViewState();
      gBridge.set_setting_str('gallery.view_mode', btn.dataset.viewMode, function () {
        refreshFromBridge(gBridge, true);
      });
      hideCtx();
      return;
    }

    switch (btn.id) {
      case 'ctxExplorer':
        if (item && item.path && gBridge && gBridge.open_in_explorer) {
          gBridge.open_in_explorer(item.path);
        }
        break;
        
      case 'ctxPhotoshop':
        if (item && item.path && gBridge && gBridge.open_in_editor) {
            gBridge.open_in_editor('photoshop', item.path);
        }
        hideCtx();
        break;

      case 'ctxAffinity':
        if (item && item.path && gBridge && gBridge.open_in_editor) {
            gBridge.open_in_editor('affinity', item.path);
        }
        hideCtx();
        break;
        
      case 'ctxRotCW':
        if (item && item.path && gBridge && gBridge.rotate_image) {
            gBridge.rotate_image(item.path, -90);
        }
        hideCtx();
        break;
        
      case 'ctxRotCCW':
        if (item && item.path && gBridge && gBridge.rotate_image) {
            gBridge.rotate_image(item.path, 90);
        }
        hideCtx();
        break;
      case 'ctxHide':
        if (item && item.path && gBridge && (item.is_folder ? gBridge.set_folder_hidden : gBridge.set_media_hidden)) {
          if (fromLb) closeLightbox();
          setGlobalLoading(true, 'Hiding…', 25);
          const hideFn = item.is_folder ? gBridge.set_folder_hidden : gBridge.set_media_hidden;
          hideFn.call(gBridge, item.path, true, (success) => {
             if (success) {
                 // Refresh or update local state
                 item.is_hidden = true;
                 refreshFromBridge(gBridge);
             }
          });
        }
        break;
      case 'ctxUnhide':
        if (item && item.path && gBridge && (item.is_folder ? gBridge.set_folder_hidden : gBridge.set_media_hidden)) {
          if (fromLb) closeLightbox();
          setGlobalLoading(true, 'Unhiding…', 25);
          const unhideFn = item.is_folder ? gBridge.set_folder_hidden : gBridge.set_media_hidden;
          unhideFn.call(gBridge, item.path, false, (success) => {
             if (success) {
                 item.is_hidden = false;
                 refreshFromBridge(gBridge);
             }
          });
        }
        break;
      case 'ctxRename':
        if (item && item.path && gBridge && gBridge.rename_path_async) {
          const curName = item.path.split(/[/\\]/).pop();
          const next = prompt('Rename to:', curName);
          if (next && next !== curName) {
            if (fromLb) closeLightbox();
            setGlobalLoading(true, 'Renaming…', 25);
            gBridge.rename_path_async(item.path, next, () => { });
          }
        }
        break;
      case 'ctxAddToCollection':
        if (gBridge && gBridge.add_paths_to_collection_interactive) {
          const paths = getTargetPaths().filter(path => {
            const card = document.querySelector(`.card[data-path="${CSS.escape(path)}"]`);
            return !(card && card.getAttribute('data-is-folder') === 'true');
          });
          if (paths.length > 0) {
            gBridge.add_paths_to_collection_interactive(paths, function () { });
          }
        }
        break;
      case 'ctxMeta':
        if (item && item.path && gBridge && gBridge.show_metadata && !item.is_folder) {
          const pathForMeta = item.path;
          hideCtx();
          // Ensure the right panel is visible (void slot - no callback)
          if (gBridge.set_setting_bool) {
            gBridge.set_setting_bool('ui.show_right_panel', true);
          }
          // Select the card in the gallery
          document.querySelectorAll('.card.selected').forEach(c => c.classList.remove('selected'));
          const metaCard = document.querySelector(`.card[data-path="${CSS.escape(pathForMeta)}"]`);
          if (metaCard) { metaCard.classList.add('selected'); gLockedCard = metaCard; }
          // Small delay lets any click-triggered deselects process first before we request metadata
          setTimeout(() => {
            gBridge.show_metadata(pathForMeta, () => { });
          }, 60);
        }
        break;
      case 'ctxDelete':
        if (item && item.path && gBridge && gBridge.delete_path) {
          gBridge.delete_path(item.path, (ok) => { if (ok) refreshFromBridge(gBridge); });
        }
        break;
      case 'ctxCut':
        if (item && item.path && gBridge && gBridge.cut_to_clipboard) {
          gBridge.cut_to_clipboard([item.path]);
        }
        break;
      case 'ctxCopy':
        if (item && item.path && gBridge && gBridge.copy_to_clipboard) {
          gBridge.copy_to_clipboard([item.path]);
        }
        break;
      case 'ctxPaste':
        if (gBridge && gBridge.paste_into_folder_async) {
          const folder = item && item.is_folder ? item.path : (gSelectedFolders.length > 0 ? gSelectedFolders[0] : '');
          setGlobalLoading(true, 'Pasting…', 25);
          if (folder) gBridge.paste_into_folder_async(folder);
        }
        break;
      case 'ctxNewFolder':
        const name = prompt('New Folder Name:');
        if (name && gBridge && gBridge.create_folder && gSelectedFolders.length > 0) {
          const folder = gSelectedFolders[0];
          gBridge.create_folder(folder, name, (res) => { if (res) refreshFromBridge(gBridge); });
        }
        break;
      case 'ctxSelectAll':
        selectAll();
        break;
      case 'ctxSelectNone':
        deselectAll();
        syncMetadataToBridge();
        break;
      case 'ctxCollapseAll':
        setAllGroupsCollapsed(true);
        break;
      case 'ctxExpandAll':
        setAllGroupsCollapsed(false);
        break;
    }
    hideCtx();
  });
}

// applySearch is no longer used for local filtering.

function renderMediaList(items, scrollToTop = true) {
  const el = document.getElementById('mediaList');
  if (!el) return;
  applyGalleryViewMode(gGalleryViewMode);

  el.innerHTML = '';
  const main = document.querySelector('main');
  if (scrollToTop && main) {
    main.scrollTop = 0;
  }
  gMedia = Array.isArray(items) ? items : [];
  gMedia.forEach((item, idx) => { item.__galleryIndex = idx; });
  const viewItems = gMedia;

  resetMediaState();
  ensureMediaObserver();

  // Cancel any previous background idle drain
  if (gBackgroundIdleId) {
    if (typeof cancelIdleCallback !== 'undefined') cancelIdleCallback(gBackgroundIdleId);
    else clearTimeout(gBackgroundIdleId);
    gBackgroundIdleId = null;
  }
  gBackgroundQueue = [];

  gTotalOnPage = 0;
  gLoadedOnPage = 0;
  if (!items || items.length === 0) {
    const div = document.createElement('div');
    div.className = 'empty';
    div.textContent = 'No media discovered yet.';
    el.appendChild(div);
    renderTimelineRail([]);
    return;
  }

  if (viewItems.length === 0) {
    const div = document.createElement('div');
    div.className = 'empty';
    div.textContent = 'No results.';
    el.appendChild(div);
    renderTimelineRail([]);
    return;
  }

  if (gGroupBy === 'date') {
    renderGroupedMediaList(el, viewItems);
    return;
  }

  if (gGalleryViewMode !== 'masonry') {
    renderStructuredMediaList(el, viewItems);
    renderTimelineRail([]);
    return;
  }

  viewItems.forEach((item, idx) => {
    el.appendChild(createMasonryCard(item, idx));
  });

  // After building all cards, queue the items NOT yet visible into the
  // background idle-time loader. The IntersectionObserver will handle them
  // first if the user scrolls near them; the background queue will handle
  // anything that hasn't been touched yet once the browser is idle.
  requestAnimationFrame(() => {
    const unobserved = el.querySelectorAll('img[data-src]:not([src]), img[data-video-path]:not([src])');
    unobserved.forEach(img => {
      if (gPosterRequested.has(img)) return;
      const imgSrc = img.getAttribute('data-src');
      const path = img.getAttribute('data-video-path');
      const item = gMedia.find(m => m.path === path || m.url === imgSrc); // Find the original item to get width/height
      if (imgSrc) {
        gBackgroundQueue.push({ type: 'image', el: img, imgSrc });
      } else if (path && item) {
        gBackgroundQueue.push({ type: 'video', el: img, path, width: item.width, height: item.height });
      }
    });
    scheduleBackgroundDrain();
  });
  renderTimelineRail([]);
}



// (Variable declarations moved to the top of the file)

document.addEventListener('DOMContentLoaded', () => {
  // Global error handler to route JS errors to the terminal diagnostics
  window.onerror = function (msg, url, line, col, error) {
    if (gBridge && gBridge.debug_log) {
      gBridge.debug_log(`JS ERROR: ${msg} [at ${url}:${line}:${col}]`);
    } else {
      console.error('JS ERROR:', msg, url, line, col, error);
    }
  };

  // Hook up custom dropdowns
  function setupCustomSelect(id, onChange) {
    const el = document.getElementById(id);
    if (!el) return;
    const trigger = el.querySelector('.select-trigger');
    const options = el.querySelector('.select-options');

    // Toggle open
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      // Close others
      document.querySelectorAll('.custom-select').forEach(s => {
        if (s !== el) s.classList.remove('open');
      });
      el.classList.toggle('open');
    });

    // Handle option click
    options.addEventListener('click', (e) => {
      e.stopPropagation();
      const opt = e.target.closest('[data-value]');
      if (!opt) return;

      const val = opt.getAttribute('data-value');
      const text = opt.textContent;

      // Update UI
      trigger.textContent = text;
      el.querySelectorAll('.selected').forEach(s => s.classList.remove('selected'));
      opt.classList.add('selected');
      el.classList.remove('open');

      // Callback
      onChange(val);
    });
  }

  // Close on outside click and handle global deselection
  document.addEventListener('click', (e) => {
    document.querySelectorAll('.custom-select').forEach(s => s.classList.remove('open'));

    // If we clicked something that is NOT a card or a descendant of a card,
    // and not a menu item or other interactive element that should keep selection,
    // and not within the right side panels (metadata/bulk tag editor).
    if (!e.target.closest('.card') &&
      !e.target.closest('.ctx') &&
      !e.target.closest('.select-trigger') &&
      !e.target.closest('.select-options') &&
      !e.target.closest('.pane-right')) {
      deselectAll();
    }
  });
  window.addEventListener('pointerup', () => {
    gTimelineScrubActive = false;
    gTimelineScrubPointerId = null;
  });
  window.addEventListener('pointermove', (e) => {
    if (!gTimelineScrubActive) return;
    if (gTimelineScrubPointerId !== null && e.pointerId !== gTimelineScrubPointerId) return;
    scrubTimelineAt(e.clientY);
  });

  setupCustomSelect('sortSelect', (val) => {
    gSort = val;
    if (gBridge) refreshFromBridge(gBridge, true);
  });

  setupCustomSelect('filterSelect', (val) => {
    gFilter = val;
    gPage = 0; // Reset page on filter change
    if (gBridge) refreshFromBridge(gBridge, true);
  });

  setupCustomSelect('groupBySelect', (val) => {
    gGroupBy = val === 'date' ? 'date' : 'none';
    syncGroupByUi();
    if (gBridge && gBridge.set_setting_str) {
      gBridge.set_setting_str('gallery.group_by', gGroupBy, function () {
        refreshFromBridge(gBridge, true);
      });
    } else if (gBridge) {
      refreshFromBridge(gBridge, true);
    }
  });

  setupCustomSelect('dateGranularitySelect', (val) => {
    gGroupDateGranularity = ['day', 'month', 'year'].includes(val) ? val : 'day';
    if (gBridge && gBridge.set_setting_str) {
      gBridge.set_setting_str('gallery.group_date_granularity', gGroupDateGranularity, function () {
        refreshFromBridge(gBridge, true);
      });
    } else if (gBridge) {
      refreshFromBridge(gBridge, true);
    }
  });
});

// Lazy poster loading for videos

let gIndex = -1;
let gLightboxNativeVideo = false;

function findNearestMediaIndex(idx, direction = 1) {
  if (!Array.isArray(gMedia) || gMedia.length === 0) return -1;
  let cursor = Math.max(0, Math.min(idx, gMedia.length - 1));
  while (cursor >= 0 && cursor < gMedia.length) {
    if (gMedia[cursor] && !gMedia[cursor].is_folder) return cursor;
    cursor += direction >= 0 ? 1 : -1;
  }
  return -1;
}

function openLightboxByIndex(idx) {
  const lb = document.getElementById('lightbox');
  const img = document.getElementById('lightboxImg');
  const vid = document.getElementById('lightboxVideo');
  if (!lb || !img || !vid) return;

  document.body.classList.add('lightbox-open');

  // Stop native overlay ONLY if it was previously opened for a video.
  if (gLightboxNativeVideo && gBridge && gBridge.close_native_video) {
    gBridge.close_native_video(function () { });
  }
  gLightboxNativeVideo = false;

  // Also cleanup any in-place playback
  if (gPlayingInplaceCard) {
    gPlayingInplaceCard.classList.remove('playing-inplace');
    gPlayingInplaceCard.removeAttribute('data-paused');
    gPlayingInplaceCard = null;
    // (close_native_video already called above if gLightboxNativeVideo was true, 
    // but in-place doesn't set that flag. So we call it if not already called.)
    if (!gLightboxNativeVideo && gBridge && gBridge.close_native_video) {
      gBridge.close_native_video(function () { });
    }
  }

  if (!gMedia || gMedia.length === 0) return;
  if (idx < 0) idx = 0;
  if (idx >= gMedia.length) idx = gMedia.length - 1;
  idx = findNearestMediaIndex(idx, 1);
  if (idx < 0) return;

  gIndex = idx;

  const item = gMedia[gIndex];
  if (item.media_type === 'video') {
    // Open web lightbox chrome, but delegate actual video rendering to native overlay.
    // (QtWebEngine codec support is unreliable on Windows.)
    const lb = document.getElementById('lightbox');
    const imgEl = document.getElementById('lightboxImg');
    const vidEl = document.getElementById('lightboxVideo');
    if (lb) lb.hidden = false;
    if (imgEl) {
      imgEl.style.display = 'none';
      imgEl.src = '';
    }
    if (vidEl) {
      vidEl.style.display = 'none';
      vidEl.src = '';
    }
    document.body.style.overflow = 'hidden';

    if (gBridge && gBridge.open_native_video && item.path) {
      gLightboxNativeVideo = true;
      const lbClose = document.getElementById('lbClose');
      const lbPrev = document.getElementById('lbPrev');
      const lbNext = document.getElementById('lbNext');
      if (lbClose) lbClose.hidden = true; // Hide web buttons so only native shows
      if (lbPrev) lbPrev.hidden = true;
      if (lbNext) lbNext.hidden = true;
      gBridge.get_video_duration_seconds(item.path, function (dur) {
        const seconds = Number(dur || 0);
        const loop = seconds > 0 && seconds < 60;
        // Always autoplay, always muted, loop only if short
        gBridge.open_native_video(item.path, true, loop, true, item.width || 0, item.height || 0);
      });
    }
    return;
  } else {
    vid.pause();
    vid.style.display = 'none';
    vid.src = '';
    img.style.display = 'block';
    img.src = item.url;

    const lbClose = document.getElementById('lbClose');
    const lbPrev = document.getElementById('lbPrev');
    const lbNext = document.getElementById('lbNext');
    if (lbClose) lbClose.hidden = false;
    if (lbPrev) lbPrev.hidden = false;
    if (lbNext) lbNext.hidden = false;
  }

  lb.hidden = false;

  // prevent background scroll while open
  document.body.style.overflow = 'hidden';
}



let gClosingFromNative = false;

function closeLightbox() {
  const lb = document.getElementById('lightbox');
  const img = document.getElementById('lightboxImg');
  const vid = document.getElementById('lightboxVideo');
  if (!lb || !img || !vid) return;
  lb.hidden = true;
  document.body.classList.remove('lightbox-open');

  const lbClose = document.getElementById('lbClose');
  const lbPrev = document.getElementById('lbPrev');
  const lbNext = document.getElementById('lbNext');
  if (lbClose) lbClose.hidden = false;
  if (lbPrev) lbPrev.hidden = false;
  if (lbNext) lbNext.hidden = false;

  img.src = '';
  img.style.display = 'block';

  vid.pause();
  vid.src = '';
  vid.style.display = 'none';


  if (!gClosingFromNative && gBridge && gBridge.close_native_video) {
    gBridge.close_native_video(function () { });
  }

  gIndex = -1;
  document.body.style.overflow = '';
}

// Called from native when the native overlay closes.
window.__mmx_closeLightboxFromNative = function () {
  gClosingFromNative = true;
  try {
    closeLightbox();
  } finally {
    gClosingFromNative = false;
  }

  if (gPlayingInplaceCard) {
    gPlayingInplaceCard.classList.remove('playing-inplace', 'playing-inprogress', 'playing-confirmed');
    gPlayingInplaceCard.removeAttribute('data-paused');
    gPlayingInplaceCard = null;
  }
};

function lightboxPrev() {
  if (gIndex <= 0) return;
  const prevIndex = findNearestMediaIndex(gIndex - 1, -1);
  if (prevIndex >= 0) openLightboxByIndex(prevIndex);
}
window.lightboxPrev = lightboxPrev;

function lightboxNext() {
  if (gMedia && gIndex >= 0 && gIndex < gMedia.length - 1) {
    const nextIndex = findNearestMediaIndex(gIndex + 1, 1);
    if (nextIndex >= 0) openLightboxByIndex(nextIndex);
  }
}
window.lightboxNext = lightboxNext;

function wireLightbox() {
  const lb = document.getElementById('lightbox');
  const backdrop = document.getElementById('lightboxBackdrop');
  const img = document.getElementById('lightboxImg');
  const vid = document.getElementById('lightboxVideo');

  // Click anywhere on the lightbox area (including background or media) closes it,
  // EXCEPT when clicking specifically on navigation/UI buttons.
  if (lb) {
    lb.addEventListener('click', (e) => {
      // If the target is a navigation button or a UI control, don't close.
      // We check for "lb-btn" class or if it's inside the lightbox-ui.
      if (e.target.closest('.lb-btn')) {
        return;
      }
      closeLightbox();
    });
  }

  // Right-click anywhere on the lightbox (including the image) opens the same context menu.
  // Use capture to avoid any odd event swallowing.
  const handler = (e) => {
    if (!gMedia || gIndex < 0 || gIndex >= gMedia.length) return;
    e.preventDefault();
    e.stopPropagation();
    showCtx(e.clientX, e.clientY, gMedia[gIndex], gIndex, true);
  };

  if (lb) lb.addEventListener('contextmenu', handler, true);
  if (img) img.addEventListener('contextmenu', handler, true);
  if (vid) vid.addEventListener('contextmenu', handler, true);

  const btnPrev = document.getElementById('lbPrev');
  const btnNext = document.getElementById('lbNext');
  const btnClose = document.getElementById('lbClose');
  if (btnPrev) btnPrev.addEventListener('click', lightboxPrev);
  if (btnNext) btnNext.addEventListener('click', lightboxNext);
  if (btnClose) btnClose.addEventListener('click', closeLightbox);

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowLeft') lightboxPrev();
    if (e.key === 'ArrowRight') lightboxNext();
  });
}

function totalPages() {
  return Math.max(1, Math.ceil((gTotal || 0) / PAGE_SIZE));
}

function pagerPagesToShow() {
  const tp = totalPages();
  const cur = gPage + 1; // 1-based
  const set = new Set([1, tp, cur]);
  if (cur - 1 >= 1) set.add(cur - 1);
  if (cur + 1 <= tp) set.add(cur + 1);
  return Array.from(set).sort((a, b) => a - b);
}

function renderPager() {
  const tp = totalPages();
  const cur = gPage + 1;

  const pages = pagerPagesToShow();

  document.querySelectorAll('[data-pager]').forEach((root) => {
    const prev = root.querySelector('[data-prev]');
    const next = root.querySelector('[data-next]');
    const links = root.querySelector('[data-links]');

    if (prev) prev.disabled = gPage === 0;
    if (next) next.disabled = cur >= tp;

    if (!links) return;
    links.innerHTML = '';

    let last = 0;
    for (const p of pages) {
      if (last && p > last + 1) {
        const ell = document.createElement('span');
        ell.className = 'tb-ellipsis';
        ell.textContent = '…';
        links.appendChild(ell);
      }

      const btn = document.createElement('button');
      btn.className = 'tb-page';
      btn.textContent = String(p);
      if (p === cur) btn.setAttribute('aria-current', 'page');
      btn.addEventListener('click', () => {
        gPage = p - 1;
        refreshFromBridge(gBridge);
      });
      links.appendChild(btn);

      last = p;
    }
  });
}

function refreshFromBridge(bridge, resetPage = false) {
  if (!bridge) return;
  bridge.get_selected_folders(function (folders) {
    gSelectedFolders = folders || [];
    bridge.get_active_collection(function (activeCollection) {
      gActiveCollection = activeCollection && activeCollection.id ? activeCollection : null;
      setSelectedFolder(gSelectedFolders, gActiveCollection);

      if (gSelectedFolders.length === 0 && !gActiveCollection) {
        gTotal = 0;
        setGlobalLoading(false);
        renderMediaList([]);
        renderPager();
        return;
      }

      if (resetPage) {
        gPage = 0;
      }

    // ── 1. Fast Path Reconcile (Hybrid Load) ─────────────────────────────
    // This loads the synthesized candidates from disk + DB without waiting for scan.
      bridge.count_media(gSelectedFolders, gFilter, gSearchQuery || '', function (count) {
        gTotal = count || 0;
        bridge.list_media(gSelectedFolders, PAGE_SIZE, gPage * PAGE_SIZE, gSort, gFilter, gSearchQuery || '', function (items) {
          renderMediaList(items, true);
          renderPager();
          // Hide the "Starting..." or "Loading..." overlay once we have the first batch of results.
          setGlobalLoading(false);
          if (bridge.start_scan_paths) {
            bridge.start_scan_paths((items || []).filter(item => !item.is_folder).map(item => item.path).filter(Boolean));
          }
        });
      });

    // ── 2. Background Enrichment Scan ────────────────────────────────────
    // This fills in hashes and metadata in the DB.
    if (gSelectedFolders.length > 0) {
      bridge.start_scan(gSelectedFolders, gSearchQuery || '');
    }
    });
  });
}

function nextPage() {
  if (!gBridge) return;
  const tp = totalPages();
  gPage = Math.min(tp - 1, gPage + 1);
  refreshFromBridge(gBridge);
}

function prevPage() {
  if (!gBridge) return;
  gPage = Math.max(0, gPage - 1);
  refreshFromBridge(gBridge);
}

function wirePager() {
  document.querySelectorAll('[data-pager]').forEach((root) => {
    const prev = root.querySelector('[data-prev]');
    const next = root.querySelector('[data-next]');
    if (prev) prev.addEventListener('click', prevPage);
    if (next) next.addEventListener('click', nextPage);
  });

  const scrollBtn = document.getElementById('scrollTop');
  if (scrollBtn) {
    scrollBtn.addEventListener('click', () => {
      const main = document.querySelector('main');
      if (main) main.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  const scrollBottomBtn = document.getElementById('scrollBottom');
  if (scrollBottomBtn) {
    scrollBottomBtn.addEventListener('click', () => {
      const main = document.querySelector('main');
      if (main) {
        main.scrollTo({
          top: main.scrollHeight,
          behavior: 'smooth'
        });
      }
    });
  }

  renderPager();
}

function openSettings() {
  const m = document.getElementById('settingsModal');
  if (m) m.hidden = false;
}

// Called from native menu
window.__mmx_openSettings = openSettings;

function closeSettings() {
  const m = document.getElementById('settingsModal');
  if (m) m.hidden = true;
}

function syncStartFolderEnabled() {
  const restoreToggle = document.getElementById('toggleRestoreLast');
  const startInput = document.getElementById('startFolder');
  const browse = document.getElementById('browseStartFolder');
  const on = !!(restoreToggle && restoreToggle.checked);
  if (startInput) startInput.disabled = on;
  if (browse) browse.disabled = on;
}

function wireSettings() {
  const openBtn = document.getElementById('openSettings');
  const closeBtn = document.getElementById('closeSettings');
  const browse = document.getElementById('browseStartFolder');
  const backdrop = document.getElementById('settingsBackdrop');
  const toggle = document.getElementById('toggleRandomize');
  const glassToggle = document.getElementById('toggleGlass');

  // Pane switching logic
  const navItems = document.querySelectorAll('.settings-nav-item');
  const panes = document.querySelectorAll('.settings-pane');
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const targetPane = item.getAttribute('data-pane');
      navItems.forEach(i => i.classList.toggle('active', i === item));
      panes.forEach(p => {
        p.hidden = p.id !== `pane-${targetPane}`;
      });
    });
  });

  if (glassToggle) {
    glassToggle.addEventListener('change', () => {
      if (!gBridge || !gBridge.set_setting_bool) return;
      document.body.classList.toggle('no-glass', !glassToggle.checked);
      gBridge.set_setting_bool('ui.enable_glassmorphism', glassToggle.checked, function () { });
    });
  }

  if (openBtn) openBtn.addEventListener('click', openSettings);
  if (closeBtn) closeBtn.addEventListener('click', closeSettings);
  if (backdrop) backdrop.addEventListener('click', closeSettings);

  const startInput = document.getElementById('startFolder');
  const restoreToggle = document.getElementById('toggleRestoreLast');
  const toggleShowHidden = document.getElementById('toggleShowHidden');
  const accentInput = document.getElementById('accentColor');

  if (browse) {
    browse.addEventListener('click', () => {
      if (!gBridge || !gBridge.pick_folder) return;
      gBridge.pick_folder(function (path) {
        if (!path) return;
        if (startInput) startInput.value = path;
        if (gBridge.set_setting_str) {
          gBridge.set_setting_str('gallery.start_folder', path, function () { });
        }
      });
    });
  }

  const loadNowBtn = document.getElementById('loadStartFolderNow');
  if (loadNowBtn) {
    loadNowBtn.addEventListener('click', () => {
      if (!gBridge || !gBridge.load_folder_now) return;
      if (startInput) {
        const path = startInput.value;
        if (path) gBridge.load_folder_now(path);
      }
    });
  }

  if (startInput) {
    startInput.addEventListener('change', () => {
      if (!gBridge || !gBridge.set_setting_str) return;
      gBridge.set_setting_str('gallery.start_folder', startInput.value || '', function () { });
    });
  }
  if (restoreToggle) {
    restoreToggle.addEventListener('change', () => {
      if (!gBridge || !gBridge.set_setting_bool) return;
      gBridge.set_setting_bool('gallery.restore_last', !!restoreToggle.checked, function () {
        syncStartFolderEnabled();
      });
    });
  }

  if (toggleShowHidden) {
    toggleShowHidden.addEventListener('change', () => {
      if (!gBridge || !gBridge.set_setting_bool) return;
      gBridge.set_setting_bool('gallery.show_hidden', !!toggleShowHidden.checked, function () {
        gPage = 0;
        refreshFromBridge(gBridge);
      });
    });
  }

  const autoUpdateToggle = document.getElementById('toggleAutoUpdate');
  if (autoUpdateToggle) {
    autoUpdateToggle.addEventListener('change', () => {
      if (!gBridge || !gBridge.set_setting_bool) return;
      gBridge.set_setting_bool('updates.check_on_launch', !!autoUpdateToggle.checked, function () { });
    });
  }

  const btnCheckUpdate = document.getElementById('btnCheckUpdate');
  if (btnCheckUpdate) {
    btnCheckUpdate.addEventListener('click', () => {
      if (!gBridge || !gBridge.check_for_updates) return;
      const statusText = document.getElementById('updateStatusText');
      if (statusText) statusText.textContent = 'Checking...';
      gBridge.check_for_updates(true); // manual=true
    });
  }

  if (accentInput) {
    accentInput.addEventListener('input', () => {
      const v = accentInput.value || '#8ab4f8';
      document.documentElement.style.setProperty('--accent', v);
      if (gBridge && gBridge.set_setting_str) {
        gBridge.set_setting_str('ui.accent_color', v, function () { });
      }
    });
  }

  if (toggle) {
    toggle.addEventListener('change', () => {
      if (!gBridge || !gBridge.set_setting_bool) return;
      gBridge.set_setting_bool('gallery.randomize', !!toggle.checked, function () {
        gPage = 0;
        refreshFromBridge(gBridge);
      });
    });
  }

  document.querySelectorAll('input[name="theme_mode"]').forEach(radio => {
    radio.addEventListener('change', () => {
      if (!gBridge || !gBridge.set_setting_str) return;
      const theme = radio.value;
      document.documentElement.classList.toggle('light-mode', theme === 'light');
      updateThemeAwareIcons(theme);
      gBridge.set_setting_str('ui.theme_mode', theme, function () { });
    });
  });

  wireMetadataSettings();
}

function metadataConfigFor(mode) {
  return METADATA_SETTINGS_CONFIG[mode] || METADATA_SETTINGS_CONFIG.image;
}

function metadataGroupOrderKey(mode) {
  return `metadata.layout.${mode}.group_order`;
}

function metadataFieldOrderKey(mode, groupKey) {
  return `metadata.layout.${mode}.field_order.${groupKey}`;
}

function metadataGroupEnabledKey(mode, groupKey) {
  return `metadata.display.${mode}.groups.${groupKey}`;
}

function metadataGroupCollapsedKey(mode, groupKey) {
  return `metadata.display.${mode}.groupcollapsed.${groupKey}`;
}

function metadataFieldEnabledKey(mode, fieldKey) {
  return `metadata.display.${mode}.${fieldKey}`;
}

function getMetadataGroupOrder(settings, mode) {
  const cfg = metadataConfigFor(mode);
  const raw = settings && settings[metadataGroupOrderKey(mode)];
  let order = [];
  try { order = raw ? JSON.parse(raw) : []; } catch (e) { order = []; }
  if (!Array.isArray(order)) order = [];
  cfg.groupOrder.forEach(key => { if (!order.includes(key)) order.push(key); });
  return order.filter(key => cfg.groups[key]);
}

function getMetadataFieldOrder(settings, mode, groupKey) {
  const cfg = metadataConfigFor(mode);
  const defaults = cfg.groups[groupKey].fields.map(([key]) => key);
  const raw = settings && settings[metadataFieldOrderKey(mode, groupKey)];
  let order = [];
  try { order = raw ? JSON.parse(raw) : []; } catch (e) { order = []; }
  if (!Array.isArray(order)) order = [];
  defaults.forEach(key => { if (!order.includes(key)) order.push(key); });
  return order.filter(key => defaults.includes(key));
}

function renderMetadataSettings(settings) {
  const mount = document.getElementById('metadataSettingsMount');
  if (!mount) return;
  const cfg = metadataConfigFor(gActiveMetadataMode);
  const groupOrder = getMetadataGroupOrder(settings, gActiveMetadataMode);
  mount.innerHTML = '';

  groupOrder.forEach(groupKey => {
    const groupCfg = cfg.groups[groupKey];
    if (!groupCfg) return;
    const section = document.createElement('section');
    section.className = 'metadata-group';
    section.draggable = true;
    section.dataset.groupKey = groupKey;

    const collapsed = !!(settings && settings[metadataGroupCollapsedKey(gActiveMetadataMode, groupKey)]);
    if (collapsed) section.classList.add('collapsed');

    const header = document.createElement('div');
    header.className = 'metadata-group-header';
    header.innerHTML = `
      <div class="drag-handle" title="Drag group">☰</div>
      <label class="toggle">
        <input type="checkbox" class="metadata-group-toggle" ${((settings && settings[metadataGroupEnabledKey(gActiveMetadataMode, groupKey)]) !== false) ? 'checked' : ''} />
        <span class="metadata-group-title">${groupCfg.label}</span>
      </label>
      <button class="collapse-btn" type="button">${collapsed ? '+' : '−'}</button>
    `;
    section.appendChild(header);

    const body = document.createElement('div');
    body.className = 'metadata-group-body';
    body.dataset.groupKey = groupKey;
    const fieldMap = Object.fromEntries(groupCfg.fields.map(field => [field[0], field]));
    getMetadataFieldOrder(settings, gActiveMetadataMode, groupKey).forEach(fieldKey => {
      const fieldCfg = fieldMap[fieldKey];
      if (!fieldCfg) return;
      const [key, label, defaultEnabled] = fieldCfg;
      const row = document.createElement('div');
      row.className = 'sortable-item';
      row.draggable = true;
      row.dataset.key = key;
      row.dataset.groupKey = groupKey;
      const enabled = settings && settings[metadataFieldEnabledKey(gActiveMetadataMode, key)];
      row.innerHTML = `
        <div class="drag-handle" title="Drag field">☰</div>
        <label class="toggle">
          <input type="checkbox" class="metadata-field-toggle" data-field-key="${key}" ${enabled !== undefined ? (enabled ? 'checked' : '') : (defaultEnabled ? 'checked' : '')} />
          <span>${label}</span>
        </label>
      `;
      body.appendChild(row);
    });
    section.appendChild(body);
    mount.appendChild(section);
  });
}

function saveMetadataGroupOrder() {
  const mount = document.getElementById('metadataSettingsMount');
  if (!mount || !gBridge || !gBridge.set_setting_str) return;
  const order = Array.from(mount.querySelectorAll('.metadata-group')).map(el => el.dataset.groupKey);
  gBridge.set_setting_str(metadataGroupOrderKey(gActiveMetadataMode), JSON.stringify(order), () => {});
}

function saveMetadataFieldOrder(groupKey) {
  const body = document.querySelector(`.metadata-group-body[data-group-key="${groupKey}"]`);
  if (!body || !gBridge || !gBridge.set_setting_str) return;
  const order = Array.from(body.querySelectorAll('.sortable-item')).map(el => el.dataset.key);
  gBridge.set_setting_str(metadataFieldOrderKey(gActiveMetadataMode, groupKey), JSON.stringify(order), () => {});
}

function wireMetadataSettings() {
  const mount = document.getElementById('metadataSettingsMount');
  if (!mount) return;

  document.querySelectorAll('input[name="metadata_mode"]').forEach(radio => {
    radio.addEventListener('change', () => {
      if (!radio.checked) return;
      gActiveMetadataMode = radio.value;
      if (gBridge && gBridge.set_setting_str) {
        gBridge.set_setting_str('metadata.layout.active_mode', gActiveMetadataMode, () => {});
      }
      if (gBridge && gBridge.get_settings) {
        gBridge.get_settings(renderMetadataSettings);
      }
    });
  });

  let dragGroup = null;
  let dragField = null;

  mount.addEventListener('change', (e) => {
    const groupToggle = e.target.closest('.metadata-group-toggle');
    if (groupToggle) {
      const section = groupToggle.closest('.metadata-group');
      if (gBridge && gBridge.set_setting_bool && section) {
        gBridge.set_setting_bool(metadataGroupEnabledKey(gActiveMetadataMode, section.dataset.groupKey), !!groupToggle.checked, () => {});
      }
      return;
    }
    const fieldToggle = e.target.closest('.metadata-field-toggle');
    if (fieldToggle && gBridge && gBridge.set_setting_bool) {
      gBridge.set_setting_bool(metadataFieldEnabledKey(gActiveMetadataMode, fieldToggle.dataset.fieldKey), !!fieldToggle.checked, () => {});
    }
  });

  mount.addEventListener('click', (e) => {
    const btn = e.target.closest('.collapse-btn');
    if (!btn) return;
    const section = btn.closest('.metadata-group');
    if (!section) return;
    section.classList.toggle('collapsed');
    btn.textContent = section.classList.contains('collapsed') ? '+' : '−';
    if (gBridge && gBridge.set_setting_bool) {
      gBridge.set_setting_bool(metadataGroupCollapsedKey(gActiveMetadataMode, section.dataset.groupKey), section.classList.contains('collapsed'), () => {});
    }
  });

  mount.addEventListener('dragstart', (e) => {
    const field = e.target.closest('.sortable-item');
    const group = e.target.closest('.metadata-group');
    if (field) {
      dragField = field;
      field.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
      return;
    }
    if (group) {
      dragGroup = group;
      group.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
    }
  });

  mount.addEventListener('dragend', () => {
    if (dragField) {
      const groupKey = dragField.dataset.groupKey;
      dragField.classList.remove('dragging');
      dragField = null;
      saveMetadataFieldOrder(groupKey);
    }
    if (dragGroup) {
      dragGroup.classList.remove('dragging');
      dragGroup = null;
      saveMetadataGroupOrder();
    }
    mount.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
  });

  mount.addEventListener('dragover', (e) => {
    e.preventDefault();
    if (dragField) {
      const target = e.target.closest('.sortable-item');
      if (target && target !== dragField && target.dataset.groupKey === dragField.dataset.groupKey) {
        target.classList.add('drag-over');
      }
      return;
    }
    if (dragGroup) {
      const target = e.target.closest('.metadata-group');
      if (target && target !== dragGroup) {
        target.classList.add('drag-over');
      }
    }
  });

  mount.addEventListener('dragleave', (e) => {
    const target = e.target.closest('.drag-over');
    if (target) target.classList.remove('drag-over');
  });

  mount.addEventListener('drop', (e) => {
    e.preventDefault();
    if (dragField) {
      const target = e.target.closest('.sortable-item');
      if (target && target !== dragField && target.dataset.groupKey === dragField.dataset.groupKey) {
        const rect = target.getBoundingClientRect();
        const next = (e.clientY - rect.top) > (rect.height / 2);
        target.parentElement.insertBefore(dragField, next ? target.nextSibling : target);
      }
      return;
    }
    if (dragGroup) {
      const target = e.target.closest('.metadata-group');
      if (target && target !== dragGroup) {
        const rect = target.getBoundingClientRect();
        const next = (e.clientY - rect.top) > (rect.height / 2);
        mount.insertBefore(dragGroup, next ? target.nextSibling : target);
      }
    }
  });
}

function updateThemeAwareIcons(theme) {
  const isLight = theme === 'light';
  const suffix = isLight ? '-black' : '';

  // Update Logo
  const logo = document.getElementById('mainLogo');
  if (logo) {
    logo.src = `media-manager-logo-64${suffix}.png`;
  }

  // Update Sidebar Icons
  ['Left', 'Right'].forEach(side => {
    const icon = document.getElementById('icon' + side + 'Panel');
    if (icon) {
      const isOpened = icon.src.includes('opened');
      const sideKey = side.toLowerCase();
      const state = isOpened ? 'opened' : 'closed';
      icon.src = `${sideKey}-sidebar-${state}${suffix}.png`;
    }
  });
}

function updateSidebarButtonIcons(side, visible) {
  const icon = document.getElementById('icon' + (side === 'left' ? 'Left' : 'Right') + 'Panel');
  if (!icon) return;
  const isLight = document.documentElement.classList.contains('light-mode');
  const suffix = isLight ? '-black' : '';
  const state = visible ? 'opened' : 'closed';
  icon.src = `${side}-sidebar-${state}${suffix}.png`;
}

function wireSidebarToggles() {
  const btnLeft = document.getElementById('toggleLeftPanel');
  const btnRight = document.getElementById('toggleRightPanel');

  if (btnLeft) {
    btnLeft.addEventListener('click', () => {
      if (!gBridge || !gBridge.get_settings) return;
      gBridge.get_settings(function (s) {
        const cur = !!(s && s['ui.show_left_panel']);
        gBridge.set_setting_bool('ui.show_left_panel', !cur);
      });
    });
  }

  if (btnRight) {
    btnRight.addEventListener('click', () => {
      if (!gBridge || !gBridge.get_settings) return;
      gBridge.get_settings(function (s) {
        const cur = !!(s && s['ui.show_right_panel']);
        gBridge.set_setting_bool('ui.show_right_panel', !cur);
      });
    });
  }
}

function wireSearch() {
  const inp = document.getElementById('searchInput');
  if (!inp) return;

  inp.addEventListener('input', () => {
    gSearchQuery = inp.value || '';
    gPage = 0; // Reset to page 1 on search
    refreshFromBridge(gBridge);
  });
}

function wireGalleryBackground() {
  const main = document.querySelector('main');
  if (!main) return;

  main.addEventListener('click', (e) => {
    // If we click the background (anything not a card or inside a card)
    if (!e.target.closest('.card')) {
      deselectAll();
      syncMetadataToBridge();
    }
  });

  main.addEventListener('contextmenu', (e) => {
    // If we right-click the background
    if (!e.target.closest('.card')) {
      e.preventDefault();
      showCtx(e.clientX, e.clientY, null, -1, false);
    }
  });

  main.addEventListener('scroll', () => {
    if (gPlayingInplaceCard && gBridge && gBridge.update_native_video_rect) {
      const target = gPlayingInplaceCard.querySelector('.structured-thumb') || gPlayingInplaceCard;
      const rect = target.getBoundingClientRect();
      // If it scrolls off-screen, we might want to stop it, 
      // but let's first try just moving it.
      gBridge.update_native_video_rect(rect.x, rect.y, rect.width, rect.height);
    }
  });
}

window.addEventListener('resize', () => {
  const mediaList = document.getElementById('mediaList');
  if (mediaList && mediaList.classList.contains('gallery-details')) {
    applyDetailsColumnWidths(mediaList);
  }
});

async function main() {
  wirePager();
  wireSettings();
  wireSearch();
  wireSidebarToggles();


  // Show immediately on first paint (prevents "nothing then overlay" behavior)
  setGlobalLoading(true, 'Starting…', 10);
  setStatus('Loading bridge…');

  if (!window.qt || !window.qt.webChannelTransport) {
    setStatus('No Qt bridge (running in a normal browser?)');
    return;
  }

  // Expose a bridge object from Qt.
  new QWebChannel(window.qt.webChannelTransport, function (channel) {
    const bridge = channel.objects.bridge;
    if (!bridge) {
      setStatus('Bridge missing');
      return;
    }

    gBridge = bridge;
    if (gBridge && gBridge.debug_log) {
      gBridge.debug_log('Bridge Connected: QWebChannel is alive');
      console.log('Bridge Connected');
    }

    wireLightbox();
    wireCtxMenu();
    wireGalleryBackground();

    if (bridge.dragOverFolder) {
      bridge.dragOverFolder.connect(function (folderName) {
        gCurrentTargetFolderName = folderName || '';
      });
    }

    if (bridge.updateAvailable) {
      bridge.updateAvailable.connect(function (newVer, manual) {
        const toast = document.getElementById('updateToast');
        const label = document.getElementById('updateToastLabel');
        const text = document.getElementById('updateToastText');
        const actions = document.getElementById('updateToastActions');
        const statusText = document.getElementById('updateStatusText');

        if (newVer) {
          if (statusText) statusText.textContent = `Version ${newVer} available!`;
          if (label) label.textContent = 'Update Available!';
          if (text) text.textContent = `Version ${newVer} is available!`;
          if (actions) actions.style.display = 'flex';
          if (toast) {
            toast.classList.remove('info-only');
            toast.hidden = false;
          }
        } else if (manual) {
          if (statusText) statusText.textContent = 'You are using the latest version.';
          if (label) label.textContent = 'Up to Date';
          
          if (bridge.get_app_version) {
              bridge.get_app_version(function(v) {
                  if (text) text.textContent = `Version ${v} is the newest.`;
              });
          } else {
              if (text) text.textContent = 'You are using the newest version.';
          }
          
          if (actions) actions.style.display = 'none';
          if (toast) {
            toast.classList.add('info-only');
            toast.hidden = false;
            // Auto-hide after 5 seconds if it's just an info toast
            if (gUpdateToastTimer) clearTimeout(gUpdateToastTimer);
            gUpdateToastTimer = setTimeout(() => { toast.hidden = true; }, 5000);
          }
        }
      });
    }

    const btnUpdateNow = document.getElementById('btnUpdateNow');
    if (btnUpdateNow) {
      btnUpdateNow.addEventListener('click', () => {
        if (!gBridge || !gBridge.download_and_install_update) return;
        setGlobalLoading(true, 'Downloading update...', 0);
        const toast = document.getElementById('updateToast');
        if (toast) toast.hidden = true;
        gBridge.download_and_install_update();
      });
    }

    // Dismiss toast on click if it's info only
    const toast = document.getElementById('updateToast');
    if (toast) {
      toast.addEventListener('click', () => {
        if (toast.classList.contains('info-only')) {
           toast.hidden = true;
           if (gUpdateToastTimer) clearTimeout(gUpdateToastTimer);
        }
      });
    }

    const btnUpdateLater = document.getElementById('btnUpdateLater');
    if (btnUpdateLater) {
      btnUpdateLater.addEventListener('click', () => {
        const toast = document.getElementById('updateToast');
        if (toast) toast.hidden = true;
      });
    }

    if (bridge.updateDownloadProgress) {
      bridge.updateDownloadProgress.connect(function (pct) {
        // Hide the update toast as soon as we start seeing download progress
        const toast = document.getElementById('updateToast');
        if (toast) toast.hidden = true;
        
        setGlobalLoading(true, 'Downloading update...', pct);
      });
    }

    if (bridge.updateError) {
      bridge.updateError.connect(function (msg) {
        setGlobalLoading(false);
        const st = document.getElementById('updateStatusText');
        if (st) st.textContent = 'Update error: ' + msg;
        alert('Update error: ' + msg);
      });
    }



    if (bridge.fileOpFinished) {
      bridge.fileOpFinished.connect(function (op, ok, oldPath, newPath) {
        setGlobalLoading(false);
        if (!ok) return;

        if (op === 'rename' && oldPath && newPath) {
          // ── In-place patch: update the card's data-path without reordering the gallery ──
          const oldCard = document.querySelector(`.card[data-path="${CSS.escape(oldPath)}"]`);
          if (oldCard) {
            oldCard.setAttribute('data-path', newPath);
            // Keep gLockedCard reference valid
            if (gLockedCard === oldCard) {
              // card element is the same object, no change needed
            }
          }
          // Patch gMedia in-place so card click closures (which capture 'item' by reference)
          // see the updated path immediately — Object.assign would create a new object and break closures.
          for (let i = 0; i < gMedia.length; i++) {
            if (gMedia[i].path === oldPath) {
              gMedia[i].path = newPath;
              break;
            }
          }
          // No full refresh needed — gallery order is preserved
          return;
        }

        // For all other ops (delete, hide, unhide, move, etc.) do a full refresh
        refreshFromBridge(bridge, false);
      });
    }

    if (bridge.scanStarted) {
      bridge.scanStarted.connect(function (folder) {
        // Silent background scan now, non-blocking
      });
    }

    if (bridge.scanFinished) {
      bridge.scanFinished.connect(function (folder, count) {
        gTotal = count || 0;
        const tp = totalPages();
        if (gPage >= tp) gPage = Math.max(0, tp - 1);

        // Silent background refresh to pick up new metadata without blocking
        bridge.list_media(gSelectedFolders, PAGE_SIZE, gPage * PAGE_SIZE, gSort, gFilter, gSearchQuery || '', function (items) {
          renderMediaList(items, false);
          renderPager();
        });
      });
    }

    wireScanIndicator();

    bridge.get_tools_status(function (st) {
      // Diagnostic data moved to About popup.
      // Controls are strictly for sort/filter now.
      console.log('tools_status', st);
    });

    bridge.get_settings(function (s) {
      const t = document.getElementById('toggleRandomize');
      if (t) t.checked = !!(s && s['gallery.randomize']);

      const r = document.getElementById('toggleRestoreLast');
      if (r) r.checked = !!(s && s['gallery.restore_last']);
      // keep start folder UI in sync
      syncStartFolderEnabled && syncStartFolderEnabled();

      const hd = document.getElementById('toggleShowHidden');
      if (hd) hd.checked = !!(s && s['gallery.show_hidden']);

      const sf = document.getElementById('startFolder');
      if (sf) sf.value = (s && s['gallery.start_folder']) || '';

      const nextViewMode = (s && s['gallery.view_mode']) || 'masonry';
      const viewModeChanged = nextViewMode !== gGalleryViewMode;
      applyGalleryViewMode(nextViewMode);
      updateCtxViewState();
      gGroupBy = ((s && s['gallery.group_by']) || 'none') === 'date' ? 'date' : 'none';
      gGroupDateGranularity = (s && s['gallery.group_date_granularity']) || 'day';
      setCustomSelectValue('groupBySelect', gGroupBy);
      setCustomSelectValue('dateGranularitySelect', gGroupDateGranularity);
      syncGroupByUi();
      if (viewModeChanged && gBridge) {
        refreshFromBridge(gBridge, false);
      }

      const ac = document.getElementById('accentColor');
      const v = (s && s['ui.accent_color']) || '#8ab4f8';
      document.documentElement.style.setProperty('--accent', v);
      if (ac) ac.value = v;

      const theme = (s && s['ui.theme_mode']) || 'dark';
      document.documentElement.classList.toggle('light-mode', theme === 'light');
      updateThemeAwareIcons(theme);
      const radio = document.getElementById(theme === 'light' ? 'themeLight' : 'themeDark');
      if (radio) radio.checked = true;

      const glass = (s && s['ui.enable_glassmorphism']) !== false; // Default true
      document.body.classList.toggle('no-glass', !glass);
      const gt = document.getElementById('toggleGlass');
      if (gt) gt.checked = glass;

      updateSidebarButtonIcons('left', !!(s && s['ui.show_left_panel']));
      updateSidebarButtonIcons('right', !!(s && s['ui.show_right_panel']));

      const savedMode = (s && s['metadata.layout.active_mode']) || 'image';
      gActiveMetadataMode = ['image', 'video', 'gif'].includes(savedMode) ? savedMode : 'image';
      const modeRadio = document.getElementById(`metadataMode${gActiveMetadataMode.charAt(0).toUpperCase()}${gActiveMetadataMode.slice(1)}`);
      if (modeRadio) modeRadio.checked = true;
      renderMetadataSettings(s || {});

      // Update settings
      const autoUpdate = document.getElementById('toggleAutoUpdate');
      if (autoUpdate) autoUpdate.checked = (s && s['updates.check_on_launch']) !== false;

      // App version text (from bridge or static)
      if (gBridge && gBridge.get_app_version) {
        gBridge.get_app_version(function (v) {
          const el = document.getElementById('currentVersionText');
          if (el) el.textContent = v;
        });
      }

    });
    
    // Fetch external editors
    if (bridge.get_external_editors) {
        bridge.get_external_editors(function(editors) {
            gExternalEditors = editors || {};
        });
    }

    // Initial sync
    refreshFromBridge(bridge);

    // React to future changes
    if (bridge.selectionChanged) {
      bridge.selectionChanged.connect(function (folders) {
        gSelectedFolders = folders || [];
        gPage = 0;
        refreshFromBridge(bridge);
      });
    }

    if (bridge.accentColorChanged) {
      bridge.accentColorChanged.connect(function (v) {
        document.documentElement.style.setProperty('--accent', v);
        const ac = document.getElementById('accentColor');
        if (ac) ac.value = v;
      });
    }

    if (bridge.videoPlaybackStarted) {
      bridge.videoPlaybackStarted.connect(function () {
        if (gPlayingInplaceCard) {
          gPlayingInplaceCard.classList.remove('playing-inprogress');
          gPlayingInplaceCard.classList.add('playing-confirmed');
        }
      });
    }

    if (bridge.videoSuppressed) {
      bridge.videoSuppressed.connect(function (suppressed) {
        if (gPlayingInplaceCard) {
          gPlayingInplaceCard.classList.toggle('suppressed-poster', suppressed);
        }
      });
    }

    if (bridge.uiFlagChanged) {
      bridge.uiFlagChanged.connect(function (key, value) {
        if (key === 'gallery.show_hidden' || key === 'gallery.view_mode' || key === 'gallery.group_by' || key === 'gallery.group_date_granularity') {
          if (key === 'gallery.view_mode' && bridge.get_settings) {
            bridge.get_settings(function (s) {
              applyGalleryViewMode((s && s['gallery.view_mode']) || 'masonry');
              gGroupBy = ((s && s['gallery.group_by']) || 'none') === 'date' ? 'date' : 'none';
              gGroupDateGranularity = (s && s['gallery.group_date_granularity']) || 'day';
              setCustomSelectValue('groupBySelect', gGroupBy);
              setCustomSelectValue('dateGranularitySelect', gGroupDateGranularity);
              syncGroupByUi();
              updateCtxViewState();
              refreshFromBridge(bridge, true);
            });
            return;
          }
          if ((key === 'gallery.group_by' || key === 'gallery.group_date_granularity') && bridge.get_settings) {
            bridge.get_settings(function (s) {
              gGroupBy = ((s && s['gallery.group_by']) || 'none') === 'date' ? 'date' : 'none';
              gGroupDateGranularity = (s && s['gallery.group_date_granularity']) || 'day';
              setCustomSelectValue('groupBySelect', gGroupBy);
              setCustomSelectValue('dateGranularitySelect', gGroupDateGranularity);
              syncGroupByUi();
              refreshFromBridge(bridge, true);
            });
            return;
          }
          refreshFromBridge(bridge, false);
        }
      });
    }
  });
}

main();
