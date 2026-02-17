/* global QWebChannel */

function setStatus(text) {
  const el = document.getElementById('status');
  if (el) el.textContent = text;
}

function setSelectedFolder(text) {
  const el = document.getElementById('selectedFolder');
  if (el) el.textContent = text || '(none)';
}

function ensurePosterObserver() {
  if (gPosterObserver) return;
  gPosterObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const el = entry.target;
        const path = el.getAttribute('data-video-path');
        if (!path) continue;
        if (gPosterRequested.has(path)) {
          gPosterObserver.unobserve(el);
          continue;
        }
        gPosterRequested.add(path);

        if (gBridge && gBridge.get_video_poster) {
          gBridge.get_video_poster(path, function (posterUrl) {
            if (posterUrl) {
              el.src = posterUrl;
            } else {
              el.removeAttribute('src');
              if (gBridge.debug_video_poster) {
                gBridge.debug_video_poster(path, function (info) {
                  console.log('debug_video_poster', info);
                });
              }
            }
          });
        }

        gPosterObserver.unobserve(el);
      }
    },
    {
      // Start loading slightly before visible so scrolling feels instant.
      root: null,
      rootMargin: '600px 0px 600px 0px',
      threshold: 0.01,
    }
  );
}

function resetPosterState() {
  gPosterRequested.clear();
  if (gPosterObserver) {
    gPosterObserver.disconnect();
    gPosterObserver = null;
  }
}

let gLoadingShownAt = 0;
const MIN_LOADING_MS = 1000;

function setGlobalLoading(on, text = 'Loading…', pct = null) {
  const gl = document.getElementById('globalLoading');
  const t = document.getElementById('loadingText');
  const b = document.getElementById('loadingBar');
  if (!gl || !t || !b) return;

  if (on) {
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

  // Delay hiding a bit so it's actually visible (prevents "never showed" when
  // operations complete extremely quickly).
  const elapsed = Date.now() - (gLoadingShownAt || Date.now());
  const wait = Math.max(0, MIN_LOADING_MS - elapsed);
  window.setTimeout(() => {
    gl.hidden = true;
  }, wait);
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
  const hideBtn = document.getElementById('ctxHide');
  const unhideBtn = document.getElementById('ctxUnhide');
  const renameBtn = document.getElementById('ctxRename');
  const metaBtn = document.getElementById('ctxMeta');
  const cancelBtn = document.getElementById('ctxCancel');

  if (cancelBtn) cancelBtn.addEventListener('click', hideCtx);
  window.addEventListener('click', (e) => {
    if (ctx && !ctx.hidden && !ctx.contains(e.target)) hideCtx();
  });
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') hideCtx();
  });

  if (hideBtn) {
    hideBtn.addEventListener('click', () => {
      const item = gCtxItem;
      const fromLb = gCtxFromLightbox;
      hideCtx();
      if (!item || !item.path || !gBridge || !gBridge.hide_by_renaming_dot_async) return;
      if (fromLb) closeLightbox();
      setGlobalLoading(true, 'Hiding…', 25);
      gBridge.hide_by_renaming_dot_async(item.path, function () { });
    });
  }

  if (unhideBtn) {
    unhideBtn.addEventListener('click', () => {
      const item = gCtxItem;
      const fromLb = gCtxFromLightbox;
      hideCtx();
      if (!item || !item.path || !gBridge || !gBridge.unhide_by_renaming_dot_async) return;
      if (fromLb) closeLightbox();
      setGlobalLoading(true, 'Unhiding…', 25);
      gBridge.unhide_by_renaming_dot_async(item.path, function () { });
    });
  }

  if (renameBtn) {
    renameBtn.addEventListener('click', () => {
      const item = gCtxItem;
      const fromLb = gCtxFromLightbox;
      hideCtx();
      if (!item || !item.path || !gBridge || !gBridge.rename_path_async) return;
      const curName = item.path.split(/[/\\]/).pop();
      const next = prompt('Rename to:', curName);
      if (!next || next === curName) return;
      if (fromLb) closeLightbox();
      setGlobalLoading(true, 'Renaming…', 25);
      gBridge.rename_path_async(item.path, next, function () { });
    });
  }

  if (metaBtn) {
    metaBtn.addEventListener('click', () => {
      const item = gCtxItem;
      hideCtx();
      if (!item || !item.path || !gBridge || !gBridge.show_metadata) return;
      gBridge.show_metadata(item.path, function () { });
    });
  }

  const explorerBtn = document.getElementById('ctxExplorer');
  if (explorerBtn) {
    explorerBtn.addEventListener('click', () => {
      const item = gCtxItem;
      hideCtx();
      if (!item || !item.path || !gBridge || !gBridge.open_in_explorer) return;
      gBridge.open_in_explorer(item.path);
    });
  }

  const cutBtn = document.getElementById('ctxCut');
  if (cutBtn) {
    cutBtn.addEventListener('click', () => {
      const item = gCtxItem;
      hideCtx();
      if (!item || !item.path || !gBridge || !gBridge.cut_to_clipboard) return;
      gBridge.cut_to_clipboard([item.path]);
    });
  }

  const copyBtn = document.getElementById('ctxCopy');
  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      const item = gCtxItem;
      hideCtx();
      if (!item || !item.path || !gBridge || !gBridge.copy_to_clipboard) return;
      gBridge.copy_to_clipboard([item.path]);
    });
  }

  const pasteBtn = document.getElementById('ctxPaste');
  if (pasteBtn) {
    pasteBtn.addEventListener('click', () => {
      hideCtx();
      if (!gBridge || !gBridge.paste_into_folder_async) return;
      gBridge.get_selected_folder(function (folder) {
        if (!folder) return;
        setGlobalLoading(true, 'Pasting…', 25);
        gBridge.paste_into_folder_async(folder);
      });
    });
  }

  const deleteBtn = document.getElementById('ctxDelete');
  if (deleteBtn) {
    deleteBtn.addEventListener('click', () => {
      const item = gCtxItem;
      hideCtx();
      if (!item || !item.path || !gBridge || !gBridge.delete_path) return;
      gBridge.delete_path(item.path, function (ok) {
        if (ok) refreshFromBridge(gBridge);
      });
    });
  }

  const newFolderBtn = document.getElementById('ctxNewFolder');
  if (newFolderBtn) {
    newFolderBtn.addEventListener('click', () => {
      hideCtx();
      const name = prompt('New Folder Name:');
      if (!name) return;
      if (!gBridge || !gBridge.create_folder || !gBridge.get_selected_folder) return;
      gBridge.get_selected_folder(function (folder) {
        if (!folder) return;
        gBridge.create_folder(folder, name, function (res) {
          if (res) refreshFromBridge(gBridge);
        });
      });
    });
  }
}

