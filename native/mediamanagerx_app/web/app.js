
// Globals for state
let gSearchQuery = '';
let gActiveTagScopeQuery = '';
let gSelectAllAfterRefresh = false;
let gPage = 0;
const PAGE_SIZE = 100;
let gTotal = 0;
let gMedia = []; // Current page items
let gSelectedFolders = [];
let gActiveCollection = null;
let gActiveSmartCollection = null;
let gPinnedFolders = new Set();
let gBridge = null;
let gPosterRequested = new Set();
let gPosterObserver = null;
let gSort = 'none';
let gFilter = 'all';
let gFilterGroups = { media: 'all', text: 'all', meta: 'all', ai: 'all' };
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
let gGalleryRelayoutTimer = 0;
let gGalleryRelayoutRaf = 0;
let gGalleryResizeObserver = null;
let gGalleryLastLayoutWidth = 0;
let gGalleryLastLayoutHeight = 0;
let gDuplicateKeepOverrides = new Map();
let gDuplicateDeleteOverrides = new Map();
let gDuplicateBestOverrides = new Map();
let gLastCompareSeedKey = '';
let gLastCompareSelectionRevision = -1;
let gDuplicateGroupOrder = new Map();
let gCachedSettings = {};
let gMuteVideoByDefault = true;
let gAutoplayGalleryAnimatedGifs = true;
let gAutoplayPreviewAnimatedGifs = true;
let gVideoLoopMode = 'short';
let gVideoLoopCutoffSeconds = 90;
let gScanActive = false;
let gAwaitingScanResults = false;
let gLastRequestedFullScanKey = '';
let gDismissedReviewPaths = new Set();
let gSimilarityThreshold = 'low';
let gTextProcessingDismissed = false;
let gTextProcessingActive = false;
let gTextProcessingPaused = false;
let gTextProcessingWaiting = false;
let gTextProcessingForceVisible = false;
let gTextProcessingStage = '';
let gTextProcessingCurrent = 0;
let gTextProcessingTotal = 0;
let gRenderTextProcessingToast = null;
let gRenderScanToast = null;
let gCompareState = { visible: false, left: {}, right: {}, best_path: '', keep_paths: [], delete_paths: [] };
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
const HEADER_LOGO_LIGHT = 'MediaLens-Logo-3-64.png';
const HEADER_LOGO_DARK = 'MediaLens-Logo-3-64.png';
const ADVANCED_SEARCH_MAX_RULES = 6;
const ADVANCED_SEARCH_SAVED_LIMIT = 8;
const ADVANCED_SEARCH_MODE_OPTIONS = [
  ['include', 'Include'],
  ['exclude', 'Exclude'],
];
const ADVANCED_SEARCH_MATCH_OPTIONS = [
  ['contains', 'Contains'],
  ['exact', 'Exact Phrase'],
];
const ADVANCED_SEARCH_JOIN_OPTIONS = [
  ['', 'Finish'],
  ['AND', 'AND'],
  ['OR', 'OR'],
];
const ADVANCED_SEARCH_FIELD_DEFS = [
  { key: '', label: 'Any Field', kind: 'text' },
  { key: 'file', label: 'Filename', kind: 'text' },
  { key: 'folder', label: 'Folder', kind: 'text' },
  { key: 'tag', label: 'Tags', kind: 'text' },
  { key: 'collection', label: 'Collection', kind: 'text' },
  { key: 'description', label: 'Description', kind: 'text' },
  { key: 'notes', label: 'Notes', kind: 'text' },
  { key: 'title', label: 'Title', kind: 'text' },
  { key: 'type', label: 'Media Type', kind: 'text' },
  { key: 'ext', label: 'Extension', kind: 'text' },
  { key: 'date-modified', label: 'Date Modified', kind: 'date' },
  { key: 'original-file-date', label: 'Original File Date', kind: 'date' },
  { key: 'date-taken', label: 'Date Taken', kind: 'date' },
  { key: 'date-acquired', label: 'Date Acquired', kind: 'date' },
  { key: 'date-created', label: 'Date Created', kind: 'date' },
  { key: 'size', label: 'File Size', kind: 'detail' },
  { key: 'duration', label: 'Duration', kind: 'detail' },
  { key: 'width', label: 'Width', kind: 'detail' },
  { key: 'height', label: 'Height', kind: 'detail' },
  { key: 'path', label: 'Path', kind: 'text' },
  { key: 'source', label: 'Source', kind: 'text' },
  { key: 'prompt', label: 'AI Prompt', kind: 'text' },
  { key: 'negative', label: 'AI Negative Prompt', kind: 'text' },
  { key: 'tool', label: 'Tool', kind: 'text' },
  { key: 'model', label: 'Model', kind: 'text' },
  { key: 'checkpoint', label: 'Checkpoint', kind: 'text' },
  { key: 'sampler', label: 'Sampler', kind: 'text' },
  { key: 'scheduler', label: 'Scheduler', kind: 'text' },
  { key: 'family', label: 'Metadata Family', kind: 'text' },
  { key: 'lora', label: 'LoRA', kind: 'text' },
  { key: 'cfg', label: 'CFG', kind: 'detail' },
  { key: 'steps', label: 'Steps', kind: 'detail' },
  { key: 'seed', label: 'Seed', kind: 'detail' },
];
const ADVANCED_SEARCH_TEXT_OPERATOR_OPTIONS = [
  ['=', '='],
  ['!=', '!='],
];
const ADVANCED_SEARCH_VALUE_OPERATOR_OPTIONS = [
  ['=', '='],
  ['<', '<'],
  ['<=', '<='],
  ['>', '>'],
  ['>=', '>='],
];
const ADVANCED_SEARCH_FIELD_ALIASES = {
  path: 'path',
  filename: 'filename',
  file: 'filename',
  name: 'filename',
  folder: 'folder',
  dir: 'folder',
  title: 'title',
  description: 'description',
  desc: 'description',
  notes: 'notes',
  note: 'notes',
  tags: 'tags',
  tag: 'tags',
  collection: 'collection_names',
  collections: 'collection_names',
  prompt: 'ai_prompt',
  negative: 'ai_negative_prompt',
  negprompt: 'ai_negative_prompt',
  tool: 'tool_name',
  model: 'model_name',
  checkpoint: 'checkpoint_name',
  sampler: 'sampler',
  scheduler: 'scheduler',
  source: 'source_formats',
  family: 'metadata_families',
  lora: 'ai_loras',
  type: 'media_type',
  ext: 'ext',
  extension: 'ext',
  cfg: 'cfg_scale',
  steps: 'steps',
  seed: 'seed',
  width: 'width',
  height: 'height',
  duration: 'duration',
  size: 'file_size',
  'date-taken': 'exif_date_taken',
  datetaken: 'exif_date_taken',
  'exif-date-taken': 'exif_date_taken',
  exifdatetaken: 'exif_date_taken',
  'date-acquired': 'metadata_date',
  dateacquired: 'metadata_date',
  'metadata-date': 'metadata_date',
  metadatadate: 'metadata_date',
  'original-file-date': 'original_file_date',
  originalfiledate: 'original_file_date',
  'date-created': 'file_created_time',
  datecreated: 'file_created_time',
  'file-created-date': 'file_created_time',
  filecreateddate: 'file_created_time',
  created: 'file_created_time',
  'date-modified': 'modified_time',
  datemodified: 'modified_time',
  'file-modified-date': 'modified_time',
  filemodifieddate: 'modified_time',
  modified: 'modified_time',
};
const ADVANCED_SEARCH_TEXT_FIELD_KEYS = new Set([
  'path', 'filename', 'folder', 'title', 'description', 'notes', 'tags', 'collection_names',
  'ai_prompt', 'ai_negative_prompt', 'tool_name', 'model_name', 'checkpoint_name', 'sampler',
  'scheduler', 'source_formats', 'metadata_families', 'ai_loras', 'media_type', 'ext',
]);
const ADVANCED_SEARCH_NUMERIC_FIELD_KEYS = new Set([
  'cfg_scale', 'steps', 'seed', 'width', 'height', 'duration', 'file_size',
]);
const ADVANCED_SEARCH_DATE_FIELD_KEYS = new Set([
  'exif_date_taken', 'metadata_date', 'original_file_date', 'file_created_time', 'modified_time',
]);
const ADVANCED_SEARCH_PREFERRED_ALIASES = {
  path: 'path',
  filename: 'file',
  folder: 'folder',
  title: 'title',
  description: 'description',
  notes: 'notes',
  tags: 'tag',
  collection_names: 'collection',
  ai_prompt: 'prompt',
  ai_negative_prompt: 'negative',
  tool_name: 'tool',
  model_name: 'model',
  checkpoint_name: 'checkpoint',
  sampler: 'sampler',
  scheduler: 'scheduler',
  source_formats: 'source',
  metadata_families: 'family',
  ai_loras: 'lora',
  media_type: 'type',
  ext: 'ext',
  cfg_scale: 'cfg',
  steps: 'steps',
  seed: 'seed',
  width: 'width',
  height: 'height',
  duration: 'duration',
  file_size: 'size',
  exif_date_taken: 'date-taken',
  metadata_date: 'date-acquired',
  original_file_date: 'original-file-date',
  file_created_time: 'date-created',
  modified_time: 'date-modified',
};
const SEARCH_OPERATORS = ['>=', '<=', '>', '<', '='];
const ADVANCED_SEARCH_DEFAULT_SAVED_QUERIES = [
  {
    name: 'Date Range and Search Term',
    query: 'original-file-date:>=2024-01-06 AND original-file-date:<=2026-04-01 AND',
  },
  {
    name: 'File Size Range and Search Term',
    query: 'size:>=1kb AND size:<=100kb AND',
  },
];
let gAdvancedSearchExpanded = false;
let gAdvancedSearchSavedQueries = [];
let gAdvancedSearchCarryoverTokens = [];
let gAdvancedSearchCollections = [];
let gShowHidden = false;

function normalizedVideoLoopCutoffSeconds() {
  const parsed = Number(gVideoLoopCutoffSeconds);
  if (!Number.isFinite(parsed)) return 90;
  return Math.max(1, Math.round(parsed));
}

function shouldLoopVideoForDurationSeconds(durationSeconds) {
  const mode = gVideoLoopMode === 'all' || gVideoLoopMode === 'none' || gVideoLoopMode === 'short'
    ? gVideoLoopMode
    : 'short';
  if (mode === 'all') return true;
  if (mode === 'none') return false;
  const seconds = Number(durationSeconds || 0);
  return seconds > 0 && seconds < normalizedVideoLoopCutoffSeconds();
}

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

