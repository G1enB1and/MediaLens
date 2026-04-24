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

    const reasons = getDisplayDuplicateReasons(item);
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
  if (groups && groups.length) {
    gAwaitingScanResults = false;
  }
  gLastRenderedReviewSignature = computeReviewRenderSignature(gMedia);
  renderTimelineRail([]);
  restoreGroupScrollAnchor();
  groups.forEach((group) => {
    setDuplicateKeepPaths(group.key, getDuplicateKeepPaths(group.key));
    setDuplicateDeletePaths(group.key, getDuplicateDeletePaths(group.key));
    const bestPath = getDuplicateBestPath(group.key);
    if (bestPath) setDuplicateBestPath(group.key, bestPath);
  });
  applyDuplicateReviewSummaryToRoot(el);
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

function seedDuplicateGroupState(group) {
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
    storeDuplicateKeepPaths(group.key, defaultKeepPaths);
  } else if (validKeepPaths.length !== existingKeepPaths.length) {
    storeDuplicateKeepPaths(group.key, validKeepPaths);
  }
  if (!validDeletePaths.length && !hasDeleteOverride) {
    storeDuplicateDeletePaths(group.key, group.items.map(item => item.path).filter(path => path && !defaultKeepSet.has(normalizeMediaPath(path))));
  } else if (validDeletePaths.length !== existingDeletePaths.length) {
    storeDuplicateDeletePaths(group.key, validDeletePaths);
  }
  if (!existingBestPath || !groupPaths.has(existingBestPath)) {
    storeDuplicateBestPath(
      group.key,
      (group.keepItem && group.keepItem.path) ? group.keepItem.path : ((group.items[0] && group.items[0].path) || '')
    );
  }
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
    seedDuplicateGroupState(group);
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

  applyDuplicateReviewSummaryToRoot(el);

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

      markGalleryMutationScrollPreserve(hidden ? targetPaths : null);
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
        if (item && item.path && gBridge && gBridge.rename_path_async && gBridge.themed_text_input) {
          const curName = item.path.split(/[/\\]/).pop();
          gBridge.themed_text_input('Rename File', 'Rename to:', curName, function (next) {
            if (next && next !== curName) {
              if (fromLb) closeLightbox();
              setGlobalLoading(true, 'Renaming…', 25);
              gBridge.rename_path_async(item.path, next, () => { });
            }
          });
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
          deletePathFromUi(item.path, (ok) => { if (ok) refreshFromBridge(gBridge, false); });
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
        if (gBridge && gBridge.themed_text_input && gBridge.create_folder && gSelectedFolders.length > 0) {
          gBridge.themed_text_input('New Folder', 'Folder Name:', '', function (name) {
            if (name) {
              const folder = gSelectedFolders[0];
              gBridge.create_folder(folder, name, (res) => { if (res) refreshFromBridge(gBridge); });
            }
          });
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
  if (gIsRenderingGallery) return;
  gIsRenderingGallery = true;

  const finalizeRender = () => {
    requestAnimationFrame(() => {
      gIsRenderingGallery = false;
    });
  };

  try {
    const el = document.getElementById('mediaList');
    if (!el) {
      finalizeRender();
      return;
    }
    const nextRenderSignature = computeGalleryRenderSignature(items);
    if (nextRenderSignature && nextRenderSignature === gLastGalleryRenderSignature && !gPendingScrollAnchor) {
      gMedia = Array.isArray(items) ? items : [];
      gMedia.forEach((item, idx) => {
        item.__galleryIndex = idx;
      });
      reconcileSelectionWithVisibleItems(gMedia);
      renderTimelineRail(gGroupBy === 'date' ? buildGroupedItems(gMedia.filter(item => !item.is_folder)) : []);
      scheduleTimelineScrollTargetRefresh();
      prioritizeVisibleMediaLoads(el);
      finalizeRender();
      return;
    }
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
    gLastGalleryRenderSignature = nextRenderSignature;
    const main = document.querySelector('main');
    if (scrollToTop && main && !gPendingScrollAnchor) {
      main.scrollTop = 0;
    }
    gMedia = Array.isArray(items) ? items : [];
    gMedia.forEach((item, idx) => {
      item.__galleryIndex = idx;
    });
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
      finalizeRender();
      return;
    }

    if (viewItems.length === 0) {
      const div = document.createElement('div');
      div.className = 'empty';
      div.textContent = 'No results.';
      el.appendChild(div);
      renderTimelineRail([]);
      finalizeRender();
      return;
    }

    if (isDuplicateModeActive()) {
      if (gReviewLoadingActive) {
        const staging = document.createElement('div');
        const groups = renderDuplicateMediaList(staging, viewItems, {
          deferFinalize: true
        });
        staging.classList.forEach((cls) => el.classList.add(cls));
        const reviewLoadingGeneration = gReviewLoadingGeneration;
        prioritizeVisibleMediaLoads(staging);
        waitForInitialReviewCards(staging, reviewLoadingGeneration).then(() => {
          if (!gReviewLoadingActive || reviewLoadingGeneration !== gReviewLoadingGeneration) return;
          el.replaceChildren(...Array.from(staging.childNodes));
          finalizeDuplicateMediaList(el, groups);
        });
      } else {
        renderDuplicateMediaList(el, viewItems);
      }
      finalizeRender();
      return;
    }

    if (gGroupBy === 'date') {
      renderGroupedMediaList(el, viewItems);
      finalizeRender();
      return;
    }

    if (gGalleryViewMode !== 'masonry') {
      renderStructuredMediaList(el, viewItems);
      renderTimelineRail([]);
      requestAnimationFrame(() => {
        restorePendingGalleryScrollAnchor();
      });
      finalizeRender();
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
      restorePendingGalleryScrollAnchor();
      prioritizeVisibleMediaLoads(el);
      const unobserved = el.querySelectorAll('img[data-src]:not([src]), img[data-poster-path]:not([src]), img[data-video-path]:not([src])');
      unobserved.forEach(img => {
        if (gPosterRequested.has(img)) return;
        const imgSrc = img.getAttribute('data-src');
        const posterPath = img.getAttribute('data-poster-path');
        const path = img.getAttribute('data-video-path');
        const item = gMedia.find(m => m.path === path || m.url === imgSrc); // Find the original item to get width/height
        if (imgSrc) {
          gBackgroundQueue.push({
            type: 'image',
            el: img,
            imgSrc
          });
        } else if (posterPath) {
          gBackgroundQueue.push({
            type: 'poster',
            el: img,
            path: posterPath
          });
        } else if (path && item) {
          gBackgroundQueue.push({
            type: 'video',
            el: img,
            path,
            width: item.width,
            height: item.height
          });
        }
      });
      scheduleBackgroundDrain();
    });
    renderTimelineRail([]);
    finalizeRender();
  } catch (err) {
    finalizeRender();
    throw err;
  }
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
  function closeCustomSelects(except = null) {
    document.querySelectorAll('.custom-select.open').forEach((select) => {
      if (select !== except) select.classList.remove('open');
    });
  }

  function setupCustomSelect(id, onChange) {
    const el = document.getElementById(id);
    if (!el) return;
    const trigger = el.querySelector('.select-trigger');
    const options = el.querySelector('.select-options');

    // Toggle open
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      closeCustomSelects(el);
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
      closeCustomSelects(el);
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

  document.addEventListener('pointerdown', (e) => {
    if (!e.target.closest('.custom-select')) {
      closeCustomSelects();
    }
  }, true);

  document.addEventListener('focusin', (e) => {
    if (!e.target.closest('.custom-select')) {
      closeCustomSelects();
    }
  }, true);

  // Close on outside click and handle global deselection
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.custom-select')) {
      closeCustomSelects();
    }

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
      gLastRequestedFullScanKey = '';
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