function applySearch(items) {
  const q = (gSearchQuery || '').trim().toLowerCase();
  if (!q) return items;
  return items.filter((it) => {
    const p = (it.path || '').toLowerCase();
    return p.includes(q);
  });
}

function renderMediaList(items) {
  const el = document.getElementById('mediaList');
  if (!el) return;

  el.innerHTML = '';
  gMedia = Array.isArray(items) ? items : [];

  const viewItems = applySearch(gMedia);

  resetPosterState();
  ensurePosterObserver();

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
    card.className = 'card';
    card.tabIndex = 0;

    if (item.media_type === 'image') {
      const sk = document.createElement('div');
      sk.className = 'skel';
      card.appendChild(sk);

      const img = document.createElement('img');
      img.className = 'thumb';
      img.loading = 'lazy';
      img.src = item.url;
      img.alt = '';
      img.addEventListener('load', () => sk.remove());
      img.addEventListener('error', () => sk.remove());
      card.appendChild(img);

      card.addEventListener('click', () => openLightboxByIndex(idx));
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') openLightboxByIndex(idx);
      });

      card.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        showCtx(e.clientX, e.clientY, item, idx, false);
      });
    } else {
      const sk = document.createElement('div');
      sk.className = 'skel';
      card.appendChild(sk);
      // Video tile: lazy poster load only when near viewport.
      const img = document.createElement('img');
      img.className = 'thumb poster';
      img.alt = '';
      img.setAttribute('data-video-path', item.path || '');
      img.addEventListener('load', () => sk.remove());
      img.addEventListener('error', () => sk.remove());
      card.appendChild(img);

      const badge = document.createElement('div');
      badge.className = 'videoBadge';
      badge.textContent = 'VIDEO';
      card.appendChild(badge);

      if (item.path) gPosterObserver.observe(img);

      card.addEventListener('click', () => openLightboxByIndex(idx));
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') openLightboxByIndex(idx);
      });

      card.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        showCtx(e.clientX, e.clientY, item, idx, false);
      });
    }

    el.appendChild(card);
  });

  // Enable background context menu for pasting into current folder
  el.addEventListener('contextmenu', (e) => {
    if (e.target === el) {
      e.preventDefault();
      showCtx(e.clientX, e.clientY, null, -1, false);
    }
  });
}

let gMedia = [];
let gIndex = -1;
let gBridge = null;
let gPage = 0;
let gTotal = 0;
const PAGE_SIZE = 100;

let gSearchQuery = '';

// Lazy poster loading for videos
let gPosterObserver = null;
const gPosterRequested = new Set();

let gLightboxNativeVideo = false;

