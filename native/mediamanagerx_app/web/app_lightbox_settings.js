let gIndex = -1;
let gLightboxNativeVideo = false;
let gLightboxPerformanceSuspended = false;
let gLightboxImageZoom = 1;
let gLightboxImagePanX = 0;
let gLightboxImagePanY = 0;
let gLightboxImageDrag = null;
let gLightboxImageSuppressClick = false;

function pauseGalleryAnimatedImagesForLightbox() {
  document.querySelectorAll('main img[data-animated="true"][src]').forEach((img) => {
    if (img.hasAttribute('data-lightbox-paused-src')) return;
    const src = img.getAttribute('src') || '';
    if (!src) return;
    img.setAttribute('data-lightbox-paused-src', src);
    img.removeAttribute('src');
  });
}

function resumeGalleryAnimatedImagesAfterLightbox() {
  document.querySelectorAll('img[data-lightbox-paused-src]').forEach((img) => {
    const src = img.getAttribute('data-lightbox-paused-src') || '';
    img.removeAttribute('data-lightbox-paused-src');
    if (src) img.setAttribute('src', src);
  });
}

function suspendLightboxBackgroundWork() {
  if (gLightboxPerformanceSuspended) return;
  gLightboxPerformanceSuspended = true;
  pauseGalleryAnimatedImagesForLightbox();
  if (gBridge && gBridge.pause_lightbox_background_work) {
    gBridge.pause_lightbox_background_work();
  }
}

function resumeLightboxBackgroundWork() {
  if (!gLightboxPerformanceSuspended) return;
  gLightboxPerformanceSuspended = false;
  resumeGalleryAnimatedImagesAfterLightbox();
  if (gBridge && gBridge.resume_lightbox_background_work) {
    gBridge.resume_lightbox_background_work();
  }
}

function resetLightboxImagePanZoom() {
  gLightboxImageZoom = 1;
  gLightboxImagePanX = 0;
  gLightboxImagePanY = 0;
  gLightboxImageDrag = null;
  gLightboxImageSuppressClick = false;
  applyLightboxImagePanZoom();
}

function lightboxImageContentRect() {
  const img = document.getElementById('lightboxImg');
  const content = img ? img.closest('.lightbox-content') : null;
  return content ? content.getBoundingClientRect() : null;
}

function lightboxImageRenderedSize() {
  const img = document.getElementById('lightboxImg');
  const rect = lightboxImageContentRect();
  if (!img || !rect || !img.naturalWidth || !img.naturalHeight) {
    return rect ? { width: rect.width, height: rect.height } : { width: 0, height: 0 };
  }
  const scale = Math.min(rect.width / img.naturalWidth, rect.height / img.naturalHeight);
  return {
    width: img.naturalWidth * scale,
    height: img.naturalHeight * scale,
  };
}

function clampLightboxImagePan() {
  const rect = lightboxImageContentRect();
  if (!rect || gLightboxImageZoom <= 1.001) {
    gLightboxImageZoom = 1;
    gLightboxImagePanX = 0;
    gLightboxImagePanY = 0;
    return;
  }
  const rendered = lightboxImageRenderedSize();
  const maxX = Math.max(0, (rendered.width * gLightboxImageZoom - rect.width) / 2);
  const maxY = Math.max(0, (rendered.height * gLightboxImageZoom - rect.height) / 2);
  gLightboxImagePanX = Math.max(-maxX, Math.min(maxX, gLightboxImagePanX));
  gLightboxImagePanY = Math.max(-maxY, Math.min(maxY, gLightboxImagePanY));
}

