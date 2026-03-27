
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
let gCurrentDropFolderPath = '';
let gCurrentDragPaths = [];
let gCurrentDropFolderCard = null;
let gGalleryDragHandled = false;
let gExternalEditors = {};
let gCurrentDragCount = 0;
let gPlayingInplaceCard = null;
let gActiveMetadataMode = 'image';
let gDuplicateSettingsMode = 'rules';
let gUpdateToastTimer = null;
let gScanManuallyHidden = false;
let gGalleryViewMode = 'masonry';
let gLastStandardViewMode = 'masonry';
let gGroupBy = 'none';
let gGroupDateGranularity = 'day';
let gCollapsedGroupKeys = new Set();
let gTimelineScrubActive = false;
let gTimelineScrubPointerId = null;
let gTimelineHoverActive = false;
let gTimelineScrubRatio = 0;
let gPendingScrollAnchor = null;
let gInfiniteScrollLoading = false;
let gTimelineScrollTargetsFrozen = null;
let gTimelineRefreshTargetsRaf = 0;
let gTimelineLastScrollTop = 0;
let gTimelineLastThumbRatio = 0;
let gTimelineUserScrollActiveUntil = 0;
let gTimelineWheelSessionTimer = 0;
let gTimelineNavigationActiveUntil = 0;
let gTimelineHeaderObserver = null;
let gTimelineVisibleGroupKeys = new Set();
let gTimelineActiveGroupKey = '';
let gDuplicateKeepOverrides = new Map();
let gDuplicateGroupOrder = new Map();
let gScanActive = false;
let gSimilarityThreshold = 'low';
let gShowDismissedProgressToasts = false;
let gTextProcessingDismissed = false;
let gTextProcessingActive = false;
let gTextProcessingStage = '';
let gTextProcessingCurrent = 0;
let gTextProcessingTotal = 0;
let gRenderTextProcessingToast = null;
const TIMELINE_INSET_PX = 20;
const TIMELINE_THUMB_SIZE_PX = 14;
const TIMELINE_TOP_YEAR_TOP_PX = 20;
const TIMELINE_TOP_MONTH_TOP_PX = 35;
const TIMELINE_THUMB_OFFSET_PX = 8;
const TIMELINE_MIN_POINT_GAP_PX = 26;
const TIMELINE_NAV_LANE_PX = 28;
const TIMELINE_VIEWPORT_TOP_MARGIN_PX = -6;
const TIMELINE_VIEWPORT_BOTTOM_MARGIN_PX = 32;
const TIMELINE_MIN_HEIGHT_PX = 140;

const GALLERY_VIEW_MODES = new Set(['masonry', 'grid_small', 'grid_medium', 'grid_large', 'grid_xlarge', 'list', 'content', 'details', 'duplicates', 'similar', 'similar_only']);
const REVIEW_VIEW_MODES = new Set(['duplicates', 'similar', 'similar_only']);
const DETAILS_COLUMN_CONFIG = [
  { key: 'thumb', label: '', min: 72, width: 72, resizable: false },
  { key: 'name', label: 'File Name', min: 25, width: 260, resizable: true },
  { key: 'folder', label: 'Folder', min: 25, width: 280, resizable: true },
  { key: 'type', label: 'Type', min: 25, width: 120, resizable: true },
  { key: 'modified', label: 'Date modified', min: 25, width: 170, resizable: true },
  { key: 'size', label: 'Size', min: 25, width: 110, resizable: true },
];
let gDetailsColumnWidths = Object.fromEntries(DETAILS_COLUMN_CONFIG.map(col => [col.key, col.width]));

function getReviewMode() {
  if (gGalleryViewMode === 'similar_only' || gGroupBy === 'similar_only') return 'similar_only';
  if (gGalleryViewMode === 'similar' || gGroupBy === 'similar') return 'similar';
  if (gGalleryViewMode === 'duplicates' || gGroupBy === 'duplicates') return 'duplicates';
  return '';
}

function isDuplicateModeActive() {
  return !!getReviewMode();
}

function isTextFilterActive() {
  return gFilter === 'text_detected' || gFilter === 'text_more_likely' || gFilter === 'text_verified';
}

const METADATA_SETTINGS_CONFIG = {
  image: {
    groups: {
      general: {
        label: 'General',
        fields: [
          ['res', 'Resolution', true], ['size', 'File Size', true],
          ['exifdatetaken', 'Date Taken', false], ['metadatadate', 'Date Acquired', false],
          ['filecreateddate', 'Date Created', false], ['filemodifieddate', 'Date Modified', false],
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
          ['exifdatetaken', 'Date Taken', false], ['metadatadate', 'Date Acquired', false],
          ['filecreateddate', 'Date Created', false], ['filemodifieddate', 'Date Modified', false],
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
          ['exifdatetaken', 'Date Taken', false], ['metadatadate', 'Date Acquired', false],
          ['filecreateddate', 'Date Created', false], ['filemodifieddate', 'Date Modified', false],
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

const DUPLICATE_RULE_POLICIES = [
  {
    key: 'duplicate.rules.crop_policy',
    label: 'Crop / Full Composition',
    options: [
      ['prefer_full', 'Prefer Full Composition'],
      ['prefer_cropped', 'Prefer Cropped'],
      ['keep_each', 'Keep Best from Each'],
    ],
    defaultValue: 'prefer_full',
  },
  {
    key: 'duplicate.rules.color_policy',
    label: 'Color / Black & White',
    options: [
      ['prefer_color', 'Prefer Color'],
      ['prefer_bw', 'Prefer Black & White'],
      ['keep_each', 'Keep Best from Each'],
    ],
    defaultValue: 'prefer_color',
  },
  {
    key: 'duplicate.rules.text_policy',
    label: 'Text / No Text',
    options: [
      ['prefer_text', 'Prefer Text'],
      ['prefer_no_text', 'Prefer No Text'],
      ['keep_each', 'Keep Best from Each'],
    ],
    defaultValue: 'keep_each',
  },
  {
    key: 'duplicate.rules.file_size_policy',
    label: 'File Size Variants',
    options: [
      ['prefer_largest', 'Prefer Largest File Size'],
      ['prefer_smallest', 'Prefer Smallest File Size'],
      ['keep_each', 'Keep Best from Each'],
    ],
    defaultValue: 'prefer_largest',
  },
];

const DUPLICATE_FORMAT_ORDER_DEFAULT = ['PNG', 'WebP', 'JPEG', 'RAW', 'TIFF', 'BMP', 'GIF', 'HEIC', 'AVIF'];
const DUPLICATE_MERGE_FIELDS = [
  ['duplicate.rules.merge.tags', 'Tags', true],
  ['duplicate.rules.merge.description', 'Description', true],
  ['duplicate.rules.merge.comments', 'Comments', true],
  ['duplicate.rules.merge.notes', 'Notes', true],
  ['duplicate.rules.merge.ai_prompts', 'AI Prompts', true],
  ['duplicate.rules.merge.ai_parameters', 'AI Parameters (Can only keep 1)', true],
  ['duplicate.rules.merge.workflows', 'Workflows (Can only keep 1)', true],
  ['duplicate.rules.merge.all', 'All (Includes more than listed above)', false],
];
const DUPLICATE_PRIORITY_ORDER_DEFAULT = [
  'File Size',
  'Resolution',
  'File Format',
  'Compression',
  'Color / Grey Preference',
  'Text / No Text Preference',
  'Cropped / Full Preference',
];

// Loading progress tracking
let gTotalOnPage = 0;
let gLoadedOnPage = 0;
let gLoadingDismissed = false;
let gNavState = { canBack: false, canForward: false, canUp: false, currentPath: '' };
let gAddressBarEditing = false;
let gAddressBarFallbackText = '(none)';
let gOpenCrumbChevron = null;
let gCurrentFolderChildren = [];
let gFolderChildCache = new Map();
let gCrumbMenuLevels = [];
let gFolderChildrenToken = 0;
let gChildFolderRequestSeq = 0;
let gPendingChildFolderRequests = new Map();
let gGalleryRequestSeq = 0;
let gPendingMediaCountRequests = new Map();
let gPendingMediaListRequests = new Map();
let gRefreshGeneration = 0;
let gSelectedFolderLabelHidden = false;
let gSelectedFolderLabelWidth = 0;

function buildDragPreviewCanvas(img, item = null) {
  if (!img) return null;
  const sourceWidth = (item && item.width) || img.naturalWidth || img.width || 0;
  const sourceHeight = (item && item.height) || img.naturalHeight || img.height || 0;
  if (!sourceWidth || !sourceHeight) return null;

  const previewMaxWidth = 75;
  const previewMaxHeight = 75;
  const cursorOffsetX = 20;
  const cursorOffsetY = 20;
  const scale = Math.min(previewMaxWidth / sourceWidth, previewMaxHeight / sourceHeight, 1);
  const drawWidth = Math.max(1, Math.round(sourceWidth * scale));
  const drawHeight = Math.max(1, Math.round(sourceHeight * scale));
  const cssWidth = drawWidth + cursorOffsetX;
  const cssHeight = drawHeight + cursorOffsetY;
  const dpr = Math.max(1, window.devicePixelRatio || 1);

  const canvas = document.createElement('canvas');
  canvas.width = Math.round(cssWidth * dpr);
  canvas.height = Math.round(cssHeight * dpr);
  canvas.style.width = `${cssWidth}px`;
  canvas.style.height = `${cssHeight}px`;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;
  ctx.scale(dpr, dpr);

  const offsetX = cursorOffsetX;
  const offsetY = cursorOffsetY;
  ctx.clearRect(0, 0, cssWidth, cssHeight);
  ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight);
  return canvas;
}

function primeGalleryDragState(paths) {
  if (window.qt && gBridge && gBridge.set_drag_paths) {
    gBridge.set_drag_paths(paths);
  }
  gGalleryDragHandled = false;
  clearGalleryFolderDropTargets();
  gCurrentDragPaths = paths.slice();
  gCurrentDragCount = paths.length;
  debugGalleryDrag(`dragstart count=${paths.length} first=${paths[0] || ''}`);
}

function clearGalleryDragState() {
  if (gBridge && gBridge.hide_drag_tooltip) {
    gBridge.hide_drag_tooltip();
  }
  if (window.qt && gBridge && gBridge.set_drag_paths) {
    gBridge.set_drag_paths([]);
  }
  clearGalleryFolderDropTargets();
  gCurrentDragPaths = [];
  gCurrentDragCount = 0;
  gCurrentTargetFolderName = '';
  gCurrentDropFolderPath = '';
  gGalleryDragHandled = false;
}

function startNativeGalleryDrag(e, item, paths) {
  if (!(window.qt && gBridge && gBridge.start_native_drag)) return false;
  e.preventDefault();
  e.stopPropagation();
  primeGalleryDragState(paths);
  gBridge.start_native_drag(paths, item.path || '', item.width || 0, item.height || 0);
  return true;
}

function setStatus(text) {
  const el = document.getElementById('status');
  if (el) el.textContent = text;
}

function updateGalleryCountChip(count) {
  const el = document.getElementById('galleryCountChip');
  if (!el) return;
  const safeCount = Math.max(0, Number(count || 0));
  el.textContent = `${safeCount.toLocaleString()} Files`;
}

function normalizeFolderPath(path) {
  return String(path || '').replace(/\//g, '\\').trim();
}

function getFolderBreadcrumbs(path) {
  const normalized = normalizeFolderPath(path);
  if (!normalized) return [];

  if (normalized.startsWith('\\\\')) {
    const parts = normalized.split('\\').filter(Boolean);
    if (parts.length < 2) {
      return [{ label: normalized, path: normalized }];
    }
    const root = `\\\\${parts[0]}\\${parts[1]}`;
    const breadcrumbs = [{ label: root, path: root }];
    let current = root;
    for (let i = 2; i < parts.length; i += 1) {
      current += `\\${parts[i]}`;
      breadcrumbs.push({ label: parts[i], path: current });
    }
    return breadcrumbs;
  }

  const driveMatch = normalized.match(/^[A-Za-z]:/);
  if (driveMatch) {
    const drive = driveMatch[0];
    const parts = normalized.slice(drive.length).split('\\').filter(Boolean);
    const breadcrumbs = [{ label: drive, path: `${drive}\\` }];
    let current = drive;
    parts.forEach((part) => {
      current += `\\${part}`;
      breadcrumbs.push({ label: part, path: current });
    });
    return breadcrumbs;
  }

  const parts = normalized.split('\\').filter(Boolean);
  let current = '';
  return parts.map((part) => {
    current = current ? `${current}\\${part}` : part;
    return { label: part, path: current };
  });
}

function fetchFolderChildren(path) {
  const normalized = normalizeFolderPath(path);
  if (!normalized || !gBridge) {
    return Promise.resolve([]);
  }
  if (gFolderChildCache.has(normalized)) {
    return Promise.resolve(gFolderChildCache.get(normalized) || []);
  }
  if (gBridge.list_child_folders_async) {
    return new Promise((resolve) => {
      const requestId = `child-${Date.now()}-${++gChildFolderRequestSeq}`;
      gPendingChildFolderRequests.set(requestId, { path: normalized, resolve });
      gBridge.list_child_folders_async(requestId, normalized);
    });
  }
  if (!gBridge.list_child_folders) {
    return Promise.resolve([]);
  }
  return new Promise((resolve) => {
    gBridge.list_child_folders(normalized, function (items) {
      const nextItems = Array.isArray(items) ? items : [];
      gFolderChildCache.set(normalized, nextItems);
      resolve(nextItems);
    });
  });
}

function fetchMediaCount(folders, filterType, searchQuery) {
  if (!gBridge) return Promise.resolve(0);
  if (gBridge.count_media_async) {
    return new Promise((resolve) => {
      const requestId = `count-${Date.now()}-${++gGalleryRequestSeq}`;
      gPendingMediaCountRequests.set(requestId, resolve);
      gBridge.count_media_async(requestId, folders || [], filterType || 'all', searchQuery || '');
    });
  }
  if (!gBridge.count_media) {
    return Promise.resolve(0);
  }
  return new Promise((resolve) => {
    gBridge.count_media(folders || [], filterType || 'all', searchQuery || '', function (count) {
      resolve(Number(count || 0));
    });
  });
}

function getSelectedFolderLabelWidth() {
  const label = document.getElementById('selectedFolderLabel');
  if (!label) return gSelectedFolderLabelWidth || 0;
  if (!gSelectedFolderLabelWidth) {
    gSelectedFolderLabelWidth = Math.ceil(label.getBoundingClientRect().width || label.scrollWidth || 0);
  }
  return gSelectedFolderLabelWidth;
}

function getFolderAddressContentWidth(address) {
  if (!address) return 0;
  const children = Array.from(address.children || []);
  if (!children.length) {
    return Math.ceil(address.scrollWidth || 0);
  }
  let width = 0;
  children.forEach((child) => {
    width += Math.ceil(child.getBoundingClientRect().width || 0);
  });
  const styles = window.getComputedStyle(address);
  const gap = parseFloat(styles.columnGap || styles.gap || '0') || 0;
  const paddingLeft = parseFloat(styles.paddingLeft || '0') || 0;
  const paddingRight = parseFloat(styles.paddingRight || '0') || 0;
  if (children.length > 1) {
    width += Math.ceil(gap * (children.length - 1));
  }
  width += Math.ceil(paddingLeft + paddingRight);
  return width;
}

function updateSelectedFolderLabelVisibility() {
  const address = document.getElementById('selectedFolder');
  const row = address ? address.closest('.kv') : null;
  if (!address || !row) return;
  const contentWidth = getFolderAddressContentWidth(address);
  const overflowPx = Math.ceil(contentWidth - address.clientWidth);
  const labelWidth = getSelectedFolderLabelWidth();
  const spareRoomPx = Math.floor(address.clientWidth - contentWidth);
  const hideThreshold = 1;
  const showThreshold = 100;
  if (!gSelectedFolderLabelHidden && overflowPx > hideThreshold) {
    gSelectedFolderLabelHidden = true;
  } else if (gSelectedFolderLabelHidden && spareRoomPx >= labelWidth + showThreshold) {
    gSelectedFolderLabelHidden = false;
  }
  row.classList.toggle('hide-selected-folder-label', gSelectedFolderLabelHidden);
}

function fetchMediaList(folders, limit, offset, sortBy, filterType, searchQuery) {
  if (!gBridge) return Promise.resolve([]);
  if (gBridge.list_media_async) {
    return new Promise((resolve) => {
      const requestId = `list-${Date.now()}-${++gGalleryRequestSeq}`;
      gPendingMediaListRequests.set(requestId, resolve);
      gBridge.list_media_async(
        requestId,
        folders || [],
        Number(limit || 0),
        Number(offset || 0),
        sortBy || 'name_asc',
        filterType || 'all',
        searchQuery || ''
      );
    });
  }
  if (!gBridge.list_media) {
    return Promise.resolve([]);
  }
  return new Promise((resolve) => {
    gBridge.list_media(
      folders || [],
      Number(limit || 0),
      Number(offset || 0),
      sortBy || 'name_asc',
      filterType || 'all',
      searchQuery || '',
      function (items) {
        resolve(Array.isArray(items) ? items : []);
      }
    );
  });
}

function refreshCurrentFolderChildren() {
  const currentPath = normalizeFolderPath(gNavState.currentPath);
  const token = ++gFolderChildrenToken;
  if (!currentPath) {
    gCurrentFolderChildren = [];
    renderFolderAddress();
    updateSelectedFolderLabelVisibility();
    return;
  }
  fetchFolderChildren(currentPath).then((items) => {
    if (token !== gFolderChildrenToken) return;
    if (normalizeFolderPath(gNavState.currentPath) !== currentPath) return;
    gCurrentFolderChildren = Array.isArray(items) ? items : [];
    renderFolderAddress();
    updateSelectedFolderLabelVisibility();
  });
}

function renderFolderAddress() {
  const el = document.getElementById('selectedFolder');
  if (!el) return;

  const currentPath = normalizeFolderPath(gNavState.currentPath);
  const textValue = currentPath || gAddressBarFallbackText || '(none)';
  el.title = textValue;
  el.classList.toggle('is-empty', !currentPath);
  el.classList.toggle('is-editing', gAddressBarEditing);

  if (gAddressBarEditing) {
    closeFolderCrumbMenu();
    el.innerHTML = '<input id="selectedFolderInput" class="folder-address-input" type="text" spellcheck="false" />';
    const input = document.getElementById('selectedFolderInput');
    if (!input) return;
    input.value = textValue;
    input.focus();
    input.select();
    requestAnimationFrame(updateSelectedFolderLabelVisibility);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const nextPath = normalizeFolderPath(input.value);
        gAddressBarEditing = false;
        renderFolderAddress();
        if (nextPath && gBridge && gBridge.navigate_to_folder) {
          gBridge.navigate_to_folder(nextPath);
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        gAddressBarEditing = false;
        renderFolderAddress();
      }
    });
    input.addEventListener('blur', () => {
      gAddressBarEditing = false;
      renderFolderAddress();
    });
    return;
  }

  if (!currentPath) {
    el.textContent = textValue;
    requestAnimationFrame(updateSelectedFolderLabelVisibility);
    return;
  }

  const crumbs = getFolderBreadcrumbs(currentPath);
  el.innerHTML = '';
  crumbs.forEach((crumb, index) => {
    const btn = document.createElement('button');
    btn.className = 'folder-address-segment';
    if (index === crumbs.length - 1) btn.classList.add('current');
    btn.type = 'button';
    btn.textContent = crumb.label;
    btn.title = crumb.path;
    btn.dataset.path = crumb.path;
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      openFolderItem(crumb.path);
    });
    el.appendChild(btn);

    if (index < crumbs.length - 1) {
      const chevron = document.createElement('button');
      chevron.className = 'folder-address-chevron';
      chevron.type = 'button';
      chevron.textContent = '>';
      chevron.title = `Show folders under ${crumb.label}`;
      chevron.setAttribute('aria-haspopup', 'menu');
      chevron.setAttribute('aria-expanded', 'false');
      chevron.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleFolderCrumbMenu(crumb.path, chevron, 0);
      });
      el.appendChild(chevron);
    }
  });
  if (Array.isArray(gCurrentFolderChildren) && gCurrentFolderChildren.length > 0) {
    const chevron = document.createElement('button');
    chevron.className = 'folder-address-chevron';
    chevron.type = 'button';
    chevron.textContent = '>';
    chevron.title = 'Show folders in the current folder';
    chevron.setAttribute('aria-haspopup', 'menu');
    chevron.setAttribute('aria-expanded', 'false');
    chevron.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleFolderCrumbMenu(currentPath, chevron, 0, gCurrentFolderChildren);
    });
    el.appendChild(chevron);
  }
  el.scrollLeft = el.scrollWidth;
  requestAnimationFrame(updateSelectedFolderLabelVisibility);
}