function openLightboxByIndex(idx) {
  const lb = document.getElementById('lightbox');
  const img = document.getElementById('lightboxImg');
  const vid = document.getElementById('lightboxVideo');
  if (!lb || !img || !vid) return;

  // Stop native overlay ONLY if it was previously opened for a video.
  if (gLightboxNativeVideo && gBridge && gBridge.close_native_video) {
    gBridge.close_native_video(function () { });
  }
  gLightboxNativeVideo = false;

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
};

function lightboxPrev() {
  if (gIndex <= 0) return;
  openLightboxByIndex(gIndex - 1);
}

function lightboxNext() {
  if (gMedia && gIndex >= 0 && gIndex < gMedia.length - 1) {
    openLightboxByIndex(gIndex + 1);
  }
}

function wireLightbox() {
  const backdrop = document.getElementById('lightboxBackdrop');
  const img = document.getElementById('lightboxImg');
  const vid = document.getElementById('lightboxVideo');

  // Click outside closes (most clicks should hit backdrop because content has pointer-events:none)
  if (backdrop) backdrop.addEventListener('click', closeLightbox);
  if (img) img.addEventListener('click', (e) => e.stopPropagation());
  if (vid) vid.addEventListener('click', (e) => e.stopPropagation());

  // Right-click anywhere on the lightbox (including the image) opens the same context menu.
  // Use capture to avoid any odd event swallowing.
  const lb = document.getElementById('lightbox');
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

function refreshFromBridge(bridge) {
  bridge.get_selected_folder(function (folder) {
    setSelectedFolder(folder);
    if (!folder) {
      gTotal = 0;
      setGlobalLoading(false);
      renderMediaList([]);
      renderPager();
      return;
    }

    setGlobalLoading(true, 'Scanning media…', 15);

    bridge.count_media(folder, function (count) {
      gTotal = count || 0;
      const tp = totalPages();
      if (gPage >= tp) gPage = tp - 1;

      setGlobalLoading(true, `Loading page ${gPage + 1} of ${tp}…`, 55);

      bridge.list_media(folder, PAGE_SIZE, gPage * PAGE_SIZE, function (items) {
        renderMediaList(items);
        renderPager();
        // Hide after containers are painted at least once.
        requestAnimationFrame(() => setGlobalLoading(false));
      });
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

  if (openBtn) openBtn.addEventListener('click', openSettings);
  if (closeBtn) closeBtn.addEventListener('click', closeSettings);
  if (backdrop) backdrop.addEventListener('click', closeSettings);

  const startInput = document.getElementById('startFolder');
  const restoreToggle = document.getElementById('toggleRestoreLast');
  const hideDotToggle = document.getElementById('toggleHideDot');
  const leftToggle = document.getElementById('toggleLeftPanel');
  const rightToggle = document.getElementById('toggleRightPanel');
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

  if (leftToggle) {
    leftToggle.addEventListener('change', () => {
      if (!gBridge || !gBridge.set_setting_bool) return;
      gBridge.set_setting_bool('ui.show_left_panel', !!leftToggle.checked, function () { });
    });
  }

  if (rightToggle) {
    rightToggle.addEventListener('change', () => {
      if (!gBridge || !gBridge.set_setting_bool) return;
      gBridge.set_setting_bool('ui.show_right_panel', !!rightToggle.checked, function () { });
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
}

function wireSearch() {
  const inp = document.getElementById('searchInput');
  if (!inp) return;

  inp.addEventListener('input', () => {
    gSearchQuery = inp.value || '';
    // Re-render current page with filter applied.
    renderMediaList(gMedia);
  });
}

async function main() {
  wireLightbox();
  wirePager();
  wireSettings();
  wireCtxMenu();
  wireSearch();

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

    if (bridge.fileOpFinished) {
      bridge.fileOpFinished.connect(function (op, ok, oldPath, newPath) {
        // hide overlay regardless; refresh handles the rest.
        setGlobalLoading(false);
        if (ok) {
          refreshFromBridge(bridge);
        }
      });
    }

    bridge.get_tools_status(function (st) {
      setStatus('Ready');
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

      const lp = document.getElementById('toggleLeftPanel');
      if (lp) lp.checked = !!(s && s['ui.show_left_panel']);

      const rp = document.getElementById('toggleRightPanel');
      if (rp) rp.checked = !!(s && s['ui.show_right_panel']);

      const sf = document.getElementById('startFolder');
      if (sf) sf.value = (s && s['gallery.start_folder']) || '';

      const ac = document.getElementById('accentColor');
      const v = (s && s['ui.accent_color']) || '#8ab4f8';
      document.documentElement.style.setProperty('--accent', v);
      if (ac) ac.value = v;
    });

    // Initial sync
    refreshFromBridge(bridge);

    // React to future changes
    if (bridge.selectedFolderChanged) {
      bridge.selectedFolderChanged.connect(function () {
        gPage = 0;
        refreshFromBridge(bridge);
      });
    }
  });
}

main();
