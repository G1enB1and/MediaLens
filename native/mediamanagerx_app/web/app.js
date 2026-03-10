
// Globals for state
let gSearchQuery = '';
let gPage = 0;
const PAGE_SIZE = 100;
let gTotal = 0;
let gMedia = []; // Current page items
let gSelectedFolders = [];
let gBridge = null;
let gPosterRequested = new Set();
let gPosterObserver = null;
let gSort = 'name_asc';
let gFilter = 'all';
let gCurrentTargetFolderName = '';
let gCurrentDragCount = 0;
let gPlayingInplaceCard = null;

// Loading progress tracking
let gTotalOnPage = 0;
let gLoadedOnPage = 0;
let gLoadingDismissed = false;

function setStatus(text) {
  const el = document.getElementById('status');
  if (el) el.textContent = text;
}

function setSelectedFolder(paths) {
  const el = document.getElementById('selectedFolder');
  if (!el) return;
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
        tempImg.onload = tempImg.onerror = () => {
          el.src = posterUrl;
          gLoadedOnPage++;
          // Push opacity change one frame out so the CSS transition fires
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
    // Single click minimizes, but we'll also allow double click to hide completely?
    // User said "hideable by clicking", so let's toggle hidden if already minimized or just hide.
    if (el.classList.contains('minimized')) {
      el.hidden = true;
    } else {
      el.classList.add('minimized');
    }
  };

  if (gBridge.scanProgress) {
    gBridge.scanProgress.connect((fileName, percent) => {
      el.hidden = false;
      file.textContent = fileName;
      bar.style.width = `${percent}%`;
    });
  }

  if (gBridge.scanStarted) {
    gBridge.scanStarted.connect(() => {
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

function showCtx(x, y, item, idx, fromLightbox = false) {
  const ctx = document.getElementById('ctx');
  if (!ctx) return;

  gCtxItem = item;
  gCtxIndex = idx;
  gCtxFromLightbox = !!fromLightbox;

  const hideBtn = document.getElementById('ctxHide');
  const unhideBtn = document.getElementById('ctxUnhide');
  const renameBtn = document.getElementById('ctxRename');

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
  ['ctxHide', 'ctxUnhide', 'ctxRename', 'ctxDelete', 'ctxMeta', 'ctxExplorer', 'ctxCut', 'ctxCopy'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = hasItem ? 'block' : 'none';
  });

  // Bulk actions
  const selectAllBtn = document.getElementById('ctxSelectAll');
  if (selectAllBtn) selectAllBtn.style.display = hasItem ? 'none' : 'block';
  const clearSelectionBtn = document.getElementById('ctxSelectNone');
  if (clearSelectionBtn) clearSelectionBtn.style.display = (gSelectedPaths.size > 0) ? 'block' : 'none';

  // New folder is shown only when right-clicking background (no item)
  const newFolderBtn = document.getElementById('ctxNewFolder');
  if (newFolderBtn) newFolderBtn.style.display = hasItem ? 'none' : 'block';

  // Refine Hide/Unhide display
  if (hasItem) {
    const isHidden = item && item.path && item.path.split(/[/\\]/).pop().startsWith('.');
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

    if (gBridge && gBridge.debug_log) {
      gBridge.debug_log(`ctx mousedown: id=${btn.id} path=${item ? item.path : 'null'}`);
    }

    switch (btn.id) {
      case 'ctxExplorer':
        if (item && item.path && gBridge && gBridge.open_in_explorer) {
          gBridge.open_in_explorer(item.path);
        }
        break;
      case 'ctxHide':
        if (item && item.path && gBridge && gBridge.hide_by_renaming_dot_async) {
          if (fromLb) closeLightbox();
          setGlobalLoading(true, 'Hiding…', 25);
          gBridge.hide_by_renaming_dot_async(item.path, () => { });
        }
        break;
      case 'ctxUnhide':
        if (item && item.path && gBridge && gBridge.unhide_by_renaming_dot_async) {
          if (fromLb) closeLightbox();
          setGlobalLoading(true, 'Unhiding…', 25);
          gBridge.unhide_by_renaming_dot_async(item.path, () => { });
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
      case 'ctxMeta':
        if (item && item.path && gBridge && gBridge.show_metadata) {
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
        if (gBridge && gBridge.paste_into_folder_async && gSelectedFolders.length > 0) {
          const folder = gSelectedFolders[0];
          setGlobalLoading(true, 'Pasting…', 25);
          gBridge.paste_into_folder_async(folder);
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
    }
    hideCtx();
  });
}

// applySearch is no longer used for local filtering.

function renderMediaList(items, scrollToTop = true) {
  const el = document.getElementById('mediaList');
  if (!el) return;

  el.innerHTML = '';
  const main = document.querySelector('main');
  if (scrollToTop && main) {
    main.scrollTop = 0;
  }
  gMedia = Array.isArray(items) ? items : [];
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
    return;
  }

  if (viewItems.length === 0) {
    const div = document.createElement('div');
    div.className = 'empty';
    div.textContent = 'No results.';
    el.appendChild(div);
    return;
  }

  viewItems.forEach((item, idx) => {
    const card = document.createElement('div');
    card.className = 'card loading';
    card.tabIndex = 0;
    if (item.width && item.height) {
      card.style.aspectRatio = `${item.width} / ${item.height}`;
    }

    if (item.media_type === 'image') {
      const img = document.createElement('img');
      img.className = 'thumb';
      // Use IntersectionObserver to control src injection accurately,
      // avoiding browser's default loading="lazy" black-box behavior.
      img.setAttribute('data-src', item.url);
      img.alt = '';
      if (item.is_animated) {
        img.setAttribute('data-animated', 'true');
        img.setAttribute('data-path', item.path || '');
      }
      card.appendChild(img);
      gPosterObserver.observe(img);

      card.setAttribute('data-path', item.path || '');
      // ... rest of image listeners

      card.addEventListener('click', (e) => {
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
            const c = cards[i];
            const p = c.getAttribute('data-path');
            c.classList.add('selected');
            if (p) gSelectedPaths.add(p);
          }
        } else {
          deselectAll();
          card.classList.add('selected');
          gSelectedPaths.add(path);
          gLastSelectionIdx = idx;
        }

        gLockedCard = card;
        syncMetadataToBridge();
      });
      card.addEventListener('dblclick', () => openLightboxByIndex(idx));
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          openLightboxByIndex(idx);
        }
      });

      card.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        showCtx(e.clientX, e.clientY, item, idx, false);
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

        // 1. text/uri-list (for Explorer/External)
        e.dataTransfer.setData('text/uri-list', urls.join('\r\n'));

        // 2. text/plain (Fallback and internal)
        // We put JSON here too because WebEngine might drop custom types
        e.dataTransfer.setData('text/plain', pathsJson);

        // 3. custom formats (with web prefix for better compatibility)
        e.dataTransfer.setData('web/mmx-paths', pathsJson);
        e.dataTransfer.setData('application/x-mmx-type', 'file');

        if (window.qt && gBridge && gBridge.set_drag_paths) {
          gBridge.set_drag_paths(paths);
        }
        gCurrentDragCount = paths.length;

        e.dataTransfer.effectAllowed = 'copyMove';

        // Smaller Drag Thumbnail (64x64) offset to bottom-right of cursor
        const img = card.querySelector('img');
        if (img) {
          const canvas = document.createElement('canvas');
          canvas.width = 64;
          canvas.height = 64;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, 64, 64);
          // -10, -10 offset means the cursor is at roughly top-left of the 64x64 thumbnail
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
      });
    } else {
      // Video tile: lazy poster load only when near viewport.
      const img = document.createElement('img');
      img.className = 'thumb poster';
      img.alt = '';
      img.setAttribute('data-video-path', item.path || '');

      card.appendChild(img);

      // --- Simple Play Indicator ---
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
          gBridge.open_native_video_inplace(path, rect.x, rect.y, rect.width, rect.height, true, shouldLoop, true);
        } else {
          gBridge.open_native_video(path, true, false, true);
        }
      });

      if (item.path) {
        // Fallback for path string observation if img fails to exist
        gPosterObserver.observe(img);
      }

      card.setAttribute('data-path', item.path || '');
      // ... rest of video listeners

      card.addEventListener('click', (e) => {
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
            const c = cards[i];
            const p = c.getAttribute('data-path');
            c.classList.add('selected');
            if (p) gSelectedPaths.add(p);
          }
        } else {
          deselectAll();
          card.classList.add('selected');
          gSelectedPaths.add(path);
          gLastSelectionIdx = idx;
        }

        gLockedCard = card;
        syncMetadataToBridge();
      });
      card.addEventListener('dblclick', () => openLightboxByIndex(idx));
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          openLightboxByIndex(idx);
        }
      });

      card.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        showCtx(e.clientX, e.clientY, item, idx, false);
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

        const urls = paths.map(p => 'file:///' + p.replace(/\\/g, '/'));
        const pathsJson = JSON.stringify(paths);

        // 1. text/uri-list
        e.dataTransfer.setData('text/uri-list', urls.join('\r\n'));

        // 2. text/plain
        e.dataTransfer.setData('text/plain', pathsJson);

        // 3. custom formats
        e.dataTransfer.setData('web/mmx-paths', pathsJson);
        e.dataTransfer.setData('application/x-mmx-type', 'file');

        if (window.qt && gBridge && gBridge.set_drag_paths) {
          gBridge.set_drag_paths(paths);
        }
        gCurrentDragCount = paths.length;

        e.dataTransfer.effectAllowed = 'copyMove';

        if (img) {
          const canvas = document.createElement('canvas');
          canvas.width = 64;
          canvas.height = 64;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, 64, 64);
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
      });
    }

    el.appendChild(card);
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
      if (imgSrc) {
        gBackgroundQueue.push({ type: 'image', el: img, imgSrc });
      } else if (path) {
        gBackgroundQueue.push({ type: 'video', el: img, path });
      }
    });
    scheduleBackgroundDrain();
  });
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

  setupCustomSelect('sortSelect', (val) => {
    gSort = val;
    if (gBridge) refreshFromBridge(gBridge, true);
  });

  setupCustomSelect('filterSelect', (val) => {
    gFilter = val;
    gPage = 0; // Reset page on filter change
    if (gBridge) refreshFromBridge(gBridge, true);
  });
});

