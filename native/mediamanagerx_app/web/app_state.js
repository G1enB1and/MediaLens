
// Globals for state
let gSearchQuery = '';
let gActiveTagScopeQuery = '';
let gSelectAllAfterRefresh = false;
let gPage = 0;
const PAGE_SIZE = 100;
const MAX_GALLERY_FETCH_LIMIT = 2147483647;
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
let gFilterGroups = { media: 'all', text: 'all', tags: 'all', desc: 'all', ai: 'all' };
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
let gPreserveGalleryScrollUntil = 0;
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
let gIsRenderingGallery = false;
let gLastGalleryRenderSignature = '';
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
let gScanToastGeneration = 0;
let gGalleryFilterMetadataRefreshTimer = 0;
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
  { key: 'ocr', label: 'Detected Text', kind: 'text' },
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
  ocr: 'detected_text',
  'ocr-text': 'detected_text',
  ocrtext: 'detected_text',
  'detected-text': 'detected_text',
  detectedtext: 'detected_text',
  detected_text: 'detected_text',
  'text-found': 'detected_text',
  textfound: 'detected_text',
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
  'path', 'filename', 'folder', 'title', 'description', 'notes', 'detected_text', 'tags', 'collection_names',
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
  detected_text: 'ocr',
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
let gIncludeNestedFiles = true;
let gShowFoldersInGallery = true;

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
  gLastGalleryRenderSignature = '';
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

function normalizeTagsFilter(filterValue) {
  return ['has_tags', 'no_tags'].includes(filterValue) ? filterValue : 'all';
}

function normalizeDescFilter(filterValue) {
  return ['has_description', 'no_description'].includes(filterValue) ? filterValue : 'all';
}

function normalizeAiFilter(filterValue) {
  return ['ai_generated', 'non_ai'].includes(filterValue) ? filterValue : 'all';
}

function normalizeFilterValue(filterValue) {
  const raw = String(filterValue || 'all').trim();
  if (!raw || raw === 'all') return { media: 'all', text: 'all', tags: 'all', desc: 'all', ai: 'all' };
  if (!raw.includes(':')) {
    const normalizedText = normalizeTextFilter(raw);
    if (normalizedText === 'text_detected' || normalizedText === 'no_text_detected') {
      return { media: 'all', text: normalizedText, tags: 'all', desc: 'all', ai: 'all' };
    }
    const normalizedTags = normalizeTagsFilter(raw);
    if (normalizedTags !== 'all') {
      return { media: 'all', text: 'all', tags: normalizedTags, desc: 'all', ai: 'all' };
    }
    const normalizedDesc = normalizeDescFilter(raw);
    if (normalizedDesc !== 'all') {
      return { media: 'all', text: 'all', tags: 'all', desc: normalizedDesc, ai: 'all' };
    }
    const normalizedAi = normalizeAiFilter(raw);
    if (normalizedAi !== 'all') {
      return { media: 'all', text: 'all', tags: 'all', desc: 'all', ai: normalizedAi };
    }
    return { media: normalizeMediaFilter(raw), text: 'all', tags: 'all', desc: 'all', ai: 'all' };
  }
  const groups = { media: 'all', text: 'all', tags: 'all', desc: 'all', ai: 'all' };
  raw.split(';').forEach((part) => {
    const [groupRaw, valueRaw] = String(part || '').split(':');
    const group = String(groupRaw || '').trim();
    const value = String(valueRaw || '').trim();
    if (group === 'media') groups.media = normalizeMediaFilter(value);
    if (group === 'text') groups.text = normalizeTextFilter(value) === 'no_text_detected' ? 'no_text_detected' : (normalizeTextFilter(value) === 'text_detected' ? 'text_detected' : 'all');
    if (group === 'tags') groups.tags = normalizeTagsFilter(value);
    if (group === 'desc') groups.desc = normalizeDescFilter(value);
    if (group === 'meta') {
      if (value === 'no_tags') groups.tags = 'no_tags';
      if (value === 'no_description') groups.desc = 'no_description';
    }
    if (group === 'ai') groups.ai = normalizeAiFilter(value);
  });
  return groups;
}

function serializeFilterValue(groups) {
  const media = normalizeMediaFilter(groups && groups.media);
  const normalizedText = normalizeTextFilter(groups && groups.text);
  const text = normalizedText === 'text_detected' || normalizedText === 'no_text_detected' ? normalizedText : 'all';
  const tags = normalizeTagsFilter(groups && groups.tags);
  const desc = normalizeDescFilter(groups && groups.desc);
  const ai = normalizeAiFilter(groups && groups.ai);
  const parts = [];
  if (media !== 'all') parts.push(`media:${media}`);
  if (text !== 'all') parts.push(`text:${text}`);
  if (tags !== 'all') parts.push(`tags:${tags}`);
  if (desc !== 'all') parts.push(`desc:${desc}`);
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
  if (groups.tags === 'has_tags') labels.push('Has Tags');
  else if (groups.tags === 'no_tags') labels.push('No Tags');
  if (groups.desc === 'has_description') labels.push('Has Description');
  else if (groups.desc === 'no_description') labels.push('No Description');
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
  'Preferred Folders',
  'Most metadata',
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
let gPendingMediaFileCountRequests = new Map();
let gPendingMediaListRequests = new Map();
let gRefreshGeneration = 0;

