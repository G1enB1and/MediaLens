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
let gPendingMetadataSyncHandle = 0;
let gPendingMetadataSyncTimeout = 0;
let gMetadataSyncRevision = 0;

function shouldSelectFoldersOnSelectAll() {
  return !gIncludeNestedFiles;
}

function fetchMediaFileCount(folders, filterType, searchQuery) {
  if (!gBridge) return Promise.resolve(0);
  const effectiveQuery = getEffectiveSearchQuery(searchQuery || '');
  if (gBridge.count_media_files_async) {
    return new Promise((resolve) => {
      const requestId = `file-count-${Date.now()}-${++gGalleryRequestSeq}`;
      gPendingMediaFileCountRequests.set(requestId, resolve);
      gBridge.count_media_files_async(requestId, folders || [], filterType || 'all', effectiveQuery);
    });
  }
  if (!gBridge.count_media_files) {
    return Promise.resolve(0);
  }
  return new Promise((resolve) => {
    gBridge.count_media_files(folders || [], filterType || 'all', effectiveQuery, function (count) {
      resolve(Number(count || 0));
    });
  });
}

function refreshGalleryFileCountChip() {
  return fetchMediaFileCount(gSelectedFolders, gFilter, gSearchQuery || '')
    .then((count) => {
      updateGalleryCountChip(count);
      return count;
    })
    .catch(() => {
      updateGalleryCountChip(0);
      return 0;
    });
}

function isFolderCardElement(card) {
  return !!(card && card.getAttribute('data-is-folder') === 'true');
}