function getFolderCrumbMenu(level) {
  if (gCrumbMenuLevels[level] && gCrumbMenuLevels[level].menu) {
    return gCrumbMenuLevels[level].menu;
  }
  let menu = null;
  if (level === 0) {
    menu = document.getElementById('folderCrumbMenu');
  } else {
    menu = document.createElement('div');
    menu.className = 'folder-crumb-menu';
    menu.hidden = true;
    document.body.appendChild(menu);
  }
  if (!menu) return null;
  menu.dataset.level = String(level);
  menu.addEventListener('keydown', handleFolderCrumbMenuKeydown);
  gCrumbMenuLevels[level] = { menu, anchor: null, parentButton: null, folderPath: '' };
  return menu;
}

function closeFolderCrumbMenu(fromLevel = 0) {
  for (let i = gCrumbMenuLevels.length - 1; i >= fromLevel; i -= 1) {
    const entry = gCrumbMenuLevels[i];
    if (!entry || !entry.menu) continue;
    entry.menu.hidden = true;
    entry.menu.innerHTML = '';
    if (i > 0 && entry.menu.parentNode) {
      entry.menu.parentNode.removeChild(entry.menu);
    }
    gCrumbMenuLevels[i] = null;
  }
  gCrumbMenuLevels = gCrumbMenuLevels.slice(0, fromLevel);
  if (fromLevel <= 0 && gOpenCrumbChevron) {
    gOpenCrumbChevron.setAttribute('aria-expanded', 'false');
    gOpenCrumbChevron = null;
  }
}

function positionFolderCrumbMenu(anchorRect, menu, preferredDirection = 'below') {
  if (!anchorRect || !menu) return;
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  let left = anchorRect.left;
  let top = anchorRect.bottom + 6;
  const width = menu.offsetWidth;
  const height = menu.offsetHeight;
  if (preferredDirection === 'side') {
    left = anchorRect.right + 4;
    top = anchorRect.top - 6;
    if (left + width > viewportWidth - 12) {
      left = Math.max(12, anchorRect.left - width - 4);
    }
    if (top + height > viewportHeight - 12) {
      top = Math.max(12, viewportHeight - height - 12);
    }
  } else {
    if (left + width > viewportWidth - 12) {
      left = Math.max(12, viewportWidth - width - 12);
    }
    if (top + height > viewportHeight - 12) {
      top = Math.max(12, anchorRect.top - height - 6);
    }
  }
  menu.style.left = `${left}px`;
  menu.style.top = `${top}px`;
}

function getFolderCrumbButtons(level) {
  const entry = gCrumbMenuLevels[level];
  if (!entry || !entry.menu) return [];
  return Array.from(entry.menu.querySelectorAll('.folder-crumb-menu-item'));
}

function focusFolderCrumbButton(level, index) {
  const buttons = getFolderCrumbButtons(level);
  if (!buttons.length) return;
  const nextIndex = Math.max(0, Math.min(index, buttons.length - 1));
  buttons[nextIndex].focus();
}

function populateFolderCrumbMenu(level, items) {
  const entry = gCrumbMenuLevels[level];
  const menu = entry && entry.menu;
  if (!menu) return;
  menu.innerHTML = '';
  if (!Array.isArray(items) || items.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'folder-crumb-menu-empty';
    empty.textContent = 'No subfolders';
    menu.appendChild(empty);
    return;
  }
  items.forEach((item) => {
    const btn = document.createElement('button');
    btn.className = 'folder-crumb-menu-item';
    btn.type = 'button';
    btn.dataset.path = item.path || '';
    btn.title = item.path || '';

    const label = document.createElement('span');
    label.className = 'folder-crumb-menu-item-label';
    label.textContent = item.name || item.path || '';
    const arrow = document.createElement('span');
    arrow.className = 'folder-crumb-menu-item-arrow';
    arrow.textContent = '>';

    btn.appendChild(label);
    btn.appendChild(arrow);
    btn.addEventListener('mouseenter', () => {
      openFolderCrumbChildMenu(level, btn);
    });
    btn.addEventListener('click', () => {
      closeFolderCrumbMenu();
      if (btn.dataset.path) openFolderItem(btn.dataset.path);
    });
    menu.appendChild(btn);
  });
}

function openFolderCrumbMenu(items, anchor, level = 0, parentButton = null, folderPath = '') {
  const menu = getFolderCrumbMenu(level);
  if (!menu || !anchor) return;
  closeFolderCrumbMenu(level + 1);
  populateFolderCrumbMenu(level, items);
  menu.hidden = false;
  positionFolderCrumbMenu(anchor.getBoundingClientRect(), menu, level === 0 ? 'below' : 'side');
  gCrumbMenuLevels[level] = { menu, anchor, parentButton, folderPath };
  if (level === 0) {
    if (gOpenCrumbChevron && gOpenCrumbChevron !== anchor) {
      gOpenCrumbChevron.setAttribute('aria-expanded', 'false');
    }
    gOpenCrumbChevron = anchor;
    gOpenCrumbChevron.setAttribute('aria-expanded', 'true');
  }
}

function openFolderCrumbChildMenu(level, button, focusFirst = false) {
  const folderPath = button && button.dataset ? button.dataset.path : '';
  if (!folderPath) {
    closeFolderCrumbMenu(level + 1);
    return;
  }
  fetchFolderChildren(folderPath).then((items) => {
    if (!button.isConnected) return;
    if (!Array.isArray(items) || items.length === 0) {
      closeFolderCrumbMenu(level + 1);
      return;
    }
    openFolderCrumbMenu(items, button, level + 1, button, folderPath);
    if (focusFirst) {
      focusFolderCrumbButton(level + 1, 0);
    }
  });
}

function handleFolderCrumbMenuKeydown(e) {
  const menu = e.currentTarget;
  const level = Number(menu.dataset.level || 0);
  const buttons = getFolderCrumbButtons(level);
  if (!buttons.length) return;
  const currentButton = document.activeElement && document.activeElement.closest('.folder-crumb-menu-item');
  const index = Math.max(0, buttons.indexOf(currentButton));
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    focusFolderCrumbButton(level, (index + 1) % buttons.length);
    return;
  }
  if (e.key === 'ArrowUp') {
    e.preventDefault();
    focusFolderCrumbButton(level, (index - 1 + buttons.length) % buttons.length);
    return;
  }
  if (e.key === 'ArrowRight') {
    e.preventDefault();
    openFolderCrumbChildMenu(level, buttons[index], true);
    return;
  }
  if (e.key === 'ArrowLeft') {
    e.preventDefault();
    if (level > 0) {
      const parentEntry = gCrumbMenuLevels[level - 1];
      closeFolderCrumbMenu(level);
      if (parentEntry && parentEntry.parentButton) {
        parentEntry.parentButton.focus();
      }
    } else if (gOpenCrumbChevron) {
      const anchor = gOpenCrumbChevron;
      closeFolderCrumbMenu();
      anchor.focus();
    }
    return;
  }
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    const path = buttons[index].dataset.path || '';
    closeFolderCrumbMenu();
    if (path) openFolderItem(path);
    return;
  }
  if (e.key === 'Escape') {
    e.preventDefault();
    if (gOpenCrumbChevron) {
      const anchor = gOpenCrumbChevron;
      closeFolderCrumbMenu();
      anchor.focus();
    } else {
      closeFolderCrumbMenu();
    }
  }
}

function toggleFolderCrumbMenu(folderPath, anchor, level = 0, preloadedItems = null) {
  const existingMenu = level === 0 ? document.getElementById('folderCrumbMenu') : getFolderCrumbMenu(level);
  if (existingMenu && !existingMenu.hidden && level === 0 && gOpenCrumbChevron === anchor) {
    closeFolderCrumbMenu();
    return;
  }
  const itemsPromise = Array.isArray(preloadedItems) ? Promise.resolve(preloadedItems) : fetchFolderChildren(folderPath);
  itemsPromise.then((items) => {
    if (!Array.isArray(items) || items.length === 0) {
      closeFolderCrumbMenu(level);
      return;
    }
    openFolderCrumbMenu(items, anchor, level, null, folderPath);
    const buttons = getFolderCrumbButtons(level);
    if (buttons.length) {
      buttons[0].focus();
    }
  });
}

function setSelectedFolder(paths, activeCollection = null) {
  if (activeCollection && activeCollection.name && !gNavState.currentPath) {
    gAddressBarFallbackText = activeCollection.name;
  } else if (!paths || paths.length === 0) {
    gAddressBarFallbackText = '(none)';
  } else if (paths.length === 1) {
    gAddressBarFallbackText = normalizeFolderPath(paths[0]) || '(none)';
  } else {
    gAddressBarFallbackText = `${paths.length} folders selected`;
  }
  renderFolderAddress();
}