function normalizeFolderPath(path) {
  return String(path || '').replace(/\//g, '\\').toLowerCase();
}

function currentSelectedFolderSet() {
  return new Set((Array.isArray(gSelectedFolders) ? gSelectedFolders : []).map(normalizeFolderPath).filter(Boolean));
}

function currentFullScanKey(folders) {
  return (Array.isArray(folders) ? folders : [])
    .map(normalizeFolderPath)
    .filter(Boolean)
    .sort()
    .join('|');
}

function ensureFullFolderScanRequested(bridge, folders, searchQuery) {
  if (!bridge || !bridge.start_scan) return;
  const scopeFolders = Array.isArray(folders) ? folders : [];
  if (!scopeFolders.length) return;
  const scanKey = currentFullScanKey(scopeFolders);
  if (!scanKey) return;
  if (gLastRequestedFullScanKey === scanKey && (gScanActive || !gAwaitingScanResults)) return;
  gLastRequestedFullScanKey = scanKey;
  bridge.start_scan(scopeFolders, searchQuery || '');
}

function syncPinnedFolders(nextFolders) {
  gPinnedFolders = new Set((Array.isArray(nextFolders) ? nextFolders : []).map(normalizeFolderPath).filter(Boolean));
}

function isPinnedFolder(path) {
  return gPinnedFolders.has(normalizeFolderPath(path));
}

function compareSlotPath(slotName) {
  if (!gCompareState) return '';
  const slot = slotName === 'right' ? gCompareState.right : gCompareState.left;
  return slot && slot.path ? String(slot.path) : '';
}

function normalizeMediaPath(path) {
  return String(path || '').replace(/\//g, '\\').trim().toLowerCase();
}

function getAccentContrastColor(color) {
  const value = String(color || '').trim();
  const match = value.match(/^#?([0-9a-f]{6})$/i);
  if (!match) return '#ffffff';
  const hex = match[1];
  const toLinear = (component) => {
    const srgb = component / 255;
    return srgb <= 0.03928 ? srgb / 12.92 : Math.pow((srgb + 0.055) / 1.055, 2.4);
  };
  const r = parseInt(hex.slice(0, 2), 16);
  const g = parseInt(hex.slice(2, 4), 16);
  const b = parseInt(hex.slice(4, 6), 16);
  const luminance = 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
  const contrastBlack = (luminance + 0.05) / 0.05;
  const contrastWhite = 1.05 / (luminance + 0.05);
  return contrastBlack >= contrastWhite ? '#000000' : '#ffffff';
}

function applyAccentCssVars(color) {
  const value = color || '#8ab4f8';
  document.documentElement.style.setProperty('--accent', value);
  document.documentElement.style.setProperty('--accent-contrast', getAccentContrastColor(value));
}

function compareHasEmptySlot() {
  return !compareSlotPath('left') || !compareSlotPath('right');
}

function getCompareActivePaths() {
  return Array.from(new Set(['left', 'right'].map(compareSlotPath).filter(Boolean)));
}

function getComparePathsForDuplicateGroup(groupKey) {
  const key = String(groupKey || '');
  if (!key) return [];
  const groupPaths = new Set(
    gMedia
      .filter(item => String(item.duplicate_group_key || '') === key)
      .map(item => normalizeMediaPath(item.path))
      .filter(Boolean)
  );
  return getCompareActivePaths().filter(path => groupPaths.has(normalizeMediaPath(path)));
}

function getDuplicateGroupKeyForPath(path) {
  const normalizedPath = normalizeMediaPath(path);
  const item = gMedia.find(entry => normalizeMediaPath(entry.path) === normalizedPath);
  return String(item && item.duplicate_group_key || '');
}

function maybeSeedCompareStateFromReview() {
  const comparePaths = getCompareActivePaths();
  if (!comparePaths.length) {
    gLastCompareSeedKey = '';
    return;
  }
  const groupKeys = Array.from(new Set(comparePaths.map(getDuplicateGroupKeyForPath).filter(Boolean)));
  if (groupKeys.length !== 1) return;
  const groupKey = groupKeys[0];
  const seedKey = `${comparePaths.slice().sort().join('|')}::${groupKey}`;
  if (seedKey === gLastCompareSeedKey) return;
  gLastCompareSeedKey = seedKey;
  const keepPaths = getDuplicateKeepPaths(groupKey).slice().sort();
  const deletePaths = getDuplicateDeletePaths(groupKey).slice().sort();
  const bestPath = getDuplicateBestPath(groupKey);
  syncCompareStateFromReviewGroup(groupKey, keepPaths, deletePaths, bestPath);
}

function syncCompareStateFromReviewGroup(groupKey, keepPaths, deletePaths, bestPath) {
  if (!gBridge) return;
  const comparePaths = getComparePathsForDuplicateGroup(groupKey);
  if (!comparePaths.length) return;
  const keepSet = new Set((Array.isArray(keepPaths) ? keepPaths : [keepPaths]).map(v => String(v || '')).filter(Boolean));
  const deleteSet = new Set((Array.isArray(deletePaths) ? deletePaths : [deletePaths]).map(v => String(v || '')).filter(Boolean));
  const nextBestPath = String(bestPath || '');
  const nextKeepPaths = comparePaths.filter(path => keepSet.has(path));
  const nextDeletePaths = comparePaths.filter(path => deleteSet.has(path));
  if (gBridge.set_compare_selection_state) {
    gBridge.set_compare_selection_state(nextBestPath, nextKeepPaths, nextDeletePaths);
    return;
  }
  comparePaths.forEach((path) => {
    if (gBridge.set_compare_keep_path) gBridge.set_compare_keep_path(path, keepSet.has(path));
    if (gBridge.set_compare_delete_path) gBridge.set_compare_delete_path(path, deleteSet.has(path));
  });
  if (nextBestPath && gBridge.set_compare_best_path) {
    gBridge.set_compare_best_path(nextBestPath);
  }
}

function syncDuplicateGroupFromCompareSelection(bestPath, keepPaths, deletePaths) {
  const comparePaths = getCompareActivePaths();
  if (!comparePaths.length) return;
  const groupKeys = Array.from(new Set(comparePaths.map(getDuplicateGroupKeyForPath).filter(Boolean)));
  if (groupKeys.length !== 1) return;
  const groupKey = groupKeys[0];
  const normalizedComparePaths = new Set(comparePaths.map(normalizeMediaPath).filter(Boolean));
  const normalizedKeepPaths = new Set((Array.isArray(keepPaths) ? keepPaths : []).map(normalizeMediaPath).filter(Boolean));
  const normalizedDeletePaths = new Set((Array.isArray(deletePaths) ? deletePaths : []).map(normalizeMediaPath).filter(Boolean));
  const normalizedBestPath = normalizeMediaPath(bestPath);
  const groupItems = gMedia.filter(item => String(item.duplicate_group_key || '') === groupKey);
  const existingKeepPaths = getDuplicateKeepPaths(groupKey);
  const existingDeletePaths = getDuplicateDeletePaths(groupKey);
  const normalizedExistingKeepPaths = new Set(existingKeepPaths.map(normalizeMediaPath).filter(Boolean));
  const normalizedExistingDeletePaths = new Set(existingDeletePaths.map(normalizeMediaPath).filter(Boolean));
  const nextKeepPaths = [];
  const nextDeletePaths = [];
  groupItems.forEach((item) => {
    const rawPath = String(item.path || '');
    const normalizedPath = normalizeMediaPath(rawPath);
    if (!normalizedPath) return;
    if (normalizedComparePaths.has(normalizedPath)) {
      if (normalizedKeepPaths.has(normalizedPath)) {
        nextKeepPaths.push(rawPath);
      } else if (normalizedDeletePaths.has(normalizedPath)) {
        nextDeletePaths.push(rawPath);
      } else {
        if (normalizedExistingKeepPaths.has(normalizedPath)) nextKeepPaths.push(rawPath);
        if (normalizedExistingDeletePaths.has(normalizedPath)) nextDeletePaths.push(rawPath);
      }
      return;
    }
    if (normalizedExistingKeepPaths.has(normalizedPath)) nextKeepPaths.push(rawPath);
    if (normalizedExistingDeletePaths.has(normalizedPath)) nextDeletePaths.push(rawPath);
  });
  setDuplicateKeepPaths(groupKey, nextKeepPaths);
  setDuplicateDeletePaths(groupKey, nextDeletePaths);

  const currentBestPath = getDuplicateBestPath(groupKey);
  const normalizedCurrentBestPath = normalizeMediaPath(currentBestPath);
  if (normalizedBestPath && normalizedComparePaths.has(normalizedBestPath)) {
    const matchingItem = groupItems.find(item => normalizeMediaPath(item.path) === normalizedBestPath);
    setDuplicateBestPath(groupKey, matchingItem ? String(matchingItem.path || '') : '');
    return;
  }
  if (!normalizedBestPath && normalizedComparePaths.has(normalizedCurrentBestPath)) {
    setDuplicateBestPath(groupKey, '');
  }
}

function handleDuplicateRuleSettingsChanged(settings) {
  gCachedSettings = settings || {};
  if (isDuplicateModeActive()) {
    gPendingScrollAnchor = captureCurrentGroupScrollAnchor();
    gDuplicateKeepOverrides.clear();
    gDuplicateDeleteOverrides.clear();
    gDuplicateBestOverrides.clear();
    gLastCompareSeedKey = '';
    gMedia = [];
    gTotalOnPage = 0;
    gLoadedOnPage = 0;
    const mediaList = document.getElementById('mediaList');
    if (mediaList) {
      mediaList.innerHTML = '';
    }
    renderTimelineRail([]);
    beginReviewLoading('Recalculating changed preferences, please wait.', 10);
    if (gBridge) {
      refreshFromBridge(gBridge, false);
    }
  }
  const duplicateSettingsMount = document.getElementById('duplicateSettingsMount');
  if (duplicateSettingsMount && !duplicateSettingsMount.hidden) {
    renderDuplicateSettings(gCachedSettings);
  }
}

function syncDuplicateKeepFromComparePath(path, checked) {
  const groupKey = getDuplicateGroupKeyForPath(path);
  if (!groupKey) return;
  const normalizedTargetPath = normalizeMediaPath(path);
  const groupItems = gMedia.filter(item => String(item.duplicate_group_key || '') === groupKey);
  const existingKeepPaths = getDuplicateKeepPaths(groupKey);
  const existingDeletePaths = getDuplicateDeletePaths(groupKey);
  const normalizedExistingKeepPaths = new Set(existingKeepPaths.map(normalizeMediaPath).filter(Boolean));
  const normalizedExistingDeletePaths = new Set(existingDeletePaths.map(normalizeMediaPath).filter(Boolean));
  const nextKeepPaths = [];
  const nextDeletePaths = [];
  groupItems.forEach((item) => {
    const rawPath = String(item.path || '');
    const normalizedPath = normalizeMediaPath(rawPath);
    if (!normalizedPath) return;
    if (normalizedPath === normalizedTargetPath) {
      if (checked) nextKeepPaths.push(rawPath);
      else if (normalizedExistingDeletePaths.has(normalizedPath)) nextDeletePaths.push(rawPath);
      return;
    }
    if (normalizedExistingKeepPaths.has(normalizedPath)) nextKeepPaths.push(rawPath);
    if (normalizedExistingDeletePaths.has(normalizedPath)) nextDeletePaths.push(rawPath);
  });
  setDuplicateKeepPaths(groupKey, nextKeepPaths);
  if (checked) {
    setDuplicateDeletePaths(groupKey, nextDeletePaths.filter(rawPath => normalizeMediaPath(rawPath) !== normalizedTargetPath));
  } else {
    setDuplicateDeletePaths(groupKey, nextDeletePaths);
  }
}

function syncDuplicateDeleteFromComparePath(path, checked) {
  const groupKey = getDuplicateGroupKeyForPath(path);
  if (!groupKey) return;
  const normalizedTargetPath = normalizeMediaPath(path);
  if (checked && normalizeMediaPath(getDuplicateBestPath(groupKey)) === normalizedTargetPath) {
    setDuplicateBestPath(groupKey, '');
  }
  const groupItems = gMedia.filter(item => String(item.duplicate_group_key || '') === groupKey);
  const existingKeepPaths = getDuplicateKeepPaths(groupKey);
  const existingDeletePaths = getDuplicateDeletePaths(groupKey);
  const normalizedExistingKeepPaths = new Set(existingKeepPaths.map(normalizeMediaPath).filter(Boolean));
  const normalizedExistingDeletePaths = new Set(existingDeletePaths.map(normalizeMediaPath).filter(Boolean));
  const nextKeepPaths = [];
  const nextDeletePaths = [];
  groupItems.forEach((item) => {
    const rawPath = String(item.path || '');
    const normalizedPath = normalizeMediaPath(rawPath);
    if (!normalizedPath) return;
    if (normalizedPath === normalizedTargetPath) {
      if (checked) nextDeletePaths.push(rawPath);
      else if (normalizedExistingKeepPaths.has(normalizedPath)) nextKeepPaths.push(rawPath);
      return;
    }
    if (normalizedExistingKeepPaths.has(normalizedPath)) nextKeepPaths.push(rawPath);
    if (normalizedExistingDeletePaths.has(normalizedPath)) nextDeletePaths.push(rawPath);
  });
  setDuplicateDeletePaths(groupKey, nextDeletePaths);
  if (checked) {
    setDuplicateKeepPaths(groupKey, nextKeepPaths.filter(rawPath => normalizeMediaPath(rawPath) !== normalizedTargetPath));
  } else {
    setDuplicateKeepPaths(groupKey, nextKeepPaths);
  }
}

function syncDuplicateBestFromComparePath(path, checked) {
  const groupKey = getDuplicateGroupKeyForPath(path);
  if (!groupKey) return;
  if (!checked) {
    const currentBestPath = getDuplicateBestPath(groupKey);
    if (normalizeMediaPath(currentBestPath) === normalizeMediaPath(path)) {
      setDuplicateBestPath(groupKey, '');
    }
    return;
  }
  const groupItems = gMedia.filter(item => String(item.duplicate_group_key || '') === groupKey);
  const matchingItem = groupItems.find(item => normalizeMediaPath(item.path) === normalizeMediaPath(path));
  setDuplicateBestPath(groupKey, matchingItem ? String(matchingItem.path || '') : '');
}

function getReviewMode() {
  if (gGalleryViewMode === 'similar_only' || gGroupBy === 'similar_only') return 'similar_only';
  if (gGalleryViewMode === 'similar' || gGroupBy === 'similar') return 'similar';
  if (gGalleryViewMode === 'duplicates' || gGroupBy === 'duplicates') return 'duplicates';
  return '';
}

function isDuplicateModeActive() {
  return !!getReviewMode();
}

function shouldShowScanWaitingEmptyState() {
  return isDuplicateModeActive() && (gScanActive || gAwaitingScanResults);
}

function clearDismissedReviewPaths() {
  gDismissedReviewPaths = new Set();
}

function getReviewGroupPeerPaths(groupKey, path) {
  const normalizedPath = normalizeMediaPath(path);
  const normalizedGroupKey = String(groupKey || '').trim();
  if (!normalizedPath || !normalizedGroupKey) return [];
  return gMedia
    .filter(item => !item.is_folder && String(item.duplicate_group_key || '').trim() === normalizedGroupKey)
    .map(item => String(item.path || ''))
    .filter(rawPath => {
      const normalized = normalizeMediaPath(rawPath);
      return normalized && normalized !== normalizedPath;
    });
}

function dismissReviewPath(path) {
  const normalized = normalizeMediaPath(path);
  if (!normalized) return;
  gDismissedReviewPaths.add(normalized);
  renderMediaList(gMedia, false);
  const groupKey = getDuplicateGroupKeyForPath(path);
  const peerPaths = getReviewGroupPeerPaths(groupKey, path);
  if (!gBridge || !gBridge.dismiss_review_pair || !peerPaths.length) return;
  gBridge.dismiss_review_pair(path, peerPaths, getReviewMode(), function (ok) {
    if (!ok) {
      gDismissedReviewPaths.delete(normalized);
      renderMediaList(gMedia, false);
      return;
    }
    clearDismissedReviewPaths();
    refreshFromBridge(gBridge, false);
  });
}

function clearReviewResultsForPendingScan() {
  if (!isDuplicateModeActive()) return;
  gMedia = [];
  gTotal = 0;
  gPage = 0;
  updateGalleryCountChip(0);
  renderMediaList([], true);
  renderPager();
}

function isExactDuplicateReviewItem(item) {
  if (!item || item.is_folder) return false;
  const contentHash = String(item.content_hash || '').trim();
  const groupKey = String(item.duplicate_group_key || '').trim();
  if (!contentHash || !groupKey) return false;
  let matches = 0;
  for (const entry of gMedia) {
    if (!entry || entry.is_folder) continue;
    if (String(entry.duplicate_group_key || '').trim() !== groupKey) continue;
    if (String(entry.content_hash || '').trim() !== contentHash) continue;
    matches += 1;
    if (matches > 1) return true;
  }
  return false;
}

function normalizeTextFilter(filterValue) {
  return filterValue === 'text_more_likely' || filterValue === 'text_verified' ? 'text_detected' : filterValue;
}

function normalizeMediaFilter(filterValue) {
  return ['image', 'svg', 'video', 'animated'].includes(filterValue) ? filterValue : 'all';
}

function normalizeMetaFilter(filterValue) {
  return ['no_tags', 'no_description'].includes(filterValue) ? filterValue : 'all';
}

function normalizeAiFilter(filterValue) {
  return ['ai_generated', 'non_ai'].includes(filterValue) ? filterValue : 'all';
}

function normalizeFilterValue(filterValue) {
  const raw = String(filterValue || 'all').trim();
  if (!raw || raw === 'all') return { media: 'all', text: 'all', meta: 'all', ai: 'all' };
  if (!raw.includes(':')) {
    const normalizedText = normalizeTextFilter(raw);
    if (normalizedText === 'text_detected' || normalizedText === 'no_text_detected') {
      return { media: 'all', text: normalizedText, meta: 'all', ai: 'all' };
    }
    const normalizedMeta = normalizeMetaFilter(raw);
    if (normalizedMeta !== 'all') {
      return { media: 'all', text: 'all', meta: normalizedMeta, ai: 'all' };
    }
    const normalizedAi = normalizeAiFilter(raw);
    if (normalizedAi !== 'all') {
      return { media: 'all', text: 'all', meta: 'all', ai: normalizedAi };
    }
    return { media: normalizeMediaFilter(raw), text: 'all', meta: 'all', ai: 'all' };
  }
  const groups = { media: 'all', text: 'all', meta: 'all', ai: 'all' };
  raw.split(';').forEach((part) => {
    const [groupRaw, valueRaw] = String(part || '').split(':');
    const group = String(groupRaw || '').trim();
    const value = String(valueRaw || '').trim();
    if (group === 'media') groups.media = normalizeMediaFilter(value);
    if (group === 'text') groups.text = normalizeTextFilter(value) === 'no_text_detected' ? 'no_text_detected' : (normalizeTextFilter(value) === 'text_detected' ? 'text_detected' : 'all');
    if (group === 'meta') groups.meta = normalizeMetaFilter(value);
    if (group === 'ai') groups.ai = normalizeAiFilter(value);
  });
  return groups;
}

function serializeFilterValue(groups) {
  const media = normalizeMediaFilter(groups && groups.media);
  const normalizedText = normalizeTextFilter(groups && groups.text);
  const text = normalizedText === 'text_detected' || normalizedText === 'no_text_detected' ? normalizedText : 'all';
  const meta = normalizeMetaFilter(groups && groups.meta);
  const ai = normalizeAiFilter(groups && groups.ai);
  const parts = [];
  if (media !== 'all') parts.push(`media:${media}`);
  if (text !== 'all') parts.push(`text:${text}`);
  if (meta !== 'all') parts.push(`meta:${meta}`);
  if (ai !== 'all') parts.push(`ai:${ai}`);
  return parts.length ? parts.join(';') : 'all';
}

function getFilterTriggerText(groups) {
  const labels = [];
  if (groups.media === 'image') labels.push('Images');
  else if (groups.media === 'svg') labels.push('SVGs');
  else if (groups.media === 'video') labels.push('Videos');
  else if (groups.media === 'animated') labels.push('Animated GIFs');
  if (groups.text === 'text_detected') labels.push('Text Detected');
  else if (groups.text === 'no_text_detected') labels.push('No Text Detected');
  if (groups.meta === 'no_tags') labels.push('No Tags');
  else if (groups.meta === 'no_description') labels.push('No Description');
  if (groups.ai === 'ai_generated') labels.push('AI Generated');
  else if (groups.ai === 'non_ai') labels.push('Non-AI');
  return labels.length ? `Filter: ${labels.join(' | ')}` : 'Filter: None';
}

function isTextFilterActive() {
  const normalized = normalizeTextFilter(gFilterGroups.text);
  return normalized === 'text_detected' || normalized === 'no_text_detected';
}

function resolveMetadataFieldEnabled(settings, mode, key, defaultEnabled) {
  const directKey = metadataFieldEnabledKey(mode, key);
  if (settings && settings[directKey] !== undefined) return !!settings[directKey];
  if (key === 'originalfiledate') {
    const fallbackModeKey = metadataFieldEnabledKey(mode, 'filecreateddate');
    if (settings && settings[fallbackModeKey] !== undefined) return !!settings[fallbackModeKey];
    if (settings && settings['metadata.display.filecreateddate'] !== undefined) return !!settings['metadata.display.filecreateddate'];
  }
  return !!defaultEnabled;
}

const METADATA_SETTINGS_CONFIG = {
  image: {
    groups: {
      general: {
        label: 'General',
        fields: [
          ['res', 'Resolution', true], ['size', 'File Size', true],
          ['exifdatetaken', 'Date Taken', false], ['metadatadate', 'Date Acquired', false],
          ['originalfiledate', 'Original File Date', false], ['filecreateddate', 'Windows ctime', false], ['filemodifieddate', 'Date Modified', false],
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
  svg: {
    groups: {
      general: {
        label: 'General',
        fields: [
          ['res', 'Resolution', true], ['size', 'File Size', true],
          ['metadatadate', 'Date Acquired', false],
          ['originalfiledate', 'Original File Date', false], ['filecreateddate', 'Windows ctime', false], ['filemodifieddate', 'Date Modified', false],
          ['description', 'Description', true], ['tags', 'Tags', true], ['notes', 'Notes', true],
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
  video: {
    groups: {
      general: {
        label: 'General',
        fields: [
          ['res', 'Resolution', true], ['size', 'File Size', true],
          ['exifdatetaken', 'Date Taken', false], ['metadatadate', 'Date Acquired', false],
          ['originalfiledate', 'Original File Date', false], ['filecreateddate', 'Windows ctime', false], ['filemodifieddate', 'Date Modified', false],
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
          ['originalfiledate', 'Original File Date', false], ['filecreateddate', 'Windows ctime', false], ['filemodifieddate', 'Date Modified', false],
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
  const effectiveQuery = getEffectiveSearchQuery(searchQuery || '');
  if (gBridge.count_media_async) {
    return new Promise((resolve) => {
      const requestId = `count-${Date.now()}-${++gGalleryRequestSeq}`;
      gPendingMediaCountRequests.set(requestId, resolve);
      gBridge.count_media_async(requestId, folders || [], filterType || 'all', effectiveQuery);
    });
  }
  if (!gBridge.count_media) {
    return Promise.resolve(0);
  }
  return new Promise((resolve) => {
    gBridge.count_media(folders || [], filterType || 'all', effectiveQuery, function (count) {
      resolve(Number(count || 0));
    });
  });
}

function getEffectiveSearchQuery(searchQuery) {
  const baseQuery = String(searchQuery || '').trim();
  const activeTagScope = String(gActiveTagScopeQuery || '').trim();
  if (!activeTagScope) return baseQuery;
  return baseQuery ? `${baseQuery} ${activeTagScope}` : activeTagScope;
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
  const folderNav = row.querySelector('.folder-nav');
  const rowStyles = window.getComputedStyle(row);
  const gap = parseFloat(rowStyles.columnGap || rowStyles.gap || '0') || 0;
  const navWidth = folderNav ? Math.ceil(folderNav.getBoundingClientRect().width || folderNav.scrollWidth || 0) : 0;
  const contentWidth = getFolderAddressContentWidth(address);
  const nextBasis = Math.max(0, navWidth + gap + contentWidth);
  row.style.flexBasis = `${nextBasis}px`;
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
        sortBy || 'none',
        filterType || 'all',
        getEffectiveSearchQuery(searchQuery || '')
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
      sortBy || 'none',
      filterType || 'all',
      getEffectiveSearchQuery(searchQuery || ''),
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

function setSelectedFolder(paths, activeCollection = null, activeSmartCollection = null) {
  if (activeCollection && activeCollection.name && !gNavState.currentPath) {
    gAddressBarFallbackText = activeCollection.name;
  } else if (activeSmartCollection && activeSmartCollection.name && !gNavState.currentPath) {
    gAddressBarFallbackText = activeSmartCollection.name;
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
    } else if (item.type === 'poster') {
      loadStillPoster(item.el, item.path);
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
    if (card) markCardMediaReady(card);
  };
  el.onerror = () => {
    gLoadedOnPage++;
    el.style.opacity = '1';
    const card = el.closest('.card');
    if (card) markCardMediaReady(card);
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
          if (card) markCardMediaReady(card);
        };
        tempImg.onerror = () => {
          el.removeAttribute('src');
          gLoadedOnPage++;
          requestAnimationFrame(() => { el.style.opacity = '1'; });
          if (card) markCardMediaReady(card);
        };
        tempImg.src = posterUrl;
      } else {
        el.removeAttribute('src');
        gLoadedOnPage++;
        requestAnimationFrame(() => { el.style.opacity = '1'; });
        if (card) markCardMediaReady(card);
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
        const posterPath = el.getAttribute('data-poster-path');
        const path = el.getAttribute('data-video-path');

        gTotalOnPage++;
        gPosterObserver.unobserve(el);

        // Load immediately — no delay for items entering the viewport
        if (imgSrc) {
          loadImage(el, imgSrc);
        } else if (posterPath) {
          loadStillPoster(el, posterPath);
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
let gReviewLoadingActive = false;
let gReviewLoadingGeneration = 0;
let gReviewLoadingMessage = 'Loading review results...';
let gReviewLoadingProgress = 0;

function setReviewResultsHidden(hidden) {
  const mediaList = document.getElementById('mediaList');
  if (!mediaList) return;
  if (hidden) {
    mediaList.classList.add('review-results-hidden');
  } else {
    mediaList.classList.remove('review-results-hidden');
  }
}

function beginReviewLoading(text, pct = 10) {
  gReviewLoadingActive = true;
  gReviewLoadingGeneration += 1;
  gReviewLoadingMessage = text || 'Loading review results...';
  gReviewLoadingProgress = Math.max(0, Math.min(100, Number(pct) || 0));
  if (isDuplicateModeActive()) setReviewResultsHidden(true);
  setGlobalLoading(true, gReviewLoadingMessage, gReviewLoadingProgress);
  return gReviewLoadingGeneration;
}

function updateReviewLoadingProgress(pct, text = null) {
  if (!gReviewLoadingActive) return;
  const nextPct = Math.max(gReviewLoadingProgress, Math.max(0, Math.min(100, Number(pct) || 0)));
  gReviewLoadingProgress = nextPct;
  if (text) gReviewLoadingMessage = text;
  setGlobalLoading(true, gReviewLoadingMessage, gReviewLoadingProgress);
}

function endReviewLoading(generation = null) {
  if (!gReviewLoadingActive) return;
  if (generation != null && generation !== gReviewLoadingGeneration) return;
  gReviewLoadingActive = false;
  gReviewLoadingMessage = 'Loading review results...';
  gReviewLoadingProgress = 0;
  setReviewResultsHidden(false);
  setGlobalLoading(false);
}

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

function isElementLikelyVisibleSoon(el) {
  if (!el) return false;
  const rect = el.getBoundingClientRect();
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
  return rect.bottom >= -120 && rect.top <= viewportHeight + 240;
}

function triggerMediaElementLoad(el) {
  if (!el || gPosterRequested.has(el)) return false;
  const imgSrc = el.getAttribute('data-src');
  const posterPath = el.getAttribute('data-poster-path');
  const path = el.getAttribute('data-video-path');
  if (!imgSrc && !posterPath && !path) return false;
  if (gPosterObserver) gPosterObserver.unobserve(el);
  gTotalOnPage++;
  if (imgSrc) {
    loadImage(el, imgSrc);
  } else if (posterPath) {
    loadStillPoster(el, posterPath);
  } else if (path) {
    loadVideoPoster(el, path);
    if (gBridge && gBridge.preload_video) {
      const item = gMedia.find(m => m.path === path);
      if (item) gBridge.preload_video(path, item.width || 0, item.height || 0);
    }
  }
  return true;
}

function prioritizeVisibleMediaLoads(root) {
  if (!root) return;
  const candidates = Array.from(root.querySelectorAll('img[data-src]:not([src]), img[data-poster-path]:not([src]), img[data-video-path]:not([src])'));
  if (!candidates.length) return;
  const prioritized = candidates
    .map((el, index) => ({ el, index, visible: isElementLikelyVisibleSoon(el) }))
    .sort((a, b) => {
      if (a.visible !== b.visible) return a.visible ? -1 : 1;
      return a.index - b.index;
    });
  prioritized.slice(0, 18).forEach(({ el }) => {
    triggerMediaElementLoad(el);
  });
}

function markCardMediaReady(card) {
  if (!card) return;
  card.classList.remove('loading');
  card.classList.add('ready');
  if (card.classList.contains('review-card-pending')) {
    requestAnimationFrame(() => {
      card.classList.add('review-card-visible');
      card.classList.remove('review-card-pending');
    });
  }
}

function waitForInitialReviewCards(root, generation) {
  return new Promise((resolve) => {
    if (!root || !gReviewLoadingActive || generation !== gReviewLoadingGeneration) {
      resolve();
      return;
    }
    const step = () => {
      if (!gReviewLoadingActive || generation !== gReviewLoadingGeneration) {
        resolve();
        return;
      }
      if (root.querySelector('.empty')) {
        resolve();
        return;
      }
      const reviewCards = Array.from(root.querySelectorAll('.gallery-duplicates-root .card'));
      if (!reviewCards.length) {
        requestAnimationFrame(step);
        return;
      }
      const visibleCards = reviewCards.filter(card => isElementLikelyVisibleSoon(card));
      if (!visibleCards.length) {
        requestAnimationFrame(step);
        return;
      }
      const pendingVisible = visibleCards.filter((card) => {
        if (card.classList.contains('review-card-pending')) return true;
        return !!card.querySelector('img[data-src]:not([src]), img[data-poster-path]:not([src]), img[data-video-path]:not([src])');
      });
      if (!pendingVisible.length) {
        resolve();
        return;
      }
      requestAnimationFrame(step);
    };
    step();
  });
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

  function render() {
    if (!gScanActive) {
      el.hidden = true;
      return;
    }
    if (gScanManuallyHidden) {
      el.hidden = true;
      return;
    }
    el.hidden = false;
  }
  gRenderScanToast = render;

  el.onclick = () => {
    gScanManuallyHidden = true;
    render();
  };

  if (gBridge.scanProgress) {
    gBridge.scanProgress.connect((fileName, percent) => {
      file.textContent = fileName;
      bar.style.width = `${percent}%`;
      if (gReviewLoadingActive && isDuplicateModeActive()) {
        updateReviewLoadingProgress(10 + Math.round((Math.max(0, Math.min(100, Number(percent) || 0)) * 0.8)), gReviewLoadingMessage);
      }
      render();
    });
  }

  if (gBridge.scanStarted) {
    gBridge.scanStarted.connect(() => {
      gScanManuallyHidden = false;
      bar.style.width = '0%';
      file.textContent = 'Initializing...';
      render();
    });
  }

  if (gBridge.scanFinished) {
    gBridge.scanFinished.connect(() => {
      render();
      file.textContent = 'Finished';
      bar.style.width = '100%';
      setTimeout(() => {
        render();
      }, 2000);
    });
  }
}

function loadStillPoster(el, path) {
  if (gPosterRequested.has(el)) return;
  gPosterRequested.add(el);
  el.style.opacity = '0';
  if (gBridge && gBridge.get_video_poster) {
    gBridge.get_video_poster(path, function (posterUrl) {
      const card = el.closest('.card');
      if (posterUrl) {
        const tempImg = new Image();
        tempImg.onload = () => {
          el.src = posterUrl;
          gLoadedOnPage++;
          requestAnimationFrame(() => { el.style.opacity = '1'; });
          if (card) markCardMediaReady(card);
        };
        tempImg.onerror = () => {
          el.removeAttribute('src');
          gLoadedOnPage++;
          requestAnimationFrame(() => { el.style.opacity = '1'; });
          if (card) markCardMediaReady(card);
        };
        tempImg.src = posterUrl;
      } else {
        el.removeAttribute('src');
        gLoadedOnPage++;
        requestAnimationFrame(() => { el.style.opacity = '1'; });
        if (card) markCardMediaReady(card);
      }
    });
  }
}

function wireTextProcessingIndicator() {
  const el = document.getElementById('textProcessingToast');
  const label = document.getElementById('textProcessingLabel');
  const file = document.getElementById('textProcessingFile');
  const bar = document.getElementById('textProcessingBar');
  const pauseBtn = document.getElementById('textProcessingPause');
  if (!el || !label || !file || !bar || !gBridge) return;

  function render() {
    if (!gTextProcessingActive) {
      el.hidden = true;
      return;
    }
    const allowVisible = isTextFilterActive() || gTextProcessingForceVisible;
    if (!allowVisible || gTextProcessingDismissed) {
      el.hidden = true;
      return;
    }
    el.hidden = false;
    label.textContent = gTextProcessingWaiting
      ? (gTextProcessingStage || 'Detecting Text')
      : gTextProcessingPaused
      ? `${gTextProcessingStage || 'Detecting Text'} (Paused)`
      : (gTextProcessingStage || 'Detecting Text');
    if (gTextProcessingTotal > 0) {
      file.textContent = `${gTextProcessingCurrent} / ${gTextProcessingTotal}`;
      bar.style.width = `${Math.max(0, Math.min(100, Math.round((gTextProcessingCurrent / gTextProcessingTotal) * 100)))}%`;
    } else {
      file.textContent = 'Starting...';
      bar.style.width = '0%';
    }
    if (pauseBtn) {
      pauseBtn.textContent = gTextProcessingPaused ? 'Resume' : 'Pause';
      pauseBtn.disabled = gTextProcessingWaiting;
    }
  }
  gRenderTextProcessingToast = render;

  el.onclick = () => {
    gTextProcessingDismissed = true;
    gTextProcessingForceVisible = false;
    render();
  };

  if (pauseBtn) {
    pauseBtn.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (gTextProcessingPaused) {
        gTextProcessingPaused = false;
        gTextProcessingWaiting = false;
        gTextProcessingDismissed = false;
        gTextProcessingForceVisible = true;
        if (gBridge.resume_text_processing) {
          gBridge.resume_text_processing();
        }
      } else if (gBridge.pause_text_processing) {
        gTextProcessingPaused = true;
        gTextProcessingWaiting = false;
        gBridge.pause_text_processing();
      }
      render();
    });
  }

    if (gBridge.textProcessingStarted) {
    gBridge.textProcessingStarted.connect((stage, total) => {
      gTextProcessingActive = true;
      gTextProcessingPaused = false;
      gTextProcessingWaiting = !!(stage && String(stage).toLowerCase().includes('waiting'));
      gTextProcessingStage = stage || 'Detecting Text';
      gTextProcessingCurrent = 0;
      gTextProcessingTotal = Math.max(0, Number(total || 0));
      render();
    });
  }

  if (gBridge.textProcessingProgress) {
    gBridge.textProcessingProgress.connect((stage, current, total) => {
      gTextProcessingActive = true;
      gTextProcessingPaused = false;
      gTextProcessingWaiting = false;
      gTextProcessingStage = stage || gTextProcessingStage || 'Detecting Text';
      gTextProcessingCurrent = Math.max(0, Number(current || 0));
      gTextProcessingTotal = Math.max(0, Number(total || 0));
      render();
    });
  }

  if (gBridge.textProcessingFinished) {
    gBridge.textProcessingFinished.connect(() => {
      gTextProcessingActive = false;
      gTextProcessingPaused = false;
      gTextProcessingWaiting = false;
      gTextProcessingForceVisible = false;
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

function deselectAll(force = false) {
  if (!force && gIsCtxMenuClick) {
    gIsCtxMenuClick = false;
    return;
  }
  gIsCtxMenuClick = false;
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
window.__mmx_selectAllVisible = selectAll;

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

function reconcileSelectionWithVisibleItems(items) {
  const visiblePaths = new Set(
    (Array.isArray(items) ? items : [])
      .map(item => String((item && item.path) || ''))
      .filter(Boolean)
  );
  let changed = false;
  Array.from(gSelectedPaths).forEach((path) => {
    if (!visiblePaths.has(path)) {
      gSelectedPaths.delete(path);
      changed = true;
    }
  });
  if (gSelectedPaths.size === 0) {
    gLockedCard = null;
    gLastSelectionIdx = -1;
  } else if (gLockedCard) {
    const lockedPath = gLockedCard.getAttribute('data-path') || '';
    if (!lockedPath || !gSelectedPaths.has(lockedPath)) {
      gLockedCard = null;
    }
  }
  if (changed) {
    syncMetadataToBridge();
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

function getDuplicateKeepPaths(groupKey) {
  const override = gDuplicateKeepOverrides.get(String(groupKey || ''));
  if (override instanceof Set) return Array.from(override);
  if (Array.isArray(override)) return override.filter(Boolean);
  if (override) return [override];
  const keepItem = gMedia.find(item => String(item.duplicate_group_key || '') === String(groupKey || '') && item.duplicate_is_overall_best);
  return keepItem && keepItem.path ? [keepItem.path] : [];
}

function getDefaultDuplicateKeepPaths(groupKey) {
  const computed = computeAutoResolveKeepPaths(groupKey, gCachedSettings || {});
  if (computed.length) return computed;
  const keepItem = gMedia.find(item => String(item.duplicate_group_key || '') === String(groupKey || '') && item.duplicate_is_overall_best);
  return keepItem && keepItem.path ? [keepItem.path] : [];
}

function getDefaultDuplicateBestPath(groupKey) {
  const keepItem = gMedia.find(item => String(item.duplicate_group_key || '') === String(groupKey || '') && item.duplicate_is_overall_best);
  if (keepItem && keepItem.path) return keepItem.path;
  const defaultKeepPaths = getDefaultDuplicateKeepPaths(groupKey);
  return defaultKeepPaths[0] || '';
}

function getDuplicateDeletePaths(groupKey) {
  const override = gDuplicateDeleteOverrides.get(String(groupKey || ''));
  if (override instanceof Set) return Array.from(override);
  if (Array.isArray(override)) return override.filter(Boolean);
  if (override) return [override];
  const keepPaths = new Set(getDefaultDuplicateKeepPaths(groupKey).map(normalizeMediaPath).filter(Boolean));
  return getDuplicateGroupItems(groupKey)
    .map(item => String(item.path || ''))
    .filter(path => path && !keepPaths.has(normalizeMediaPath(path)));
}

function getDuplicateBestPath(groupKey) {
  const override = gDuplicateBestOverrides.get(String(groupKey || ''));
  if (override) return String(override);
  const keepItem = gMedia.find(item => String(item.duplicate_group_key || '') === String(groupKey || '') && item.duplicate_is_overall_best);
  return keepItem && keepItem.path ? keepItem.path : '';
}

function setDuplicateKeepPaths(groupKey, paths) {
  const key = String(groupKey || '');
  if (!key) return;
  const nextPaths = Array.from(new Set((Array.isArray(paths) ? paths : [paths]).map(v => String(v || '')).filter(Boolean)));
  const normalizedNextPaths = new Set(nextPaths.map(normalizeMediaPath).filter(Boolean));
  gDuplicateKeepOverrides.set(key, new Set(nextPaths));
  document.querySelectorAll(`.card[data-duplicate-group-key="${CSS.escape(key)}"]`).forEach((card) => {
    const checked = normalizedNextPaths.has(normalizeMediaPath(card.getAttribute('data-path') || ''));
    card.setAttribute('data-duplicate-keep', checked ? 'true' : 'false');
    const toggle = card.querySelector('.duplicate-keep-toggle');
    if (toggle) toggle.checked = checked;
  });
  updateDuplicateReviewSummary();
}

function setDuplicateDeletePaths(groupKey, paths) {
  const key = String(groupKey || '');
  if (!key) return;
  const nextPaths = Array.from(new Set((Array.isArray(paths) ? paths : [paths]).map(v => String(v || '')).filter(Boolean)));
  const normalizedNextPaths = new Set(nextPaths.map(normalizeMediaPath).filter(Boolean));
  gDuplicateDeleteOverrides.set(key, new Set(nextPaths));
  document.querySelectorAll(`.card[data-duplicate-group-key="${CSS.escape(key)}"]`).forEach((card) => {
    const checked = normalizedNextPaths.has(normalizeMediaPath(card.getAttribute('data-path') || ''));
    card.setAttribute('data-duplicate-delete', checked ? 'true' : 'false');
    const toggle = card.querySelector('.duplicate-delete-toggle');
    if (toggle) toggle.checked = checked;
  });
  updateDuplicateReviewSummary();
}

function setDuplicateBestPath(groupKey, path) {
  const key = String(groupKey || '');
  const nextPath = String(path || '');
  if (!key) return;
  if (nextPath) gDuplicateBestOverrides.set(key, nextPath);
  else gDuplicateBestOverrides.delete(key);
  const normalizedNextPath = normalizeMediaPath(nextPath);
  if (normalizedNextPath) {
    const keepPaths = new Set(getDuplicateKeepPaths(key));
    const deletePaths = new Set(getDuplicateDeletePaths(key));
    const matchingItem = getDuplicateGroupItems(key).find(item => normalizeMediaPath(item.path) === normalizedNextPath);
    if (matchingItem && matchingItem.path) {
      keepPaths.add(matchingItem.path);
      deletePaths.delete(matchingItem.path);
      setDuplicateKeepPaths(key, Array.from(keepPaths));
      setDuplicateDeletePaths(key, Array.from(deletePaths));
    }
  }
  document.querySelectorAll(`.card[data-duplicate-group-key="${CSS.escape(key)}"]`).forEach((card) => {
    const checked = !!normalizedNextPath && normalizeMediaPath(card.getAttribute('data-path') || '') === normalizedNextPath;
    card.setAttribute('data-duplicate-best', checked ? 'true' : 'false');
    const toggle = card.querySelector('.duplicate-best-toggle');
    if (toggle) toggle.checked = checked;
    const overall = card.querySelector('.duplicate-overall-best');
    if (overall) overall.hidden = !checked;
  });
  syncCompareStateFromReviewGroup(key, getDuplicateKeepPaths(key), getDuplicateDeletePaths(key), nextPath);
}

function resetDuplicateGroupCheckboxesToRules(groupKey) {
  const key = String(groupKey || '');
  if (!key) return;
  const groupItems = getDuplicateGroupItems(key);
  if (!groupItems.length) return;
  const groupPaths = new Set(groupItems.map(item => String(item.path || '')).filter(Boolean));
  const defaultKeepPaths = getDefaultDuplicateKeepPaths(key).filter(path => groupPaths.has(path));
  const normalizedKeepPaths = new Set(defaultKeepPaths.map(normalizeMediaPath).filter(Boolean));
  const defaultDeletePaths = groupItems
    .map(item => String(item.path || ''))
    .filter(path => path && !normalizedKeepPaths.has(normalizeMediaPath(path)));
  const defaultBestPath = getDefaultDuplicateBestPath(key);
  gDuplicateKeepOverrides.delete(key);
  gDuplicateDeleteOverrides.delete(key);
  gDuplicateBestOverrides.delete(key);
  setDuplicateKeepPaths(key, defaultKeepPaths);
  setDuplicateDeletePaths(key, defaultDeletePaths);
  setDuplicateBestPath(key, defaultBestPath);
}

function resetAllSimilarGroupCheckboxesToRules() {
  buildDuplicateGroups(gMedia).forEach((group) => {
    resetDuplicateGroupCheckboxesToRules(group.key);
  });
}

function toggleDuplicateKeepPath(groupKey, path, checked) {
  const key = String(groupKey || '');
  const nextPath = String(path || '');
  if (!key || !nextPath) return;
  const keepPaths = new Set(getDuplicateKeepPaths(key));
  const deletePaths = new Set(getDuplicateDeletePaths(key));
  if (checked) keepPaths.add(nextPath);
  else keepPaths.delete(nextPath);
  if (checked) deletePaths.delete(nextPath);
  const nextKeepPaths = Array.from(keepPaths);
  setDuplicateKeepPaths(key, nextKeepPaths);
  setDuplicateDeletePaths(key, Array.from(deletePaths));
  syncCompareStateFromReviewGroup(key, nextKeepPaths, Array.from(deletePaths), getDuplicateBestPath(key));
}

function toggleDuplicateDeletePath(groupKey, path, checked) {
  const key = String(groupKey || '');
  const nextPath = String(path || '');
  if (!key || !nextPath) return;
  const keepPaths = new Set(getDuplicateKeepPaths(key));
  const deletePaths = new Set(getDuplicateDeletePaths(key));
  if (checked) {
    deletePaths.add(nextPath);
    keepPaths.delete(nextPath);
  } else {
    deletePaths.delete(nextPath);
  }
  if (checked && normalizeMediaPath(getDuplicateBestPath(key)) === normalizeMediaPath(nextPath)) {
    setDuplicateBestPath(key, '');
  }
  const nextKeepPaths = Array.from(keepPaths);
  setDuplicateKeepPaths(key, nextKeepPaths);
  setDuplicateDeletePaths(key, Array.from(deletePaths));
  syncCompareStateFromReviewGroup(key, nextKeepPaths, Array.from(deletePaths), getDuplicateBestPath(key));
}

function deletePathsSequential(paths, onDone) {
  const queue = Array.isArray(paths) ? paths.slice() : [];
  const step = () => {
    const next = queue.shift();
    if (!next) {
      if (typeof onDone === 'function') onDone();
      return;
    }
    if (!gBridge) {
      step();
      return;
    }
    deletePathFromUi(next, function () {
      step();
    });
  };
  step();
}

function deletePathFromUi(path, onDone) {
  if (!path || !gBridge) {
    if (typeof onDone === 'function') onDone(false);
    return;
  }
  const finish = (ok) => {
    if (typeof onDone === 'function') onDone(!!ok);
  };
  if (!gBridge.get_settings) {
    if (!gBridge.delete_path) {
      finish(false);
      return;
    }
    gBridge.delete_path(path, finish);
    return;
  }
  gBridge.get_settings((settings) => {
    const useRecycleBin = settings && settings['gallery.use_recycle_bin'] !== undefined
      ? !!settings['gallery.use_recycle_bin']
      : true;
    if (useRecycleBin) {
      if (!gBridge.delete_path) {
        finish(false);
        return;
      }
      gBridge.delete_path(path, finish);
      return;
    }
    const parts = String(path).split(/[/\\]/);
    const name = parts[parts.length - 1] || path;
    if (!window.confirm(`Permanently delete "${name}"?`)) {
      finish(false);
      return;
    }
    if (!gBridge.delete_path_permanent) {
      finish(false);
      return;
    }
    gBridge.delete_path_permanent(path, finish);
  });
}

function getDuplicateGroupItems(groupKey) {
  return gMedia
    .filter(item => String(item.duplicate_group_key || '') === String(groupKey || ''))
    .slice()
    .sort((a, b) => Number(a.duplicate_group_position || 0) - Number(b.duplicate_group_position || 0));
}

function getDuplicateReviewSummaryTotals() {
  const groupKeys = Array.from(new Set(
    gMedia
      .map(item => String(item.duplicate_group_key || '').trim())
      .filter(Boolean)
  ));
  let keepCount = 0;
  let deleteCount = 0;
  let savings = 0;
  groupKeys.forEach((groupKey) => {
    const deleteSet = new Set(getDuplicateDeletePaths(groupKey).map(normalizeMediaPath).filter(Boolean));
    getDuplicateGroupItems(groupKey).forEach((item) => {
      const normalizedPath = normalizeMediaPath(item.path || '');
      if (!normalizedPath) return;
      if (deleteSet.has(normalizedPath)) {
        deleteCount += 1;
        savings += Number(item.file_size) || 0;
      } else {
        keepCount += 1;
      }
    });
  });
  return { keepCount, deleteCount, savings };
}

function updateDuplicateReviewSummary() {
  const totals = getDuplicateReviewSummaryTotals();
  const keepEl = document.querySelector('.duplicate-review-keep .duplicate-summary-value');
  const deleteEl = document.querySelector('.duplicate-review-delete .duplicate-summary-value');
  const saveEl = document.querySelector('.duplicate-review-save .duplicate-summary-value');
  if (keepEl) keepEl.textContent = `${totals.keepCount}`;
  if (deleteEl) deleteEl.textContent = `${totals.deleteCount}`;
  if (saveEl) saveEl.textContent = `${formatFileSize(totals.savings) || '0 B'}`;
}

function computeAutoResolveKeepPaths(groupKey, settings = {}) {
  const items = getDuplicateGroupItems(groupKey).filter(item => item && item.path);
  if (!items.length) return [];
  const keep = new Set();
  const overallKeepPath = getDuplicateBestPath(groupKey) || (items[0] && items[0].path) || '';
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
  const deletePaths = getDuplicateDeletePaths(groupKey).filter(path => paths.includes(path));
  const mergeFirst = !!(settings && settings['duplicate.rules.merge_before_delete']);
  if (!deletePaths.length) {
    if (typeof onDone === 'function') onDone();
    return;
  }
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
    const items = getDuplicateGroupItems(groupKey);
    const paths = items.map(item => item.path).filter(Boolean);
    const keepPaths = new Set(getDuplicateKeepPaths(groupKey).filter(path => paths.includes(path)));
    const deletePaths = paths.filter(path => !keepPaths.has(path));
    if (!keepPaths.size || !deletePaths.length) {
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

function deleteSelectedInDuplicateGroup(groupKey) {
  if (!gBridge || !gBridge.get_settings) return;
  gPendingScrollAnchor = captureCurrentGroupScrollAnchor();
  setGlobalLoading(true, 'Deleting duplicate files...', 25);
  gBridge.get_settings((settings) => {
    const nextSettings = settings || {};
    const deletePaths = getDuplicateDeletePaths(groupKey);
    const items = getDuplicateGroupItems(groupKey);
    const paths = items.map(item => item.path).filter(Boolean);
    if (!deletePaths.length) {
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
  if (!path || !gBridge) return;
  gPendingScrollAnchor = captureCurrentGroupScrollAnchor();
  setGlobalLoading(true, 'Deleting file...', 25);
  deletePathFromUi(path, function () {
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
    deselectAll(true);
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
  items.filter(item => !item.is_folder && !gDismissedReviewPaths.has(normalizeMediaPath(item.path))).forEach((item) => {
    const key = String(item.duplicate_group_key || item.content_hash || '').trim();
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
        getDuplicateBestPath(group.key)
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

function getReviewGroupsForNavigation() {
  if (!isDuplicateModeActive()) return [];
  return buildDuplicateGroups(gMedia);
}

function getCurrentReviewGroupKeyForNavigation() {
  const comparePaths = getCompareActivePaths();
  const compareGroupKeys = Array.from(new Set(comparePaths.map(getDuplicateGroupKeyForPath).filter(Boolean)));
  if (compareGroupKeys.length === 1) return compareGroupKeys[0];

  const main = document.querySelector('main');
  const sections = Array.from(document.querySelectorAll('.gallery-group[data-group-key]'));
  if (!main || !sections.length) return '';

  const mainRect = main.getBoundingClientRect();
  let closest = null;
  sections.forEach((section) => {
    const rect = section.getBoundingClientRect();
    const distance = Math.abs(rect.top - mainRect.top);
    if (!closest || distance < closest.distance) {
      closest = { key: String(section.dataset.groupKey || ''), distance };
    }
  });
  return closest ? closest.key : '';
}

function focusReviewGroup(groupKey) {
  const targetKey = String(groupKey || '').trim();
  if (!targetKey || !gBridge) return false;
  const group = getReviewGroupsForNavigation().find(entry => String(entry.key || '') === targetKey);
  if (!group || !Array.isArray(group.items) || group.items.length < 2) return false;

  const comparePaths = group.items
    .slice(0, 2)
    .map(item => String(item && item.path || ''))
    .filter(Boolean);
  if (comparePaths.length < 2) return false;

  toggleGroupCollapsed(targetKey, false);
  if (gBridge.compare_paths) {
    gBridge.compare_paths(comparePaths);
  } else if (gBridge.set_compare_path) {
    gBridge.set_compare_path('left', comparePaths[0]);
    gBridge.set_compare_path('right', comparePaths[1]);
  }

  const keepPaths = getDuplicateKeepPaths(targetKey).slice().sort();
  const deletePaths = getDuplicateDeletePaths(targetKey).slice().sort();
  const bestPath = getDuplicateBestPath(targetKey);
  window.setTimeout(() => {
    syncCompareStateFromReviewGroup(targetKey, keepPaths, deletePaths, bestPath);
    scrollToGroup(targetKey);
  }, 0);
  return true;
}

function jumpReviewGroup(direction) {
  const groups = getReviewGroupsForNavigation();
  if (!groups.length) return false;

  const step = Number(direction) < 0 ? -1 : 1;
  const currentKey = getCurrentReviewGroupKeyForNavigation();
  const currentIndex = groups.findIndex(group => String(group.key || '') === currentKey);
  const targetIndex = currentIndex < 0
    ? (step > 0 ? 0 : groups.length - 1)
    : currentIndex + step;
  if (targetIndex < 0 || targetIndex >= groups.length) return false;
  return focusReviewGroup(groups[targetIndex].key);
}

window.__mmx_jumpReviewGroup = function (direction) {
  return jumpReviewGroup(direction);
};

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

function getGalleryLayoutMetrics() {
  const main = document.querySelector('main');
  const mediaList = document.getElementById('mediaList');
  return {
    main,
    mediaList,
    width: Math.round((main && main.clientWidth) || (mediaList && mediaList.clientWidth) || window.innerWidth || 0),
    height: Math.round((main && main.clientHeight) || (mediaList && mediaList.clientHeight) || window.innerHeight || 0),
  };
}

function runGalleryRelayout(reason = '') {
  const metrics = getGalleryLayoutMetrics();
  const { mediaList, width, height } = metrics;
  if (!mediaList) return;
  gGalleryLastLayoutWidth = width;
  gGalleryLastLayoutHeight = height;

  if (mediaList.classList.contains('gallery-details')) {
    applyDetailsColumnWidths(mediaList);
  }

  if (Array.isArray(gMedia) && gMedia.length > 0) {
    rerenderCurrentMediaPreservingScroll();
  }

  syncTimelineViewportBox();
  layoutTimelinePoints();
  refreshVisibleTimelineAnchors();
  scheduleTimelineScrollTargetRefresh();
  if (shouldUseInfiniteScrollMode()) {
    requestAnimationFrame(() => maybeLoadMoreInfiniteResults());
  }
}

function scheduleGalleryRelayout(reason = '') {
  const metrics = getGalleryLayoutMetrics();
  if (!metrics.mediaList) return;
  const widthChanged = Math.abs(metrics.width - gGalleryLastLayoutWidth) > 1;
  const heightChanged = Math.abs(metrics.height - gGalleryLastLayoutHeight) > 1;
  if (!widthChanged && !heightChanged && reason !== 'force') {
    return;
  }

  if (gGalleryRelayoutTimer) {
    clearTimeout(gGalleryRelayoutTimer);
    gGalleryRelayoutTimer = 0;
  }
  gGalleryRelayoutTimer = window.setTimeout(() => {
    gGalleryRelayoutTimer = 0;
    if (gGalleryRelayoutRaf) {
      cancelAnimationFrame(gGalleryRelayoutRaf);
      gGalleryRelayoutRaf = 0;
    }
    gGalleryRelayoutRaf = requestAnimationFrame(() => {
      gGalleryRelayoutRaf = 0;
      runGalleryRelayout(reason);
    });
  }, 90);
}

function initGalleryResizeObserver() {
  if (gGalleryResizeObserver || typeof ResizeObserver === 'undefined') return;
  const { main, width, height } = getGalleryLayoutMetrics();
  gGalleryLastLayoutWidth = width;
  gGalleryLastLayoutHeight = height;
  gGalleryResizeObserver = new ResizeObserver(() => {
    scheduleGalleryRelayout('observer');
  });
  if (main) gGalleryResizeObserver.observe(main);
}

window.__mmx_scheduleGalleryRelayout = function (reason) {
  scheduleGalleryRelayout(reason || 'qt');
};

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
  clearDismissedReviewPaths();
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
  const duplicateGroupKey = String(item.duplicate_group_key || '');
  const normalizedItemPath = normalizeMediaPath(item.path || '');
  const duplicateKeepPathSet = duplicateMode && !isFolder
    ? new Set(getDuplicateKeepPaths(duplicateGroupKey).map(normalizeMediaPath).filter(Boolean))
    : null;
  const duplicateDeletePathSet = duplicateMode && !isFolder
    ? new Set(getDuplicateDeletePaths(duplicateGroupKey).map(normalizeMediaPath).filter(Boolean))
    : null;
  const normalizedDuplicateBestPath = duplicateMode && !isFolder
    ? normalizeMediaPath(getDuplicateBestPath(duplicateGroupKey))
    : '';
  const duplicateKeepChecked = !!(duplicateKeepPathSet && normalizedItemPath && duplicateKeepPathSet.has(normalizedItemPath));
  const duplicateDeleteChecked = !!(duplicateDeletePathSet && normalizedItemPath && duplicateDeletePathSet.has(normalizedItemPath));
  const duplicateBestChecked = !!(normalizedDuplicateBestPath && normalizedItemPath && normalizedDuplicateBestPath === normalizedItemPath);
  card.className = `card structured-card${isFolder ? ' folder-card ready' : ' loading'}`;
  if (duplicateMode && !isFolder) card.classList.add('duplicate-card');
  if (duplicateMode && !isFolder) card.classList.add('review-card-pending');
  card.tabIndex = 0;
  card.setAttribute('data-path', item.path || '');
  card.setAttribute('data-is-folder', isFolder ? 'true' : 'false');
  if (duplicateMode && !isFolder) {
    card.setAttribute('data-duplicate-group-key', duplicateGroupKey);
    card.setAttribute('data-duplicate-keep', duplicateKeepChecked ? 'true' : 'false');
    card.setAttribute('data-duplicate-delete', duplicateDeleteChecked ? 'true' : 'false');
  }

  const thumbWrap = document.createElement('div');
  thumbWrap.className = 'structured-thumb';
  if (item.thumb_bg_hint) thumbWrap.setAttribute('data-thumb-bg-hint', item.thumb_bg_hint);

  if (isFolder) {
    const folderThumb = document.createElement('div');
    folderThumb.className = 'folder-thumb';
    folderThumb.innerHTML = '<div class="folder-glyph"></div>';
    thumbWrap.appendChild(folderThumb);
  } else if (!usesThumbnails) {
    const icon = document.createElement('div');
    icon.className = `media-icon ${item.media_type === 'video' ? 'video-icon' : 'image-icon'}`;
    thumbWrap.appendChild(icon);
    markCardMediaReady(card);
  } else if (item.media_type === 'image') {
    const img = document.createElement('img');
    img.className = 'thumb';
    img.alt = '';
    if (item.is_animated && !gAutoplayGalleryAnimatedGifs) {
      img.classList.add('poster');
      img.setAttribute('data-poster-path', item.path || '');
    } else {
      img.setAttribute('data-src', item.url);
    }
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
          const shouldLoop = shouldLoopVideoForDurationSeconds(item.duration || 0);
          gBridge.open_native_video_inplace(path, rect.x, rect.y, rect.width, rect.height, true, shouldLoop, gMuteVideoByDefault, item.width || 0, item.height || 0);
        } else {
          gBridge.open_native_video(path, true, shouldLoopVideoForDurationSeconds(item.duration || 0), gMuteVideoByDefault, item.width || 0, item.height || 0);
        }
      });
    }
  }

  const content = document.createElement('div');
  content.className = 'structured-content';
  const duplicateHeader = duplicateMode && !isFolder ? document.createElement('div') : null;
  if (duplicateHeader) duplicateHeader.className = 'structured-content duplicate-card-header';
  if (duplicateHeader) content.classList.add('duplicate-card-footer');
  const duplicateHeaderText = duplicateHeader ? document.createElement('div') : null;
  if (duplicateHeaderText) duplicateHeaderText.className = 'duplicate-card-header-text';
  const primaryContent = duplicateHeaderText || duplicateHeader || content;

  const title = document.createElement('div');
  title.className = 'entry-name';
  title.textContent = getItemName(item);
  title.title = item.path || getItemName(item);
  primaryContent.appendChild(title);

  const folder = document.createElement('div');
  folder.className = 'entry-folder';
  folder.textContent = duplicateMode ? (getItemFolder(item) || item.path || '') : getItemFolderDisplay(item);
  folder.title = getItemFolder(item) || item.path || '';
  primaryContent.appendChild(folder);

  if (duplicateHeader && duplicateHeaderText) {
    duplicateHeader.appendChild(duplicateHeaderText);
    const dismissBtn = document.createElement('button');
    dismissBtn.type = 'button';
    dismissBtn.className = 'duplicate-dismiss-btn';
    dismissBtn.title = 'Exclude from this review group in future scans';
    dismissBtn.setAttribute('aria-label', 'Exclude from this review group in future scans');
    dismissBtn.textContent = '×';
    dismissBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      dismissReviewPath(item.path || '');
    });
    duplicateHeader.appendChild(dismissBtn);
  }

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
    keepToggle.checked = duplicateKeepChecked;
    keepToggle.addEventListener('click', (e) => {
      e.stopPropagation();
    });
    keepToggle.addEventListener('change', (e) => {
      e.stopPropagation();
      toggleDuplicateKeepPath(item.duplicate_group_key || '', item.path || '', !!keepToggle.checked);
    });
    keepLabel.appendChild(keepToggle);
    const keepText = document.createElement('span');
    keepText.textContent = 'Keep';
    keepLabel.appendChild(keepText);
    controls.appendChild(keepLabel);

    const deleteLabel = document.createElement('label');
    deleteLabel.className = 'duplicate-keep-label';
    const deleteToggle = document.createElement('input');
    deleteToggle.type = 'checkbox';
    deleteToggle.className = 'duplicate-keep-toggle duplicate-delete-toggle';
    deleteToggle.checked = duplicateDeleteChecked;
    deleteToggle.addEventListener('click', (e) => {
      e.stopPropagation();
    });
    deleteToggle.addEventListener('change', (e) => {
      e.stopPropagation();
      toggleDuplicateDeletePath(item.duplicate_group_key || '', item.path || '', !!deleteToggle.checked);
    });
    deleteLabel.appendChild(deleteToggle);
    const deleteText = document.createElement('span');
    deleteText.textContent = 'Delete';
    deleteLabel.appendChild(deleteText);
    controls.appendChild(deleteLabel);

    const bestLabel = document.createElement('label');
    bestLabel.className = 'duplicate-keep-label';
    if (isExactDuplicateReviewItem(item)) {
      bestLabel.classList.add('duplicate-identical-label');
      const identicalText = document.createElement('span');
      identicalText.textContent = 'Identical';
      bestLabel.appendChild(identicalText);
    } else {
      const bestToggle = document.createElement('input');
      bestToggle.type = 'checkbox';
      bestToggle.className = 'duplicate-best-toggle';
      bestToggle.checked = duplicateBestChecked;
      bestToggle.addEventListener('click', (e) => {
        e.stopPropagation();
      });
      bestToggle.addEventListener('change', (e) => {
        e.stopPropagation();
        if (bestToggle.checked) {
          setDuplicateBestPath(item.duplicate_group_key || '', item.path || '');
        } else {
          bestToggle.checked = true;
        }
      });
      bestLabel.appendChild(bestToggle);
      const bestText = document.createElement('span');
      bestText.textContent = 'Best Overall';
      bestLabel.appendChild(bestText);
    }
    controls.appendChild(bestLabel);

    content.appendChild(controls);

    const bottomRow = document.createElement('div');
    bottomRow.className = 'duplicate-card-bottom';
    const bottomMeta = document.createElement('div');
    bottomMeta.className = 'duplicate-card-bottom-meta';

    const reasons = Array.isArray(item.duplicate_category_reasons) ? item.duplicate_category_reasons.filter(Boolean) : [];
    if (reasons.length) {
      const duplicateMeta = document.createElement('div');
      duplicateMeta.className = 'entry-detail duplicate-reason-list';
      for (let i = 0; i < reasons.length; i += 2) {
        const row = document.createElement('div');
        row.className = 'duplicate-reason-row';
        row.textContent = reasons.slice(i, i + 2).join(' • ');
        const rowReasons = reasons.slice(i, i + 2);
        if (rowReasons.length > 1) {
          row.textContent = '';
          rowReasons.forEach((reason, reasonIndex) => {
            const label = document.createElement('span');
            label.className = 'duplicate-reason-label';
            label.textContent = reason;
            row.appendChild(label);
            if (reasonIndex < rowReasons.length - 1) {
              const separator = document.createElement('span');
              separator.className = 'duplicate-reason-separator';
              separator.textContent = ' • ';
              row.appendChild(separator);
            }
          });
        }
        duplicateMeta.appendChild(row);
      }
      bottomMeta.appendChild(duplicateMeta);
    }

    if (item.duplicate_is_overall_best) {
      const overallBest = document.createElement('div');
      overallBest.className = 'entry-detail duplicate-overall-best';
      overallBest.textContent = '★ Best overall';
      overallBest.hidden = false;
      bottomMeta.appendChild(overallBest);
    } else {
      const overallBest = document.createElement('div');
      overallBest.className = 'entry-detail duplicate-overall-best';
      overallBest.textContent = '★ Best overall';
      overallBest.hidden = true;
      bottomMeta.appendChild(overallBest);
    }

    const actionRow = document.createElement('div');
    actionRow.className = 'duplicate-card-actions';
    const trashBtn = document.createElement('button');
    trashBtn.type = 'button';
    trashBtn.className = 'duplicate-trash-btn';
    trashBtn.title = 'Delete this file';
    trashBtn.setAttribute('aria-label', 'Delete this file');
    trashBtn.innerHTML = '<span class="duplicate-trash-icon" aria-hidden="true"></span>';
    trashBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      deleteDuplicateCard(item.path || '');
    });
    actionRow.appendChild(trashBtn);
    bottomRow.appendChild(bottomMeta);
    bottomRow.appendChild(actionRow);
    content.appendChild(bottomRow);
  }

  if (duplicateHeader) {
    card.appendChild(duplicateHeader);
  }
  card.appendChild(thumbWrap);
  card.appendChild(content);
  if (isFolder) {
    markCardMediaReady(card);
  }

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
  if (item.thumb_bg_hint) card.setAttribute('data-thumb-bg-hint', item.thumb_bg_hint);
  if (item.width && item.height) {
    card.style.aspectRatio = `${item.width} / ${item.height}`;
  }

  if (item.media_type === 'image') {
    const img = document.createElement('img');
    img.className = 'thumb';
    img.alt = '';
    if (item.is_animated && !gAutoplayGalleryAnimatedGifs) {
      img.classList.add('poster');
      img.setAttribute('data-poster-path', item.path || '');
    } else {
      img.setAttribute('data-src', item.url);
    }
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
      const shouldLoop = shouldLoopVideoForDurationSeconds(item.duration || 0);
      gBridge.open_native_video_inplace(path, rect.x, rect.y, rect.width, rect.height, true, shouldLoop, gMuteVideoByDefault, item.width || 0, item.height || 0);
    } else {
      gBridge.open_native_video(path, true, shouldLoopVideoForDurationSeconds(item.duration || 0), gMuteVideoByDefault, item.width || 0, item.height || 0);
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
    prioritizeVisibleMediaLoads(el);
    const unobserved = el.querySelectorAll('img[data-src]:not([src]), img[data-poster-path]:not([src]), img[data-video-path]:not([src])');
    unobserved.forEach(img => {
      if (gPosterRequested.has(img)) return;
      const imgSrc = img.getAttribute('data-src');
      const posterPath = img.getAttribute('data-poster-path');
      const path = img.getAttribute('data-video-path');
      const item = gMedia.find(m => m.path === path || m.url === imgSrc);
      if (imgSrc) {
        gBackgroundQueue.push({ type: 'image', el: img, imgSrc });
      } else if (posterPath) {
        gBackgroundQueue.push({ type: 'poster', el: img, path: posterPath });
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
    prioritizeVisibleMediaLoads(el);
    const unobserved = el.querySelectorAll('img[data-src]:not([src]), img[data-poster-path]:not([src]), img[data-video-path]:not([src])');
    unobserved.forEach(img => {
      if (gPosterRequested.has(img)) return;
      const imgSrc = img.getAttribute('data-src');
      const posterPath = img.getAttribute('data-poster-path');
      const path = img.getAttribute('data-video-path');
      const item = gMedia.find(m => m.path === path || m.url === imgSrc);
      if (imgSrc) {
        gBackgroundQueue.push({ type: 'image', el: img, imgSrc });
      } else if (posterPath) {
        gBackgroundQueue.push({ type: 'poster', el: img, path: posterPath });
      } else if (path && item) {
        gBackgroundQueue.push({ type: 'video', el: img, path, width: item.width, height: item.height });
      }
    });
    scheduleBackgroundDrain();
  });
}

function finalizeDuplicateMediaList(el, groups) {
  renderTimelineRail([]);
  restoreGroupScrollAnchor();
  groups.forEach((group) => {
    setDuplicateKeepPaths(group.key, getDuplicateKeepPaths(group.key));
    setDuplicateDeletePaths(group.key, getDuplicateDeletePaths(group.key));
    const bestPath = getDuplicateBestPath(group.key);
    if (bestPath) setDuplicateBestPath(group.key, bestPath);
  });
  updateDuplicateReviewSummary();
  syncDuplicateGroupFromCompareSelection(
    String(gCompareState && gCompareState.best_path || ''),
    Array.isArray(gCompareState && gCompareState.keep_paths) ? gCompareState.keep_paths : [],
    Array.isArray(gCompareState && gCompareState.delete_paths) ? gCompareState.delete_paths : []
  );
  maybeSeedCompareStateFromReview();
  prioritizeVisibleMediaLoads(el);
  const unobserved = el.querySelectorAll('img[data-src]:not([src]), img[data-poster-path]:not([src]), img[data-video-path]:not([src])');
  unobserved.forEach(img => {
    if (gPosterRequested.has(img)) return;
    const imgSrc = img.getAttribute('data-src');
    const posterPath = img.getAttribute('data-poster-path');
    const path = img.getAttribute('data-video-path');
    const item = gMedia.find(m => m.path === path || m.url === imgSrc);
    if (imgSrc) {
      gBackgroundQueue.push({ type: 'image', el: img, imgSrc });
    } else if (posterPath) {
      gBackgroundQueue.push({ type: 'poster', el: img, path: posterPath });
    } else if (path && item) {
      gBackgroundQueue.push({ type: 'video', el: img, path, width: item.width, height: item.height });
    }
  });
  scheduleBackgroundDrain();
}

function renderDuplicateMediaList(el, items, options = {}) {
  const { deferFinalize = false } = options;
  const groups = buildDuplicateGroups(items);
  const reviewMode = getReviewMode();
  const isSimilarReview = reviewMode === 'similar' || reviewMode === 'similar_only';
  const groupLabel = isSimilarReview ? 'Similar Group' : 'Duplicate Group';
  const summaryLabel = isSimilarReview ? 'Groups' : 'Duplicate Groups';
  const emptyLabel = isSimilarReview
    ? (shouldShowScanWaitingEmptyState() ? 'Scanning current folder. Wait for results to finish loading.' : 'No similar images found in the current scope.')
    : (shouldShowScanWaitingEmptyState() ? 'Scanning current folder. Wait for results to finish loading.' : 'No duplicates found in the current scope.');
  if (!groups.length) {
    const div = document.createElement('div');
    div.className = 'empty';
    div.textContent = emptyLabel;
    el.appendChild(div);
    renderTimelineRail([]);
    return;
  }
  el.classList.add('gallery-grouped', 'gallery-duplicates-root');

  const reviewNotice = document.createElement('div');
  reviewNotice.className = 'duplicate-review-note';
  reviewNotice.textContent = 'Selections applied based on your rules. Review below, then click Auto Resolve All.';
  el.appendChild(reviewNotice);

  const summary = document.createElement('section');
  summary.className = 'duplicate-summary';
  const totalFiles = groups.reduce((sum, group) => sum + group.items.length, 0);
  summary.innerHTML = `
    <div class="duplicate-summary-card">
      <div class="duplicate-summary-label">${summaryLabel}</div>
      <div class="duplicate-summary-value">${groups.length}</div>
    </div>
    <div class="duplicate-summary-card">
      <div class="duplicate-summary-label">Files</div>
      <div class="duplicate-summary-value">${totalFiles}</div>
    </div>
    <div class="duplicate-summary-card duplicate-review-stats duplicate-review-keep">
      <div class="duplicate-summary-label">Keep</div>
      <div class="duplicate-summary-value"></div>
    </div>
    <div class="duplicate-summary-card duplicate-review-stats duplicate-review-delete">
      <div class="duplicate-summary-label">Delete</div>
      <div class="duplicate-summary-value"></div>
    </div>
    <div class="duplicate-summary-card duplicate-review-stats duplicate-review-save">
      <div class="duplicate-summary-label">Potential Savings</div>
      <div class="duplicate-summary-value"></div>
    </div>
  `;
  const summaryActions = document.createElement('div');
  summaryActions.className = 'duplicate-summary-actions';
  if (reviewMode === 'similar' || reviewMode === 'similar_only') {
    const resetAllBtn = document.createElement('button');
    resetAllBtn.type = 'button';
    resetAllBtn.className = 'tb-btn highlight';
    resetAllBtn.textContent = 'Reset Checkboxes to Rules';
    resetAllBtn.addEventListener('click', resetAllSimilarGroupCheckboxesToRules);
    summaryActions.appendChild(resetAllBtn);
  }
  const autoResolveBtn = document.createElement('button');
  autoResolveBtn.type = 'button';
  autoResolveBtn.className = 'tb-btn highlight';
  autoResolveBtn.textContent = 'Auto Resolve All';
  autoResolveBtn.addEventListener('click', autoResolveAllDuplicateGroups);
  summaryActions.appendChild(autoResolveBtn);
  summary.appendChild(summaryActions);
  el.appendChild(summary);

  groups.forEach((group) => {
    const existingKeepPaths = getDuplicateKeepPaths(group.key);
    const hasDeleteOverride = gDuplicateDeleteOverrides.has(group.key);
    const existingDeletePaths = getDuplicateDeletePaths(group.key);
    const existingBestPath = getDuplicateBestPath(group.key);
    const groupPaths = new Set(group.items.map(item => item.path).filter(Boolean));
    const validKeepPaths = existingKeepPaths.filter(path => groupPaths.has(path));
    const validDeletePaths = existingDeletePaths.filter(path => groupPaths.has(path));
    const defaultKeepPaths = getDefaultDuplicateKeepPaths(group.key).filter(path => groupPaths.has(path));
    const defaultKeepSet = new Set(defaultKeepPaths.map(normalizeMediaPath).filter(Boolean));
    if (!validKeepPaths.length) {
      setDuplicateKeepPaths(group.key, defaultKeepPaths);
    } else if (validKeepPaths.length !== existingKeepPaths.length) {
      setDuplicateKeepPaths(group.key, validKeepPaths);
    }
    if (!validDeletePaths.length && !hasDeleteOverride) {
      setDuplicateDeletePaths(group.key, group.items.map(item => item.path).filter(path => path && !defaultKeepSet.has(normalizeMediaPath(path))));
    } else if (validDeletePaths.length !== existingDeletePaths.length) {
      setDuplicateDeletePaths(group.key, validDeletePaths);
    }
    if (!existingBestPath || !groupPaths.has(existingBestPath)) {
      setDuplicateBestPath(
        group.key,
        (group.keepItem && group.keepItem.path) ? group.keepItem.path : ((group.items[0] && group.items[0].path) || '')
      );
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

    const mergeBtn = document.createElement('button');
    mergeBtn.type = 'button';
    mergeBtn.className = 'tb-btn';
    mergeBtn.textContent = 'Merge Metadata';
    mergeBtn.addEventListener('click', () => mergeDuplicateGroupMetadata(group.key));
    actions.appendChild(mergeBtn);

    const deleteUncheckedBtn = document.createElement('button');
    deleteUncheckedBtn.type = 'button';
    deleteUncheckedBtn.className = 'tb-btn';
    deleteUncheckedBtn.textContent = 'Delete Selected Files';
    deleteUncheckedBtn.addEventListener('click', () => deleteSelectedInDuplicateGroup(group.key));
    actions.appendChild(deleteUncheckedBtn);

    const keepBtn = document.createElement('button');
    keepBtn.type = 'button';
    keepBtn.className = 'tb-btn';
    keepBtn.textContent = 'Keep Only Selected Files';
    keepBtn.addEventListener('click', () => keepBestInDuplicateGroup(group.key));
    actions.appendChild(keepBtn);

    if (reviewMode === 'similar' || reviewMode === 'similar_only') {
      const resetGroupBtn = document.createElement('button');
      resetGroupBtn.type = 'button';
      resetGroupBtn.className = 'tb-btn';
      resetGroupBtn.textContent = 'Reset Checkboxes to Rules';
      resetGroupBtn.addEventListener('click', () => resetDuplicateGroupCheckboxesToRules(group.key));
      actions.appendChild(resetGroupBtn);
    }

    section.appendChild(header);
    section.appendChild(body);
    section.appendChild(actions);
    el.appendChild(section);
    toggleGroupCollapsed(group.key, gCollapsedGroupKeys.has(group.key));
  });

  if (!deferFinalize) {
    requestAnimationFrame(() => finalizeDuplicateMediaList(el, groups));
  }
  return groups;
}

function showCtx(x, y, item, idx, fromLightbox = false) {
  const ctx = document.getElementById('ctx');
  if (!ctx) return;

  gCtxItem = item;
  gCtxIndex = idx;
  gCtxFromLightbox = !!fromLightbox;

  const hideBtn = document.getElementById('ctxHide');
  const unhideBtn = document.getElementById('ctxUnhide');
  const pinFolderBtn = document.getElementById('ctxPinFolder');
  const unpinFolderBtn = document.getElementById('ctxUnpinFolder');
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
  if (pinFolderBtn) pinFolderBtn.style.display = hasItem && isFolder && !isPinnedFolder(item && item.path) ? 'block' : 'none';
  if (unpinFolderBtn) unpinFolderBtn.style.display = hasItem && isFolder && isPinnedFolder(item && item.path) ? 'block' : 'none';
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
  const compareImagesBtn = document.getElementById('ctxCompareImages');
  const compareImageBtn = document.getElementById('ctxCompareImage');
  const compareLeftBtn = document.getElementById('ctxCompareLeft');
  const compareRightBtn = document.getElementById('ctxCompareRight');
  const compareLeftOccupied = !!compareSlotPath('left');
  const compareRightOccupied = !!compareSlotPath('right');
  const compareTargetPaths = (() => {
    if (item && item.path) {
      if (gSelectedPaths.has(item.path)) {
        return Array.from(gSelectedPaths).filter(path => {
          const selectedItem = gMedia.find(entry => entry.path === path);
          return selectedItem && !selectedItem.is_folder;
        });
      }
      return item.is_folder ? [] : [item.path];
    }
    return Array.from(gSelectedPaths).filter(path => {
      const selectedItem = gMedia.find(entry => entry.path === path);
      return selectedItem && !selectedItem.is_folder;
    });
  })();
  if (compareImagesBtn) compareImagesBtn.style.display = compareTargetPaths.length === 2 ? 'block' : 'none';
  if (compareImageBtn) compareImageBtn.style.display = compareTargetPaths.length === 1 && !compareLeftOccupied && !compareRightOccupied ? 'block' : 'none';
  if (compareLeftBtn) compareLeftBtn.style.display = compareTargetPaths.length === 1 && compareRightOccupied ? 'block' : 'none';
  if (compareRightBtn) compareRightBtn.style.display = compareTargetPaths.length === 1 && compareLeftOccupied ? 'block' : 'none';
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

    const applyHiddenStateToTargets = (hidden) => {
      if (!gBridge) return false;
      const targetPaths = getTargetPaths();
      if (!targetPaths.length) return false;

      if (fromLb) closeLightbox();
      setGlobalLoading(true, hidden ? 'Hiding...' : 'Unhiding...', 25);
      hideCtx();

      let pending = 0;
      let anySuccess = false;

      const finish = (success) => {
        pending -= 1;
        if (success) anySuccess = true;
        if (pending > 0) return;

        if (anySuccess) {
          targetPaths.forEach((path) => {
            const targetItem = gMedia.find(entry => entry.path === path);
            if (targetItem) targetItem.is_hidden = hidden;
          });
          refreshFromBridge(gBridge);
        } else {
          setGlobalLoading(false);
        }
      };

      targetPaths.forEach((path) => {
        const targetItem = gMedia.find(entry => entry.path === path) || (item && item.path === path ? item : null);
        if (!targetItem) return;
        const hideFn = targetItem.is_folder ? gBridge.set_folder_hidden : gBridge.set_media_hidden;
        if (!hideFn) return;
        pending += 1;
        hideFn.call(gBridge, path, hidden, finish);
      });

      if (pending === 0) {
        setGlobalLoading(false);
        return false;
      }
      return true;
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
      case 'ctxCompareImages': {
        const comparePaths = getTargetPaths().filter(path => {
          const selectedItem = gMedia.find(entry => entry.path === path);
          return selectedItem && !selectedItem.is_folder;
        }).slice(0, 2);
        if (comparePaths.length === 2 && gBridge && gBridge.compare_paths) {
          gBridge.compare_paths(comparePaths);
        }
        hideCtx();
        break;
      }
      case 'ctxCompareImage': {
        const comparePaths = getTargetPaths().filter(path => {
          const selectedItem = gMedia.find(entry => entry.path === path);
          return selectedItem && !selectedItem.is_folder;
        });
        if (comparePaths.length && gBridge && gBridge.compare_path_auto) {
          gBridge.compare_path_auto(comparePaths[0]);
        }
        hideCtx();
        break;
      }
      case 'ctxCompareLeft':
      case 'ctxCompareRight': {
        const comparePaths = getTargetPaths().filter(path => {
          const selectedItem = gMedia.find(entry => entry.path === path);
          return selectedItem && !selectedItem.is_folder;
        });
        if (comparePaths.length && gBridge && gBridge.set_compare_path) {
          gBridge.set_compare_path(btn.id === 'ctxCompareLeft' ? 'left' : 'right', comparePaths[0]);
        }
        hideCtx();
        break;
      }
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
        applyHiddenStateToTargets(true);
        break;
      case 'ctxUnhide':
        applyHiddenStateToTargets(false);
        break;
      case 'ctxPinFolder':
        if (item && item.path && item.is_folder && gBridge && gBridge.pin_folder) {
          gBridge.pin_folder(item.path, function () { });
        }
        break;
      case 'ctxUnpinFolder':
        if (item && item.path && item.is_folder && gBridge && gBridge.unpin_folder) {
          gBridge.unpin_folder(item.path, function () { });
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
        if (item && item.path && gBridge) {
          deletePathFromUi(item.path, (ok) => { if (ok) refreshFromBridge(gBridge); });
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
  reconcileSelectionWithVisibleItems(gMedia);
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
      ? (shouldShowScanWaitingEmptyState()
        ? 'Scanning current folder. Wait for results to finish loading.'
        : ((getReviewMode() === 'similar' || getReviewMode() === 'similar_only') ? 'No similar images found in the current scope.' : 'No duplicates found in the current scope.'))
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
    if (gReviewLoadingActive) {
      const staging = document.createElement('div');
      const groups = renderDuplicateMediaList(staging, viewItems, { deferFinalize: true });
      staging.classList.forEach((cls) => el.classList.add(cls));
      const reviewLoadingGeneration = gReviewLoadingGeneration;
      prioritizeVisibleMediaLoads(staging);
      waitForInitialReviewCards(staging, reviewLoadingGeneration).then(() => {
        if (!gReviewLoadingActive || reviewLoadingGeneration !== gReviewLoadingGeneration) return;
        el.replaceChildren(...Array.from(staging.childNodes));
        requestAnimationFrame(() => finalizeDuplicateMediaList(el, groups));
      });
    } else {
      renderDuplicateMediaList(el, viewItems);
    }
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
    prioritizeVisibleMediaLoads(el);
    const unobserved = el.querySelectorAll('img[data-src]:not([src]), img[data-poster-path]:not([src]), img[data-video-path]:not([src])');
    unobserved.forEach(img => {
      if (gPosterRequested.has(img)) return;
      const imgSrc = img.getAttribute('data-src');
      const posterPath = img.getAttribute('data-poster-path');
      const path = img.getAttribute('data-video-path');
      const item = gMedia.find(m => m.path === path || m.url === imgSrc); // Find the original item to get width/height
      if (imgSrc) {
        gBackgroundQueue.push({ type: 'image', el: img, imgSrc });
      } else if (posterPath) {
        gBackgroundQueue.push({ type: 'poster', el: img, path: posterPath });
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

  function setupGroupedFilterSelect(id, onChange) {
    const el = document.getElementById(id);
    if (!el) return;
    const trigger = el.querySelector('.select-trigger');
    const options = el.querySelector('.select-options');
    const clearOpt = options.querySelector('[data-clear-filters]');

    function render(groups) {
      gFilterGroups = normalizeFilterValue(serializeFilterValue(groups));
      gFilter = serializeFilterValue(gFilterGroups);
      trigger.textContent = getFilterTriggerText(gFilterGroups);
      const hasAnyFilter = gFilter !== 'all';
      if (clearOpt) clearOpt.classList.toggle('selected', !hasAnyFilter);
      options.querySelectorAll('[data-group]').forEach((opt) => {
        const group = opt.getAttribute('data-group');
        const value = opt.getAttribute('data-value');
        opt.classList.toggle('selected', gFilterGroups[group] === value);
      });
    }

    render(gFilterGroups);

    el.addEventListener('click', (e) => {
      e.stopPropagation();
      document.querySelectorAll('.custom-select').forEach(s => {
        if (s !== el) s.classList.remove('open');
      });
      el.classList.toggle('open');
    });

    options.addEventListener('click', (e) => {
      e.stopPropagation();
      const clearTarget = e.target.closest('[data-clear-filters]');
      if (clearTarget) {
        render({ media: 'all', text: 'all', meta: 'all', ai: 'all' });
        onChange(gFilter);
        return;
      }
      const opt = e.target.closest('[data-group][data-value]');
      if (!opt) return;
      const group = opt.getAttribute('data-group');
      const value = opt.getAttribute('data-value');
      const nextGroups = { ...gFilterGroups };
      nextGroups[group] = nextGroups[group] === value ? 'all' : value;
      render(nextGroups);
      onChange(gFilter);
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

  setupGroupedFilterSelect('filterSelect', (val) => {
    gFilter = val;
    if (gBridge && gBridge.set_current_gallery_scope_state) {
      gBridge.set_current_gallery_scope_state(gFilter || 'all', gSearchQuery || '');
    }
    if (gBridge && gBridge.set_current_gallery_tag_scope_state) {
      gBridge.set_current_gallery_tag_scope_state(gActiveTagScopeQuery || '');
    }
    if (gRenderScanToast) gRenderScanToast();
    if (isTextFilterActive()) {
      gTextProcessingPaused = false;
      gTextProcessingWaiting = false;
      gTextProcessingDismissed = false;
      gTextProcessingForceVisible = true;
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
    if (REVIEW_VIEW_MODES.has(gGroupBy)) beginReviewLoading('Scanning folder...', 10);
    else setGlobalLoading(true, 'Loading gallery...', 10);
    if (Array.isArray(gMedia) && gMedia.length > 0) {
      rerenderCurrentMediaPreservingScroll();
    }
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
        const loop = shouldLoopVideoForDurationSeconds(seconds);
        gBridge.open_native_video(item.path, true, loop, gMuteVideoByDefault, item.width || 0, item.height || 0);
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
  const consumeSelectAllAfterRefresh = function () {
    if (!gSelectAllAfterRefresh) return;
    gSelectAllAfterRefresh = false;
    selectAll();
  };
  bridge.get_selected_folders(function (folders) {
    if (refreshToken !== gRefreshGeneration) return;
    gSelectedFolders = folders || [];
    bridge.get_active_collection(function (activeCollection) {
      if (refreshToken !== gRefreshGeneration) return;
      gActiveCollection = activeCollection && activeCollection.id ? activeCollection : null;
      setSelectedFolder(gSelectedFolders, gActiveCollection);

      if (gSelectedFolders.length === 0 && !gActiveCollection) {
        gTotal = 0;
        gLastRequestedFullScanKey = '';
        gSelectAllAfterRefresh = false;
        updateGalleryCountChip(0);
        if (gReviewLoadingActive) endReviewLoading();
        else setGlobalLoading(false);
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
      const useInfinite = shouldUseInfiniteScrollMode();
      const duplicateMode = isDuplicateModeActive();

      if (duplicateMode && shouldShowScanWaitingEmptyState()) {
        gTotal = 0;
        updateGalleryCountChip(0);
        renderMediaList([], !gPendingScrollAnchor);
        renderPager();
        if (gReviewLoadingActive) updateReviewLoadingProgress(15, gReviewLoadingMessage);
        else setGlobalLoading(true, 'Scanning folder...', 10);
        ensureFullFolderScanRequested(bridge, gSelectedFolders, gSearchQuery || '');
        return;
      }

      if (duplicateMode) {
        if (gReviewLoadingActive) updateReviewLoadingProgress(20, gReviewLoadingMessage);
        fetchMediaCount(gSelectedFolders, gFilter, gSearchQuery || '').then(function (count) {
          if (refreshToken !== gRefreshGeneration) return;
          const normalizedCount = count || 0;
          gTotal = normalizedCount;
          updateGalleryCountChip(gTotal);
          if (gReviewLoadingActive) updateReviewLoadingProgress(35, gReviewLoadingMessage);
          const limit = Math.max(PAGE_SIZE, normalizedCount || PAGE_SIZE);
          fetchMediaList(gSelectedFolders, limit, 0, gSort, gFilter, gSearchQuery || '').then(function (items) {
            if (refreshToken !== gRefreshGeneration) return;
            if (gReviewLoadingActive && shouldShowScanWaitingEmptyState()) {
              updateReviewLoadingProgress(85, gReviewLoadingMessage);
              return;
            }
            if (gReviewLoadingActive) updateReviewLoadingProgress(80, gReviewLoadingMessage);
            renderMediaList(items, !gPendingScrollAnchor);
            consumeSelectAllAfterRefresh();
            renderPager();
            const reviewLoadingGeneration = gReviewLoadingGeneration;
            requestAnimationFrame(() => {
              if (refreshToken !== gRefreshGeneration) return;
              const mediaList = document.getElementById('mediaList');
              prioritizeVisibleMediaLoads(mediaList);
              if (gReviewLoadingActive) updateReviewLoadingProgress(92, gReviewLoadingMessage);
              waitForInitialReviewCards(mediaList, reviewLoadingGeneration).then(() => {
                if (refreshToken !== gRefreshGeneration) return;
                if (gReviewLoadingActive) {
                  updateReviewLoadingProgress(100, gReviewLoadingMessage);
                  endReviewLoading(reviewLoadingGeneration);
                } else {
                  setGlobalLoading(false);
                }
              });
            });
            if (bridge.start_scan_paths) {
              bridge.start_scan_paths((items || []).filter(item => !item.is_folder).map(item => item.path).filter(Boolean));
            }
          });
        });
        return;
      }

      const limit = useInfinite ? Math.max(PAGE_SIZE, gMedia.length || PAGE_SIZE) : PAGE_SIZE;
      const offset = useInfinite ? 0 : gPage * PAGE_SIZE;
      fetchMediaList(gSelectedFolders, limit, offset, gSort, gFilter, gSearchQuery || '').then(function (items) {
        if (refreshToken !== gRefreshGeneration) return;
        renderMediaList(items, !gPendingScrollAnchor);
        consumeSelectAllAfterRefresh();
        renderPager();
        if (useInfinite) requestAnimationFrame(() => maybeLoadMoreInfiniteResults());
        // Hide the "Starting..." or "Loading..." overlay once we have the first batch of results.
        setGlobalLoading(false);
        if (bridge.start_scan_paths) {
          bridge.start_scan_paths((items || []).filter(item => !item.is_folder).map(item => item.path).filter(Boolean));
        }
        fetchMediaCount(gSelectedFolders, gFilter, gSearchQuery || '').then(function (count) {
          if (refreshToken !== gRefreshGeneration) return;
          gTotal = count || 0;
          updateGalleryCountChip(gTotal);
          renderPager();
        });
      });

    // ── 2. Background Enrichment Scan ────────────────────────────────────
    // This fills in hashes and metadata in the DB.
    ensureFullFolderScanRequested(bridge, gSelectedFolders, gSearchQuery || '');
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
  if (gBridge && gBridge.open_settings_dialog) {
    gBridge.open_settings_dialog();
    return;
  }
  const m = document.getElementById('settingsModal');
  if (m) m.hidden = false;
  if (gBridge && gBridge.settings_modal_opened) {
    gBridge.settings_modal_opened();
  }
}

// Called from native menu
window.__mmx_openSettings = openSettings;

function closeSettings() {
  const m = document.getElementById('settingsModal');
  if (m) m.hidden = true;
  if (gBridge && gBridge.settings_modal_closed) {
    gBridge.settings_modal_closed();
  }
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
  const useRecycleBinToggle = document.getElementById('toggleUseRecycleBin');
  const toggleShowHidden = document.getElementById('toggleShowHidden');
  const toggleMuteVideoByDefault = document.getElementById('toggleMuteVideoByDefault');
  const toggleAutoplayGalleryAnimatedGifs = document.getElementById('toggleAutoplayGalleryAnimatedGifs');
  const toggleAutoplayPreviewAnimatedGifs = document.getElementById('toggleAutoplayPreviewAnimatedGifs');
  const videoLoopModeRadios = document.querySelectorAll('input[name="video_loop_mode"]');
  const videoLoopCutoffSeconds = document.getElementById('videoLoopCutoffSeconds');
  const accentInput = document.getElementById('accentColor');
  const syncVideoLoopCutoffEnabled = () => {
    if (!videoLoopCutoffSeconds) return;
    videoLoopCutoffSeconds.disabled = gVideoLoopMode !== 'short';
  };

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

  if (useRecycleBinToggle) {
    useRecycleBinToggle.addEventListener('change', () => {
      if (!gBridge || !gBridge.set_setting_bool) return;
      gBridge.set_setting_bool('gallery.use_recycle_bin', !!useRecycleBinToggle.checked, function () {});
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

  if (toggleMuteVideoByDefault) {
    toggleMuteVideoByDefault.addEventListener('change', () => {
      if (!gBridge || !gBridge.set_setting_bool) return;
      gMuteVideoByDefault = !!toggleMuteVideoByDefault.checked;
      gBridge.set_setting_bool('gallery.mute_video_by_default', gMuteVideoByDefault, function () {});
    });
  }

  if (toggleAutoplayGalleryAnimatedGifs) {
    toggleAutoplayGalleryAnimatedGifs.addEventListener('change', () => {
      if (!gBridge || !gBridge.set_setting_bool) return;
      gAutoplayGalleryAnimatedGifs = !!toggleAutoplayGalleryAnimatedGifs.checked;
      gBridge.set_setting_bool('player.autoplay_gallery_animated_gifs', gAutoplayGalleryAnimatedGifs, function () {
        gPage = 0;
        refreshFromBridge(gBridge);
      });
    });
  }

  if (toggleAutoplayPreviewAnimatedGifs) {
    toggleAutoplayPreviewAnimatedGifs.addEventListener('change', () => {
      if (!gBridge || !gBridge.set_setting_bool) return;
      gAutoplayPreviewAnimatedGifs = !!toggleAutoplayPreviewAnimatedGifs.checked;
      gBridge.set_setting_bool('player.autoplay_preview_animated_gifs', gAutoplayPreviewAnimatedGifs, function () {});
    });
  }

  if (videoLoopModeRadios && videoLoopModeRadios.length) {
    videoLoopModeRadios.forEach((radio) => {
      radio.addEventListener('change', () => {
        if (!radio.checked || !gBridge || !gBridge.set_setting_str) return;
        gVideoLoopMode = radio.value === 'all' || radio.value === 'none' ? radio.value : 'short';
        syncVideoLoopCutoffEnabled();
        gBridge.set_setting_str('player.video_loop_mode', gVideoLoopMode, function () {});
      });
    });
  }

  if (videoLoopCutoffSeconds) {
    const commitLoopCutoff = () => {
      if (!gBridge || !gBridge.set_setting_str) return;
      const parsed = Number(videoLoopCutoffSeconds.value || 90);
      gVideoLoopCutoffSeconds = Number.isFinite(parsed) ? Math.max(1, Math.round(parsed)) : 90;
      videoLoopCutoffSeconds.value = String(gVideoLoopCutoffSeconds);
      gBridge.set_setting_str('player.video_loop_cutoff_seconds', String(gVideoLoopCutoffSeconds), function () {});
    };
    videoLoopCutoffSeconds.addEventListener('change', commitLoopCutoff);
    videoLoopCutoffSeconds.addEventListener('blur', commitLoopCutoff);
  }
  syncVideoLoopCutoffEnabled();

  const autoUpdateToggle = document.getElementById('toggleAutoUpdate');
  if (autoUpdateToggle) {
    autoUpdateToggle.addEventListener('change', () => {
      if (!gBridge || !gBridge.set_setting_bool) return;
      gBridge.set_setting_bool('updates.check_on_launch', !!autoUpdateToggle.checked, function () { });
    });
  }

  const splashToggle = document.getElementById('toggleShowSplashScreen');
  if (splashToggle) {
    splashToggle.addEventListener('change', () => {
      if (!gBridge || !gBridge.set_setting_bool) return;
      gBridge.set_setting_bool('ui.show_splash_screen', !!splashToggle.checked, function () { });
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
      applyAccentCssVars(v);
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
      if (!radio.checked || !gBridge || !gBridge.set_setting_str) return;
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

    const header = document.createElement('div');
    header.className = 'metadata-group-header';
    header.innerHTML = `
      <div class="drag-handle" title="Drag group">☰</div>
      <label class="toggle">
        <input type="checkbox" class="metadata-group-toggle" ${((settings && settings[metadataGroupEnabledKey(gActiveMetadataMode, groupKey)]) !== false) ? 'checked' : ''} />
        <span class="metadata-group-title">${groupCfg.label}</span>
      </label>
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
      const enabled = resolveMetadataFieldEnabled(settings, gActiveMetadataMode, key, defaultEnabled);
      row.innerHTML = `
        <div class="drag-handle" title="Drag field">☰</div>
        <label class="toggle">
          <input type="checkbox" class="metadata-field-toggle" data-field-key="${key}" ${enabled ? 'checked' : ''} />
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

  const exclusionResetSection = document.createElement('section');
  exclusionResetSection.className = 'metadata-group duplicate-settings-section';
  exclusionResetSection.innerHTML = `
    <div class="metadata-group-header">
      <div class="metadata-group-title">Reset Group Exclusions</div>
    </div>
    <div class="metadata-group-body duplicate-exclusion-reset-body">
      <div class="duplicate-exclusion-reset-copy">
        When you click X on files in duplicate or similar groups MediaLens remembers that file should not be included in that group on future rescans. If you think you may have made mistakes excluding actual duplicates you can reset those exclusions below.
      </div>
      <div class="duplicate-exclusion-reset-actions">
        <button type="button" class="tb-btn" id="resetReviewGroupExclusionsBtn">Reset Group Exclusions</button>
      </div>
    </div>
  `;
  mount.appendChild(exclusionResetSection);
}

function saveDuplicateSortableOrder(listId, settingKey) {
  const list = document.getElementById(listId);
  if (!list || !gBridge || !gBridge.set_setting_str) return;
  const order = Array.from(list.querySelectorAll('.sortable-item')).map(el => el.dataset.key).filter(Boolean);
  gCachedSettings[settingKey] = JSON.stringify(order);
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
      if (settingKey) {
        gCachedSettings[settingKey] = policy.value || '';
        gBridge.set_setting_str(settingKey, policy.value || '', () => {});
      }
      return;
    }
    const mergeBeforeDelete = e.target.closest('#duplicateMergeBeforeDelete');
    if (mergeBeforeDelete && gBridge && gBridge.set_setting_bool) {
      gCachedSettings['duplicate.rules.merge_before_delete'] = !!mergeBeforeDelete.checked;
      gBridge.set_setting_bool('duplicate.rules.merge_before_delete', !!mergeBeforeDelete.checked, () => {});
      return;
    }
    const mergeField = e.target.closest('.duplicate-merge-field-toggle');
    if (mergeField && gBridge && gBridge.set_setting_bool) {
      gCachedSettings[mergeField.dataset.settingKey] = !!mergeField.checked;
      gBridge.set_setting_bool(mergeField.dataset.settingKey, !!mergeField.checked, () => {});
    }
  });

  mount.addEventListener('click', (e) => {
    const resetExclusionsBtn = e.target.closest('#resetReviewGroupExclusionsBtn');
    if (!resetExclusionsBtn || !gBridge || !gBridge.reset_review_group_exclusions) return;
    if (typeof window !== 'undefined' && window.confirm && !window.confirm('Reset all saved duplicate and similar group exclusions?')) {
      return;
    }
    resetExclusionsBtn.disabled = true;
    gBridge.reset_review_group_exclusions(function (ok) {
      resetExclusionsBtn.disabled = false;
      if (!ok) return;
      clearDismissedReviewPaths();
      if (isDuplicateModeActive()) {
        refreshFromBridge(gBridge, false);
      }
    });
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
    logo.src = isLight ? HEADER_LOGO_LIGHT : HEADER_LOGO_DARK;
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

  updateAdvancedSearchToggleIcon(theme);
}

function populateSelectOptions(select, options, placeholder = '') {
  if (!select) return;
  const current = select.value;
  const items = placeholder ? [['', placeholder], ...options] : options.slice();
  select.innerHTML = items.map(([value, label]) => `<option value="${value}">${label}</option>`).join('');
  if (items.some(([value]) => value === current)) {
    select.value = current;
  }
}

function stripMatchingQuotes(value) {
  const text = String(value || '').trim();
  if (text.length < 2) return text;
  if ((text.startsWith('"') && text.endsWith('"')) || (text.startsWith('\'') && text.endsWith('\''))) {
    return text.slice(1, -1);
  }
  return text;
}

function quoteSearchValue(value) {
  const text = String(value || '').trim();
  if (!text) return '';
  if (!/[\s"]/u.test(text)) return text;
  return `"${text.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
}

function tokenizeSearchQuery(query) {
  const tokens = [];
  let token = '';
  let quote = '';
  let escaping = false;
  const text = String(query || '');
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (escaping) {
      token += ch;
      escaping = false;
      continue;
    }
    if (ch === '\\') {
      token += ch;
      escaping = true;
      continue;
    }
    if (quote) {
      token += ch;
      if (ch === quote) quote = '';
      continue;
    }
    if (ch === '"' || ch === '\'') {
      token += ch;
      quote = ch;
      continue;
    }
    if (/\s/u.test(ch)) {
      if (token) {
        tokens.push(token);
        token = '';
      }
      continue;
    }
    token += ch;
  }
  if (token) tokens.push(token);
  return normalizeSearchTokens(tokens);
}

function normalizeSearchTokens(tokens) {
  const normalized = [];
  for (let i = 0; i < tokens.length; i += 1) {
    const term = tokens[i];
    const base = term && (term[0] === '+' || term[0] === '-') ? term.slice(1) : term;
    const shouldJoin = i + 1 < tokens.length && (base.endsWith(':') || SEARCH_OPERATORS.some(op => base.endsWith(op)));
    if (shouldJoin) {
      normalized.push(term + tokens[i + 1]);
      i += 1;
      continue;
    }
    normalized.push(term);
  }
  return normalized;
}

function parseSearchFieldTerm(term) {
  const raw = String(term || '');
  if (raw.includes(':')) {
    const splitIndex = raw.indexOf(':');
    const fieldCandidate = raw.slice(0, splitIndex).toLowerCase();
    const fieldKey = ADVANCED_SEARCH_FIELD_ALIASES[fieldCandidate];
    if (fieldKey) {
      const expr = raw.slice(splitIndex + 1);
      const operator = SEARCH_OPERATORS.find(op => expr.startsWith(op)) || 'contains';
      const value = operator === 'contains' ? expr : expr.slice(operator.length);
      return { fieldKey, operator, value };
    }
  }
  const match = raw.match(/^([A-Za-z_][\w-]*)(>=|<=|>|<|=)(.+)$/);
  if (match) {
    const fieldKey = ADVANCED_SEARCH_FIELD_ALIASES[String(match[1] || '').toLowerCase()];
    if (fieldKey) {
      return { fieldKey, operator: match[2], value: match[3] };
    }
  }
  return { fieldKey: '', operator: '', value: '' };
}

function buildStructuredSearchToken(filter, isNumeric) {
  if (!filter || !filter.field || !filter.value) return '';
  const preferredField = ADVANCED_SEARCH_PREFERRED_ALIASES[filter.field] || filter.field;
  const operator = isNumeric ? (filter.operator || '=') : (filter.operator === '=' ? '=' : 'contains');
  const value = String(filter.value || '').trim();
  if (!value) return '';
  const expr = operator === 'contains' ? quoteSearchValue(value) : `${operator}${quoteSearchValue(value)}`;
  const token = `${preferredField}:${expr}`;
  return filter.mode === 'exclude' ? `-${token}` : token;
}

function buildTokenListFromText(value, prefix = '') {
  const tokens = tokenizeSearchQuery(value).filter(Boolean);
  if (!prefix) return tokens;
  return tokens
    .filter(token => token.toUpperCase() !== 'OR' && token !== '|')
    .map(token => token.startsWith(prefix) ? token : `${prefix}${token}`);
}

function getAdvancedFieldDef(fieldValue) {
  return ADVANCED_SEARCH_FIELD_DEFS.find(item => item.key === fieldValue) || ADVANCED_SEARCH_FIELD_DEFS[0];
}

function advancedFieldUsesValueSelect(fieldKey) {
  return fieldKey === 'type' || fieldKey === 'collection';
}

function advancedFieldUsesUnitSelect(fieldKey) {
  return fieldKey === 'size' || fieldKey === 'duration';
}

function getAdvancedDefaultUnit(fieldKey) {
  if (fieldKey === 'size') return 'kb';
  if (fieldKey === 'duration') return 's';
  return '';
}

function getAdvancedValueOptions(fieldKey) {
  if (fieldKey === 'type') {
    return [
      ['image', 'Image'],
      ['animated', 'Animated GIF'],
      ['video', 'Video'],
      ['svg', 'SVG'],
    ];
  }
  if (fieldKey === 'collection') {
    return gAdvancedSearchCollections.map(item => [item.name, item.name]);
  }
  return [];
}

function getAdvancedUnitOptions(fieldKey) {
  if (fieldKey === 'size') {
    return [
      ['', 'No Unit'],
      ['bits', 'Bits'],
      ['b', 'Bytes'],
      ['kb', 'KB'],
      ['mb', 'MB'],
      ['gb', 'GB'],
    ];
  }
  if (fieldKey === 'duration') {
    return [
      ['', 'No Unit'],
      ['ms', 'Milliseconds'],
      ['s', 'Seconds'],
      ['m', 'Minutes'],
      ['h', 'Hours'],
    ];
  }
  return [];
}

function splitAdvancedValueAndUnit(fieldKey, rawValue) {
  const text = String(rawValue || '').trim();
  if (!advancedFieldUsesUnitSelect(fieldKey)) return { value: text, unit: '' };
  const match = text.match(/^(.+?)(bits|b|kb|mb|gb|ms|s|m|h)$/i);
  if (!match) return { value: text, unit: '' };
  return { value: String(match[1] || '').trim(), unit: String(match[2] || '').toLowerCase() };
}

function combineAdvancedValueAndUnit(fieldKey, value, unit) {
  const rawValue = String(value || '').trim();
  const rawUnit = String(unit || '').trim();
  if (!advancedFieldUsesUnitSelect(fieldKey) || !rawValue) return rawValue;
  return rawUnit ? `${rawValue}${rawUnit}` : rawValue;
}

function refreshAdvancedCollections() {
  if (!gBridge || !gBridge.list_collections) return;
  gBridge.list_collections(function (items) {
    const allItems = Array.isArray(items) ? items : [];
    gAdvancedSearchCollections = allItems
      .filter(item => !!item && !!String(item.name || '').trim())
      .filter(item => gShowHidden || !item.is_hidden)
      .map(item => ({ name: String(item.name || '').trim(), is_hidden: !!item.is_hidden }));
    renderAdvancedSearchRules(getAdvancedSearchRules());
  });
}

function createEmptyAdvancedRule() {
  return { mode: 'include', match: 'contains', field: '', operator: '=', value: '', unit: '', join: '' };
}

function normalizeAdvancedRule(rule) {
  const next = { ...createEmptyAdvancedRule(), ...(rule || {}) };
  const def = getAdvancedFieldDef(next.field);
  const allowedOperators = def.kind === 'text' ? ADVANCED_SEARCH_TEXT_OPERATOR_OPTIONS : ADVANCED_SEARCH_VALUE_OPERATOR_OPTIONS;
  if (!allowedOperators.some(([value]) => value === next.operator)) {
    next.operator = def.kind === 'text' ? '=' : '=';
  }
  if (def.kind !== 'text') {
    next.match = 'exact';
  } else if (!ADVANCED_SEARCH_MATCH_OPTIONS.some(([value]) => value === next.match)) {
    next.match = 'contains';
  }
  if (!ADVANCED_SEARCH_JOIN_OPTIONS.some(([value]) => value === next.join)) {
    next.join = '';
  }
  if (!ADVANCED_SEARCH_MODE_OPTIONS.some(([value]) => value === next.mode)) {
    next.mode = 'include';
  }
  const split = splitAdvancedValueAndUnit(next.field, next.value);
  next.value = split.value;
  next.unit = next.unit || split.unit || '';
  return next;
}

function getAdvancedSearchRules() {
  const rows = Array.from(document.querySelectorAll('.advanced-search-rule-card'));
  if (!rows.length) return [createEmptyAdvancedRule()];
  return rows.map((row) => normalizeAdvancedRule({
    mode: getSelectLikeValue(row.querySelector('[data-role="mode"]')) || 'include',
    match: getSelectLikeValue(row.querySelector('[data-role="match"]')) || 'contains',
    field: getSelectLikeValue(row.querySelector('[data-role="field"]')) || '',
    operator: getSelectLikeValue(row.querySelector('[data-role="operator"]')) || '=',
    value: advancedFieldUsesValueSelect(getSelectLikeValue(row.querySelector('[data-role="field"]')) || '')
      ? (row.querySelector('[data-role="value-select"]')?.value || '')
      : (row.querySelector('[data-role="value"]')?.value || ''),
    unit: getSelectLikeValue(row.querySelector('[data-role="unit"]')) || '',
    join: getSelectLikeValue(row.querySelector('[data-role="join"]')) || '',
  }));
}

function ensureRuleVisibility(rules) {
  const next = [];
  const source = Array.isArray(rules) && rules.length ? rules : [createEmptyAdvancedRule()];
  for (let i = 0; i < source.length && next.length < ADVANCED_SEARCH_MAX_RULES; i += 1) {
    const normalized = normalizeAdvancedRule(source[i]);
    next.push(normalized);
    if (!normalized.join) break;
    if (i === source.length - 1 && next.length < ADVANCED_SEARCH_MAX_RULES) {
      next.push(createEmptyAdvancedRule());
      break;
    }
  }
  if (!next.length) next.push(createEmptyAdvancedRule());
  return next;
}

function buildAdvancedRuleToken(rule) {
  const next = normalizeAdvancedRule(rule);
  const def = getAdvancedFieldDef(next.field);
  const value = combineAdvancedValueAndUnit(next.field, next.value, next.unit);
  const trimmedValue = String(value || '').trim();
  if (!trimmedValue) return '';
  let prefix = next.mode === 'exclude' ? '-' : '';
  if (def.kind === 'text') {
    const exact = next.match === 'exact';
    if (next.operator === '!=') prefix = '-';
    if (!next.field) {
      return `${prefix}${exact ? quoteSearchValue(trimmedValue) : trimmedValue}`;
    }
    const fieldKey = ADVANCED_SEARCH_FIELD_ALIASES[String(next.field || '').toLowerCase()] || next.field;
    const preferredField = ADVANCED_SEARCH_PREFERRED_ALIASES[fieldKey] || next.field;
    if (exact) {
      return `${prefix}${preferredField}:=${quoteSearchValue(trimmedValue)}`;
    }
    return `${prefix}${preferredField}:${quoteSearchValue(trimmedValue)}`;
  }
  const fieldKey = ADVANCED_SEARCH_FIELD_ALIASES[String(next.field || '').toLowerCase()] || next.field;
  const preferredField = ADVANCED_SEARCH_PREFERRED_ALIASES[fieldKey] || next.field;
  const normalizedValue = def.kind === 'date' ? normalizeDateQueryValue(trimmedValue) : trimmedValue;
  return `${prefix}${preferredField}:${next.operator}${quoteSearchValue(normalizedValue)}`;
}

function parseSearchQueryToAdvancedState(query) {
  const tokens = tokenizeSearchQuery(query);
  const rules = [];
  let carryover = [];
  for (let i = 0; i < tokens.length; i += 1) {
    const token = tokens[i];
    if (!token) continue;
    const upperToken = token.toUpperCase();
    if (upperToken === 'OR' || token === '|') {
      if (rules.length) {
        rules[rules.length - 1].join = 'OR';
        continue;
      }
      carryover.push(token);
      continue;
    }
    if (upperToken === 'AND') {
      if (rules.length) {
        rules[rules.length - 1].join = 'AND';
        continue;
      }
      carryover.push(token);
      continue;
    }
    const prefix = token[0] === '+' || token[0] === '-' ? token[0] : '';
    const body = prefix ? token.slice(1) : token;
    const parsed = parseSearchFieldTerm(body);
    const nextToken = tokens[i + 1];
    const nextUpperToken = String(nextToken || '').toUpperCase();
    const join = nextUpperToken === 'OR' || nextToken === '|'
      ? 'OR'
      : (nextUpperToken === 'AND' || i < tokens.length - 1 ? 'AND' : '');
    if (parsed.fieldKey) {
      const preferredField = ADVANCED_SEARCH_PREFERRED_ALIASES[parsed.fieldKey] || '';
      const def = getAdvancedFieldDef(preferredField);
      const value = stripMatchingQuotes(parsed.value);
      if (!preferredField || !value) {
        carryover.push(token);
        continue;
      }
      rules.push(normalizeAdvancedRule({
        mode: prefix === '-' ? 'exclude' : 'include',
        match: def.kind === 'text' ? (parsed.operator === '=' ? 'exact' : 'contains') : 'exact',
        field: preferredField,
        operator: def.kind === 'text' ? (prefix === '-' && parsed.operator === '=' ? '!=' : '=') : (parsed.operator || '='),
        value: def.kind === 'date' ? normalizeDateInputValue(value) || value : splitAdvancedValueAndUnit(preferredField, value).value,
        unit: splitAdvancedValueAndUnit(preferredField, value).unit,
        join,
      }));
      continue;
    }
    rules.push(normalizeAdvancedRule({
      mode: prefix === '-' ? 'exclude' : 'include',
      match: /^["'].*["']$/u.test(body) ? 'exact' : 'contains',
      field: '',
      operator: prefix === '-' ? '!=' : '=',
      value: stripMatchingQuotes(body),
      join,
    }));
  }
  gAdvancedSearchCarryoverTokens = carryover;
  return ensureRuleVisibility(rules);
}

function renderAdvancedSearchRules(rules) {
  const mount = document.getElementById('advancedSearchRules');
  if (!mount) return;
  const visibleRules = ensureRuleVisibility(rules);
  mount.innerHTML = '';
  visibleRules.forEach((rule, index) => {
    const normalized = normalizeAdvancedRule(rule);
    const def = getAdvancedFieldDef(normalized.field);
    const row = document.createElement('div');
    row.className = 'advanced-search-rule-card';
    row.dataset.ruleIndex = String(index);
    row.innerHTML = `
      <div class="advanced-search-rule-grid">
        <div class="advanced-search-rule-cell" data-cell="mode">
          <span class="advanced-search-label">Include / Exclude</span>
          <div class="custom-select advanced-search-inline-select" data-role="mode" tabindex="0">
            <div class="select-trigger"></div>
            <div class="select-options"></div>
          </div>
        </div>
        <div class="advanced-search-rule-cell" data-cell="match">
          <span class="advanced-search-label">Match</span>
          <div class="custom-select advanced-search-inline-select" data-role="match" tabindex="0">
            <div class="select-trigger"></div>
            <div class="select-options"></div>
          </div>
        </div>
        <div class="advanced-search-rule-cell" data-cell="field">
          <span class="advanced-search-label">Field Name</span>
          <div class="custom-select advanced-search-inline-select" data-role="field" tabindex="0">
            <div class="select-trigger"></div>
            <div class="select-options"></div>
          </div>
        </div>
        <div class="advanced-search-rule-cell" data-cell="operator">
          <span class="advanced-search-label">Operator</span>
          <div class="custom-select advanced-search-inline-select advanced-search-operator-select" data-role="operator" tabindex="0">
            <div class="select-trigger"></div>
            <div class="select-options"></div>
          </div>
        </div>
        <div class="advanced-search-rule-cell" data-cell="value">
          <div class="advanced-search-value-group">
            <div class="advanced-search-value-wrap">
              <span class="advanced-search-label">Search Value</span>
              <div class="advanced-search-value-controls">
                <input class="advanced-search-input" data-role="value" type="${def.kind === 'date' ? 'date' : 'text'}" />
                <select class="advanced-search-select" data-role="value-select" hidden></select>
                <div class="custom-select advanced-search-inline-select advanced-search-unit-select" data-role="unit" tabindex="0" hidden>
                  <div class="select-trigger"></div>
                  <div class="select-options"></div>
                </div>
              </div>
            </div>
            <div class="advanced-search-join-wrap">
              <span class="advanced-search-label">Then</span>
              <div class="custom-select advanced-search-inline-select advanced-search-join-select" data-role="join" tabindex="0">
                <div class="select-trigger"></div>
                <div class="select-options"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
    mount.appendChild(row);
    setCustomSelectOptions(row.querySelector('[data-role="mode"]'), ADVANCED_SEARCH_MODE_OPTIONS, normalized.mode);
    setCustomSelectOptions(row.querySelector('[data-role="match"]'), ADVANCED_SEARCH_MATCH_OPTIONS, normalized.match);
    setCustomSelectOptions(row.querySelector('[data-role="field"]'), ADVANCED_SEARCH_FIELD_DEFS.map(item => [item.key, item.label]), normalized.field);
    setCustomSelectOptions(row.querySelector('[data-role="join"]'), ADVANCED_SEARCH_JOIN_OPTIONS, normalized.join);
    updateAdvancedRuleControls(row);
    setCustomSelectOptions(
      row.querySelector('[data-role="operator"]'),
      def.kind === 'text' ? ADVANCED_SEARCH_TEXT_OPERATOR_OPTIONS : ADVANCED_SEARCH_VALUE_OPERATOR_OPTIONS,
      normalized.operator
    );
    const valueInput = row.querySelector('[data-role="value"]');
    const valueSelect = row.querySelector('[data-role="value-select"]');
    if (advancedFieldUsesValueSelect(normalized.field)) {
      if (valueSelect) valueSelect.value = normalized.value || '';
    } else if (valueInput) {
      valueInput.value = def.kind === 'date' ? (normalizeDateInputValue(normalized.value) || '') : normalized.value;
    }
    const unitSelect = row.querySelector('[data-role="unit"]');
    if (unitSelect) {
      setCustomSelectOptions(
        unitSelect,
        getAdvancedUnitOptions(normalized.field),
        normalized.unit || getAdvancedDefaultUnit(normalized.field)
      );
    }
  });
}

function updateAdvancedRuleControls(row) {
  if (!row) return;
  const fieldValue = getSelectLikeValue(row.querySelector('[data-role="field"]')) || '';
  const matchEl = row.querySelector('[data-role="match"]');
  const operatorEl = row.querySelector('[data-role="operator"]');
  const valueEl = row.querySelector('[data-role="value"]');
  const valueSelectEl = row.querySelector('[data-role="value-select"]');
  const unitEl = row.querySelector('[data-role="unit"]');
  const def = getAdvancedFieldDef(fieldValue);
  const isText = def.kind === 'text';
  const previousFieldKind = row.dataset.fieldKind || '';
  const resetValue = previousFieldKind === 'date' && def.kind !== 'date';
  if (matchEl) {
    setCustomSelectOptions(matchEl, ADVANCED_SEARCH_MATCH_OPTIONS, isText ? (getSelectLikeValue(matchEl) || 'contains') : 'exact');
    matchEl.classList.toggle('is-disabled', !isText);
  }
  if (operatorEl) {
    setCustomSelectOptions(
      operatorEl,
      isText ? ADVANCED_SEARCH_TEXT_OPERATOR_OPTIONS : ADVANCED_SEARCH_VALUE_OPERATOR_OPTIONS,
      getSelectLikeValue(operatorEl) || '='
    );
  }
  if (valueEl) {
    const prev = valueEl.value;
    const replacement = document.createElement('input');
    replacement.className = 'advanced-search-input';
    replacement.setAttribute('data-role', 'value');
    replacement.type = def.kind === 'date' ? 'date' : 'text';
    replacement.value = resetValue ? '' : (def.kind === 'date' ? (normalizeDateInputValue(prev) || '') : prev);
    valueEl.replaceWith(replacement);
  }
  const currentInput = row.querySelector('[data-role="value"]');
  if (valueSelectEl) {
    const shouldUseSelect = advancedFieldUsesValueSelect(fieldValue);
    valueSelectEl.hidden = !shouldUseSelect;
    if (shouldUseSelect) {
      populateSelectOptions(valueSelectEl, getAdvancedValueOptions(fieldValue), fieldValue === 'collection' ? 'Choose a collection' : 'Choose a value');
      if (resetValue) valueSelectEl.value = '';
    }
  }
  if (currentInput) currentInput.hidden = advancedFieldUsesValueSelect(fieldValue);
  if (unitEl) {
    const shouldUseUnit = advancedFieldUsesUnitSelect(fieldValue);
    unitEl.hidden = !shouldUseUnit;
    if (shouldUseUnit) {
      setCustomSelectOptions(
        unitEl,
        getAdvancedUnitOptions(fieldValue),
        getSelectLikeValue(unitEl) || getAdvancedDefaultUnit(fieldValue)
      );
    }
  }
  row.dataset.fieldKind = def.kind;
  row.dataset.fieldKey = fieldValue;
}
function buildSearchQueryFromAdvancedControls() {
  const parts = [];
  const rules = getAdvancedSearchRules();
  rules.forEach((rule, index) => {
    const token = buildAdvancedRuleToken(rule);
    if (!token) return;
    parts.push(token);
    if (rule.join && index < rules.length - 1) {
      parts.push(rule.join);
    }
  });
  parts.push(...gAdvancedSearchCarryoverTokens);
  return parts.join(' ').trim();
}

function syncAdvancedSearchControlsFromQuery(query) {
  renderAdvancedSearchRules(parseSearchQueryToAdvancedState(query));
}

function setAdvancedSearchQuery(query, skipSync = false) {
  const nextQuery = String(query || '').trim();
  gSearchQuery = nextQuery;
  const inp = document.getElementById('searchInput');
  if (inp && inp.value !== nextQuery) inp.value = nextQuery;
  if (gBridge && gBridge.set_current_gallery_scope_state) {
    gBridge.set_current_gallery_scope_state(gFilter || 'all', gSearchQuery || '');
  }
  if (gBridge && gBridge.set_current_gallery_tag_scope_state) {
    gBridge.set_current_gallery_tag_scope_state(gActiveTagScopeQuery || '');
  }
  if (!skipSync) syncAdvancedSearchControlsFromQuery(nextQuery);
  gPage = 0;
  refreshFromBridge(gBridge);
}

function normalizeAdvancedSearchSavedQueries(items) {
  if (!Array.isArray(items)) return [];
  return items
    .map((item) => ({
      name: String(item && item.name || '').trim(),
      query: String(item && item.query || '').trim(),
    }))
      .filter(item => item.name && item.query)
      .slice(0, ADVANCED_SEARCH_SAVED_LIMIT);
}

function getCustomSelectValue(selectId) {
  const el = document.getElementById(selectId);
  if (!el) return '';
  const selected = el.querySelector('.select-options [data-value].selected');
  return String(selected && selected.getAttribute('data-value') || '');
}

function getCustomSelectValueFromElement(el) {
  if (!el) return '';
  const selected = el.querySelector('.select-options [data-value].selected');
  return String(selected && selected.getAttribute('data-value') || '');
}

function setCustomSelectOptions(el, options, currentValue = '') {
  if (!el) return;
  const trigger = el.querySelector('.select-trigger');
  const optionsEl = el.querySelector('.select-options');
  if (!trigger || !optionsEl) return;
  const list = Array.isArray(options) ? options : [];
  const selectedValue = list.some(([value]) => value === currentValue) ? currentValue : (list[0] ? list[0][0] : '');
  const selectedOption = list.find(([value]) => value === selectedValue) || list[0] || ['', ''];
  trigger.textContent = selectedOption[1] || '';
  optionsEl.innerHTML = list.map(([value, label]) => {
    const selected = value === selectedValue ? ' class="selected"' : '';
    return `<div data-value="${escapeHtml(value)}"${selected}>${escapeHtml(label)}</div>`;
  }).join('');
}

function getSelectLikeValue(el) {
  if (!el) return '';
  if (el.tagName === 'SELECT') return el.value || '';
  if (el.classList.contains('custom-select')) return getCustomSelectValueFromElement(el);
  return '';
}

function setupAdvancedSavedSearchSelect(onChange) {
  const el = document.getElementById('advSavedSearchSelect');
  if (!el) return;
  const trigger = el.querySelector('.select-trigger');
  const options = el.querySelector('.select-options');
  if (!trigger || !options || el.dataset.wired === 'true') return;
  el.dataset.wired = 'true';

  el.addEventListener('click', (e) => {
    e.stopPropagation();
    document.querySelectorAll('.custom-select').forEach((selectEl) => {
      if (selectEl !== el) selectEl.classList.remove('open');
    });
    el.classList.toggle('open');
  });

  options.addEventListener('click', (e) => {
    e.stopPropagation();
    const opt = e.target.closest('[data-value]');
    if (!opt) return;
    const val = String(opt.getAttribute('data-value') || '');
    const text = opt.textContent || 'Load a saved search';
    trigger.textContent = text;
    el.querySelectorAll('.selected').forEach(node => node.classList.remove('selected'));
    opt.classList.add('selected');
    el.classList.remove('open');
    onChange(val);
  });
}

function parseAdvancedSearchSavedQueries(rawValue) {
  try {
    const fallback = rawValue === undefined || rawValue === null
      ? JSON.stringify(ADVANCED_SEARCH_DEFAULT_SAVED_QUERIES)
      : String(rawValue || '[]');
    return normalizeAdvancedSearchSavedQueries(JSON.parse(fallback));
  } catch (_) {
    return normalizeAdvancedSearchSavedQueries(ADVANCED_SEARCH_DEFAULT_SAVED_QUERIES);
  }
}

function persistAdvancedSearchSavedQueries() {
  if (!gBridge || !gBridge.set_setting_str) return;
  gBridge.set_setting_str('ui.advanced_search_saved_queries', JSON.stringify(gAdvancedSearchSavedQueries), function () { });
}

function renderAdvancedSearchSavedQueries() {
  const select = document.getElementById('advSavedSearchSelect');
  const deleteBtn = document.getElementById('advDeleteSavedSearch');
  if (!select || !deleteBtn) return;
  const trigger = select.querySelector('.select-trigger');
  const options = select.querySelector('.select-options');
  const current = getCustomSelectValue('advSavedSearchSelect');
  if (!trigger || !options) return;
  const selectedValue = gAdvancedSearchSavedQueries.some(item => item.name === current) ? current : '';
  const rows = [
    `<div data-value=""${selectedValue ? '' : ' class="selected"'}>Load a saved search</div>`,
    ...gAdvancedSearchSavedQueries.map((item) => {
      const selected = item.name === selectedValue ? ' class="selected"' : '';
      return `<div data-value="${escapeHtml(item.name)}"${selected}>${escapeHtml(item.name)}</div>`;
    }),
  ];
  options.innerHTML = rows.join('');
  if (selectedValue) {
    trigger.textContent = selectedValue;
  } else {
    trigger.textContent = 'Load a saved search';
  }
  const hasSaved = gAdvancedSearchSavedQueries.length > 0;
  deleteBtn.disabled = !hasSaved || !selectedValue;
  deleteBtn.innerHTML = '<span aria-hidden="true">🗑</span>';
}

function loadSelectedAdvancedSearch() {
  const name = String(getCustomSelectValue('advSavedSearchSelect') || '').trim();
  if (!name) return;
  const item = gAdvancedSearchSavedQueries.find(saved => saved.name === name);
  if (!item) return;
  setAdvancedSearchQuery(item.query);
}

function deleteSelectedAdvancedSearch() {
  const name = String(getCustomSelectValue('advSavedSearchSelect') || '').trim();
  if (!name) return;
  gAdvancedSearchSavedQueries = gAdvancedSearchSavedQueries.filter(item => item.name !== name);
  persistAdvancedSearchSavedQueries();
  renderAdvancedSearchSavedQueries();
}

function saveCurrentAdvancedSearch() {
  const nameInput = document.getElementById('advSavedSearchName');
  const name = String(nameInput && nameInput.value || '').trim();
  const query = String(document.getElementById('searchInput') && document.getElementById('searchInput').value || '').trim();
  if (!name || !query) return;
  gAdvancedSearchSavedQueries = normalizeAdvancedSearchSavedQueries([
    { name, query },
    ...gAdvancedSearchSavedQueries.filter(item => item.name.toLowerCase() !== name.toLowerCase()),
  ]);
  if (nameInput) nameInput.value = '';
  persistAdvancedSearchSavedQueries();
  renderAdvancedSearchSavedQueries();
  setCustomSelectValue('advSavedSearchSelect', name);
  renderAdvancedSearchSavedQueries();
}

function normalizeDateInputValue(value) {
  const text = String(value || '').trim();
  const isoMatch = text.match(/^(\d{4}-\d{2}-\d{2})/);
  if (isoMatch) return isoMatch[1];
  const slashMatch = text.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (slashMatch) {
    const month = slashMatch[1].padStart(2, '0');
    const day = slashMatch[2].padStart(2, '0');
    return `${slashMatch[3]}-${month}-${day}`;
  }
  return '';
}

function normalizeDateQueryValue(value) {
  const text = String(value || '').trim();
  return normalizeDateInputValue(text) || text;
}

function updateAdvancedSearchToggleIcon(theme) {
  const icon = document.getElementById('iconAdvancedSearch');
  const btn = document.getElementById('toggleAdvancedSearch');
  if (!icon || !btn) return;
  const isLight = theme === 'light';
  const iconName = gAdvancedSearchExpanded
    ? (isLight ? 'icons/search-collapse.png' : 'icons/search-collapse-white.png')
    : (isLight ? 'icons/search-expand.png' : 'icons/search-expand-white.png');
  icon.src = iconName;
  btn.title = gAdvancedSearchExpanded ? 'Collapse Advanced Search' : 'Expand Advanced Search';
  btn.setAttribute('aria-label', btn.title);
  btn.setAttribute('aria-expanded', gAdvancedSearchExpanded ? 'true' : 'false');
}

function setAdvancedSearchExpanded(expanded, persist = true) {
  gAdvancedSearchExpanded = !!expanded;
  const panel = document.getElementById('advancedSearchPanel');
  if (panel) panel.hidden = !gAdvancedSearchExpanded;
  const theme = document.documentElement.classList.contains('light-mode') ? 'light' : 'dark';
  updateAdvancedSearchToggleIcon(theme);
  if (persist && gBridge && gBridge.set_setting_bool) {
    gBridge.set_setting_bool('ui.advanced_search_expanded', gAdvancedSearchExpanded, function () { });
  }
}

function wireAdvancedSearch() {
  const toggle = document.getElementById('toggleAdvancedSearch');
  if (toggle) {
    toggle.addEventListener('click', () => {
      setAdvancedSearchExpanded(!gAdvancedSearchExpanded);
    });
  }
  renderAdvancedSearchRules([createEmptyAdvancedRule()]);
  refreshAdvancedCollections();
  const rulesMount = document.getElementById('advancedSearchRules');
  if (rulesMount) {
    const onRuleChange = () => {
      const rules = ensureRuleVisibility(getAdvancedSearchRules());
      const beforeCount = document.querySelectorAll('.advanced-search-rule-card').length;
      renderAdvancedSearchRules(rules);
      const afterCount = document.querySelectorAll('.advanced-search-rule-card').length;
      if (afterCount > beforeCount) {
        const newValue = document.querySelector(`.advanced-search-rule-card[data-rule-index="${afterCount - 1}"] [data-role="value"]`);
        if (newValue) newValue.focus();
      }
      setAdvancedSearchQuery(buildSearchQueryFromAdvancedControls(), true);
    };
    rulesMount.addEventListener('change', (e) => {
      const row = e.target.closest('.advanced-search-rule-card');
      if (!row) return;
      if (e.target.matches('[data-role="field"]')) {
        updateAdvancedRuleControls(row);
      }
      onRuleChange();
    });
    rulesMount.addEventListener('click', (e) => {
      const option = e.target.closest('.advanced-search-inline-select .select-options [data-value]');
      if (option) {
        e.stopPropagation();
        const selectEl = option.closest('.advanced-search-inline-select');
        const trigger = selectEl && selectEl.querySelector('.select-trigger');
        if (!selectEl || !trigger) return;
        trigger.textContent = option.textContent || '';
        selectEl.querySelectorAll('.selected').forEach(node => node.classList.remove('selected'));
        option.classList.add('selected');
        selectEl.classList.remove('open');
        onRuleChange();
        return;
      }
      const selectEl = e.target.closest('.advanced-search-inline-select');
      if (selectEl) {
        e.stopPropagation();
        if (selectEl.classList.contains('is-disabled')) return;
        document.querySelectorAll('.advanced-search-inline-select').forEach(node => {
          if (node !== selectEl) node.classList.remove('open');
        });
        selectEl.classList.toggle('open');
      }
    });
    rulesMount.addEventListener('input', (e) => {
      if (!e.target.closest('.advanced-search-rule-card')) return;
      setAdvancedSearchQuery(buildSearchQueryFromAdvancedControls(), true);
    });
  }

  const saveBtn = document.getElementById('advSaveCurrentSearch');
  if (saveBtn) saveBtn.addEventListener('click', saveCurrentAdvancedSearch);
  const clearBtn = document.getElementById('advClearSearch');
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      gAdvancedSearchCarryoverTokens = [];
      renderAdvancedSearchRules([createEmptyAdvancedRule()]);
      setAdvancedSearchQuery('');
      renderAdvancedSearchSavedQueries();
    });
  }
  const saveNameInput = document.getElementById('advSavedSearchName');
  if (saveNameInput) {
    saveNameInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        saveCurrentAdvancedSearch();
      }
    });
  }
  setupAdvancedSavedSearchSelect(() => {
    renderAdvancedSearchSavedQueries();
    loadSelectedAdvancedSearch();
  });
  const deleteSavedSearchBtn = document.getElementById('advDeleteSavedSearch');
  if (deleteSavedSearchBtn) deleteSavedSearchBtn.addEventListener('click', deleteSelectedAdvancedSearch);

  renderAdvancedSearchSavedQueries();
  setAdvancedSearchExpanded(false, false);
}

function updateSidebarButtonIcons(side, visible) {
  const iconIdMap = {
    left: 'iconLeftPanel',
    top: 'iconTopPanel',
    bottom: 'iconBottomPanel',
    right: 'iconRightPanel',
  };
  const icon = document.getElementById(iconIdMap[side]);
  if (!icon) return;
  const isLight = document.documentElement.classList.contains('light-mode');
  const suffix = isLight ? '-black' : '';
  const state = visible ? 'opened' : 'closed';
  const prefix = side === 'bottom' || side === 'top' ? side : `${side}-sidebar`;
  icon.src = `${prefix}-${state}${suffix}.png`;
}

function applyTopPanelVisibility(visible) {
  document.body.classList.toggle('top-panel-hidden', !visible);
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
    setAdvancedSearchQuery(inp.value || '');
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

window.__mmx_setSearchQuery = function (query) {
  setAdvancedSearchQuery(String(query || ''));
};

window.__mmx_applyTagScope = function (query) {
  gActiveTagScopeQuery = String(query || '').trim();
  if (gBridge && gBridge.set_current_gallery_tag_scope_state) {
    gBridge.set_current_gallery_tag_scope_state(gActiveTagScopeQuery || '');
  }
  gPage = 0;
  refreshFromBridge(gBridge, true);
};

window.__mmx_applyTagScopeAndSelectAll = function (query) {
  gActiveTagScopeQuery = String(query || '').trim();
  if (gBridge && gBridge.set_current_gallery_tag_scope_state) {
    gBridge.set_current_gallery_tag_scope_state(gActiveTagScopeQuery || '');
  }
  gSelectAllAfterRefresh = true;
  gPage = 0;
  refreshFromBridge(gBridge, true);
};

window.__mmx_clearTagScope = function () {
  if (!gActiveTagScopeQuery) return;
  gActiveTagScopeQuery = '';
  if (gBridge && gBridge.set_current_gallery_tag_scope_state) {
    gBridge.set_current_gallery_tag_scope_state('');
  }
  gPage = 0;
  refreshFromBridge(gBridge, true);
};

window.addEventListener('resize', () => {
  scheduleGalleryRelayout('window');
});

async function main() {
  wirePager();
  wireSettings();
  wireSearch();
  wireAdvancedSearch();
  wireSidebarToggles();
  initGalleryResizeObserver();


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
    if (bridge.compareStateChanged) {
      bridge.compareStateChanged.connect(function (state) {
        gCompareState = state || { visible: false, left: {}, right: {}, best_path: '', keep_paths: [], delete_paths: [] };
        const selectionRevision = Number(gCompareState && gCompareState.selection_revision);
        if (Number.isFinite(selectionRevision) && selectionRevision !== gLastCompareSelectionRevision) {
          gLastCompareSelectionRevision = selectionRevision;
        }
        maybeSeedCompareStateFromReview();
      });
    }
    if (bridge.compareKeepPathChanged) {
      bridge.compareKeepPathChanged.connect(function (path, checked) {
        syncDuplicateKeepFromComparePath(path, !!checked);
      });
    }
    if (bridge.compareDeletePathChanged) {
      bridge.compareDeletePathChanged.connect(function (path, checked) {
        syncDuplicateDeleteFromComparePath(path, !!checked);
      });
    }
    if (bridge.compareBestPathChanged) {
      bridge.compareBestPathChanged.connect(function (path, checked) {
        syncDuplicateBestFromComparePath(path, !!checked);
      });
    }
    if (bridge.get_compare_state) {
      bridge.get_compare_state(function (state) {
        gCompareState = state || { visible: false, left: {}, right: {}, best_path: '', keep_paths: [], delete_paths: [] };
        const selectionRevision = Number(gCompareState && gCompareState.selection_revision);
        if (Number.isFinite(selectionRevision)) {
          gLastCompareSelectionRevision = selectionRevision;
        }
        maybeSeedCompareStateFromReview();
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
        gAwaitingScanResults = true;
        // Silent background scan now, non-blocking
      });
    }

    if (bridge.scanFinished) {
      bridge.scanFinished.connect(function (folder, count) {
        const normalizedFinishedFolder = normalizeFolderPath(folder || '');
        const selectedFolders = currentSelectedFolderSet();
        const matchesCurrentSelection = !normalizedFinishedFolder || selectedFolders.size === 0 || selectedFolders.has(normalizedFinishedFolder);
        if (!matchesCurrentSelection) {
          return;
        }
        if (isDuplicateModeActive() && gReviewLoadingActive && !gAwaitingScanResults) {
          gScanActive = false;
          return;
        }
        if (isDuplicateModeActive() && !gReviewLoadingActive && !gAwaitingScanResults && Array.isArray(gMedia) && gMedia.length > 0) {
          gScanActive = false;
          gTotal = count || gTotal || 0;
          updateGalleryCountChip(gTotal);
          return;
        }
        if (gReviewLoadingActive && isDuplicateModeActive()) {
          updateReviewLoadingProgress(95, gReviewLoadingMessage);
        }
        gScanActive = false;
        gAwaitingScanResults = false;
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
      gCachedSettings = s || {};
      const t = document.getElementById('toggleRandomize');
      if (t) t.checked = !!(s && s['gallery.randomize']);

      const r = document.getElementById('toggleRestoreLast');
      if (r) r.checked = !!(s && s['gallery.restore_last']);

      const rec = document.getElementById('toggleUseRecycleBin');
      if (rec) rec.checked = (s && s['gallery.use_recycle_bin'] !== undefined) ? !!s['gallery.use_recycle_bin'] : true;
      // keep start folder UI in sync
      syncStartFolderEnabled && syncStartFolderEnabled();

      const hd = document.getElementById('toggleShowHidden');
      if (hd) hd.checked = !!(s && s['gallery.show_hidden']);
      gShowHidden = !!(s && s['gallery.show_hidden']);

      gMuteVideoByDefault = (s && s['gallery.mute_video_by_default'] !== undefined)
        ? !!s['gallery.mute_video_by_default']
        : true;
      const mv = document.getElementById('toggleMuteVideoByDefault');
      if (mv) mv.checked = gMuteVideoByDefault;

      gAutoplayGalleryAnimatedGifs = (s && s['player.autoplay_gallery_animated_gifs'] !== undefined)
        ? !!s['player.autoplay_gallery_animated_gifs']
        : ((s && s['player.autoplay_animated_gifs'] !== undefined) ? !!s['player.autoplay_animated_gifs'] : true);
      const ag = document.getElementById('toggleAutoplayGalleryAnimatedGifs');
      if (ag) ag.checked = gAutoplayGalleryAnimatedGifs;

      gAutoplayPreviewAnimatedGifs = (s && s['player.autoplay_preview_animated_gifs'] !== undefined)
        ? !!s['player.autoplay_preview_animated_gifs']
        : true;
      const ap = document.getElementById('toggleAutoplayPreviewAnimatedGifs');
      if (ap) ap.checked = gAutoplayPreviewAnimatedGifs;

      gVideoLoopMode = (s && (s['player.video_loop_mode'] === 'all' || s['player.video_loop_mode'] === 'none' || s['player.video_loop_mode'] === 'short'))
        ? s['player.video_loop_mode']
        : 'short';
      const loopModeRadio = document.getElementById(
        gVideoLoopMode === 'all' ? 'videoLoopAll' : (gVideoLoopMode === 'none' ? 'videoLoopNone' : 'videoLoopShort')
      );
      if (loopModeRadio) loopModeRadio.checked = true;

      const rawLoopCutoff = Number(s && s['player.video_loop_cutoff_seconds']);
      gVideoLoopCutoffSeconds = Number.isFinite(rawLoopCutoff) ? Math.max(1, Math.round(rawLoopCutoff)) : 90;
      const cutoffInput = document.getElementById('videoLoopCutoffSeconds');
      if (cutoffInput) cutoffInput.value = String(gVideoLoopCutoffSeconds);
      if (cutoffInput) cutoffInput.disabled = gVideoLoopMode !== 'short';

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
      setCustomSelectValue('groupBySelect', gGroupBy);
      setCustomSelectValue('dateGranularitySelect', gGroupDateGranularity);
      setCustomSelectValue('similarityThresholdSelect', gSimilarityThreshold);
      syncGroupByUi();
      if (gRenderScanToast) gRenderScanToast();
      if (gRenderTextProcessingToast) gRenderTextProcessingToast();
      if (viewModeChanged && gBridge) {
        refreshFromBridge(gBridge, false);
      }

      const ac = document.getElementById('accentColor');
      const v = (s && s['ui.accent_color']) || '#8ab4f8';
      applyAccentCssVars(v);
      if (ac) ac.value = v;

      const theme = (s && s['ui.theme_mode']) || 'dark';
      document.documentElement.classList.toggle('light-mode', theme === 'light');
      updateThemeAwareIcons(theme);
      const radio = document.getElementById(theme === 'light' ? 'themeLight' : 'themeDark');
      if (radio) radio.checked = true;
      setAdvancedSearchExpanded(!!(s && s['ui.advanced_search_expanded']), false);
      gAdvancedSearchSavedQueries = parseAdvancedSearchSavedQueries(s && s['ui.advanced_search_saved_queries']);
      renderAdvancedSearchSavedQueries();
      refreshAdvancedCollections();
      const splashToggle = document.getElementById('toggleShowSplashScreen');
      if (splashToggle) splashToggle.checked = (s && s['ui.show_splash_screen']) !== false;

      applyTopPanelVisibility((s && s['ui.show_top_panel']) !== false);
      updateSidebarButtonIcons('top', (s && s['ui.show_top_panel']) !== false);
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

    if (bridge.list_pinned_folders) {
      bridge.list_pinned_folders(function (folders) {
        syncPinnedFolders(folders || []);
      });
    }

    // Initial sync
    refreshFromBridge(bridge);

    // React to future changes
    if (bridge.selectionChanged) {
      bridge.selectionChanged.connect(function (folders) {
        deselectAll();
        syncMetadataToBridge();
        gSelectedFolders = folders || [];
        gLastRequestedFullScanKey = '';
        clearDismissedReviewPaths();
        gAwaitingScanResults = !!(folders && folders.length);
        gPage = 0;
        if (isDuplicateModeActive()) beginReviewLoading('Scanning folder...', 10);
        else setGlobalLoading(true, 'Loading folder...', 10);
        clearReviewResultsForPendingScan();
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

    if (bridge.pinnedFoldersChanged) {
      bridge.pinnedFoldersChanged.connect(function (folders) {
        syncPinnedFolders(folders || []);
      });
    }

    if (bridge.collectionsChanged) {
      bridge.collectionsChanged.connect(function () {
        refreshAdvancedCollections();
      });
    }

    if (bridge.progressToastsRevealRequested) {
      bridge.progressToastsRevealRequested.connect(function () {
        gScanManuallyHidden = false;
        if (gTextProcessingActive) {
          gTextProcessingDismissed = false;
          gTextProcessingForceVisible = true;
        }
        if (gRenderScanToast) gRenderScanToast();
        if (gRenderTextProcessingToast) gRenderTextProcessingToast();
      });
    }

    if (bridge.accentColorChanged) {
      bridge.accentColorChanged.connect(function (v) {
        applyAccentCssVars(v);
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
          scheduleGalleryRelayout('ui.show_left_panel');
          return;
        }
        if (key === 'ui.show_top_panel') {
          applyTopPanelVisibility(!!value);
          updateSidebarButtonIcons('top', !!value);
          scheduleGalleryRelayout('ui.show_top_panel');
          return;
        }
        if (key === 'ui.show_bottom_panel') {
          updateSidebarButtonIcons('bottom', !!value);
          scheduleGalleryRelayout('ui.show_bottom_panel');
          return;
        }
        if (key === 'ui.show_right_panel') {
          updateSidebarButtonIcons('right', !!value);
          scheduleGalleryRelayout('ui.show_right_panel');
          return;
        }
        if (key === 'ui.theme_mode') {
          const theme = value ? 'light' : 'dark';
          document.documentElement.classList.toggle('light-mode', theme === 'light');
          updateThemeAwareIcons(theme);
          return;
        }
        if (key === 'gallery.show_hidden' || key === 'gallery.view_mode' || key === 'gallery.group_by' || key === 'gallery.group_date_granularity' || key === 'gallery.similarity_threshold') {
          if (key === 'gallery.show_hidden') {
            gShowHidden = !!value;
            refreshAdvancedCollections();
          }
          if (key === 'gallery.view_mode' && bridge.get_settings) {
            bridge.get_settings(function (s) {
              gCachedSettings = s || {};
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
              gCachedSettings = s || {};
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
          return;
        }
        if ((key && key.startsWith('duplicate.rules.')) || key === 'duplicate.priorities.order') {
          if (bridge.get_settings) {
            bridge.get_settings(function (s) {
              handleDuplicateRuleSettingsChanged(s || {});
            });
          }
          return;
        }
      });
    }
  });
}

main();