// Lazy poster loading for videos

let gLightboxNativeVideo = false;

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
      gBridge.get_video_duration_seconds(item.path, function (dur) {
        const seconds = Number(dur || 0);
        const loop = seconds > 0 && seconds < 60;
        // Always autoplay, always muted, loop only if short
        gBridge.open_native_video(item.path, true, loop, true);
      });
    }
    return;
  } else {
    vid.pause();
    vid.style.display = 'none';
    vid.src = '';
    img.style.display = 'block';
    img.src = item.url;
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
  openLightboxByIndex(gIndex - 1);
}
window.lightboxPrev = lightboxPrev;

function lightboxNext() {
  if (gMedia && gIndex >= 0 && gIndex < gMedia.length - 1) {
    openLightboxByIndex(gIndex + 1);
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
    setSelectedFolder(gSelectedFolders);

    if (gSelectedFolders.length === 0) {
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
      });
    });

    // ── 2. Background Enrichment Scan ────────────────────────────────────
    // This fills in hashes and metadata in the DB.
    bridge.start_scan(gSelectedFolders, gSearchQuery || '');
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
  const hideDotToggle = document.getElementById('toggleHideDot');
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

  if (hideDotToggle) {
    hideDotToggle.addEventListener('change', () => {
      if (!gBridge || !gBridge.set_setting_bool) return;
      gBridge.set_setting_bool('gallery.hide_dot', !!hideDotToggle.checked, function () {
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

  // Wire up Metadata toggles
  const metaToggles = [
    'metaShowRes', 'metaShowSize', 'metaShowDescription', 'metaShowTags', 'metaShowNotes',
    'metaShowCamera', 'metaShowLocation', 'metaShowISO',
    'metaShowShutter', 'metaShowAperture', 'metaShowSoftware', 'metaShowLens',
    'metaShowDPI', 'metaShowEmbeddedTags', 'metaShowEmbeddedComments',
    'metaShowEmbeddedTool', 'metaShowCombinedDB',
    'metaShowAIPrompt', 'metaShowAINegPrompt', 'metaShowAIParams',
    'metaShowSep1', 'metaShowSep2', 'metaShowSep3'
  ];
  metaToggles.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('change', () => {
        if (!gBridge || !gBridge.set_setting_bool) return;
        // Use lowercase for key compatibility with bridge (e.g. metaShowRes -> res)
        const key = `metadata.display.${id.replace('metaShow', '').toLowerCase()}`;
        gBridge.set_setting_bool(key, el.checked, function () {
          // Future: trigger metadata panel refresh if open
        });
      });
    }
  });

  wireSortableMetadata();
}

function wireSortableMetadata() {
  const list = document.getElementById('metaSortableList');
  if (!list) return;

  let dragItem = null;

  list.addEventListener('dragstart', (e) => {
    // Only allow dragging from the handle or if user clicks near it (to be simpler let's allow the whole item but handles look better)
    dragItem = e.target.closest('.sortable-item');
    if (dragItem) {
      dragItem.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
    }
  });

  list.addEventListener('dragend', (e) => {
    if (dragItem) {
      dragItem.classList.remove('dragging');
    }
    dragItem = null;
    document.querySelectorAll('.sortable-item').forEach(i => i.classList.remove('drag-over'));
    saveMetadataOrder();
  });

  list.addEventListener('dragover', (e) => {
    e.preventDefault();
    const target = e.target.closest('.sortable-item');
    if (target && target !== dragItem) {
      target.classList.add('drag-over');
    }
  });

  list.addEventListener('dragleave', (e) => {
    const target = e.target.closest('.sortable-item');
    if (target) {
      target.classList.remove('drag-over');
    }
  });

  list.addEventListener('drop', (e) => {
    e.preventDefault();
    const target = e.target.closest('.sortable-item');
    if (target && target !== dragItem) {
      const rect = target.getBoundingClientRect();
      const next = (e.clientY - rect.top) > (rect.height / 2);
      list.insertBefore(dragItem, next ? target.nextSibling : target);
    }
  });
}

function saveMetadataOrder() {
  const items = document.querySelectorAll('#metaSortableList .sortable-item');
  const order = Array.from(items).map(i => i.getAttribute('data-key'));
  if (gBridge && gBridge.set_setting_str) {
    gBridge.set_setting_str('metadata.display.order', JSON.stringify(order), () => { });
  }
}

function applyMetadataOrder(orderJson) {
  if (!orderJson) return;
  let order = [];
  try {
    order = typeof orderJson === 'string' ? JSON.parse(orderJson) : orderJson;
  } catch (e) { return; }

  if (!Array.isArray(order)) return;
  const list = document.getElementById('metaSortableList');
  if (!list) return;

  order.forEach(key => {
    const item = list.querySelector(`.sortable-item[data-key="${key}"]`);
    if (item) {
      list.appendChild(item);
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
      const rect = gPlayingInplaceCard.getBoundingClientRect();
      // If it scrolls off-screen, we might want to stop it, 
      // but let's first try just moving it.
      gBridge.update_native_video_rect(rect.x, rect.y, rect.width, rect.height);
    }
  });
}

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
        const text = document.getElementById('updateToastText');
        const statusText = document.getElementById('updateStatusText');

        if (newVer) {
          if (text) text.textContent = `Version ${newVer} is available!`;
          if (toast) toast.hidden = false;
          if (statusText) statusText.textContent = `Version ${newVer} available!`;
        } else if (manual) {
          if (statusText) statusText.textContent = 'You are using the latest version.';
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

    const btnUpdateLater = document.getElementById('btnUpdateLater');
    if (btnUpdateLater) {
      btnUpdateLater.addEventListener('click', () => {
        const toast = document.getElementById('updateToast');
        if (toast) toast.hidden = true;
      });
    }

    if (bridge.updateDownloadProgress) {
      bridge.updateDownloadProgress.connect(function (pct) {
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

      const hd = document.getElementById('toggleHideDot');
      if (hd) hd.checked = !!(s && s['gallery.hide_dot']);

      const sf = document.getElementById('startFolder');
      if (sf) sf.value = (s && s['gallery.start_folder']) || '';

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

      // Init new metadata toggles
      const metaToggles = [
        'metaShowRes', 'metaShowSize', 'metaShowDescription', 'metaShowTags', 'metaShowNotes',
        'metaShowCamera', 'metaShowLocation', 'metaShowISO',
        'metaShowShutter', 'metaShowAperture', 'metaShowSoftware', 'metaShowLens',
        'metaShowDPI', 'metaShowEmbeddedTags', 'metaShowEmbeddedComments',
        'metaShowEmbeddedTool', 'metaShowCombinedDB',
        'metaShowAIPrompt', 'metaShowAINegPrompt', 'metaShowAIParams',
        'metaShowSep1', 'metaShowSep2', 'metaShowSep3'
      ];
      metaToggles.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
          const key = `metadata.display.${id.replace('metaShow', '').toLowerCase()}`;
          // Default to checked if not set yet (optional, based on user preference)
          const val = s && s[key];
          if (val !== undefined) {
            el.checked = !!val;
          }
        }
      });

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

      // Load metadata order
      const order = s && s['metadata.display.order'];
      if (order) {
        applyMetadataOrder(order);
      }
    });

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
  });
}

main();