function applyLightboxImagePanZoom() {
  const img = document.getElementById('lightboxImg');
  if (!img) return;
  clampLightboxImagePan();
  img.style.transform = `translate(${gLightboxImagePanX}px, ${gLightboxImagePanY}px) scale(${gLightboxImageZoom})`;
  img.classList.toggle('is-zoomed', gLightboxImageZoom > 1.001);
  img.classList.toggle('is-panning', !!gLightboxImageDrag);
}

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
  document.body.classList.add('lightbox-open');
  suspendLightboxBackgroundWork();
  if (item.media_type === 'video') {
    resetLightboxImagePanZoom();
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
    resetLightboxImagePanZoom();
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
  resetLightboxImagePanZoom();

  vid.pause();
  vid.src = '';
  vid.style.display = 'none';


  if (!gClosingFromNative && gBridge && gBridge.close_native_video) {
    gBridge.close_native_video(function () { });
  }

  gIndex = -1;
  document.body.style.overflow = '';
  resumeLightboxBackgroundWork();
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

  if (img) {
    img.addEventListener('wheel', (e) => {
      if (img.style.display === 'none') return;
      const rect = lightboxImageContentRect();
      if (!rect) return;
      e.preventDefault();
      e.stopPropagation();
      const oldZoom = gLightboxImageZoom;
      const step = e.deltaY < 0 ? 1.15 : (1 / 1.15);
      const nextZoom = Math.max(1, Math.min(12, oldZoom * step));
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      const cursorX = e.clientX - centerX;
      const cursorY = e.clientY - centerY;
      const sceneX = (cursorX - gLightboxImagePanX) / oldZoom;
      const sceneY = (cursorY - gLightboxImagePanY) / oldZoom;
      gLightboxImageZoom = nextZoom;
      if (gLightboxImageZoom <= 1.001) {
        gLightboxImageZoom = 1;
        gLightboxImagePanX = 0;
        gLightboxImagePanY = 0;
      } else {
        gLightboxImagePanX = cursorX - sceneX * gLightboxImageZoom;
        gLightboxImagePanY = cursorY - sceneY * gLightboxImageZoom;
      }
      applyLightboxImagePanZoom();
    }, { passive: false });

    img.addEventListener('pointerdown', (e) => {
      if (gLightboxImageZoom <= 1.001 || e.button !== 0) return;
      e.preventDefault();
      e.stopPropagation();
      gLightboxImageDrag = {
        pointerId: e.pointerId,
        startX: e.clientX,
        startY: e.clientY,
        panX: gLightboxImagePanX,
        panY: gLightboxImagePanY,
      };
      gLightboxImageSuppressClick = false;
      img.setPointerCapture(e.pointerId);
      applyLightboxImagePanZoom();
    });

    img.addEventListener('pointermove', (e) => {
      if (!gLightboxImageDrag || gLightboxImageDrag.pointerId !== e.pointerId) return;
      e.preventDefault();
      e.stopPropagation();
      const dx = e.clientX - gLightboxImageDrag.startX;
      const dy = e.clientY - gLightboxImageDrag.startY;
      if (Math.abs(dx) > 2 || Math.abs(dy) > 2) gLightboxImageSuppressClick = true;
      gLightboxImagePanX = gLightboxImageDrag.panX + dx;
      gLightboxImagePanY = gLightboxImageDrag.panY + dy;
      applyLightboxImagePanZoom();
    });

    img.addEventListener('pointerup', (e) => {
      if (!gLightboxImageDrag || gLightboxImageDrag.pointerId !== e.pointerId) return;
      e.preventDefault();
      e.stopPropagation();
      try {
        img.releasePointerCapture(e.pointerId);
      } catch (_) { }
      gLightboxImageDrag = null;
      applyLightboxImagePanZoom();
    });

    img.addEventListener('pointercancel', (e) => {
      if (!gLightboxImageDrag || gLightboxImageDrag.pointerId !== e.pointerId) return;
      gLightboxImageDrag = null;
      applyLightboxImagePanZoom();
    });

    img.addEventListener('click', (e) => {
      if (gLightboxImageZoom > 1.001 || gLightboxImageSuppressClick) {
        e.preventDefault();
        e.stopPropagation();
        gLightboxImageSuppressClick = false;
      }
    });
  }

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

  window.addEventListener('resize', () => {
    if (!lb || lb.hidden) return;
    applyLightboxImagePanZoom();
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
        navigateToGalleryPage(p - 1);
      });
      links.appendChild(btn);

      last = p;
    }
  });
}

function navigateToGalleryPage(pageIndex) {
  if (!gBridge) return;
  const tp = totalPages();
  const nextPageIndex = Math.max(0, Math.min(tp - 1, Number(pageIndex) || 0));
  if (nextPageIndex === gPage) return;
  gPage = nextPageIndex;
  gPendingScrollAnchor = null;
  const main = document.querySelector('main');
  if (main) main.scrollTop = 0;
  refreshFromBridge(gBridge);
}