function applyNavigationState(state = {}) {
  const prevPath = normalizeFolderPath(gNavState.currentPath);
  gNavState = {
    canBack: !!state.canBack,
    canForward: !!state.canForward,
    canUp: !!state.canUp,
    currentPath: state.currentPath || '',
  };

  const backBtn = document.getElementById('navBack');
  const forwardBtn = document.getElementById('navForward');
  const upBtn = document.getElementById('navUp');
  const refreshBtn = document.getElementById('navRefresh');

  if (backBtn) backBtn.disabled = !gNavState.canBack;
  if (forwardBtn) forwardBtn.disabled = !gNavState.canForward;
  if (upBtn) upBtn.disabled = !gNavState.canUp;
  if (refreshBtn) refreshBtn.disabled = !gNavState.currentPath;
  if (prevPath !== normalizeFolderPath(gNavState.currentPath)) {
    closeFolderCrumbMenu();
    gCurrentFolderChildren = [];
    refreshCurrentFolderChildren();
  } else {
    renderFolderAddress();
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

function wireTextProcessingIndicator() {
  const el = document.getElementById('textProcessingToast');
  const label = document.getElementById('textProcessingLabel');
  const file = document.getElementById('textProcessingFile');
  const bar = document.getElementById('textProcessingBar');
  const cancelBtn = document.getElementById('textProcessingCancel');
  if (!el || !label || !file || !bar || !gBridge) return;

  function render() {
    if (!gTextProcessingActive) {
      el.hidden = true;
      return;
    }
    const allowVisible = isTextFilterActive() || gShowDismissedProgressToasts;
    if (!allowVisible || (gTextProcessingDismissed && !gShowDismissedProgressToasts)) {
      el.hidden = true;
      return;
    }
    el.hidden = false;
    label.textContent = gTextProcessingStage || 'Detecting Text';
    if (gTextProcessingTotal > 0) {
      file.textContent = `${gTextProcessingCurrent} / ${gTextProcessingTotal}`;
      bar.style.width = `${Math.max(0, Math.min(100, Math.round((gTextProcessingCurrent / gTextProcessingTotal) * 100)))}%`;
    } else {
      file.textContent = 'Starting...';
      bar.style.width = '0%';
    }
  }
  gRenderTextProcessingToast = render;

  el.onclick = () => {
    gTextProcessingDismissed = true;
    render();
  };

  if (cancelBtn) {
    cancelBtn.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      gTextProcessingDismissed = true;
      if (gBridge.pause_text_processing) {
        gBridge.pause_text_processing();
      }
      render();
    });
  }

  if (gBridge.textProcessingStarted) {
    gBridge.textProcessingStarted.connect((stage, total) => {
      gTextProcessingActive = true;
      gTextProcessingStage = stage || 'Detecting Text';
      gTextProcessingCurrent = 0;
      gTextProcessingTotal = Math.max(0, Number(total || 0));
      render();
    });
  }

  if (gBridge.textProcessingProgress) {
    gBridge.textProcessingProgress.connect((stage, current, total) => {
      gTextProcessingActive = true;
      gTextProcessingStage = stage || gTextProcessingStage || 'Detecting Text';
      gTextProcessingCurrent = Math.max(0, Number(current || 0));
      gTextProcessingTotal = Math.max(0, Number(total || 0));
      render();
    });
  }

  if (gBridge.textProcessingFinished) {
    gBridge.textProcessingFinished.connect(() => {
      gTextProcessingActive = false;
      gTextProcessingCurrent = gTextProcessingTotal;
      render();
      if (isTextFilterActive() && gBridge) {
        refreshFromBridge(gBridge, false);
      }
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

function selectDuplicateGroupForKeep(groupKey) {
  deselectAll();
  const cards = Array.from(document.querySelectorAll(`.card[data-duplicate-group-key="${CSS.escape(groupKey)}"]`));
  cards.forEach((card) => {
    if (card.getAttribute('data-duplicate-keep') === 'true') return;
    card.classList.add('selected');
    const path = card.getAttribute('data-path');
    if (path) gSelectedPaths.add(path);
  });
  gIsCtxMenuClick = true;
  syncMetadataToBridge();
}

function getDuplicateKeepPath(groupKey) {
  const override = gDuplicateKeepOverrides.get(String(groupKey || ''));
  if (override) return override;
  const keepItem = gMedia.find(item => String(item.duplicate_group_key || '') === String(groupKey || '') && item.duplicate_is_overall_best);
  return keepItem && keepItem.path ? keepItem.path : '';
}

function setDuplicateKeepPath(groupKey, path) {
  const key = String(groupKey || '');
  const nextPath = String(path || '');
  if (!key || !nextPath) return;
  gDuplicateKeepOverrides.set(key, nextPath);
  document.querySelectorAll(`.card[data-duplicate-group-key="${CSS.escape(key)}"]`).forEach((card) => {
    const checked = card.getAttribute('data-path') === nextPath;
    card.setAttribute('data-duplicate-keep', checked ? 'true' : 'false');
    const toggle = card.querySelector('.duplicate-keep-toggle');
    if (toggle) toggle.checked = checked;
    const overall = card.querySelector('.duplicate-overall-best');
    if (overall) overall.hidden = !checked;
  });
}

function deletePathsSequential(paths, onDone) {
  const queue = Array.isArray(paths) ? paths.slice() : [];
  const step = () => {
    const next = queue.shift();
    if (!next) {
      if (typeof onDone === 'function') onDone();
      return;
    }
    if (!gBridge || !gBridge.delete_path) {
      step();
      return;
    }
    gBridge.delete_path(next, function () {
      step();
    });
  };
  step();
}

function getDuplicateGroupItems(groupKey) {
  return gMedia
    .filter(item => String(item.duplicate_group_key || '') === String(groupKey || ''))
    .slice()
    .sort((a, b) => Number(a.duplicate_group_position || 0) - Number(b.duplicate_group_position || 0));
}

function computeAutoResolveKeepPaths(groupKey, settings = {}) {
  const items = getDuplicateGroupItems(groupKey).filter(item => item && item.path);
  if (!items.length) return [];
  const keep = new Set();
  const overallKeepPath = getDuplicateKeepPath(groupKey) || (items[0] && items[0].path) || '';
  if (overallKeepPath) keep.add(overallKeepPath);

  const pickFirst = (predicate) => {
    const match = items.find(predicate);
    if (match && match.path) keep.add(match.path);
  };

  if ((settings['duplicate.rules.color_policy'] || '') === 'keep_each') {
    pickFirst(item => String(item.color_variant || '') === 'color');
    pickFirst(item => String(item.color_variant || '') === 'grayscale');
  }

  if ((settings['duplicate.rules.crop_policy'] || '') === 'keep_each') {
    pickFirst(item => String(item.duplicate_crop_variant || '') === 'full');
    pickFirst(item => String(item.duplicate_crop_variant || '') === 'cropped');
  }

  if ((settings['duplicate.rules.file_size_policy'] || '') === 'keep_each') {
    const sizes = items.map(item => Number(item.file_size) || 0);
    const largest = Math.max(...sizes);
    const smallest = Math.min(...sizes);
    if (largest > smallest) {
      pickFirst(item => (Number(item.file_size) || 0) === largest);
      pickFirst(item => (Number(item.file_size) || 0) === smallest);
    }
  }

  return Array.from(keep);
}

function runDuplicateGroupResolution(groupKey, settings, onDone) {
  const items = getDuplicateGroupItems(groupKey);
  const paths = items.map(item => item.path).filter(Boolean);
  const keepPaths = new Set(computeAutoResolveKeepPaths(groupKey, settings));
  const deletePaths = paths.filter(path => !keepPaths.has(path));
  const mergeFirst = !!(settings && settings['duplicate.rules.merge_before_delete']);
  const finish = () => deletePathsSequential(deletePaths, onDone);
  if (mergeFirst && paths.length >= 2 && gBridge && gBridge.merge_duplicate_group_metadata) {
    gBridge.merge_duplicate_group_metadata(paths);
  }
  finish();
}

function keepBestInDuplicateGroup(groupKey) {
  if (!gBridge || !gBridge.get_settings) return;
  gPendingScrollAnchor = captureCurrentGroupScrollAnchor();
  setGlobalLoading(true, 'Deleting duplicate files...', 25);
  gBridge.get_settings((settings) => {
    const nextSettings = settings || {};
    const keepPath = getDuplicateKeepPath(groupKey);
    const items = getDuplicateGroupItems(groupKey);
    const paths = items.map(item => item.path).filter(Boolean);
    const deletePaths = paths.filter(path => path !== keepPath);
    if (!keepPath || !deletePaths.length) {
      setGlobalLoading(false);
      return;
    }
    if (nextSettings['duplicate.rules.merge_before_delete'] && paths.length >= 2 && gBridge.merge_duplicate_group_metadata) {
      gBridge.merge_duplicate_group_metadata(paths);
    }
    deletePathsSequential(deletePaths, () => {
      setGlobalLoading(false);
      refreshFromBridge(gBridge, false);
    });
  });
}

function mergeDuplicateGroupMetadata(groupKey) {
  const paths = gMedia
    .filter(item => String(item.duplicate_group_key || '') === String(groupKey || ''))
    .map(item => item.path)
    .filter(Boolean);
  if (paths.length < 2 || !gBridge || !gBridge.merge_duplicate_group_metadata) return;
  gPendingScrollAnchor = captureCurrentGroupScrollAnchor();
  setGlobalLoading(true, 'Merging duplicate metadata...', 25);
  const ok = gBridge.merge_duplicate_group_metadata(paths);
  setGlobalLoading(false);
  if (ok && gBridge) {
    refreshFromBridge(gBridge, false);
  }
}

function autoResolveAllDuplicateGroups() {
  const groupKeys = Array.from(new Set(
    gMedia
      .map(item => String(item.duplicate_group_key || '').trim())
      .filter(Boolean)
  ));
  if (!groupKeys.length) return;
  gPendingScrollAnchor = captureCurrentGroupScrollAnchor();
  setGlobalLoading(true, 'Auto resolving duplicate groups...', 20);
  if (!gBridge || !gBridge.get_settings) {
    setGlobalLoading(false);
    return;
  }
  gBridge.get_settings((settings) => {
    const nextSettings = settings || {};
    const queue = groupKeys.slice();
    const step = () => {
      const nextGroup = queue.shift();
      if (!nextGroup) {
        setGlobalLoading(false);
        refreshFromBridge(gBridge, false);
        return;
      }
      runDuplicateGroupResolution(nextGroup, nextSettings, step);
    };
    step();
  });
}

function deleteDuplicateCard(path) {
  if (!path || !gBridge || !gBridge.delete_path) return;
  gPendingScrollAnchor = captureCurrentGroupScrollAnchor();
  setGlobalLoading(true, 'Deleting file...', 25);
  gBridge.delete_path(path, function () {
    setGlobalLoading(false);
    refreshFromBridge(gBridge, false);
  });
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
  if (nextMode === 'duplicates' || nextMode === 'similar' || nextMode === 'similar_only') {
    return ['gallery-duplicates'];
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
  if (!REVIEW_VIEW_MODES.has(nextMode)) {
    gLastStandardViewMode = nextMode;
  }
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
  const targets = [container, ...container.querySelectorAll('.gallery-details')];
  targets.forEach(target => {
    DETAILS_COLUMN_CONFIG.forEach(col => {
      const width = col.resizable ? (gDetailsColumnWidths[col.key] || col.width) : col.width;
      target.style.setProperty(`--details-col-${col.key}`, `${Math.round(width)}px`);
    });
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
      timelineDayLabel: '?',
      yearNumber: null,
      monthIndex: null,
      dayNumber: null,
      sortValue: -1,
      rangeStart: null,
      rangeEnd: null,
    };
  }

  const year = date.getFullYear();
  const month = date.getMonth();
  const day = date.getDate();
  const monthLabel = date.toLocaleDateString(undefined, { month: 'short' });
  const monthLong = date.toLocaleDateString(undefined, { month: 'long' });

  if (gGroupDateGranularity === 'year') {
    const rangeStart = Date.UTC(year, 0, 1);
    const rangeEnd = Date.UTC(year, 11, 31);
    return {
      key: `${year}`,
      label: `${year}`,
      timelineYear: `${year}`,
      timelineLabel: `${year}`,
      timelineTitle: `${year}`,
      timelineDayLabel: '1',
      yearNumber: year,
      monthIndex: 0,
      dayNumber: 1,
      sortValue: rangeStart,
      rangeStart,
      rangeEnd,
    };
  }

  if (gGroupDateGranularity === 'month') {
    const rangeStart = Date.UTC(year, month, 1);
    const rangeEnd = Date.UTC(year, month + 1, 0);
    return {
      key: `${year}-${String(month + 1).padStart(2, '0')}`,
      label: `${monthLong} ${year}`,
      timelineYear: `${year}`,
      timelineLabel: monthLabel,
      timelineTitle: `${monthLong} ${year}`,
      timelineDayLabel: '1',
      yearNumber: year,
      monthIndex: month,
      dayNumber: 1,
      sortValue: rangeStart,
      rangeStart,
      rangeEnd,
    };
  }

  const rangeStart = Date.UTC(year, month, day);

  return {
    key: `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`,
    label: date.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' }),
    timelineYear: `${year}`,
    timelineLabel: monthLabel,
    timelineTitle: `${monthLong} ${year}`,
    timelineDayLabel: `${day}`,
    yearNumber: year,
    monthIndex: month,
    dayNumber: day,
    sortValue: rangeStart,
    rangeStart,
    rangeEnd: rangeStart,
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

function getDuplicateCandidateScore(item) {
  const width = Number(item && item.width) || 0;
  const height = Number(item && item.height) || 0;
  const resolution = width * height;
  const size = Number(item && item.file_size) || 0;
  const dateValue = Number(item && (item.auto_date || item.file_created_time || item.modified_time)) || 0;
  const path = String(item && item.path || '').toLowerCase();
  return [resolution, size, dateValue > 0 ? -dateValue : 0, path];
}

function compareDuplicateCandidates(a, b) {
  const scoreA = getDuplicateCandidateScore(a);
  const scoreB = getDuplicateCandidateScore(b);
  for (let i = 0; i < scoreA.length; i += 1) {
    if (scoreA[i] === scoreB[i]) continue;
    if (typeof scoreA[i] === 'string' || typeof scoreB[i] === 'string') {
      return String(scoreA[i]).localeCompare(String(scoreB[i]));
    }
    return scoreB[i] - scoreA[i];
  }
  return 0;
}

function buildDuplicateGroups(items) {
  const reviewMode = getReviewMode();
  const baseLabel = reviewMode === 'duplicates' ? 'Duplicate Group' : 'Similar Group';
  const seen = new Map();
  items.filter(item => !item.is_folder).forEach((item) => {
    const key = String((reviewMode && reviewMode !== 'duplicates')
      ? (item.duplicate_group_key || item.content_hash || '')
      : (item.content_hash || item.duplicate_group_key || '')).trim();
    if (!key) return;
    let group = seen.get(key);
    if (!group) {
      group = { key, items: [] };
      seen.set(key, group);
    }
    group.items.push(item);
  });

  const groups = Array.from(seen.values())
    .filter(group => group.items.length > 1)
    .map((group, index) => {
      const sortedItems = group.items.slice().sort(compareDuplicateCandidates);
      const keepItem = sortedItems[0] || null;
      const keepSize = Number(keepItem && keepItem.file_size) || 0;
      const totalSize = sortedItems.reduce((sum, item) => sum + (Number(item.file_size) || 0), 0);
      const savings = Math.max(0, totalSize - keepSize);
      const stablePath = String(
        getDuplicateKeepPath(group.key)
        || (keepItem && keepItem.path)
        || (sortedItems.find(item => item && item.path) || {}).path
        || group.key
        || ''
      ).toLowerCase();
      const label = `${baseLabel} ${index + 1}`;
      return {
        key: group.key,
        label,
        items: sortedItems,
        keepItem,
        sortValue: savings,
        stableOrderKey: stablePath,
        previousOrder: gDuplicateGroupOrder.has(stablePath) ? Number(gDuplicateGroupOrder.get(stablePath)) : null,
        rangeStart: null,
        rangeEnd: null,
        subtitle: `${sortedItems.length} items${savings > 0 ? ` • Save ${formatFileSize(savings)}` : ''}`,
      };
    });

  groups.sort((a, b) => {
    const aPrev = Number(a.previousOrder);
    const bPrev = Number(b.previousOrder);
    const aHasPrev = Number.isFinite(aPrev);
    const bHasPrev = Number.isFinite(bPrev);
    if (aHasPrev && bHasPrev && aPrev !== bPrev) return aPrev - bPrev;
    if (aHasPrev !== bHasPrev) return aHasPrev ? -1 : 1;
    if (b.sortValue !== a.sortValue) return b.sortValue - a.sortValue;
    if (b.items.length !== a.items.length) return b.items.length - a.items.length;
    return String(a.stableOrderKey || a.label).localeCompare(String(b.stableOrderKey || b.label));
  });

  groups.forEach((group, index) => {
    group.label = `${baseLabel} ${index + 1}`;
    if (group.stableOrderKey) {
      gDuplicateGroupOrder.set(group.stableOrderKey, index);
    }
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
  scheduleTimelineScrollTargetRefresh();
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

function captureCurrentGroupScrollAnchor() {
  const main = document.querySelector('main');
  if (!main) return null;
  const groups = Array.from(document.querySelectorAll('.gallery-group'));
  if (!groups.length) {
    return {
      scrollTop: main.scrollTop,
      groupSortValue: null,
      offsetWithinGroup: 0,
    };
  }
  const mainRect = main.getBoundingClientRect();
  let best = null;
  groups.forEach((group) => {
    const rect = group.getBoundingClientRect();
    const topWithinMain = rect.top - mainRect.top;
    if (topWithinMain <= 8) {
      if (!best || topWithinMain > best.topWithinMain) {
        best = { group, topWithinMain };
      }
    }
  });
  if (!best) {
    best = {
      group: groups[0],
      topWithinMain: groups[0].getBoundingClientRect().top - mainRect.top,
    };
  }
  const groupSortValueRaw = Number(best.group.dataset.sortValue);
  const groupRangeStartRaw = Number(best.group.dataset.rangeStart);
  const groupRangeEndRaw = Number(best.group.dataset.rangeEnd);
  const groupTopScroll = main.scrollTop + best.topWithinMain;
  return {
    scrollTop: main.scrollTop,
    groupSortValue: Number.isFinite(groupSortValueRaw) ? groupSortValueRaw : null,
    rangeStart: Number.isFinite(groupRangeStartRaw) ? groupRangeStartRaw : null,
    rangeEnd: Number.isFinite(groupRangeEndRaw) ? groupRangeEndRaw : null,
    offsetWithinGroup: Math.max(0, main.scrollTop - groupTopScroll),
  };
}

function restoreGroupScrollAnchor() {
  const anchor = gPendingScrollAnchor;
  gPendingScrollAnchor = null;
  if (!anchor) return;
  const main = document.querySelector('main');
  if (!main) return;
  const groups = Array.from(document.querySelectorAll('.gallery-group'));
  if (!groups.length) {
    main.scrollTop = anchor.scrollTop || 0;
    return;
  }
  if (!Number.isFinite(anchor.groupSortValue)) {
    main.scrollTop = anchor.scrollTop || 0;
    return;
  }
  const groupsWithRanges = groups.map((group) => ({
    group,
    sortValue: Number(group.dataset.sortValue),
    rangeStart: Number(group.dataset.rangeStart),
    rangeEnd: Number(group.dataset.rangeEnd),
  })).filter(entry => Number.isFinite(entry.sortValue));

  const containingPreferred = groupsWithRanges.filter(entry => (
    Number.isFinite(entry.rangeStart) &&
    Number.isFinite(entry.rangeEnd) &&
    anchor.groupSortValue >= entry.rangeStart &&
    anchor.groupSortValue <= entry.rangeEnd
  ));

  const overlappingRange = containingPreferred.length ? containingPreferred : groupsWithRanges.filter(entry => (
    Number.isFinite(entry.rangeStart) &&
    Number.isFinite(entry.rangeEnd) &&
    Number.isFinite(anchor.rangeStart) &&
    Number.isFinite(anchor.rangeEnd) &&
    entry.rangeStart <= anchor.rangeEnd &&
    entry.rangeEnd >= anchor.rangeStart
  ));

  const candidatePool = overlappingRange.length ? overlappingRange : groupsWithRanges;
  let bestGroup = null;
  let bestDistance = Number.POSITIVE_INFINITY;
  candidatePool.forEach((entry) => {
    const compareValue = Number.isFinite(entry.sortValue) ? entry.sortValue : entry.rangeStart;
    const distance = Math.abs(compareValue - anchor.groupSortValue);
    if (distance < bestDistance) {
      bestGroup = entry.group;
      bestDistance = distance;
    }
  });
  if (!bestGroup) {
    main.scrollTop = anchor.scrollTop || 0;
    return;
  }
  const targetScrollTop = (bestGroup.offsetTop || 0) + (anchor.offsetWithinGroup || 0);
  main.scrollTop = Math.max(0, targetScrollTop);
}

function rerenderCurrentMediaPreservingScroll() {
  gPendingScrollAnchor = captureCurrentGroupScrollAnchor();
  renderMediaList(gMedia, false);
}

function shouldUseInfiniteDateScroll() {
  return gGroupBy === 'date' && gGalleryViewMode !== 'masonry';
}

function shouldUseInfiniteScrollMode() {
  if (isDuplicateModeActive()) return false;
  if (shouldUseInfiniteDateScroll()) return true;
  return gGalleryViewMode === 'list'
    || gGalleryViewMode === 'details'
    || gGalleryViewMode === 'content'
    || gGalleryViewMode === 'grid_small'
    || gGalleryViewMode === 'grid_medium';
}

function hasMoreInfiniteResults() {
  return shouldUseInfiniteScrollMode() && Array.isArray(gMedia) && gMedia.length < (gTotal || 0);
}

function maybeLoadMoreInfiniteResults() {
  const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
  if (gTimelineScrubActive || now <= gTimelineNavigationActiveUntil) return;
  if (!shouldUseInfiniteScrollMode() || gInfiniteScrollLoading || !gBridge || !hasMoreInfiniteResults()) return;
  const main = document.querySelector('main');
  if (!main) return;
  const remaining = main.scrollHeight - (main.scrollTop + main.clientHeight);
  if (remaining > 600) return;
  gInfiniteScrollLoading = true;
  const nextOffset = gMedia.length;
  fetchMediaList(gSelectedFolders, PAGE_SIZE, nextOffset, gSort, gFilter, gSearchQuery || '').then(function (items) {
    const nextItems = Array.isArray(items) ? items : [];
    if (nextItems.length > 0) {
      renderMediaList(gMedia.concat(nextItems), false);
    }
    gInfiniteScrollLoading = false;
    renderPager();
    requestAnimationFrame(() => maybeLoadMoreInfiniteResults());
  });
}

function clampTimelineRatio(ratio) {
  if (!Number.isFinite(ratio)) return 0;
  return Math.max(0, Math.min(1, ratio));
}

function getTimelineTopCss(ratio) {
  return `calc(${TIMELINE_INSET_PX + TIMELINE_NAV_LANE_PX + TIMELINE_THUMB_OFFSET_PX}px + ${clampTimelineRatio(ratio)} * (100% - ${(TIMELINE_INSET_PX + TIMELINE_NAV_LANE_PX) * 2}px) - ${TIMELINE_THUMB_SIZE_PX / 2}px)`;
}

function updateTimelineViewport(ratio) {
  const rail = document.getElementById('timelineRail');
  const layer = rail && rail.querySelector('.timeline-anchor-layer');
  const layout = rail && rail.__timelineLayout;
  if (!rail || !layer || !layout) return;
  const clampedRatio = clampTimelineRatio(ratio);
  rail.__currentTimelineRatio = clampedRatio;
  const viewportOffset = (layout.overflow || 0) * clampedRatio;
  layer.style.transform = `translateY(${-viewportOffset}px)`;
}

function updateTimelineThumb(ratio) {
  const thumb = document.querySelector('#timelineRail .timeline-scrubber-thumb');
  if (!thumb) return;
  const clampedRatio = clampTimelineRatio(ratio);
  thumb.style.top = getTimelineTopCss(clampedRatio);
  updateTimelineViewport(clampedRatio);
}

function layoutTimelinePoints() {
  const rail = document.getElementById('timelineRail');
  const layer = rail && rail.querySelector('.timeline-anchor-layer');
  const points = rail && Array.isArray(rail.__timelinePoints) ? rail.__timelinePoints : [];
  if (!rail || !layer || !points.length) return;
  const contentInset = TIMELINE_INSET_PX + TIMELINE_NAV_LANE_PX;
  const availableHeight = Math.max(1, rail.clientHeight - (contentInset * 2));
  const virtualSpan = Math.max(availableHeight, Math.max(0, points.length - 1) * TIMELINE_MIN_POINT_GAP_PX);
  const overflow = Math.max(0, virtualSpan - availableHeight);
  rail.__timelineLayout = { availableHeight, virtualSpan, overflow };
  points.forEach((point, index) => {
    if (!point.marker) return;
    const ratio = points.length <= 1 ? 0 : index / (points.length - 1);
    point.marker.style.top = `${contentInset + (ratio * virtualSpan)}px`;
  });
  updateTimelineViewport(rail.__currentTimelineRatio || 0);
}

function syncTimelineViewportBox() {
  const rail = document.getElementById('timelineRail');
  const main = document.querySelector('main');
  if (!rail || !main) return;
  const mainRect = main.getBoundingClientRect();
  const availableHeight = Math.max(0, Math.floor(mainRect.height - TIMELINE_VIEWPORT_TOP_MARGIN_PX - TIMELINE_VIEWPORT_BOTTOM_MARGIN_PX));
  rail.style.top = `${TIMELINE_VIEWPORT_TOP_MARGIN_PX}px`;
  rail.style.height = `${Math.max(TIMELINE_MIN_HEIGHT_PX, availableHeight)}px`;
}

function panTimelineByWheel(deltaY) {
  const rail = document.getElementById('timelineRail');
  const layout = rail && rail.__timelineLayout;
  if (!rail || !layout || !(layout.overflow > 0)) return false;
  beginTimelineWheelSession();
  const currentRatio = clampTimelineRatio(rail.__currentTimelineRatio || 0);
  const nextRatio = clampTimelineRatio(currentRatio + (deltaY / Math.max(layout.virtualSpan, 1)));
  gTimelineHoverActive = true;
  gTimelineScrubRatio = nextRatio;
  updateTimelineThumb(nextRatio);
  refreshTimelineTooltip(nextRatio);
  scrollTimelineToRatio(nextRatio);
  return true;
}

function nudgeTimelineByStep(direction) {
  const rail = document.getElementById('timelineRail');
  const points = rail && Array.isArray(rail.__timelinePoints) ? rail.__timelinePoints : [];
  if (!rail || !points.length) return;
  beginTimelineNavigationSession();
  const stepRatio = points.length <= 1 ? 0.08 : Math.max(1 / Math.max(1, points.length - 1), 0.055);
  const currentRatio = clampTimelineRatio(rail.__currentTimelineRatio || 0);
  const nextRatio = clampTimelineRatio(currentRatio + (direction * stepRatio));
  gTimelineHoverActive = true;
  gTimelineScrubRatio = nextRatio;
  updateTimelineThumb(nextRatio);
  refreshTimelineTooltip(nextRatio);
  scrollTimelineToRatio(nextRatio);
  endTimelineNavigationSession(220);
}

function getTimelineHoverPoint(ratio) {
  const rail = document.getElementById('timelineRail');
  const points = rail && Array.isArray(rail.__timelinePoints) ? rail.__timelinePoints : [];
  if (!points.length) return null;
  const clampedRatio = clampTimelineRatio(ratio);
  let closest = points[0];
  let closestDistance = Math.abs(clampedRatio - closest.ratio);
  for (let i = 1; i < points.length; i += 1) {
    const point = points[i];
    const distance = Math.abs(clampedRatio - point.ratio);
    if (distance < closestDistance) {
      closest = point;
      closestDistance = distance;
    }
  }
  return closest;
}

function setTimelineTooltip(visible, ratio = 0, text = '') {
  const rail = document.getElementById('timelineRail');
  const tooltip = rail && rail.querySelector('.timeline-scrubber-tooltip');
  if (!rail || !tooltip) return;
  const shouldShow = !!visible && !!text;
  tooltip.hidden = !shouldShow;
  rail.classList.toggle('is-hovering', shouldShow);
  if (!shouldShow) return;
  tooltip.textContent = text;
  tooltip.style.top = `calc(${TIMELINE_INSET_PX + TIMELINE_NAV_LANE_PX}px + ${clampTimelineRatio(ratio)} * (100% - ${(TIMELINE_INSET_PX + TIMELINE_NAV_LANE_PX) * 2}px))`;
}

function showTimelineTooltipForPoint(point) {
  const rail = document.getElementById('timelineRail');
  if (rail) rail.__activeSnapTarget = point || null;
  if (!point) {
    setTimelineTooltip(false);
    return;
  }
  setTimelineTooltip(true, point.ratio, point.title || point.label || '');
}

function refreshTimelineTooltip(ratio) {
  const point = getTimelineHoverPoint(ratio);
  if (!point) {
    const rail = document.getElementById('timelineRail');
    if (rail) rail.__activeSnapTarget = null;
    setTimelineTooltip(false);
    return null;
  }
  const rail = document.getElementById('timelineRail');
  if (rail) rail.__activeSnapTarget = point;
  setTimelineTooltip(gTimelineScrubActive || gTimelineHoverActive, ratio, point.title || point.label || '');
  return point;
}

function getTimelineRatioFromClientY(clientY) {
  const rail = document.getElementById('timelineRail');
  const track = rail && rail.querySelector('.timeline-scrubber-track');
  if (!track) return 0;
  const rect = track.getBoundingClientRect();
  const rawRatio = rect.height <= 0 ? 0 : (clientY - rect.top) / rect.height;
  return clampTimelineRatio(rawRatio);
}

function refreshTimelineScrollTargets() {
  const rail = document.getElementById('timelineRail');
  const main = document.querySelector('main');
  if (!rail || !main) return;
  const baseTargets = Array.isArray(rail.__snapTargets) ? rail.__snapTargets : [];
  const mainRect = main.getBoundingClientRect();
  rail.__scrollTargets = baseTargets
    .map((target) => {
      const section = document.querySelector(`.gallery-group[data-group-key="${CSS.escape(target.key)}"]`);
      if (!section) return null;
      const sectionRect = section.getBoundingClientRect();
      return {
        ...target,
        scrollTop: main.scrollTop + (sectionRect.top - mainRect.top),
      };
    })
    .filter(Boolean)
    .sort((a, b) => a.ratio - b.ratio);
}

function applyTimelineMarkerStates() {
  const rail = document.getElementById('timelineRail');
  const points = rail && Array.isArray(rail.__timelinePoints) ? rail.__timelinePoints : [];
  points.forEach((point) => {
    if (!point.marker) return;
    const isActive = !!gTimelineActiveGroupKey && point.key === gTimelineActiveGroupKey;
    const isVisible = gTimelineVisibleGroupKeys.has(point.key);
    point.marker.classList.toggle('is-active', isActive);
    point.marker.classList.toggle('is-visible', !isActive && isVisible);
    point.marker.classList.toggle('is-dim', !isActive && !isVisible);
  });
}

function setTimelineActiveGroupKey(groupKey) {
  gTimelineActiveGroupKey = groupKey || '';
  applyTimelineMarkerStates();
}

function refreshVisibleTimelineAnchors() {
  const main = document.querySelector('main');
  const sections = document.querySelectorAll('.gallery-group[data-group-key]');
  if (!main || !sections.length) {
    gTimelineVisibleGroupKeys = new Set();
    applyTimelineMarkerStates();
    return;
  }
  const mainRect = main.getBoundingClientRect();
  const visibleKeys = new Set();
  sections.forEach((section) => {
    const header = section.querySelector('.gallery-group-header');
    if (!header) return;
    const rect = header.getBoundingClientRect();
    const visibleHeight = Math.min(rect.bottom, mainRect.bottom) - Math.max(rect.top, mainRect.top);
    if (visibleHeight >= 12) {
      const key = section.dataset.groupKey || '';
      if (key) visibleKeys.add(key);
    }
  });
  gTimelineVisibleGroupKeys = visibleKeys;
  applyTimelineMarkerStates();
}

function disconnectTimelineHeaderObserver() {
  if (gTimelineHeaderObserver) {
    gTimelineHeaderObserver.disconnect();
    gTimelineHeaderObserver = null;
  }
}

function debugGalleryDrag(message) {
  if (gBridge && gBridge.debug_log) {
    gBridge.debug_log(`[gallery-dnd] ${message}`);
  }
}

function setupTimelineHeaderObserver() {
  disconnectTimelineHeaderObserver();
  gTimelineVisibleGroupKeys = new Set();
  const main = document.querySelector('main');
  const sections = document.querySelectorAll('.gallery-group[data-group-key]');
  if (!main || !sections.length || typeof IntersectionObserver === 'undefined') {
    refreshVisibleTimelineAnchors();
    return;
  }
  gTimelineHeaderObserver = new IntersectionObserver((entries) => {
    let changed = false;
    entries.forEach((entry) => {
      const section = entry.target.closest('.gallery-group[data-group-key]');
      const key = section && section.dataset.groupKey;
      if (!key) return;
      const isVisible = entry.isIntersecting && entry.intersectionRect.height >= 12;
      if (isVisible) {
        if (!gTimelineVisibleGroupKeys.has(key)) {
          gTimelineVisibleGroupKeys.add(key);
          changed = true;
        }
      } else if (gTimelineVisibleGroupKeys.delete(key)) {
        changed = true;
      }
    });
    if (changed) applyTimelineMarkerStates();
  }, {
    root: main,
    threshold: [0, 0.25, 0.5, 0.75, 1],
    rootMargin: '-8px 0px -8px 0px',
  });

  sections.forEach((section) => {
    const header = section.querySelector('.gallery-group-header');
    if (header) gTimelineHeaderObserver.observe(header);
  });
  refreshVisibleTimelineAnchors();
}

function getNearestTimelinePointForRatio(ratio) {
  const rail = document.getElementById('timelineRail');
  const points = rail && Array.isArray(rail.__timelinePoints) ? rail.__timelinePoints : [];
  if (!points.length) return null;
  const clampedRatio = clampTimelineRatio(ratio);
  let closest = points[0];
  let closestDistance = Math.abs(clampedRatio - closest.ratio);
  for (let i = 1; i < points.length; i += 1) {
    const point = points[i];
    const distance = Math.abs(clampedRatio - point.ratio);
    if (distance < closestDistance) {
      closest = point;
      closestDistance = distance;
    }
  }
  return closest;
}

function getActiveTimelineScrollTargets() {
  if (Array.isArray(gTimelineScrollTargetsFrozen) && gTimelineScrollTargetsFrozen.length) {
    return gTimelineScrollTargetsFrozen;
  }
  const rail = document.getElementById('timelineRail');
  return rail && Array.isArray(rail.__scrollTargets) ? rail.__scrollTargets : [];
}

function freezeTimelineScrollTargets() {
  refreshTimelineScrollTargets();
  const rail = document.getElementById('timelineRail');
  const targets = rail && Array.isArray(rail.__scrollTargets) ? rail.__scrollTargets : [];
  gTimelineScrollTargetsFrozen = targets.map(target => ({ ...target }));
}

function unfreezeTimelineScrollTargets() {
  gTimelineScrollTargetsFrozen = null;
}

function beginTimelineWheelSession() {
  beginTimelineNavigationSession();
  endTimelineNavigationSession(180);
}

function beginTimelineNavigationSession() {
  const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
  gTimelineNavigationActiveUntil = now + 240;
  freezeTimelineScrollTargets();
}

function endTimelineNavigationSession(delayMs = 180) {
  if (gTimelineWheelSessionTimer) clearTimeout(gTimelineWheelSessionTimer);
  gTimelineWheelSessionTimer = setTimeout(() => {
    gTimelineWheelSessionTimer = 0;
    if (gTimelineScrubActive) return;
    const settleNow = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    gTimelineNavigationActiveUntil = settleNow + 240;
    unfreezeTimelineScrollTargets();
    scheduleTimelineScrollTargetRefresh();
  }, delayMs);
}

function scheduleTimelineScrollTargetRefresh() {
  const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
  if (gTimelineScrubActive || now <= gTimelineNavigationActiveUntil) {
    if (!gTimelineRefreshTargetsRaf) {
      gTimelineRefreshTargetsRaf = requestAnimationFrame(() => {
        gTimelineRefreshTargetsRaf = 0;
        scheduleTimelineScrollTargetRefresh();
      });
    }
    return;
  }
  if (gTimelineRefreshTargetsRaf) return;
  gTimelineRefreshTargetsRaf = requestAnimationFrame(() => {
    gTimelineRefreshTargetsRaf = 0;
    refreshTimelineScrollTargets();
    syncTimelineFromScroll();
  });
}

function getTimelineInterpolatedStateFromScroll(scrollTop) {
  const targets = getActiveTimelineScrollTargets();
  if (!targets.length) return null;
  if (targets.length === 1) return { ratio: targets[0].ratio, point: targets[0] };
  if (scrollTop <= targets[0].scrollTop) return { ratio: targets[0].ratio, point: targets[0] };
  const last = targets[targets.length - 1];
  if (scrollTop >= last.scrollTop) return { ratio: last.ratio, point: last };
  for (let i = 0; i < targets.length - 1; i += 1) {
    const current = targets[i];
    const next = targets[i + 1];
    if (scrollTop >= current.scrollTop && scrollTop <= next.scrollTop) {
      const span = next.scrollTop - current.scrollTop;
      const progress = span <= 0 ? 0 : (scrollTop - current.scrollTop) / span;
      return {
        ratio: current.ratio + ((next.ratio - current.ratio) * progress),
        point: progress < 0.5 ? current : next,
      };
    }
  }
  return { ratio: last.ratio, point: last };
}

function syncTimelineFromScroll() {
  const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
  if (gTimelineScrubActive || now <= gTimelineNavigationActiveUntil) return;
  const main = document.querySelector('main');
  if (!main) return;
  const targets = getActiveTimelineScrollTargets();
  if (!targets.length) return;
  const maxScrollTop = Math.max(0, main.scrollHeight - main.clientHeight);
  const atBottom = maxScrollTop <= 0 || main.scrollTop >= (maxScrollTop - 4);
  if (atBottom) {
    const last = targets[targets.length - 1];
    updateTimelineThumb(last.ratio);
    setTimelineActiveGroupKey(last.key);
    if (gTimelineHoverActive) showTimelineTooltipForPoint(last);
    gTimelineLastScrollTop = main.scrollTop;
    gTimelineLastThumbRatio = last.ratio;
    return;
  }
  const state = getTimelineInterpolatedStateFromScroll(main.scrollTop);
  if (!state) return;
  const scrollDelta = main.scrollTop - gTimelineLastScrollTop;
  let nextRatio = state.ratio;

  // During active user scrolling, ignore small backward corrections caused by
  // lazy-load/layout shifts so the timeline keeps moving in the intended direction.
  if (now <= gTimelineUserScrollActiveUntil) {
    const backwardThreshold = 0.035;
    if (scrollDelta > 0 && nextRatio < (gTimelineLastThumbRatio - backwardThreshold)) {
      nextRatio = gTimelineLastThumbRatio;
    } else if (scrollDelta < 0 && nextRatio > (gTimelineLastThumbRatio + backwardThreshold)) {
      nextRatio = gTimelineLastThumbRatio;
    }
  }

  updateTimelineThumb(nextRatio);
  setTimelineActiveGroupKey(state.point && state.point.key ? state.point.key : '');
  if (gTimelineHoverActive) refreshTimelineTooltip(nextRatio);
  gTimelineLastScrollTop = main.scrollTop;
  gTimelineLastThumbRatio = nextRatio;
}

function scrollTimelineToRatio(ratio) {
  const main = document.querySelector('main');
  const targets = getActiveTimelineScrollTargets();
  if (!main || !targets.length) return;
  const clampedRatio = clampTimelineRatio(ratio);
  if (targets.length === 1) {
    main.scrollTop = targets[0].scrollTop;
    return;
  }
  if (clampedRatio <= targets[0].ratio) {
    main.scrollTop = targets[0].scrollTop;
    return;
  }
  const last = targets[targets.length - 1];
  if (clampedRatio >= last.ratio) {
    main.scrollTop = last.scrollTop;
    return;
  }
  for (let i = 0; i < targets.length - 1; i += 1) {
    const current = targets[i];
    const next = targets[i + 1];
    if (clampedRatio >= current.ratio && clampedRatio <= next.ratio) {
      const span = next.ratio - current.ratio;
      const progress = span <= 0 ? 0 : (clampedRatio - current.ratio) / span;
      main.scrollTop = current.scrollTop + ((next.scrollTop - current.scrollTop) * progress);
      return;
    }
  }
}

function snapTimelineToNearestPoint(ratio) {
  const rail = document.getElementById('timelineRail');
  const targets = rail && Array.isArray(rail.__snapTargets) ? rail.__snapTargets : [];
  if (!targets.length) return;
  const activeTarget = rail && rail.__activeSnapTarget;
  if (activeTarget && activeTarget.key) {
    updateTimelineThumb(activeTarget.ratio);
    showTimelineTooltipForPoint(activeTarget);
    scrollToGroup(activeTarget.key);
    return;
  }
  const clampedRatio = clampTimelineRatio(ratio);
  let closest = targets[0];
  let closestDistance = Math.abs(clampedRatio - closest.ratio);
  for (let i = 1; i < targets.length; i += 1) {
    const target = targets[i];
    const distance = Math.abs(clampedRatio - target.ratio);
    if (distance < closestDistance) {
      closest = target;
      closestDistance = distance;
    }
  }
  updateTimelineThumb(closest.ratio);
  refreshTimelineTooltip(closest.ratio);
  scrollToGroup(closest.key);
}

function scrubTimelineAt(clientY, { snap = false } = {}) {
  const ratio = getTimelineRatioFromClientY(clientY);
  gTimelineScrubRatio = ratio;
  updateTimelineThumb(ratio);
  const point = getNearestTimelinePointForRatio(ratio);
  if (point) setTimelineActiveGroupKey(point.key);
  refreshTimelineTooltip(ratio);
  if (snap) snapTimelineToNearestPoint(ratio);
  else scrollTimelineToRatio(ratio);
}

function buildTimelinePoints(groups) {
  if (!Array.isArray(groups) || !groups.length) {
    return { points: [], snapTargets: [] };
  }

  const points = groups.map((group, index) => ({
    key: group.key,
    ratio: groups.length <= 1 ? 0 : index / (groups.length - 1),
    label: group.label,
    title: group.label,
  }));

  return {
    points,
    snapTargets: points,
  };
}

function renderTimelineRail(groups) {
  const rail = document.getElementById('timelineRail');
  if (!rail) return;
  disconnectTimelineHeaderObserver();
  rail.innerHTML = '';
  rail.__timelinePoints = [];
  rail.__snapTargets = [];
  rail.__scrollTargets = [];
  rail.__activeSnapTarget = null;
  gTimelineVisibleGroupKeys = new Set();
  gTimelineActiveGroupKey = '';
  rail.classList.remove('timeline-granularity-day', 'timeline-granularity-month', 'timeline-granularity-year');
  rail.classList.add(`timeline-granularity-${gGroupDateGranularity}`);

  if (gGroupBy !== 'date' || !Array.isArray(groups) || groups.length === 0) {
    rail.hidden = true;
    return;
  }

  const timeline = buildTimelinePoints(groups);
  rail.__timelinePoints = timeline.points;
  rail.__snapTargets = timeline.snapTargets;
  const scale = document.createElement('div');
  scale.className = 'timeline-scale';

  const upArrow = document.createElement('button');
  upArrow.type = 'button';
  upArrow.className = 'timeline-nav timeline-nav-up';
  upArrow.setAttribute('aria-label', 'Scroll timeline earlier');
  upArrow.textContent = '▲';
  upArrow.addEventListener('click', (e) => {
    e.preventDefault();
    nudgeTimelineByStep(-1);
  });
  scale.appendChild(upArrow);

  const downArrow = document.createElement('button');
  downArrow.type = 'button';
  downArrow.className = 'timeline-nav timeline-nav-down';
  downArrow.setAttribute('aria-label', 'Scroll timeline later');
  downArrow.textContent = '▼';
  downArrow.addEventListener('click', (e) => {
    e.preventDefault();
    nudgeTimelineByStep(1);
  });
  scale.appendChild(downArrow);

  const anchorLayer = document.createElement('div');
  anchorLayer.className = 'timeline-anchor-layer';
  scale.appendChild(anchorLayer);
  timeline.points.forEach((point) => {
    const marker = document.createElement('button');
    marker.type = 'button';
    marker.className = 'timeline-marker timeline-entry is-dim';
    marker.textContent = point.label;
    marker.setAttribute('aria-label', point.title);
    marker.dataset.groupKey = point.key;
    point.marker = marker;
    marker.addEventListener('click', () => scrollToGroup(point.key));
    marker.addEventListener('pointerenter', () => {
      gTimelineHoverActive = true;
      showTimelineTooltipForPoint(point);
    });
    marker.addEventListener('pointermove', () => {
      gTimelineHoverActive = true;
      showTimelineTooltipForPoint(point);
    });
    marker.addEventListener('pointerleave', () => {
      if (gTimelineScrubActive) return;
      gTimelineHoverActive = false;
      setTimelineTooltip(false);
    });
    anchorLayer.appendChild(marker);
  });

  const scrubber = document.createElement('div');
  scrubber.className = 'timeline-scrubber';
  scrubber.innerHTML = '<div class="timeline-scrubber-tooltip" hidden></div><div class="timeline-scrubber-track"></div><div class="timeline-scrubber-thumb"></div>';
  scrubber.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    if (scrubber.setPointerCapture) scrubber.setPointerCapture(e.pointerId);
    const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    gTimelineNavigationActiveUntil = now + 240;
    freezeTimelineScrollTargets();
    gTimelineScrubActive = true;
    gTimelineHoverActive = true;
    gTimelineScrubPointerId = e.pointerId;
    scrubTimelineAt(e.clientY, { snap: false });
  });
  scrubber.addEventListener('pointerenter', (e) => {
    gTimelineHoverActive = true;
    refreshTimelineTooltip(getTimelineRatioFromClientY(e.clientY));
  });
  scrubber.addEventListener('pointermove', (e) => {
    if (!gTimelineHoverActive && !gTimelineScrubActive) return;
    refreshTimelineTooltip(getTimelineRatioFromClientY(e.clientY));
  });
  scrubber.addEventListener('pointerleave', () => {
    if (gTimelineScrubActive) return;
    gTimelineHoverActive = false;
    setTimelineTooltip(false);
  });
  scrubber.addEventListener('wheel', (e) => {
    if (!panTimelineByWheel(e.deltaY)) return;
    e.preventDefault();
  }, { passive: false });
  scale.appendChild(scrubber);

  rail.appendChild(scale);
  requestAnimationFrame(() => {
    syncTimelineViewportBox();
    layoutTimelinePoints();
    setupTimelineHeaderObserver();
    applyTimelineMarkerStates();
    scheduleTimelineScrollTargetRefresh();
  });
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
  const similaritySelect = document.getElementById('similarityThresholdSelect');
  if (similaritySelect) {
    similaritySelect.hidden = !['similar', 'similar_only'].includes(gGroupBy);
  }
}

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function setReviewMode(mode) {
  const nextMode = mode === 'similar_only' ? 'similar_only' : (mode === 'similar' ? 'similar' : 'duplicates');
  if (!REVIEW_VIEW_MODES.has(gGalleryViewMode)) {
    gLastStandardViewMode = gGalleryViewMode;
  }
  applyGalleryViewMode(nextMode);
  updateCtxViewState();
  return nextMode;
}

function clearReviewMode() {
  const restoreMode = gLastStandardViewMode && !REVIEW_VIEW_MODES.has(gLastStandardViewMode) ? gLastStandardViewMode : 'masonry';
  applyGalleryViewMode(restoreMode);
  updateCtxViewState();
  return restoreMode;
}

function setDuplicateMode(active) {
  if (active) {
    if (!REVIEW_VIEW_MODES.has(gGalleryViewMode)) {
      gLastStandardViewMode = gGalleryViewMode;
    }
    applyGalleryViewMode('duplicates');
    updateCtxViewState();
    return 'duplicates';
  }
  const restoreMode = gLastStandardViewMode && !REVIEW_VIEW_MODES.has(gLastStandardViewMode) ? gLastStandardViewMode : 'masonry';
  applyGalleryViewMode(restoreMode);
  updateCtxViewState();
  return restoreMode;
}

function openFolderItem(path) {
  if (gBridge && gBridge.navigate_to_folder && path) {
    deselectAll();
    gBridge.navigate_to_folder(path);
  }
}

function isInternalGalleryDragEvent(e) {
  if (gBridge && Array.isArray(gBridge.drag_paths) && gBridge.drag_paths.length) return true;
  const dt = e && e.dataTransfer;
  if (!dt) return gCurrentDragCount > 0;
  try {
    if (dt.types && Array.from(dt.types).includes('web/mmx-paths')) return true;
    if (dt.getData && dt.getData('web/mmx-paths')) return true;
  } catch (_err) {
    // Ignore inaccessible drag data and fall back to local state.
  }
  return gCurrentDragCount > 0;
}

function getDraggedPathsFromDataTransfer(dt) {
  if (Array.isArray(gCurrentDragPaths) && gCurrentDragPaths.length) {
    return gCurrentDragPaths.slice();
  }
  if (gBridge && Array.isArray(gBridge.drag_paths) && gBridge.drag_paths.length) {
    return gBridge.drag_paths.slice();
  }
  if (!dt) return [];
  const customPaths = dt.getData('web/mmx-paths');
  if (customPaths) {
    try {
      const parsed = JSON.parse(customPaths);
      if (Array.isArray(parsed)) return parsed.filter(Boolean);
    } catch (_err) {
      // Ignore malformed custom path payloads and fall through.
    }
  }
  if (dt.files && dt.files.length) {
    return Array.from(dt.files).map((file) => file.path).filter(Boolean);
  }
  const uriList = dt.getData('text/uri-list');
  if (uriList) {
    return uriList
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith('#'))
      .map((line) => {
        try {
          if (!line.startsWith('file:///')) return '';
          return decodeURIComponent(line.replace('file:///', '').replace(/\//g, '\\'));
        } catch (_err) {
          return '';
        }
      })
      .filter(Boolean);
  }
  return [];
}

function getDraggedPathsFromEvent(e) {
  return getDraggedPathsFromDataTransfer(e && e.dataTransfer);
}

function clearGalleryFolderDropTargets() {
  document.querySelectorAll('.folder-drop-target').forEach((node) => node.classList.remove('folder-drop-target'));
  gCurrentTargetFolderName = '';
  gCurrentDropFolderPath = '';
  gCurrentDropFolderCard = null;
}

function getEligibleDroppedPaths(paths, targetPath) {
  if (!Array.isArray(paths) || !paths.length || !targetPath) return [];
  const targetNorm = targetPath.replace(/\//g, '\\').toLowerCase();
  return paths.filter((path) => {
    const srcFolder = (path || '').replace(/\//g, '\\').replace(/\\[^\\]+$/, '').toLowerCase();
    return srcFolder !== targetNorm;
  });
}

function cancelInternalGalleryDrop(e) {
  if (!isInternalGalleryDragEvent(e)) return false;
  e.preventDefault();
  e.stopPropagation();
  debugGalleryDrag(`cancel hovered=${gCurrentDropFolderPath || ''} dragCount=${gCurrentDragPaths.length}`);
  if (gBridge && gBridge.hide_drag_tooltip) gBridge.hide_drag_tooltip();
  clearGalleryFolderDropTargets();
  return true;
}

function getFolderCardFromEventTarget(target) {
  const node = target && target.nodeType === Node.TEXT_NODE ? target.parentElement : target;
  if (!node || !node.closest) return null;
  return node.closest('.folder-card');
}

function getFolderCardFromPoint(clientX, clientY, fallbackTarget = null) {
  const hit = typeof document.elementFromPoint === 'function'
    ? document.elementFromPoint(clientX, clientY)
    : null;
  const fromPoint = getFolderCardFromEventTarget(hit);
  if (fromPoint) return fromPoint;
  return getFolderCardFromEventTarget(fallbackTarget);
}

function updateGalleryDragHoverFromPoint(clientX, clientY, fallbackTarget = null) {
  const folderCard = getFolderCardFromPoint(clientX, clientY, fallbackTarget);
  const targetPath = folderCard ? (folderCard.getAttribute('data-path') || '') : '';
  const eligiblePaths = getEligibleDroppedPaths(gCurrentDragPaths, targetPath);
  if (!folderCard || !targetPath || !eligiblePaths.length) {
    clearGalleryFolderDropTargets();
    return false;
  }
  if (gCurrentDropFolderCard !== folderCard) {
    clearGalleryFolderDropTargets();
    folderCard.classList.add('folder-drop-target');
    gCurrentDropFolderCard = folderCard;
    gCurrentTargetFolderName = getItemName({ path: targetPath, is_folder: true });
    gCurrentDropFolderPath = targetPath;
    debugGalleryDrag(`hover folder=${targetPath} eligible=${eligiblePaths.length}`);
  }
  return true;
}

function executeGalleryDropToCurrentTarget(isCopy) {
  const targetPath = gCurrentDropFolderPath || '';
  const eligiblePaths = getEligibleDroppedPaths(gCurrentDragPaths, targetPath);
  if (!targetPath || !eligiblePaths.length || gGalleryDragHandled) return false;
  gGalleryDragHandled = true;
  if (gBridge && gBridge.hide_drag_tooltip) gBridge.hide_drag_tooltip();
  debugGalleryDrag(`execute target=${targetPath} count=${eligiblePaths.length} op=${isCopy ? 'copy' : 'move'}`);
  setGlobalLoading(true, isCopy ? 'Copying…' : 'Moving…', 25);
  if (gBridge && (isCopy ? gBridge.copy_paths_async : gBridge.move_paths_async)) {
    const op = isCopy ? gBridge.copy_paths_async : gBridge.move_paths_async;
    op.call(gBridge, eligiblePaths, targetPath);
    return true;
  }
  return false;
}

function createStructuredCard(item, idx) {
  const mediaIdx = getItemIndex(item, idx);
  const card = document.createElement('div');
  const isFolder = !!item.is_folder;
  const usesThumbnails = viewUsesThumbnails();
  const supportsInlinePlayback = !isFolder && item.media_type === 'video' && viewSupportsInlineVideoPlayback();
  const duplicateMode = isDuplicateModeActive();
  card.className = `card structured-card${isFolder ? ' folder-card ready' : ' loading'}`;
  if (duplicateMode && !isFolder) card.classList.add('duplicate-card');
  card.tabIndex = 0;
  card.setAttribute('data-path', item.path || '');
  card.setAttribute('data-is-folder', isFolder ? 'true' : 'false');
  if (duplicateMode && !isFolder) {
    card.setAttribute('data-duplicate-group-key', item.duplicate_group_key || '');
    card.setAttribute('data-duplicate-keep', 'false');
  }

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
  title.title = item.path || getItemName(item);
  content.appendChild(title);

  const folder = document.createElement('div');
  folder.className = 'entry-folder';
  folder.textContent = duplicateMode ? (getItemFolder(item) || item.path || '') : getItemFolderDisplay(item);
  folder.title = getItemFolder(item) || item.path || '';
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

  if (duplicateMode && !isFolder) {
    const duplicateStats = document.createElement('div');
    duplicateStats.className = 'entry-detail duplicate-stats';
    duplicateStats.textContent = [formatFileSize(item.file_size), formatModifiedTime(item.modified_time)].filter(Boolean).join(' • ');
    content.appendChild(duplicateStats);

    const controls = document.createElement('div');
    controls.className = 'duplicate-card-controls';

    const keepLabel = document.createElement('label');
    keepLabel.className = 'duplicate-keep-label';
    const keepToggle = document.createElement('input');
    keepToggle.type = 'checkbox';
    keepToggle.className = 'duplicate-keep-toggle';
    keepToggle.checked = false;
    keepToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      setDuplicateKeepPath(item.duplicate_group_key || '', item.path || '');
    });
    keepLabel.appendChild(keepToggle);
    const keepText = document.createElement('span');
    keepText.textContent = 'Keep';
    keepLabel.appendChild(keepText);
    controls.appendChild(keepLabel);

    const trashBtn = document.createElement('button');
    trashBtn.type = 'button';
    trashBtn.className = 'duplicate-trash-btn';
    trashBtn.title = 'Delete this file';
    trashBtn.setAttribute('aria-label', 'Delete this file');
    trashBtn.textContent = '🗑';
    trashBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      deleteDuplicateCard(item.path || '');
    });
    controls.appendChild(trashBtn);
    content.appendChild(controls);

    const reasons = Array.isArray(item.duplicate_category_reasons) ? item.duplicate_category_reasons.filter(Boolean) : [];
    if (reasons.length) {
      const duplicateMeta = document.createElement('div');
      duplicateMeta.className = 'entry-detail duplicate-reason-list';
      reasons.forEach((reason) => {
        const chip = document.createElement('div');
        chip.className = 'duplicate-reason';
        chip.textContent = reason;
        duplicateMeta.appendChild(chip);
      });
      content.appendChild(duplicateMeta);
    }

    if (item.duplicate_is_overall_best) {
      const overallBest = document.createElement('div');
      overallBest.className = 'entry-detail duplicate-overall-best';
      overallBest.textContent = '★ Best overall';
      overallBest.hidden = false;
      content.appendChild(overallBest);
    } else {
      const overallBest = document.createElement('div');
      overallBest.className = 'entry-detail duplicate-overall-best';
      overallBest.textContent = '★ Best overall';
      overallBest.hidden = true;
      content.appendChild(overallBest);
    }
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

  if (isFolder) {
    card.addEventListener('dragenter', (e) => {
      if (!isInternalGalleryDragEvent(e)) return;
      const paths = getDraggedPathsFromEvent(e);
      const targetPath = item.path || '';
      const eligiblePaths = getEligibleDroppedPaths(paths, targetPath);
      if (!eligiblePaths.length) return;
      e.preventDefault();
      e.stopPropagation();
      clearGalleryFolderDropTargets();
      card.classList.add('folder-drop-target');
      gCurrentTargetFolderName = getItemName(item);
      gCurrentDropFolderPath = targetPath;
    });
    card.addEventListener('dragover', (e) => {
      if (!isInternalGalleryDragEvent(e)) return;
      const paths = getDraggedPathsFromEvent(e);
      const targetPath = item.path || '';
      const eligiblePaths = getEligibleDroppedPaths(paths, targetPath);
      if (!eligiblePaths.length) {
        card.classList.remove('folder-drop-target');
        return;
      }
      e.preventDefault();
      e.stopPropagation();
      const isCopy = e.ctrlKey || e.metaKey;
      if (e.dataTransfer) e.dataTransfer.dropEffect = isCopy ? 'copy' : 'move';
      if (!card.classList.contains('folder-drop-target')) {
        clearGalleryFolderDropTargets();
        card.classList.add('folder-drop-target');
        gCurrentTargetFolderName = getItemName(item);
        gCurrentDropFolderPath = targetPath;
        debugGalleryDrag(`hover folder=${targetPath} eligible=${eligiblePaths.length}`);
      }
      if (gBridge && gBridge.update_drag_tooltip) {
        const count = gCurrentDragCount || eligiblePaths.length || 1;
        gBridge.update_drag_tooltip(count, isCopy, gCurrentTargetFolderName);
      }
    });
    card.addEventListener('dragleave', (e) => {
      if (card.contains(e.relatedTarget)) return;
      clearGalleryFolderDropTargets();
    });
    card.addEventListener('drop', (e) => {
      if (!isInternalGalleryDragEvent(e)) return;
      const paths = getDraggedPathsFromEvent(e);
      const targetPath = item.path || gCurrentDropFolderPath || '';
      const eligiblePaths = getEligibleDroppedPaths(paths, targetPath);
      e.preventDefault();
      e.stopPropagation();
      clearGalleryFolderDropTargets();
      if (!eligiblePaths.length) {
        debugGalleryDrag(`folder-card drop ignored target=${targetPath} paths=${paths.length}`);
        return;
      }
      const isCopy = e.ctrlKey || e.metaKey;
      if (gBridge && gBridge.hide_drag_tooltip) gBridge.hide_drag_tooltip();
      debugGalleryDrag(`folder-card drop execute target=${targetPath} count=${eligiblePaths.length} op=${isCopy ? 'copy' : 'move'}`);
      setGlobalLoading(true, isCopy ? 'Copying…' : 'Moving…', 25);
      if (gBridge && (isCopy ? gBridge.copy_paths_async : gBridge.move_paths_async)) {
        const op = isCopy ? gBridge.copy_paths_async : gBridge.move_paths_async;
        op.call(gBridge, eligiblePaths, targetPath);
      }
    });
  } else {
    card.draggable = true;
    card.addEventListener('dragover', (e) => {
      if (!isInternalGalleryDragEvent(e)) return;
      e.preventDefault();
      e.stopPropagation();
      if (e.dataTransfer) e.dataTransfer.dropEffect = 'none';
    });
    card.addEventListener('drop', (e) => {
      cancelInternalGalleryDrop(e);
    });
    card.addEventListener('dragstart', (e) => {
      const path = item.path || '';
      if (!path) return;
      const paths = gSelectedPaths.has(path) ? Array.from(gSelectedPaths) : [path];
      if (startNativeGalleryDrag(e, item, paths)) return;
      const urls = paths.map(p => 'file:///' + p.replace(/\\/g, '/'));
      const pathsJson = JSON.stringify(paths);
      e.dataTransfer.setData('text/uri-list', urls.join('\r\n'));
      e.dataTransfer.setData('text/plain', pathsJson);
      e.dataTransfer.setData('web/mmx-paths', pathsJson);
      e.dataTransfer.setData('application/x-mmx-type', 'file');
      primeGalleryDragState(paths);
      e.dataTransfer.effectAllowed = 'copyMove';
    });
    card.addEventListener('drag', (e) => {
      if (gBridge && gBridge.update_drag_tooltip && e.clientX > 0 && e.clientY > 0) {
        updateGalleryDragHoverFromPoint(e.clientX, e.clientY, e.target);
        const isCopy = e.ctrlKey || e.metaKey;
        const count = gCurrentDragCount || 1;
        gBridge.update_drag_tooltip(count, isCopy, gCurrentTargetFolderName);
      }
    });
    card.addEventListener('dragend', (e) => {
      if (e && e.clientX > 0 && e.clientY > 0) {
        updateGalleryDragHoverFromPoint(e.clientX, e.clientY, e.target);
      }
      executeGalleryDropToCurrentTarget(!!(e && (e.ctrlKey || e.metaKey)));
      clearGalleryDragState();
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

      if (startNativeGalleryDrag(e, item, paths)) return;

      const urls = paths.map(p => 'file:///' + p.replace(/\\/g, '/'));
      const pathsJson = JSON.stringify(paths);

      e.dataTransfer.setData('text/uri-list', urls.join('\r\n'));
      e.dataTransfer.setData('text/plain', pathsJson);
      e.dataTransfer.setData('web/mmx-paths', pathsJson);
      e.dataTransfer.setData('application/x-mmx-type', 'file');

      primeGalleryDragState(paths);
      e.dataTransfer.effectAllowed = 'copyMove';

      const previewImg = card.querySelector('img');
      if (previewImg) {
        const canvas = buildDragPreviewCanvas(previewImg, item);
        if (canvas) {
          e.dataTransfer.setDragImage(canvas, 0, 0);
        }
      }
    });
    card.addEventListener('drag', (e) => {
      if (gBridge && gBridge.update_drag_tooltip && e.clientX > 0 && e.clientY > 0) {
        updateGalleryDragHoverFromPoint(e.clientX, e.clientY, e.target);
        const isCopy = e.ctrlKey || e.metaKey;
        const count = gCurrentDragCount || 1;
        gBridge.update_drag_tooltip(count, isCopy, gCurrentTargetFolderName);
      }
    });
    card.addEventListener('dragend', (e) => {
      if (e && e.clientX > 0 && e.clientY > 0) {
        updateGalleryDragHoverFromPoint(e.clientX, e.clientY, e.target);
      }
      executeGalleryDropToCurrentTarget(!!(e && (e.ctrlKey || e.metaKey)));
      clearGalleryDragState();
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
    if (startNativeGalleryDrag(e, item, paths)) return;
    const urls = paths.map(p => 'file:///' + p.replace(/\\/g, '/'));
    const pathsJson = JSON.stringify(paths);

    e.dataTransfer.setData('text/uri-list', urls.join('\r\n'));
    e.dataTransfer.setData('text/plain', pathsJson);
    e.dataTransfer.setData('web/mmx-paths', pathsJson);
    e.dataTransfer.setData('application/x-mmx-type', 'file');

    primeGalleryDragState(paths);
    e.dataTransfer.effectAllowed = 'copyMove';
  });
  card.addEventListener('drag', (e) => {
    if (gBridge && gBridge.update_drag_tooltip && e.clientX > 0 && e.clientY > 0) {
      updateGalleryDragHoverFromPoint(e.clientX, e.clientY, e.target);
      const isCopy = e.ctrlKey || e.metaKey;
      const count = gCurrentDragCount || 1;
      gBridge.update_drag_tooltip(count, isCopy, gCurrentTargetFolderName);
    }
  });
  card.addEventListener('dragend', (e) => {
    if (e && e.clientX > 0 && e.clientY > 0) {
      updateGalleryDragHoverFromPoint(e.clientX, e.clientY, e.target);
    }
    executeGalleryDropToCurrentTarget(!!(e && (e.ctrlKey || e.metaKey)));
    clearGalleryDragState();
  });

  return card;
}

function renderStructuredMediaList(el, items, options = {}) {
  const { renderHeader = true } = options;
  if (gGalleryViewMode === 'details' && renderHeader) {
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

  if (gGalleryViewMode === 'details') {
    applyDetailsColumnWidths(el);
    renderDetailsHeader(el);
  }

  if (folderItems.length > 0) {
    const prefix = document.createElement('div');
    prefix.className = 'gallery-group-prefix';
    applyGalleryClasses(prefix, gGalleryViewMode);
    if (gGalleryViewMode === 'masonry') {
      folderItems.forEach((item, idx) => prefix.appendChild(createMasonryCard(item, idx)));
    } else {
      renderStructuredMediaList(prefix, folderItems, { renderHeader: false });
    }
    el.appendChild(prefix);
  }

  groups.forEach(group => {
    const section = document.createElement('section');
    section.className = 'gallery-group';
    section.dataset.groupKey = group.key;
    section.dataset.sortValue = Number.isFinite(group.sortValue) ? `${group.sortValue}` : '';
    section.dataset.rangeStart = Number.isFinite(group.rangeStart) ? `${group.rangeStart}` : '';
    section.dataset.rangeEnd = Number.isFinite(group.rangeEnd) ? `${group.rangeEnd}` : '';

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
      renderStructuredMediaList(body, group.items, { renderHeader: false });
    }

    section.appendChild(header);
    section.appendChild(body);
    el.appendChild(section);
    toggleGroupCollapsed(group.key, gCollapsedGroupKeys.has(group.key));
  });

  renderTimelineRail(groups);
  requestAnimationFrame(() => {
    restoreGroupScrollAnchor();
    scheduleTimelineScrollTargetRefresh();
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

function renderDuplicateMediaList(el, items) {
  const groups = buildDuplicateGroups(items);
  const reviewMode = getReviewMode();
  const isSimilarReview = reviewMode === 'similar' || reviewMode === 'similar_only';
  const groupLabel = isSimilarReview ? 'Similar Group' : 'Duplicate Group';
  const summaryLabel = isSimilarReview ? 'Similar Groups' : 'Duplicate Groups';
  const emptyLabel = isSimilarReview
    ? (gScanActive ? 'No similar images found in the current scope yet. Still scanning...' : 'No similar images found in the current scope.')
    : 'No duplicates found in the current scope.';
  if (!groups.length) {
    const div = document.createElement('div');
    div.className = 'empty';
    div.textContent = emptyLabel;
    el.appendChild(div);
    renderTimelineRail([]);
    return;
  }
  el.classList.add('gallery-grouped', 'gallery-duplicates-root');

  const summary = document.createElement('section');
  summary.className = 'duplicate-summary';
  const totalFiles = groups.reduce((sum, group) => sum + group.items.length, 0);
  const totalSavings = groups.reduce((sum, group) => sum + (group.sortValue || 0), 0);
  summary.innerHTML = `
    <div class="duplicate-summary-card">
      <div class="duplicate-summary-label">${summaryLabel}</div>
      <div class="duplicate-summary-value">${groups.length}</div>
    </div>
    <div class="duplicate-summary-card">
      <div class="duplicate-summary-label">Files in Groups</div>
      <div class="duplicate-summary-value">${totalFiles}</div>
    </div>
    <div class="duplicate-summary-card">
      <div class="duplicate-summary-label">Potential Savings</div>
      <div class="duplicate-summary-value">${escapeHtml(formatFileSize(totalSavings) || '0 B')}</div>
    </div>
  `;
  const summaryActions = document.createElement('div');
  summaryActions.className = 'duplicate-summary-actions';
  const autoResolveBtn = document.createElement('button');
  autoResolveBtn.type = 'button';
  autoResolveBtn.className = 'tb-btn highlight';
  autoResolveBtn.textContent = 'Auto Resolve All';
  autoResolveBtn.addEventListener('click', autoResolveAllDuplicateGroups);
  summaryActions.appendChild(autoResolveBtn);
  summary.appendChild(summaryActions);
  el.appendChild(summary);

  groups.forEach((group) => {
    const existingKeep = getDuplicateKeepPath(group.key);
    const groupPaths = new Set(group.items.map(item => item.path).filter(Boolean));
    if (!existingKeep || !groupPaths.has(existingKeep)) {
      gDuplicateKeepOverrides.set(group.key, (group.keepItem && group.keepItem.path) ? group.keepItem.path : (group.items[0] && group.items[0].path) || '');
    }
    const section = document.createElement('section');
    section.className = 'gallery-group duplicate-group';
    section.dataset.groupKey = group.key;

    const header = document.createElement('div');
    header.className = 'gallery-group-header duplicate-group-header';

    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'gallery-group-toggle';
    const title = group.label || `${groupLabel} ${groups.indexOf(group) + 1}`;
    toggle.innerHTML = `<span class="gallery-group-chevron" aria-hidden="true"></span><span class="gallery-group-title">${title}</span><span class="gallery-group-count">${group.items.length}</span>`;
    toggle.addEventListener('click', () => toggleGroupCollapsed(group.key));
    header.appendChild(toggle);

    const meta = document.createElement('div');
    meta.className = 'duplicate-group-meta';
    meta.textContent = group.subtitle;
    header.appendChild(meta);

    const body = document.createElement('div');
    applyGalleryClasses(body, 'duplicates');
    body.classList.add('gallery-group-body');
    renderStructuredMediaList(body, group.items, { renderHeader: false });

    const actions = document.createElement('div');
    actions.className = 'duplicate-group-actions';

    const keepBtn = document.createElement('button');
    keepBtn.type = 'button';
    keepBtn.className = 'tb-btn';
    keepBtn.textContent = 'Keep Best';
    keepBtn.addEventListener('click', () => keepBestInDuplicateGroup(group.key));
    actions.appendChild(keepBtn);

    const mergeBtn = document.createElement('button');
    mergeBtn.type = 'button';
    mergeBtn.className = 'tb-btn';
    mergeBtn.textContent = 'Merge Metadata';
    mergeBtn.addEventListener('click', () => mergeDuplicateGroupMetadata(group.key));
    actions.appendChild(mergeBtn);

    section.appendChild(header);
    section.appendChild(body);
    section.appendChild(actions);
    el.appendChild(section);
    toggleGroupCollapsed(group.key, gCollapsedGroupKeys.has(group.key));
  });

  renderTimelineRail([]);
  requestAnimationFrame(() => {
    restoreGroupScrollAnchor();
    groups.forEach((group) => {
      const keepPath = getDuplicateKeepPath(group.key);
      if (keepPath) {
        setDuplicateKeepPath(group.key, keepPath);
      }
    });
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
  const showGroupActions = gGroupBy === 'date' || isDuplicateModeActive();
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

  const viewportPadding = 8;
  ctx.hidden = false;
  ctx.style.visibility = 'hidden';
  ctx.style.left = '0px';
  ctx.style.top = '0px';

  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const rect = ctx.getBoundingClientRect();
  const w = rect.width || 200;
  const h = rect.height || 180;

  const maxLeft = Math.max(viewportPadding, vw - w - viewportPadding);
  const maxTop = Math.max(viewportPadding, vh - h - viewportPadding);
  const rightAlignedLeft = x - w;
  const bottomAlignedTop = y - h;

  let left = x;
  let top = y;

  if (left > maxLeft) {
    left = rightAlignedLeft >= viewportPadding ? rightAlignedLeft : maxLeft;
  }
  if (top > maxTop) {
    top = bottomAlignedTop >= viewportPadding ? bottomAlignedTop : maxTop;
  }

  left = Math.max(viewportPadding, Math.min(maxLeft, left));
  top = Math.max(viewportPadding, Math.min(maxTop, top));

  ctx.style.left = `${left}px`;
  ctx.style.top = `${top}px`;
  ctx.style.visibility = '';
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
      const nextViewMode = btn.dataset.viewMode;
      gGroupBy = (nextViewMode === 'duplicates' || nextViewMode === 'similar' || nextViewMode === 'similar_only')
        ? nextViewMode
        : (REVIEW_VIEW_MODES.has(gGroupBy) ? 'none' : gGroupBy);
      if (REVIEW_VIEW_MODES.has(nextViewMode)) {
        setReviewMode(nextViewMode);
      } else {
        applyGalleryViewMode(nextViewMode);
        updateCtxViewState();
      }
      syncGroupByUi();
      setCustomSelectValue('groupBySelect', gGroupBy);
      gBridge.set_setting_str('gallery.view_mode', gGalleryViewMode, function () {
        gBridge.set_setting_str('gallery.group_by', gGroupBy, function () {
          refreshFromBridge(gBridge, true);
        });
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
  if (!el.dataset.internalDropCancelBound) {
    el.addEventListener('dragover', (e) => {
      if (!isInternalGalleryDragEvent(e)) return;
      const folderTarget = getFolderCardFromPoint(e.clientX, e.clientY, e.target);
      const paths = getDraggedPathsFromEvent(e);
      if (folderTarget) {
        const targetPath = folderTarget.getAttribute('data-path') || '';
        const eligiblePaths = getEligibleDroppedPaths(paths, targetPath);
        if (eligiblePaths.length) {
          e.preventDefault();
          e.stopPropagation();
          clearGalleryFolderDropTargets();
          folderTarget.classList.add('folder-drop-target');
          gCurrentTargetFolderName = getItemName({ path: targetPath, is_folder: true });
          gCurrentDropFolderPath = targetPath;
          const isCopy = e.ctrlKey || e.metaKey;
          if (e.dataTransfer) e.dataTransfer.dropEffect = isCopy ? 'copy' : 'move';
          if (gBridge && gBridge.update_drag_tooltip) {
            const count = gCurrentDragCount || eligiblePaths.length || 1;
            gBridge.update_drag_tooltip(count, isCopy, gCurrentTargetFolderName);
          }
          return;
        }
      }
      clearGalleryFolderDropTargets();
      e.preventDefault();
      if (e.dataTransfer) e.dataTransfer.dropEffect = 'none';
    });
    el.addEventListener('dragleave', (e) => {
      if (el.contains(e.relatedTarget)) return;
      clearGalleryFolderDropTargets();
    });
    el.addEventListener('drop', (e) => {
      const folderTarget = getFolderCardFromPoint(e.clientX, e.clientY, e.target);
      if (folderTarget && isInternalGalleryDragEvent(e)) {
        const paths = getDraggedPathsFromEvent(e);
        const targetPath = folderTarget.getAttribute('data-path') || gCurrentDropFolderPath || '';
        const eligiblePaths = getEligibleDroppedPaths(paths, targetPath);
        if (eligiblePaths.length) {
          e.preventDefault();
          e.stopPropagation();
          clearGalleryFolderDropTargets();
          const isCopy = e.ctrlKey || e.metaKey;
          if (gBridge && gBridge.hide_drag_tooltip) gBridge.hide_drag_tooltip();
          debugGalleryDrag(`gallery drop execute target=${targetPath} count=${eligiblePaths.length} op=${isCopy ? 'copy' : 'move'}`);
          setGlobalLoading(true, isCopy ? 'Copying…' : 'Moving…', 25);
          if (gBridge && (isCopy ? gBridge.copy_paths_async : gBridge.move_paths_async)) {
            const op = isCopy ? gBridge.copy_paths_async : gBridge.move_paths_async;
            op.call(gBridge, eligiblePaths, targetPath);
          }
          return;
        }
      }
      debugGalleryDrag(`gallery drop cancel hovered=${gCurrentDropFolderPath || ''} dragCount=${gCurrentDragPaths.length}`);
      cancelInternalGalleryDrop(e);
    });
    el.dataset.internalDropCancelBound = 'true';
  }
  applyGalleryViewMode(gGalleryViewMode);

  el.innerHTML = '';
  const main = document.querySelector('main');
  if (scrollToTop && main && !gPendingScrollAnchor) {
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
    div.textContent = isDuplicateModeActive()
      ? ((getReviewMode() === 'similar' || getReviewMode() === 'similar_only') ? 'No similar images found in the current scope.' : 'No duplicates found in the current scope.')
      : 'No media discovered yet.';
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

  if (isDuplicateModeActive()) {
    renderDuplicateMediaList(el, viewItems);
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
  window.addEventListener('pointerup', (e) => {
    if (gTimelineScrubActive) {
      if (gTimelineScrubPointerId === null || e.pointerId === gTimelineScrubPointerId) {
        scrubTimelineAt(e.clientY, { snap: false });
      }
      snapTimelineToNearestPoint(gTimelineScrubRatio);
    }
    const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    gTimelineNavigationActiveUntil = now + 260;
    gTimelineScrubActive = false;
    gTimelineScrubPointerId = null;
    if (gTimelineWheelSessionTimer) {
      clearTimeout(gTimelineWheelSessionTimer);
      gTimelineWheelSessionTimer = 0;
    }
    unfreezeTimelineScrollTargets();
    scheduleTimelineScrollTargetRefresh();
    if (!gTimelineHoverActive) setTimelineTooltip(false);
  });
  window.addEventListener('pointermove', (e) => {
    if (!gTimelineScrubActive) return;
    if (gTimelineScrubPointerId !== null && e.pointerId !== gTimelineScrubPointerId) return;
    const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    gTimelineNavigationActiveUntil = now + 240;
    scrubTimelineAt(e.clientY, { snap: false });
  });

  setupCustomSelect('sortSelect', (val) => {
    gSort = val;
    if (gBridge) refreshFromBridge(gBridge, true);
  });

  setupCustomSelect('filterSelect', (val) => {
    gFilter = val;
    if (isTextFilterActive()) {
      gTextProcessingDismissed = false;
      if (gBridge && gBridge.resume_text_processing) {
        gBridge.resume_text_processing();
      }
      if (gRenderTextProcessingToast) gRenderTextProcessingToast();
    } else if (gRenderTextProcessingToast) {
      gRenderTextProcessingToast();
    }
    gPage = 0; // Reset page on filter change
    if (gBridge) refreshFromBridge(gBridge, true);
  });

  setupCustomSelect('groupBySelect', (val) => {
    gGroupBy = val === 'date' ? 'date' : (val === 'duplicates' ? 'duplicates' : (val === 'similar' ? 'similar' : (val === 'similar_only' ? 'similar_only' : 'none')));
    if (['duplicates', 'similar', 'similar_only'].includes(gGroupBy)) {
      setReviewMode(gGroupBy);
    } else if (REVIEW_VIEW_MODES.has(gGalleryViewMode)) {
      clearReviewMode();
    }
    syncGroupByUi();
    if (gBridge && gBridge.set_setting_str) {
      gBridge.set_setting_str('gallery.group_by', gGroupBy, function () {
        gBridge.set_setting_str('gallery.view_mode', gGalleryViewMode, function () {
          refreshFromBridge(gBridge, true);
        });
      });
    } else if (gBridge) {
      refreshFromBridge(gBridge, true);
    }
  });

  setupCustomSelect('dateGranularitySelect', (val) => {
    gGroupDateGranularity = ['day', 'month', 'year'].includes(val) ? val : 'day';
    rerenderCurrentMediaPreservingScroll();
    if (gBridge && gBridge.set_setting_str) {
      gBridge.set_setting_str('gallery.group_date_granularity', gGroupDateGranularity, function () { });
    }
  });

  setupCustomSelect('similarityThresholdSelect', (val) => {
    gSimilarityThreshold = ['very_low', 'low', 'medium', 'high', 'very_high'].includes(val) ? val : 'low';
    if (gBridge && gBridge.set_setting_str) {
      gBridge.set_setting_str('gallery.similarity_threshold', gSimilarityThreshold, function () {
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
  const infiniteMode = shouldUseInfiniteScrollMode() || isDuplicateModeActive();
  const tp = totalPages();
  const cur = gPage + 1;

  const pages = pagerPagesToShow();

  document.querySelectorAll('[data-pager]').forEach((root) => {
    root.hidden = false;
    const prev = root.querySelector('[data-prev]');
    const next = root.querySelector('[data-next]');
    const links = root.querySelector('[data-links]');
    if (prev) {
      prev.hidden = infiniteMode;
      prev.style.display = infiniteMode ? 'none' : '';
    }
    if (next) {
      next.hidden = infiniteMode;
      next.style.display = infiniteMode ? 'none' : '';
    }
    if (links) {
      links.hidden = infiniteMode;
      links.style.display = infiniteMode ? 'none' : '';
      if (infiniteMode) links.innerHTML = '';
    }

    if (infiniteMode) return;

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
  const refreshToken = ++gRefreshGeneration;
  bridge.get_selected_folders(function (folders) {
    if (refreshToken !== gRefreshGeneration) return;
    gSelectedFolders = folders || [];
    bridge.get_active_collection(function (activeCollection) {
      if (refreshToken !== gRefreshGeneration) return;
      gActiveCollection = activeCollection && activeCollection.id ? activeCollection : null;
      setSelectedFolder(gSelectedFolders, gActiveCollection);

      if (gSelectedFolders.length === 0 && !gActiveCollection) {
        gTotal = 0;
        updateGalleryCountChip(0);
        setGlobalLoading(false);
        renderMediaList([]);
        renderPager();
        return;
      }

      if (resetPage) {
        gPage = 0;
      }
      if (resetPage || !shouldUseInfiniteScrollMode()) {
        gInfiniteScrollLoading = false;
      }

    // ── 1. Fast Path Reconcile (Hybrid Load) ─────────────────────────────
    // This loads the synthesized candidates from disk + DB without waiting for scan.
      fetchMediaCount(gSelectedFolders, gFilter, gSearchQuery || '').then(function (count) {
        if (refreshToken !== gRefreshGeneration) return;
        gTotal = count || 0;
        updateGalleryCountChip(gTotal);
        const useInfinite = shouldUseInfiniteScrollMode();
        const duplicateMode = isDuplicateModeActive();
        const limit = duplicateMode
          ? Math.max(PAGE_SIZE, gTotal || PAGE_SIZE)
          : (useInfinite ? Math.max(PAGE_SIZE, gMedia.length || PAGE_SIZE) : PAGE_SIZE);
        const offset = (useInfinite || duplicateMode) ? 0 : gPage * PAGE_SIZE;
        fetchMediaList(gSelectedFolders, limit, offset, gSort, gFilter, gSearchQuery || '').then(function (items) {
          if (refreshToken !== gRefreshGeneration) return;
          renderMediaList(items, !gPendingScrollAnchor);
          renderPager();
          if (useInfinite) requestAnimationFrame(() => maybeLoadMoreInfiniteResults());
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

  const backBtn = document.getElementById('navBack');
  if (backBtn) {
    backBtn.addEventListener('click', () => {
      if (gBridge && gBridge.navigate_back) gBridge.navigate_back();
    });
  }

  const forwardBtn = document.getElementById('navForward');
  if (forwardBtn) {
    forwardBtn.addEventListener('click', () => {
      if (gBridge && gBridge.navigate_forward) gBridge.navigate_forward();
    });
  }

  const upBtn = document.getElementById('navUp');
  if (upBtn) {
    upBtn.addEventListener('click', () => {
      if (gBridge && gBridge.navigate_up) gBridge.navigate_up();
    });
  }

  const refreshBtn = document.getElementById('navRefresh');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      if (gBridge && gBridge.refresh_current_folder) gBridge.refresh_current_folder();
    });
  }

  const addressBar = document.getElementById('selectedFolder');
  if (addressBar) {
    addressBar.addEventListener('click', (e) => {
      if (e.target && e.target.closest('.folder-address-segment')) return;
      if (e.target && e.target.closest('.folder-address-chevron')) return;
      if (gAddressBarEditing) return;
      closeFolderCrumbMenu();
      gAddressBarEditing = true;
      renderFolderAddress();
    });
    addressBar.addEventListener('keydown', (e) => {
      if ((e.key === 'Enter' || e.key === ' ') && !gAddressBarEditing) {
        e.preventDefault();
        gAddressBarEditing = true;
        renderFolderAddress();
      }
    });
  }

  document.addEventListener('click', (e) => {
    if (e.target && (e.target.closest('.folder-crumb-menu') || e.target.closest('.folder-address-chevron'))) {
      return;
    }
    closeFolderCrumbMenu();
  });

  window.addEventListener('resize', () => {
    closeFolderCrumbMenu();
    updateSelectedFolderLabelVisibility();
  });

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
  wireDuplicateSettings();
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

function duplicateSettingsArray(settings, key, defaults) {
  const raw = settings && settings[key];
  let order = [];
  try { order = raw ? JSON.parse(raw) : []; } catch (e) { order = []; }
  if (!Array.isArray(order)) order = [];
  defaults.forEach(item => {
    if (!order.includes(item)) order.push(item);
  });
  return order.filter(item => defaults.includes(item));
}

function duplicateRuleValue(settings, rule) {
  const raw = settings && settings[rule.key];
  const allowed = rule.options.map(([value]) => value);
  return allowed.includes(raw) ? raw : rule.defaultValue;
}

function renderDuplicateSettings(settings) {
  const mount = document.getElementById('duplicateSettingsMount');
  if (!mount) return;
  mount.innerHTML = '';

  if (gDuplicateSettingsMode === 'priorities') {
    const section = document.createElement('section');
    section.className = 'metadata-group';
    section.innerHTML = `
      <div class="metadata-group-header">
        <div class="metadata-group-title">Order of Importance</div>
      </div>
      <div class="metadata-group-body duplicate-sortable-list" id="duplicatePriorityList"></div>
    `;
    mount.appendChild(section);
    const list = section.querySelector('#duplicatePriorityList');
    duplicateSettingsArray(settings, 'duplicate.priorities.order', DUPLICATE_PRIORITY_ORDER_DEFAULT).forEach((label) => {
      const row = document.createElement('div');
      row.className = 'sortable-item';
      row.draggable = true;
      row.dataset.key = label;
      row.innerHTML = `
        <div class="drag-handle" title="Drag priority">☰</div>
        <span>${escapeHtml(label)}</span>
      `;
      list.appendChild(row);
    });
    return;
  }

  DUPLICATE_RULE_POLICIES.forEach((rule, idx) => {
    const field = document.createElement('section');
    field.className = 'field duplicate-settings-section';
    const selected = duplicateRuleValue(settings, rule);
    field.innerHTML = `
      <div class="field-label">${escapeHtml(rule.label)}</div>
      <div class="segmented-control duplicate-policy-control" data-setting-key="${rule.key}">
        ${rule.options.map(([value, label]) => `
          <input type="radio" name="duplicate_rule_${idx}" value="${value}" id="duplicateRule_${idx}_${value}" ${selected === value ? 'checked' : ''} />
          <label for="duplicateRule_${idx}_${value}">${escapeHtml(label)}</label>
        `).join('')}
      </div>
    `;
    mount.appendChild(field);
  });

  const formatSection = document.createElement('section');
  formatSection.className = 'metadata-group duplicate-settings-section';
  formatSection.innerHTML = `
    <div class="metadata-group-header">
      <div class="metadata-group-title">Preferred File Formats in Ranked Order</div>
      <div class="hint">Drag and drop to sort</div>
    </div>
    <div class="metadata-group-body duplicate-sortable-list" id="duplicateFormatOrderList"></div>
  `;
  mount.appendChild(formatSection);
  const formatList = formatSection.querySelector('#duplicateFormatOrderList');
  duplicateSettingsArray(settings, 'duplicate.rules.format_order', DUPLICATE_FORMAT_ORDER_DEFAULT).forEach((format) => {
    const row = document.createElement('div');
    row.className = 'sortable-item';
    row.draggable = true;
    row.dataset.key = format;
    row.innerHTML = `
      <div class="drag-handle" title="Drag format">☰</div>
      <span>${escapeHtml(format)}</span>
    `;
    formatList.appendChild(row);
  });

  const mergeSection = document.createElement('section');
  mergeSection.className = 'metadata-group duplicate-settings-section';
  mergeSection.innerHTML = `
    <div class="metadata-group-header">
      <label class="toggle duplicate-merge-toggle">
        <input type="checkbox" id="duplicateMergeBeforeDelete" ${(settings && settings['duplicate.rules.merge_before_delete']) ? 'checked' : ''} />
        <span class="metadata-group-title">Always merge metadata before deleting</span>
      </label>
    </div>
    <div class="metadata-group-body duplicate-merge-fields">
      <div class="field-label duplicate-merge-label">Metadata to merge</div>
      ${DUPLICATE_MERGE_FIELDS.map(([key, label, defaultEnabled]) => {
        const enabled = settings && settings[key];
        const checked = enabled !== undefined ? !!enabled : !!defaultEnabled;
        return `
          <label class="toggle">
            <input type="checkbox" class="duplicate-merge-field-toggle" data-setting-key="${key}" ${checked ? 'checked' : ''} />
            <span>${escapeHtml(label)}</span>
          </label>
        `;
      }).join('')}
    </div>
  `;
  mount.appendChild(mergeSection);
}

function saveDuplicateSortableOrder(listId, settingKey) {
  const list = document.getElementById(listId);
  if (!list || !gBridge || !gBridge.set_setting_str) return;
  const order = Array.from(list.querySelectorAll('.sortable-item')).map(el => el.dataset.key).filter(Boolean);
  gBridge.set_setting_str(settingKey, JSON.stringify(order), () => {});
}

function wireDuplicateSettings() {
  const mount = document.getElementById('duplicateSettingsMount');
  if (!mount) return;

  document.querySelectorAll('input[name="duplicate_settings_mode"]').forEach(radio => {
    radio.addEventListener('change', () => {
      if (!radio.checked) return;
      gDuplicateSettingsMode = radio.value === 'priorities' ? 'priorities' : 'rules';
      if (gBridge && gBridge.set_setting_str) {
        gBridge.set_setting_str('duplicate.settings.active_tab', gDuplicateSettingsMode, () => {});
      }
      if (gBridge && gBridge.get_settings) {
        gBridge.get_settings(renderDuplicateSettings);
      }
    });
  });

  mount.addEventListener('change', (e) => {
    const policy = e.target.closest('.duplicate-policy-control input[type="radio"]');
    if (policy && policy.checked && gBridge && gBridge.set_setting_str) {
      const control = policy.closest('.duplicate-policy-control');
      const settingKey = control && control.dataset.settingKey;
      if (settingKey) gBridge.set_setting_str(settingKey, policy.value || '', () => {});
      return;
    }
    const mergeBeforeDelete = e.target.closest('#duplicateMergeBeforeDelete');
    if (mergeBeforeDelete && gBridge && gBridge.set_setting_bool) {
      gBridge.set_setting_bool('duplicate.rules.merge_before_delete', !!mergeBeforeDelete.checked, () => {});
      return;
    }
    const mergeField = e.target.closest('.duplicate-merge-field-toggle');
    if (mergeField && gBridge && gBridge.set_setting_bool) {
      gBridge.set_setting_bool(mergeField.dataset.settingKey, !!mergeField.checked, () => {});
    }
  });

  let dragItem = null;
  mount.addEventListener('dragstart', (e) => {
    const item = e.target.closest('.sortable-item');
    if (!item) return;
    dragItem = item;
    item.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
  });

  mount.addEventListener('dragend', () => {
    if (!dragItem) return;
    const parentId = dragItem.parentElement && dragItem.parentElement.id;
    dragItem.classList.remove('dragging');
    dragItem = null;
    mount.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
    if (parentId === 'duplicateFormatOrderList') {
      saveDuplicateSortableOrder(parentId, 'duplicate.rules.format_order');
    } else if (parentId === 'duplicatePriorityList') {
      saveDuplicateSortableOrder(parentId, 'duplicate.priorities.order');
    }
  });

  mount.addEventListener('dragover', (e) => {
    e.preventDefault();
    if (!dragItem) return;
    const target = e.target.closest('.sortable-item');
    if (target && target !== dragItem && target.parentElement === dragItem.parentElement) {
      target.classList.add('drag-over');
    }
  });

  mount.addEventListener('dragleave', (e) => {
    const target = e.target.closest('.drag-over');
    if (target) target.classList.remove('drag-over');
  });

  mount.addEventListener('drop', (e) => {
    e.preventDefault();
    if (!dragItem) return;
    const target = e.target.closest('.sortable-item');
    if (!target || target === dragItem || target.parentElement !== dragItem.parentElement) return;
    const rect = target.getBoundingClientRect();
    const next = (e.clientY - rect.top) > (rect.height / 2);
    target.parentElement.insertBefore(dragItem, next ? target.nextSibling : target);
  });
}

function updateThemeAwareIcons(theme) {
  const isLight = theme === 'light';
  const suffix = isLight ? '-black' : '';

  // Update Logo
  const logo = document.getElementById('mainLogo');
  if (logo) {
    logo.src = isLight ? 'MediaLens-Logo-64.png' : 'MediaLens-Logo-Dark-64.png';
  }

  // Update Sidebar Icons
  ['Left', 'Bottom', 'Right'].forEach(side => {
    const icon = document.getElementById('icon' + side + 'Panel');
    if (icon) {
      const isOpened = icon.src.includes('opened');
      const sideKey = side.toLowerCase();
      const state = isOpened ? 'opened' : 'closed';
      const prefix = sideKey === 'bottom' ? 'bottom' : `${sideKey}-sidebar`;
      icon.src = `${prefix}-${state}${suffix}.png`;
    }
  });
}

function updateSidebarButtonIcons(side, visible) {
  const iconIdMap = {
    left: 'iconLeftPanel',
    bottom: 'iconBottomPanel',
    right: 'iconRightPanel',
  };
  const icon = document.getElementById(iconIdMap[side]);
  if (!icon) return;
  const isLight = document.documentElement.classList.contains('light-mode');
  const suffix = isLight ? '-black' : '';
  const state = visible ? 'opened' : 'closed';
  const prefix = side === 'bottom' ? 'bottom' : `${side}-sidebar`;
  icon.src = `${prefix}-${state}${suffix}.png`;
}

function wireSidebarToggles() {
  const btnLeft = document.getElementById('toggleLeftPanel');
  const btnBottom = document.getElementById('toggleBottomPanel');
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

  if (btnBottom) {
    btnBottom.addEventListener('click', () => {
      if (!gBridge || !gBridge.get_settings) return;
      gBridge.get_settings(function (s) {
        const cur = !!(s && s['ui.show_bottom_panel']);
        gBridge.set_setting_bool('ui.show_bottom_panel', !cur);
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

  const syncScrollTopState = () => {
    document.body.classList.toggle('gallery-scroll-top', main.scrollTop <= 2);
  };

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
    const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    gTimelineUserScrollActiveUntil = now + 220;
    syncScrollTopState();
    refreshVisibleTimelineAnchors();
    syncTimelineFromScroll();
    maybeLoadMoreInfiniteResults();
    if (gPlayingInplaceCard && gBridge && gBridge.update_native_video_rect) {
      const target = gPlayingInplaceCard.querySelector('.structured-thumb') || gPlayingInplaceCard;
      const rect = target.getBoundingClientRect();
      // If it scrolls off-screen, we might want to stop it, 
      // but let's first try just moving it.
      gBridge.update_native_video_rect(rect.x, rect.y, rect.width, rect.height);
    }
  });

  syncScrollTopState();
}

window.addEventListener('resize', () => {
  const mediaList = document.getElementById('mediaList');
  if (mediaList && mediaList.classList.contains('gallery-details')) {
    applyDetailsColumnWidths(mediaList);
  }
  syncTimelineViewportBox();
  layoutTimelinePoints();
  refreshVisibleTimelineAnchors();
  scheduleTimelineScrollTargetRefresh();
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
        gScanActive = true;
        // Silent background scan now, non-blocking
      });
    }

    if (bridge.scanFinished) {
      bridge.scanFinished.connect(function (folder, count) {
        gScanActive = false;
        gTotal = count || 0;
        const tp = totalPages();
        if (gPage >= tp) gPage = Math.max(0, tp - 1);
        refreshFromBridge(bridge, false);
      });
    }

    wireScanIndicator();
    wireTextProcessingIndicator();

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
      const nextGroupBy = (s && s['gallery.group_by']) || 'none';
      gGroupBy = ['date', 'duplicates', 'similar', 'similar_only'].includes(nextGroupBy) ? nextGroupBy : 'none';
      if (!REVIEW_VIEW_MODES.has(gGalleryViewMode)) {
        gLastStandardViewMode = gGalleryViewMode;
      }
      gGroupDateGranularity = (s && s['gallery.group_date_granularity']) || 'day';
      gSimilarityThreshold = (s && s['gallery.similarity_threshold']) || 'low';
      gShowDismissedProgressToasts = !!(s && s['ui.show_dismissed_progress_toasts']);
      setCustomSelectValue('groupBySelect', gGroupBy);
      setCustomSelectValue('dateGranularitySelect', gGroupDateGranularity);
      setCustomSelectValue('similarityThresholdSelect', gSimilarityThreshold);
      syncGroupByUi();
      if (gRenderTextProcessingToast) gRenderTextProcessingToast();
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

      updateSidebarButtonIcons('left', !!(s && s['ui.show_left_panel']));
      updateSidebarButtonIcons('bottom', !!(s && s['ui.show_bottom_panel']));
      updateSidebarButtonIcons('right', !!(s && s['ui.show_right_panel']));

      const savedMode = (s && s['metadata.layout.active_mode']) || 'image';
      gActiveMetadataMode = ['image', 'video', 'gif'].includes(savedMode) ? savedMode : 'image';
      const modeRadio = document.getElementById(`metadataMode${gActiveMetadataMode.charAt(0).toUpperCase()}${gActiveMetadataMode.slice(1)}`);
      if (modeRadio) modeRadio.checked = true;
      renderMetadataSettings(s || {});
      const duplicateSettingsMode = (s && s['duplicate.settings.active_tab']) || 'rules';
      gDuplicateSettingsMode = duplicateSettingsMode === 'priorities' ? 'priorities' : 'rules';
      const duplicateModeRadio = document.getElementById(gDuplicateSettingsMode === 'priorities' ? 'duplicateSettingsPriorities' : 'duplicateSettingsRules');
      if (duplicateModeRadio) duplicateModeRadio.checked = true;
      renderDuplicateSettings(s || {});

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

    if (bridge.get_navigation_state) {
      bridge.get_navigation_state(function (state) {
        applyNavigationState(state || {});
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

    if (bridge.navigationStateChanged) {
      bridge.navigationStateChanged.connect(function (canBack, canForward, canUp, currentPath) {
        applyNavigationState({
          canBack,
          canForward,
          canUp,
          currentPath,
        });
      });
    }

    if (bridge.childFoldersListed) {
      bridge.childFoldersListed.connect(function (requestId, items) {
        const pending = gPendingChildFolderRequests.get(requestId);
        if (!pending) return;
        gPendingChildFolderRequests.delete(requestId);
        const nextItems = Array.isArray(items) ? items : [];
        if (pending.path) {
          gFolderChildCache.set(pending.path, nextItems);
        }
        pending.resolve(nextItems);
      });
    }

    if (bridge.mediaCounted) {
      bridge.mediaCounted.connect(function (requestId, count) {
        const pending = gPendingMediaCountRequests.get(requestId);
        if (!pending) return;
        gPendingMediaCountRequests.delete(requestId);
        pending(Number(count || 0));
      });
    }

    if (bridge.mediaListed) {
      bridge.mediaListed.connect(function (requestId, items) {
        const pending = gPendingMediaListRequests.get(requestId);
        if (!pending) return;
        gPendingMediaListRequests.delete(requestId);
        pending(Array.isArray(items) ? items : []);
      });
    }

    if (bridge.nativeDragFinished) {
      bridge.nativeDragFinished.connect(function () {
        clearGalleryDragState();
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
        if (key === 'ui.show_left_panel') {
          updateSidebarButtonIcons('left', !!value);
          return;
        }
        if (key === 'ui.show_bottom_panel') {
          updateSidebarButtonIcons('bottom', !!value);
          return;
        }
        if (key === 'ui.show_right_panel') {
          updateSidebarButtonIcons('right', !!value);
          return;
        }
        if (key === 'ui.show_dismissed_progress_toasts') {
          gShowDismissedProgressToasts = !!value;
          if (gRenderTextProcessingToast) gRenderTextProcessingToast();
          return;
        }
        if (key === 'ui.theme_mode') {
          const theme = value ? 'light' : 'dark';
          document.documentElement.classList.toggle('light-mode', theme === 'light');
          updateThemeAwareIcons(theme);
          return;
        }
        if (key === 'gallery.show_hidden' || key === 'gallery.view_mode' || key === 'gallery.group_by' || key === 'gallery.group_date_granularity' || key === 'gallery.similarity_threshold') {
          if (key === 'gallery.view_mode' && bridge.get_settings) {
            bridge.get_settings(function (s) {
              applyGalleryViewMode((s && s['gallery.view_mode']) || 'masonry');
              const nextGroupBy = (s && s['gallery.group_by']) || 'none';
              gGroupBy = ['date', 'duplicates', 'similar', 'similar_only'].includes(nextGroupBy) ? nextGroupBy : 'none';
              gGroupDateGranularity = (s && s['gallery.group_date_granularity']) || 'day';
              gSimilarityThreshold = (s && s['gallery.similarity_threshold']) || 'low';
              if (!REVIEW_VIEW_MODES.has(gGalleryViewMode)) {
                gLastStandardViewMode = gGalleryViewMode;
              }
              setCustomSelectValue('groupBySelect', gGroupBy);
              setCustomSelectValue('dateGranularitySelect', gGroupDateGranularity);
              setCustomSelectValue('similarityThresholdSelect', gSimilarityThreshold);
              syncGroupByUi();
              updateCtxViewState();
              refreshFromBridge(bridge, false);
            });
            return;
          }
          if ((key === 'gallery.group_by' || key === 'gallery.group_date_granularity' || key === 'gallery.similarity_threshold') && bridge.get_settings) {
            bridge.get_settings(function (s) {
              const prevGroupBy = gGroupBy;
              const prevGranularity = gGroupDateGranularity;
              const prevSimilarity = gSimilarityThreshold;
              const nextGroupBy = (s && s['gallery.group_by']) || 'none';
              gGroupBy = ['date', 'duplicates', 'similar', 'similar_only'].includes(nextGroupBy) ? nextGroupBy : 'none';
              gGroupDateGranularity = (s && s['gallery.group_date_granularity']) || 'day';
              gSimilarityThreshold = (s && s['gallery.similarity_threshold']) || 'low';
              setCustomSelectValue('groupBySelect', gGroupBy);
              setCustomSelectValue('dateGranularitySelect', gGroupDateGranularity);
              setCustomSelectValue('similarityThresholdSelect', gSimilarityThreshold);
              syncGroupByUi();
              if (key === 'gallery.group_date_granularity' || key === 'gallery.similarity_threshold' || prevGroupBy !== gGroupBy || prevGranularity !== gGroupDateGranularity || prevSimilarity !== gSimilarityThreshold) {
                rerenderCurrentMediaPreservingScroll();
              }
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