function deselectAll(force = false) {
  if (!force && gIsCtxMenuClick) {
    gIsCtxMenuClick = false;
    return;
  }
  gIsCtxMenuClick = false;
  queryGalleryCards('.selected').forEach(c => c.classList.remove('selected'));
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
  queryGalleryCards().forEach(c => {
    const selectCard = !isFolderCardElement(c) || shouldSelectFoldersOnSelectAll();
    c.classList.toggle('selected', selectCard);
    const path = c.getAttribute('data-path');
    if (path && selectCard) gSelectedPaths.add(path);
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

  if (path && gBridge && gBridge.rename_path_async && gBridge.themed_text_input) {
    const curName = path.split(/[/\\]/).pop();
    gBridge.themed_text_input('Rename File', 'Rename to:', curName, function (next) {
      if (next && next !== curName) {
        if (typeof closeLightbox === 'function') closeLightbox();
        setGlobalLoading(true, 'Renaming…', 25);
        gBridge.rename_path_async(path, next, () => { });
      }
    });
  }
}
window.triggerRename = triggerRename;

function syncMetadataToBridge() {
  if (gPendingMetadataSyncHandle) {
    cancelAnimationFrame(gPendingMetadataSyncHandle);
    gPendingMetadataSyncHandle = 0;
  }
  if (gPendingMetadataSyncTimeout) {
    clearTimeout(gPendingMetadataSyncTimeout);
    gPendingMetadataSyncTimeout = 0;
  }
  const revision = ++gMetadataSyncRevision;
  gPendingMetadataSyncHandle = requestAnimationFrame(() => {
    gPendingMetadataSyncHandle = 0;
    gPendingMetadataSyncTimeout = window.setTimeout(() => {
      gPendingMetadataSyncTimeout = 0;
      if (revision !== gMetadataSyncRevision) return;
      if (gBridge && gBridge.show_metadata) {
        const paths = Array.from(gSelectedPaths);
        gBridge.show_metadata(paths);
      }
    }, 0);
  });
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
  const cards = queryGalleryCards(`[data-duplicate-group-key="${CSS.escape(groupKey)}"]`);
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

function storeDuplicateKeepPaths(groupKey, paths) {
  const key = String(groupKey || '');
  if (!key) return;
  const nextPaths = Array.from(new Set((Array.isArray(paths) ? paths : [paths]).map(v => String(v || '')).filter(Boolean)));
  gDuplicateKeepOverrides.set(key, new Set(nextPaths));
}

function setDuplicateKeepPaths(groupKey, paths) {
  const key = String(groupKey || '');
  if (!key) return;
  const nextPaths = Array.from(new Set((Array.isArray(paths) ? paths : [paths]).map(v => String(v || '')).filter(Boolean)));
  const normalizedNextPaths = new Set(nextPaths.map(normalizeMediaPath).filter(Boolean));
  storeDuplicateKeepPaths(key, nextPaths);
  document.querySelectorAll(`.card[data-duplicate-group-key="${CSS.escape(key)}"]`).forEach((card) => {
    const checked = normalizedNextPaths.has(normalizeMediaPath(card.getAttribute('data-path') || ''));
    card.setAttribute('data-duplicate-keep', checked ? 'true' : 'false');
    const toggle = card.querySelector('.duplicate-keep-toggle');
    if (toggle) toggle.checked = checked;
  });
  updateDuplicateReviewSummary();
}

function storeDuplicateDeletePaths(groupKey, paths) {
  const key = String(groupKey || '');
  if (!key) return;
  const nextPaths = Array.from(new Set((Array.isArray(paths) ? paths : [paths]).map(v => String(v || '')).filter(Boolean)));
  gDuplicateDeleteOverrides.set(key, new Set(nextPaths));
}

function setDuplicateDeletePaths(groupKey, paths) {
  const key = String(groupKey || '');
  if (!key) return;
  const nextPaths = Array.from(new Set((Array.isArray(paths) ? paths : [paths]).map(v => String(v || '')).filter(Boolean)));
  const normalizedNextPaths = new Set(nextPaths.map(normalizeMediaPath).filter(Boolean));
  storeDuplicateDeletePaths(key, nextPaths);
  document.querySelectorAll(`.card[data-duplicate-group-key="${CSS.escape(key)}"]`).forEach((card) => {
    const checked = normalizedNextPaths.has(normalizeMediaPath(card.getAttribute('data-path') || ''));
    card.setAttribute('data-duplicate-delete', checked ? 'true' : 'false');
    const toggle = card.querySelector('.duplicate-delete-toggle');
    if (toggle) toggle.checked = checked;
  });
  updateDuplicateReviewSummary();
}

function storeDuplicateBestPath(groupKey, path) {
  const key = String(groupKey || '');
  const nextPath = String(path || '');
  if (!key) return;
  if (nextPath) gDuplicateBestOverrides.set(key, nextPath);
  else gDuplicateBestOverrides.delete(key);
}

function setDuplicateBestPath(groupKey, path) {
  const key = String(groupKey || '');
  const nextPath = String(path || '');
  if (!key) return;
  storeDuplicateBestPath(key, nextPath);
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
  if (queue.length) markGalleryMutationScrollPreserve(queue);
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
  if (!gPendingScrollAnchor) {
    markGalleryMutationScrollPreserve([path]);
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

function getDisplayDuplicateReasons(item) {
  const reasons = Array.isArray(item && item.duplicate_category_reasons)
    ? item.duplicate_category_reasons.filter(Boolean)
    : [];
  if (!item || reasons.includes('Preferred Folder')) return reasons;
  const groupKey = String(item.duplicate_group_key || '').trim();
  if (!groupKey) return reasons;
  const groupItems = getDuplicateGroupItems(groupKey);
  if (!groupItems.length) return reasons;
  const scores = groupItems.map(entry => Number(entry.duplicate_preferred_folder_score) || 0);
  const maxScore = Math.max(...scores);
  const minScore = Math.min(...scores);
  const itemScore = Number(item.duplicate_preferred_folder_score) || 0;
  if (maxScore > 0 && maxScore > minScore && itemScore === maxScore) {
    reasons.push('Preferred Folder');
  }
  return reasons;
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

function applyDuplicateReviewSummaryToRoot(root) {
  if (!root) return;
  const totals = getDuplicateReviewSummaryTotals();
  const keepEl = root.querySelector('.duplicate-review-keep .duplicate-summary-value');
  const deleteEl = root.querySelector('.duplicate-review-delete .duplicate-summary-value');
  const saveEl = root.querySelector('.duplicate-review-save .duplicate-summary-value');
  if (keepEl) keepEl.textContent = `${totals.keepCount}`;
  if (deleteEl) deleteEl.textContent = `${totals.deleteCount}`;
  if (saveEl) saveEl.textContent = `${formatFileSize(totals.savings) || '0 B'}`;
}

function updateDuplicateReviewSummary() {
  applyDuplicateReviewSummaryToRoot(document);
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
  return queryGalleryCards('.selected').some(card => card.getAttribute('data-is-folder') !== 'true');
}

function syncSelectedCardClasses() {
  queryGalleryCards().forEach((card) => {
    const path = card.getAttribute('data-path') || '';
    card.classList.toggle('selected', !!path && gSelectedPaths.has(path));
  });
}

function updateLockedCardAfterSelection(preferredCard = null) {
  if (preferredCard) {
    const preferredPath = preferredCard.getAttribute('data-path') || '';
    if (preferredPath && gSelectedPaths.has(preferredPath)) {
      gLockedCard = preferredCard;
      return;
    }
  }
  const firstSelectedPath = Array.from(gSelectedPaths)[0] || '';
  gLockedCard = firstSelectedPath ? queryGalleryCardByPath(firstSelectedPath) : null;
}

function updateCtxViewState() {
  document.querySelectorAll('.ctx-view-item').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.viewMode === gGalleryViewMode);
  });
}

function handleCardSelection(card, item, idx, e) {
  e.stopPropagation();
  const path = card.getAttribute('data-path') || item.path || '';
  if (!path) return;

  if (e.ctrlKey || e.metaKey) {
    if (gSelectedPaths.has(path)) {
      gSelectedPaths.delete(path);
    } else {
      gSelectedPaths.add(path);
    }
    syncSelectedCardClasses();
    updateLockedCardAfterSelection(card);
    gLastSelectionIdx = gSelectedPaths.has(path) ? idx : -1;
  } else if (e.shiftKey && gLastSelectionIdx !== -1) {
    const start = Math.min(gLastSelectionIdx, idx);
    const end = Math.max(gLastSelectionIdx, idx);
    const cards = queryGalleryCards();
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
    gLockedCard = card;
  }

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
  const main = document.querySelector('main');
  const target = document.querySelector(`.gallery-group[data-group-key="${CSS.escape(groupKey)}"]`);
  if (!target) return;
  if (!main) {
    target.scrollIntoView({ block: 'start', behavior: gTimelineScrubActive ? 'auto' : 'smooth' });
    return;
  }
  const mainRect = main.getBoundingClientRect();
  const targetRect = target.getBoundingClientRect();
  const stickyOffset = getReviewStickyHeaderOffset(main);
  const targetScrollTop = main.scrollTop + (targetRect.top - mainRect.top) - stickyOffset;
  main.scrollTo({
    top: Math.max(0, targetScrollTop),
    behavior: gTimelineScrubActive ? 'auto' : 'smooth',
  });
}

function queueReviewGroupReturnScroll(groupKey) {
  gPendingReviewGroupReturnKey = String(groupKey || '').trim();
}

const REVIEW_GROUP_SCROLL_CLEARANCE_PX = 12;

function getReviewStickyHeaderOffset(main) {
  if (!main) return 0;
  let offset = 0;
  document.querySelectorAll('.duplicate-summary').forEach((header) => {
    const style = window.getComputedStyle(header);
    if (style.display === 'none' || style.visibility === 'hidden') return;
    const rect = header.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;
    const stickyTop = Number.parseFloat(style.top || '0') || 0;
    offset = Math.max(offset, rect.height + Math.min(0, stickyTop));
  });
  return Math.ceil(Math.max(0, offset)) + REVIEW_GROUP_SCROLL_CLEARANCE_PX;
}

function getReviewGroupsForNavigation() {
  if (!isDuplicateModeActive()) return [];
  return buildDuplicateGroups(gMedia);
}

function getVisibleReviewGroupKeyFromDom() {
  const main = document.querySelector('main');
  const sections = Array.from(document.querySelectorAll('.gallery-group[data-group-key]'));
  if (!main || !sections.length) return '';

  const mainRect = main.getBoundingClientRect();
  const topClearance = getReviewStickyHeaderOffset(main);
  const targetTop = mainRect.top + topClearance;
  const visible = sections.find((section) => {
    const rect = section.getBoundingClientRect();
    return rect.top >= targetTop && rect.top < mainRect.bottom;
  });
  if (visible) return String(visible.dataset.groupKey || '');

  let closest = null;
  sections.forEach((section) => {
    const rect = section.getBoundingClientRect();
    const distance = Math.abs(rect.top - targetTop);
    if (!closest || distance < closest.distance) {
      closest = { key: String(section.dataset.groupKey || ''), distance };
    }
  });
  return closest ? closest.key : '';
}

function captureReviewGroupForComparisonOpen() {
  const key = getVisibleReviewGroupKeyFromDom();
  if (!key) return '';
  gReviewSingleGroupKey = key;
  gPendingReviewGroupOpenKey = key;
  return key;
}

function getCurrentReviewGroupKeyForNavigation() {
  if (isComparePanelReviewSingleMode()) {
    return String(gPendingReviewGroupOpenKey || '').trim() || compareReviewGroupKeyFromState() || String(gReviewSingleGroupKey || '').trim();
  }

  const domKey = getVisibleReviewGroupKeyFromDom();
  if (domKey) return domKey;

  {
    const comparePaths = getCompareActivePaths();
    const compareGroupKeys = Array.from(new Set(comparePaths.map(getDuplicateGroupKeyForPath).filter(Boolean)));
    return compareGroupKeys.length === 1 ? compareGroupKeys[0] : '';
  }
}

function focusReviewGroup(groupKey) {
  const targetKey = String(groupKey || '').trim();
  if (!targetKey || !gBridge) return false;
  const previousKey = getCurrentReviewGroupKeyForNavigation();
  const group = getReviewGroupsForNavigation().find(entry => String(entry.key || '') === targetKey);
  if (!group || !Array.isArray(group.items) || group.items.length < 2) return false;

  const comparePaths = group.items
    .slice(0, 2)
    .map(item => String(item && item.path || ''))
    .filter(Boolean);
  if (comparePaths.length < 2) return false;

  if (previousKey && previousKey !== targetKey) {
    deselectAll(true);
    syncMetadataToBridge();
  }

  gReviewSingleGroupKey = targetKey;
  gPendingReviewGroupOpenKey = targetKey;
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
    if (isComparePanelReviewSingleMode()) {
      gLastGalleryRenderSignature = '';
      renderMediaList(gMedia, false);
    } else {
      scrollToGroup(targetKey);
    }
  }, 0);
  return true;
}

function seedCompareFromFirstReviewGroup() {
  const groups = getReviewGroupsForNavigation();
  if (!groups.length) return false;
  return focusReviewGroup(groups[0].key);
}

function seedCompareFromCurrentReviewGroup() {
  const groups = getReviewGroupsForNavigation();
  if (!groups.length) return false;
  const currentKey = getCurrentReviewGroupKeyForNavigation();
  const group = groups.find(entry => String(entry.key || '') === currentKey) || groups[0];
  return focusReviewGroup(group.key);
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

function getReviewCompareNavContext() {
  const groups = getReviewGroupsForNavigation();
  const currentKey = getCurrentReviewGroupKeyForNavigation();
  const currentIndex = groups.findIndex(group => String(group.key || '') === currentKey);
  const group = currentIndex >= 0 ? groups[currentIndex] : null;
  const items = group && Array.isArray(group.items) ? group.items : [];
  const leftPath = compareSlotPath('left');
  const rightPath = compareSlotPath('right');
  const normalizedLeft = normalizeMediaPath(leftPath);
  const normalizedRight = normalizeMediaPath(rightPath);
  const indexForPath = (path) => {
    const normalized = normalizeMediaPath(path);
    if (!normalized) return -1;
    return items.findIndex(item => normalizeMediaPath(item && item.path) === normalized);
  };
  return {
    groups,
    currentIndex,
    group,
    items,
    leftPath,
    rightPath,
    normalizedLeft,
    normalizedRight,
    leftIndex: indexForPath(leftPath),
    rightIndex: indexForPath(rightPath),
  };
}

function findReviewImageStepPath(items, currentIndex, otherIndex, direction) {
  if (!Array.isArray(items) || currentIndex < 0) return '';
  const step = Number(direction) < 0 ? -1 : 1;
  for (let index = currentIndex + step; index >= 0 && index < items.length; index += step) {
    if (index === otherIndex) continue;
    const path = String(items[index] && items[index].path || '');
    if (path) return path;
  }
  return '';
}

function getReviewCompareNavState() {
  const ctx = getReviewCompareNavContext();
  const leftPreviousPath = findReviewImageStepPath(ctx.items, ctx.leftIndex, ctx.rightIndex, -1);
  const leftNextPath = findReviewImageStepPath(ctx.items, ctx.leftIndex, ctx.rightIndex, 1);
  const rightPreviousPath = findReviewImageStepPath(ctx.items, ctx.rightIndex, ctx.leftIndex, -1);
  const rightNextPath = findReviewImageStepPath(ctx.items, ctx.rightIndex, ctx.leftIndex, 1);
  return {
    previousGroup: ctx.currentIndex > 0,
    nextGroup: ctx.currentIndex >= 0 && ctx.currentIndex < ctx.groups.length - 1,
    leftPrevious: !!leftPreviousPath,
    leftNext: !!leftNextPath,
    rightPrevious: !!rightPreviousPath,
    rightNext: !!rightNextPath,
    leftPreviousPath,
    leftNextPath,
    rightPreviousPath,
    rightNextPath,
  };
}

function jumpReviewImage(slotName, direction) {
  if (!gBridge || !gBridge.set_compare_path) return false;
  const slot = String(slotName || '').trim().toLowerCase() === 'right' ? 'right' : 'left';
  const step = Number(direction) < 0 ? -1 : 1;
  const ctx = getReviewCompareNavContext();
  const currentIndex = slot === 'right' ? ctx.rightIndex : ctx.leftIndex;
  const otherIndex = slot === 'right' ? ctx.leftIndex : ctx.rightIndex;
  const nextPath = findReviewImageStepPath(ctx.items, currentIndex, otherIndex, step);
  if (!nextPath) return false;
  gBridge.set_compare_path(slot, nextPath);
  const key = String(ctx.group && ctx.group.key || '').trim();
  if (key) {
    const keepPaths = getDuplicateKeepPaths(key).slice().sort();
    const deletePaths = getDuplicateDeletePaths(key).slice().sort();
    const bestPath = getDuplicateBestPath(key);
    window.setTimeout(() => syncCompareStateFromReviewGroup(key, keepPaths, deletePaths, bestPath), 0);
  }
  return true;
}

window.__mmx_seedCompareFromFirstReviewGroup = function () {
  return seedCompareFromFirstReviewGroup();
};

window.__mmx_seedCompareFromCurrentReviewGroup = function () {
  return seedCompareFromCurrentReviewGroup();
};

window.__mmx_captureReviewGroupForComparisonOpen = function () {
  return captureReviewGroupForComparisonOpen();
};

window.__mmx_jumpReviewGroup = function (direction) {
  return jumpReviewGroup(direction);
};

window.__mmx_jumpReviewImage = function (slotName, direction) {
  return jumpReviewImage(slotName, direction);
};

window.__mmx_getReviewCompareNavState = function () {
  return getReviewCompareNavState();
};

function captureCurrentGroupScrollAnchor(excludedPaths = null) {
  const main = document.querySelector('main');
  if (!main) return null;
  const topCard = captureCurrentCardScrollAnchor(main, excludedPaths);
  if (topCard) return topCard;
  const groups = Array.from(document.querySelectorAll('.gallery-group'));
  if (!groups.length) {
    return {
      type: 'scroll',
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
    type: 'group',
    scrollTop: main.scrollTop,
    groupSortValue: Number.isFinite(groupSortValueRaw) ? groupSortValueRaw : null,
    rangeStart: Number.isFinite(groupRangeStartRaw) ? groupRangeStartRaw : null,
    rangeEnd: Number.isFinite(groupRangeEndRaw) ? groupRangeEndRaw : null,
    offsetWithinGroup: Math.max(0, main.scrollTop - groupTopScroll),
  };
}

function captureDeleteScrollAnchor(paths) {
  const excludedPaths = new Set(
    (Array.isArray(paths) ? paths : [paths])
      .map(normalizeMediaPath)
      .filter(Boolean)
  );
  const main = document.querySelector('main');
  if (!main) return null;
  return captureCurrentGroupScrollAnchor(excludedPaths);
}

function markGalleryMutationScrollPreserve(paths = null) {
  if (!gPendingScrollAnchor) {
    const pathList = Array.isArray(paths) ? paths : (paths ? [paths] : []);
    gPendingScrollAnchor = pathList.length
      ? captureDeleteScrollAnchor(pathList)
      : captureCurrentGroupScrollAnchor();
  }
  gPreserveGalleryScrollUntil = Date.now() + 3000;
}

function shouldPreserveGalleryScrollForRefresh() {
  return !!gPendingScrollAnchor || Date.now() < gPreserveGalleryScrollUntil;
}

function prepareGalleryScrollPreservationForRefresh(resetPage = false) {
  if (resetPage) {
    gPreserveGalleryScrollUntil = 0;
    gPendingScrollAnchor = null;
    return false;
  }
  if (!shouldPreserveGalleryScrollForRefresh()) return false;
  if (!gPendingScrollAnchor) {
    gPendingScrollAnchor = captureCurrentGroupScrollAnchor();
  }
  return !!gPendingScrollAnchor;
}

function captureCurrentCardScrollAnchor(mainOverride = null, excludedPaths = null) {
  const main = mainOverride || document.querySelector('main');
  if (!main) return null;
  const cards = queryGalleryCards('[data-path]');
  if (!cards.length) return null;
  const mainRect = main.getBoundingClientRect();
  let best = null;
  const excluded = excludedPaths instanceof Set ? excludedPaths : new Set();
  cards.forEach((card) => {
    const path = card.getAttribute('data-path') || '';
    if (excluded.has(normalizeMediaPath(path))) return;
    const rect = card.getBoundingClientRect();
    if (rect.bottom < mainRect.top || rect.top > mainRect.bottom) return;
    const topWithinMain = rect.top - mainRect.top;
    const distance = Math.abs(topWithinMain);
    if (!best || distance < best.distance) {
      best = { card, topWithinMain, distance };
    }
  });
  if (!best) return null;
  return {
    type: 'card',
    path: best.card.getAttribute('data-path') || '',
    scrollTop: main.scrollTop,
    offsetWithinCard: best.topWithinMain,
  };
}

function restoreGroupScrollAnchor() {
  const anchor = gPendingScrollAnchor;
  gPendingScrollAnchor = null;
  if (!anchor) return;
  const main = document.querySelector('main');
  if (!main) return;
  if (anchor.type === 'card') {
    const path = String(anchor.path || '');
    if (path) {
      const card = queryGalleryCardByPath(path);
      if (card) {
        const mainRect = main.getBoundingClientRect();
        const cardRect = card.getBoundingClientRect();
        const currentTopWithinMain = cardRect.top - mainRect.top;
        main.scrollTop = Math.max(0, main.scrollTop + currentTopWithinMain - (anchor.offsetWithinCard || 0));
        return;
      }
    }
    main.scrollTop = anchor.scrollTop || 0;
    return;
  }
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

function restorePendingGalleryScrollAnchor() {
  if (!gPendingScrollAnchor) return;
  restoreGroupScrollAnchor();
  if (Date.now() >= gPreserveGalleryScrollUntil) {
    gPreserveGalleryScrollUntil = 0;
  }
}

function rerenderCurrentMediaPreservingScroll() {
  gPendingScrollAnchor = captureCurrentGroupScrollAnchor();
  gLastGalleryRenderSignature = '';
  renderMediaList(gMedia, false);
}

function computeGalleryRenderSignature(items) {
  const rows = Array.isArray(items) ? items : [];
  const parts = [
    gGalleryViewMode,
    gGroupBy,
    getReviewMode(),
    isComparePanelReviewSingleMode() ? 'compare-single' : 'full-review',
    isComparePanelReviewSingleMode() ? (compareReviewGroupKeyFromState() || String(gReviewSingleGroupKey || '')) : '',
    shouldShowScanWaitingEmptyState() ? 'waiting' : 'ready',
  ];
  for (const item of rows) {
    if (!item) continue;
    parts.push([
      item.is_folder ? 'folder' : 'media',
      item.path || '',
      item.media_type || '',
      item.is_hidden ? 'hidden' : 'visible',
      item.width || '',
      item.height || '',
      item.file_size || '',
      item.modified_time || '',
      item.thumb_bg_hint || '',
      item.duplicate_group_key || '',
      item.duplicate_group_position || '',
      item.compare_keep_checked ? 'keep' : '',
      item.compare_delete_checked ? 'delete' : '',
      item.compare_marked_best ? 'best' : '',
    ].join('|'));
  }
  return parts.join('\n');
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

  // Only perform a full DOM rerender if explicitly forced. 
  // Standard grid/list/masonry modes rely on CSS for responsiveness.
  const needsFullRerender = reason === 'force';
  if (needsFullRerender && Array.isArray(gMedia) && gMedia.length > 0 && !isDuplicateModeActive()) {
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
  if (gIsRenderingGallery) return;

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
    if (gIsRenderingGallery) return; // Final guard before RAF
    if (gGalleryRelayoutRaf) {
      cancelAnimationFrame(gGalleryRelayoutRaf);
      gGalleryRelayoutRaf = 0;
    }
    gGalleryRelayoutRaf = requestAnimationFrame(() => {
      gGalleryRelayoutRaf = 0;
      if (gIsRenderingGallery) return;
      runGalleryRelayout(reason);
    });
  }, 250);
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