function refreshFromBridge(bridge, resetPage = false) {
  if (!bridge) return;
  const preserveScroll = prepareGalleryScrollPreservationForRefresh(resetPage);
  const refreshToken = ++gRefreshGeneration;
  const consumeSelectAllAfterRefresh = function () {
    if (!gSelectAllAfterRefresh) return;
    gSelectAllAfterRefresh = false;
    selectAll();
  };
  bridge.get_selected_folders(function (folders) {
    if (refreshToken !== gRefreshGeneration) return;
    gSelectedFolders = asArray(folders);
    bridge.get_active_collection(function (activeCollection) {
      if (refreshToken !== gRefreshGeneration) return;
      gActiveCollection = activeCollection && activeCollection.id ? activeCollection : null;
      setSelectedFolder(gSelectedFolders, gActiveCollection);

      if (gSelectedFolders.length === 0 && !gActiveCollection) {
        gNoFolderSelected = true;
        gTotal = 0;
        gLastRequestedFullScanKey = '';
        gLastGalleryRenderSignature = '';
        gSelectAllAfterRefresh = false;
        updateGalleryCountChip(0);
        if (gReviewLoadingActive) endReviewLoading();
        else setGlobalLoading(false);
        renderMediaList([]);
        renderPager();
        return;
      }
      gNoFolderSelected = false;

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

      const currentReviewSignature = duplicateMode ? computeReviewRenderSignature(gMedia) : '';
      if (duplicateMode && shouldShowScanWaitingEmptyState() && !currentReviewSignature) {
        gTotal = 0;
        updateGalleryCountChip(0);
        renderMediaList([], !preserveScroll);
        renderPager();
        if (gReviewLoadingActive) updateReviewLoadingProgress(15, getReviewBuildStageText('scan'));
        else setGlobalLoading(true, 'Scanning folder...', 10);
        ensureFullFolderScanRequested(bridge, gSelectedFolders, gSearchQuery || '');
        return;
      }

      if (duplicateMode) {
        if (gReviewLoadingActive) updateReviewLoadingProgress(76, getReviewBuildStageText('group'));
        fetchMediaList(gSelectedFolders, MAX_GALLERY_FETCH_LIMIT, 0, gSort, gFilter, gSearchQuery || '').then(function (items) {
          if (refreshToken !== gRefreshGeneration) return;
          const reviewSignature = computeReviewRenderSignature(items);
          if (gReviewLoadingActive && shouldShowScanWaitingEmptyState() && !currentReviewSignature) {
            updateReviewLoadingProgress(76, getReviewBuildStageText('group'));
            return;
          }
          gTotal = Array.isArray(items) ? items.length : 0;
          refreshGalleryFileCountChip();
          if (!gReviewLoadingActive && reviewSignature && reviewSignature === gLastRenderedReviewSignature) {
            consumeSelectAllAfterRefresh();
            renderPager();
            setGlobalLoading(false);
            return;
          }
          if (gReviewLoadingActive) updateReviewLoadingProgress(90, getReviewBuildStageText('prepare'));
          renderMediaList(items, !preserveScroll);
          consumeSelectAllAfterRefresh();
          renderPager();
          const reviewLoadingGeneration = gReviewLoadingGeneration;
          requestAnimationFrame(() => {
            if (refreshToken !== gRefreshGeneration) return;
            const mediaList = document.getElementById('mediaList');
            prioritizeVisibleMediaLoads(mediaList);
            if (gReviewLoadingActive) updateReviewLoadingProgress(96, getReviewBuildStageText('render'));
            waitForInitialReviewCards(mediaList, reviewLoadingGeneration).then(() => {
              if (refreshToken !== gRefreshGeneration) return;
              if (gReviewLoadingActive) {
                updateReviewLoadingProgress(100, getReviewBuildStageText('render'));
                endReviewLoading(reviewLoadingGeneration);
              } else {
                setGlobalLoading(false);
              }
            });
          });
          if (bridge.start_scan_paths) {
            bridge.start_scan_paths(asArray(items).filter(item => !item.is_folder).map(item => item.path).filter(Boolean));
          }
        });
        return;
      }

      const limit = useInfinite ? Math.max(PAGE_SIZE, gMedia.length || PAGE_SIZE) : PAGE_SIZE;
      const offset = useInfinite ? 0 : gPage * PAGE_SIZE;
      fetchMediaList(gSelectedFolders, limit, offset, gSort, gFilter, gSearchQuery || '').then(function (items) {
        if (refreshToken !== gRefreshGeneration) return;
        renderMediaList(items, !preserveScroll);
        consumeSelectAllAfterRefresh();
        renderPager();
        if (useInfinite) requestAnimationFrame(() => maybeLoadMoreInfiniteResults());
        // Hide the "Starting..." or "Loading..." overlay once we have the first batch of results.
        setGlobalLoading(false);
        if (bridge.start_scan_paths) {
          bridge.start_scan_paths(asArray(items).filter(item => !item.is_folder).map(item => item.path).filter(Boolean));
        }
        fetchMediaCount(gSelectedFolders, gFilter, gSearchQuery || '').then(function (count) {
          if (refreshToken !== gRefreshGeneration) return;
          gTotal = count || 0;
          refreshGalleryFileCountChip();
          renderPager();
        });
      });

    // ── 2. Background Enrichment Scan ────────────────────────────────────
    // This fills in hashes and metadata in the DB.
    ensureFullFolderScanRequested(bridge, gSelectedFolders, gSearchQuery || '');
    });
  });
}

function scheduleFilterSensitiveMetadataRefresh() {
  if (!gBridge) return;
  if (gGalleryFilterMetadataRefreshTimer) {
    clearTimeout(gGalleryFilterMetadataRefreshTimer);
  }
  gGalleryFilterMetadataRefreshTimer = window.setTimeout(() => {
    gGalleryFilterMetadataRefreshTimer = 0;
    refreshFromBridge(gBridge, false);
  }, 60);
}

function nextPage() {
  navigateToGalleryPage(gPage + 1);
}

function prevPage() {
  navigateToGalleryPage(gPage - 1);
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

function syncGalleryScopeToggles() {
  const settingsNestedToggle = document.getElementById('toggleIncludeNestedFiles');
  const settingsFoldersToggle = document.getElementById('toggleShowFoldersInGallery');
  const headerNestedToggle = document.getElementById('headerIncludeNestedFiles');
  if (settingsNestedToggle) settingsNestedToggle.checked = !!gIncludeNestedFiles;
  if (settingsFoldersToggle) settingsFoldersToggle.checked = !!gShowFoldersInGallery;
  if (headerNestedToggle) headerNestedToggle.checked = !!gIncludeNestedFiles;
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
  const toggleIncludeNestedFiles = document.getElementById('toggleIncludeNestedFiles');
  const toggleShowFoldersInGallery = document.getElementById('toggleShowFoldersInGallery');
  const headerIncludeNestedFiles = document.getElementById('headerIncludeNestedFiles');
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

  const applyIncludeNestedFilesSetting = (checked) => {
    if (!gBridge || !gBridge.set_setting_bool) return;
    gIncludeNestedFiles = !!checked;
    syncGalleryScopeToggles();
    gBridge.set_setting_bool('gallery.include_nested_files', gIncludeNestedFiles, function () {
      gPage = 0;
      refreshFromBridge(gBridge);
    });
  };

  if (toggleIncludeNestedFiles) {
    toggleIncludeNestedFiles.addEventListener('change', () => {
      applyIncludeNestedFilesSetting(!!toggleIncludeNestedFiles.checked);
    });
  }

  if (headerIncludeNestedFiles) {
    headerIncludeNestedFiles.addEventListener('change', () => {
      applyIncludeNestedFilesSetting(!!headerIncludeNestedFiles.checked);
    });
  }

  if (toggleShowFoldersInGallery) {
    toggleShowFoldersInGallery.addEventListener('change', () => {
      if (!gBridge || !gBridge.set_setting_bool) return;
      gShowFoldersInGallery = !!toggleShowFoldersInGallery.checked;
      syncGalleryScopeToggles();
      gBridge.set_setting_bool('gallery.show_folders', gShowFoldersInGallery, function () {
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
  asArray(cfg.groupOrder).forEach(key => { if (!order.includes(key)) order.push(key); });
  return order.filter(key => cfg.groups && cfg.groups[key]);
}

function getMetadataFieldOrder(settings, mode, groupKey) {
  const cfg = metadataConfigFor(mode);
  const groupCfg = cfg.groups && cfg.groups[groupKey] ? cfg.groups[groupKey] : { fields: [] };
  const defaults = asArray(groupCfg.fields).map(([key]) => key);
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
    const fieldMap = Object.fromEntries(asArray(groupCfg.fields).map(field => [field[0], field]));
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

