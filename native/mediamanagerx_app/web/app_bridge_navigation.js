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

const THIS_PC_CRUMB_PATH = '__medialens_this_pc__';
let gCollapsedAddressCrumbs = [];

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
    const breadcrumbs = [{ label: 'This PC', path: THIS_PC_CRUMB_PATH, isThisPc: true }, { label: drive, path: `${drive}\\` }];
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

function folderTooltipName(path) {
  const normalized = normalizeFolderPath(path);
  if (!normalized) return '';
  const breadcrumbs = getFolderBreadcrumbs(normalized).filter(crumb => !crumb.isThisPc);
  if (breadcrumbs.length > 0) {
    return breadcrumbs[breadcrumbs.length - 1].label || normalized;
  }
  const parts = normalized.split('\\').filter(Boolean);
  return parts.length ? parts[parts.length - 1] : normalized;
}

function setNavButtonTooltip(button, baseText, enabled, targetPath = '') {
  if (!button) return;
  const targetName = enabled ? folderTooltipName(targetPath) : '';
  const text = targetName ? `${baseText} to ${targetName}` : baseText;
  button.title = text;
  button.setAttribute('aria-label', text);
}

function createFolderAddressChevron(title, onClick) {
  const chevron = document.createElement('button');
  chevron.className = 'folder-address-chevron';
  chevron.type = 'button';
  chevron.title = title;
  chevron.setAttribute('aria-haspopup', 'menu');
  chevron.setAttribute('aria-expanded', 'false');
  chevron.addEventListener('click', (e) => {
    e.stopPropagation();
    onClick(chevron);
  });
  return chevron;
}

function createFolderAddressSegment(crumb, index, isCurrent) {
  const btn = document.createElement('button');
  btn.className = 'folder-address-segment';
  if (crumb.isThisPc) btn.classList.add('this-pc');
  if (isCurrent) btn.classList.add('current');
  btn.type = 'button';
  btn.title = crumb.isThisPc ? 'This PC' : crumb.path;
  if (crumb.isThisPc) btn.setAttribute('aria-label', 'This PC');
  btn.dataset.path = crumb.path;
  btn.dataset.crumbIndex = String(index);

  if (crumb.isThisPc) {
    const icon = document.createElement('span');
    icon.className = 'folder-address-this-pc-icon';
    icon.setAttribute('aria-hidden', 'true');
    btn.appendChild(icon);
  }

  if (!crumb.isThisPc) {
    const label = document.createElement('span');
    label.className = 'folder-address-segment-label';
    label.textContent = crumb.label;
    btn.appendChild(label);
  }

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    if (crumb.isThisPc) {
      const firstChevron = document.querySelector('.folder-address-chevron[data-after-index="0"]');
      if (firstChevron) toggleFolderCrumbMenu(THIS_PC_CRUMB_PATH, firstChevron, 0);
      return;
    }
    openFolderItem(crumb.path);
  });
  return btn;
}

function createFolderAddressOverflowButton() {
  const btn = document.createElement('button');
  btn.className = 'folder-address-overflow';
  btn.type = 'button';
  btn.textContent = '...';
  btn.title = 'Show hidden path folders';
  btn.setAttribute('aria-haspopup', 'menu');
  btn.setAttribute('aria-expanded', 'false');
  btn.hidden = true;
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    const items = (gCollapsedAddressCrumbs || [])
      .filter((crumb) => crumb && crumb.path && !crumb.isThisPc)
      .map((crumb) => ({
        name: crumb.label,
        path: crumb.path,
      }));
    if (!items.length) return;
    openFolderCrumbMenu(items, btn, 0, null, '');
  });
  return btn;
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

function updateFolderAddressOverflow() {
  const address = document.getElementById('selectedFolder');
  if (!address || address.classList.contains('is-editing')) return;

  const overflow = address.querySelector('.folder-address-overflow');
  const segments = Array.from(address.querySelectorAll('.folder-address-segment[data-crumb-index]'));
  const chevrons = Array.from(address.querySelectorAll('.folder-address-chevron[data-after-index]'));
  const currentChildrenChevron = address.querySelector('.folder-address-chevron[data-current-children="true"]');
  if (!segments.length || !overflow) {
    gCollapsedAddressCrumbs = [];
    return;
  }

  segments.forEach((segment) => {
    segment.hidden = false;
    segment.classList.remove('allow-overflow-truncation');
  });
  chevrons.forEach((chevron) => {
    chevron.hidden = false;
  });
  overflow.hidden = true;
  gCollapsedAddressCrumbs = [];

  const crumbs = segments.map((segment) => ({
    label: segment.querySelector('.folder-address-segment-label')?.textContent || segment.textContent || '',
    path: segment.dataset.path || '',
    isThisPc: segment.dataset.path === THIS_PC_CRUMB_PATH,
  }));
  const hiddenIndexes = [];
  const collapsibleIndexes = [];
  for (let i = 1; i < segments.length; i += 1) {
    collapsibleIndexes.push(i);
  }
  const currentIndex = segments.length - 1;

  const applyHiddenIndexes = () => {
    segments.forEach((segment) => {
      const index = Number(segment.dataset.crumbIndex || -1);
      segment.hidden = hiddenIndexes.includes(index);
    });
    chevrons.forEach((chevron) => {
      const index = Number(chevron.dataset.afterIndex || -1);
      chevron.hidden = hiddenIndexes.includes(index);
    });
    if (currentChildrenChevron) {
      currentChildrenChevron.hidden = hiddenIndexes.includes(currentIndex);
    }
    gCollapsedAddressCrumbs = hiddenIndexes.map((index) => crumbs[index]).filter(Boolean);
    overflow.hidden = gCollapsedAddressCrumbs.length === 0;
  };

  while (address.scrollWidth > address.clientWidth + 1 && collapsibleIndexes.length > 0) {
    hiddenIndexes.push(collapsibleIndexes.shift());
    applyHiddenIndexes();
  }
}

function updateSelectedFolderLabelVisibility() {
  const address = document.getElementById('selectedFolder');
  const row = address ? address.closest('.kv') : null;
  if (!address || !row) return;
  row.style.flexBasis = '';
  updateFolderAddressOverflow();
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
  gCollapsedAddressCrumbs = [];
  crumbs.forEach((crumb, index) => {
    const btn = createFolderAddressSegment(crumb, index, index === crumbs.length - 1);
    el.appendChild(btn);

    if (index < crumbs.length - 1) {
      const chevron = createFolderAddressChevron(`Show folders under ${crumb.label}`, () => {
        toggleFolderCrumbMenu(crumb.path, chevron, 0);
      });
      chevron.dataset.afterIndex = String(index);
      el.appendChild(chevron);
      if (index === 0 && crumbs[0] && crumbs[0].isThisPc) {
        el.appendChild(createFolderAddressOverflowButton());
      }
    }
  });
  if (Array.isArray(gCurrentFolderChildren) && gCurrentFolderChildren.length > 0) {
    const chevron = createFolderAddressChevron('Show folders in the current folder', () => {
      toggleFolderCrumbMenu(currentPath, chevron, 0, gCurrentFolderChildren);
    });
    chevron.dataset.currentChildren = 'true';
    el.appendChild(chevron);
  }
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

window.hideFolderAddressMenus = function hideFolderAddressMenus() {
  closeFolderCrumbMenu();
};

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
    arrow.setAttribute('aria-hidden', 'true');

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
  setNavButtonTooltip(backBtn, 'Back', gNavState.canBack, state.backPath || '');
  setNavButtonTooltip(forwardBtn, 'Forward', gNavState.canForward, state.forwardPath || '');
  setNavButtonTooltip(upBtn, 'Up', gNavState.canUp, state.upPath || '');
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
  const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
  if (gAppMinimized || now < gAppRestoringUntil) {
    scheduleBackgroundDrain();
    return;
  }
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
  const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
  const delay = gAppMinimized ? 750 : Math.max(16, Math.ceil(gAppRestoringUntil - now));
  if (gAppMinimized || now < gAppRestoringUntil) {
    gBackgroundIdleId = setTimeout(flushBackgroundQueue, delay);
    return;
  }
  if (typeof requestIdleCallback !== 'undefined') {
    gBackgroundIdleId = requestIdleCallback(flushBackgroundQueue, { timeout: 500 });
  } else {
    gBackgroundIdleId = setTimeout(flushBackgroundQueue, 16);
  }
}

window.__mmx_setAppMinimized = function (minimized) {
  gAppRestoreGeneration += 1;
  const restoreGeneration = gAppRestoreGeneration;
  gAppMinimized = !!minimized;
  if (gBackgroundIdleId) {
    if (typeof cancelIdleCallback !== 'undefined') {
      try { cancelIdleCallback(gBackgroundIdleId); } catch (_) {}
    }
    clearTimeout(gBackgroundIdleId);
    gBackgroundIdleId = null;
  }
  if (gAppMinimized) {
    gAppRestoringUntil = 0;
    return;
  }
  const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
  gAppRestoringUntil = now + 900;
  scheduleBackgroundDrain();
  window.setTimeout(() => {
    if (restoreGeneration !== gAppRestoreGeneration || gAppMinimized) return;
    gAppRestoringUntil = 0;
    scheduleGalleryRelayout('restore');
    scheduleBackgroundDrain();
  }, 950);
};

function loadImage(el, imgSrc) {
  if (gPosterRequested.has(el)) return;
  gPosterRequested.add(el);
  el.onload = () => {
    gLoadedOnPage++;
    el.style.opacity = '1';
    const card = closestGalleryCard(el);
    if (card) markCardMediaReady(card);
  };
  el.onerror = () => {
    gLoadedOnPage++;
    const card = closestGalleryCard(el);
    const fallback = typeof createMediaErrorThumb === 'function'
      ? createMediaErrorThumb('Unsupported or corrupt image')
      : null;
    if (fallback && el.parentNode) {
      el.replaceWith(fallback);
    } else {
      el.style.opacity = '1';
    }
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
      const card = closestGalleryCard(el);
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
let gLastRenderedReviewSignature = '';

function setReviewResultsHidden(hidden) {
  const mediaList = document.getElementById('mediaList');
  if (!mediaList) return;
  if (hidden) {
    mediaList.classList.add('review-results-hidden');
  } else {
    mediaList.classList.remove('review-results-hidden');
  }
}

function computeReviewRenderSignature(items) {
  return (Array.isArray(items) ? items : [])
    .filter(item => item && !item.is_folder)
    .map(item => `${String(item.duplicate_group_key || '').trim()}::${String(item.path || '').trim()}::${Number(item.duplicate_group_position || 0)}`)
    .join('|');
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

function getReviewBuildStageText(stage = 'loading') {
  const mode = isDuplicateModeActive()
    ? String(gGroupBy || '').trim().toLowerCase()
    : '';
  const duplicateMode = mode === 'duplicates';
  const similarMode = mode === 'similar' || mode === 'similar_only';
  switch (stage) {
    case 'scan':
      return 'Scanning folder...';
    case 'group':
      if (duplicateMode) return 'Grouping duplicate files...';
      if (similarMode) return 'Finding similar files...';
      return 'Preparing review results...';
    case 'prepare':
      if (duplicateMode) return 'Preparing duplicate review cards...';
      if (similarMode) return 'Preparing similar review cards...';
      return 'Preparing review cards...';
    case 'render':
      return 'Rendering review results...';
    default:
      return 'Loading review results...';
  }
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
    const startedAt = Date.now();
    const maxWaitMs = 2500;
    const step = () => {
      if (!gReviewLoadingActive || generation !== gReviewLoadingGeneration) {
        resolve();
        return;
      }
      if (Date.now() - startedAt >= maxWaitMs) {
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

function footerProgressElements() {
  const el = document.getElementById('scanIndicator');
  const label = document.getElementById('scanLabel');
  const file = document.getElementById('scanFile');
  const bar = document.getElementById('scanBar');
  if (!el || !label || !file || !bar) return null;
  return { el, label, file, bar };
}

function setFooterProgress(owner, labelText, detailText, percent) {
  const parts = footerProgressElements();
  if (!parts) return false;
  gFooterProgressOwner = owner || '';
  parts.label.textContent = labelText || '';
  parts.file.textContent = detailText || '';
  parts.bar.style.width = `${Math.max(0, Math.min(100, Math.round(Number(percent || 0))))}%`;
  parts.el.hidden = false;
  return true;
}

function clearFooterProgress(owner) {
  const parts = footerProgressElements();
  if (!parts) return;
  if (owner && gFooterProgressOwner !== owner) return;
  gFooterProgressOwner = '';
  parts.el.hidden = true;
}

function wireScanIndicator() {
  const parts = footerProgressElements();
  if (!parts) return;
  const { el, file, bar } = parts;
  if (!el || !file || !bar) return;

  function render() {
    if (!gScanActive) {
      clearFooterProgress('scan');
      return;
    }
    if (gScanManuallyHidden) {
      clearFooterProgress('scan');
      return;
    }
    setFooterProgress('scan', 'Scanning:', file.textContent || '...', parseFloat(bar.style.width) || 0);
  }
  gRenderScanToast = render;

  el.onclick = () => {
    if (gFooterProgressOwner === 'text') {
      gTextProcessingDismissed = true;
      gTextProcessingForceVisible = false;
      if (gRenderTextProcessingToast) gRenderTextProcessingToast();
      return;
    }
    if (gFooterProgressOwner === 'scan') {
      gScanManuallyHidden = true;
      render();
      if (gRenderTextProcessingToast) gRenderTextProcessingToast();
    }
  };

  if (gBridge.scanProgress) {
    gBridge.scanProgress.connect((fileName, percent) => {
      if (!gScanActive) return;
      setFooterProgress('scan', 'Scanning:', fileName, percent);
      if (gReviewLoadingActive && isDuplicateModeActive()) {
        updateReviewLoadingProgress(
          10 + Math.round((Math.max(0, Math.min(100, Number(percent) || 0)) * 0.6)),
          getReviewBuildStageText('scan')
        );
      }
      render();
    });
  }

  if (gBridge.scanStarted) {
    gBridge.scanStarted.connect((folder) => {
      if (!acceptScanStartedForCurrentSelection(folder || '')) return;
      gScanToastGeneration += 1;
      gScanManuallyHidden = false;
      gScanActive = true;
      setFooterProgress('scan', 'Scanning:', 'Initializing...', 0);
      render();
      if (gRenderTextProcessingToast) gRenderTextProcessingToast();
    });
  }

  if (gBridge.scanFinished) {
    gBridge.scanFinished.connect((folder) => {
      if (!scanFolderMatchesCurrentSelection(folder || '')) return;
      const finishedGeneration = gScanToastGeneration;
      setFooterProgress('scan', 'Scanning:', 'Finished', 100);
      render();
      setTimeout(() => {
        if (finishedGeneration !== gScanToastGeneration) {
          if (gRenderScanToast) gRenderScanToast();
          return;
        }
        gScanActive = false;
        gAwaitingScanResults = false;
        if (gRenderScanToast) gRenderScanToast();
        if (gRenderTextProcessingToast) gRenderTextProcessingToast();
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
      const card = closestGalleryCard(el);
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
      clearFooterProgress('text');
      el.hidden = true;
      return;
    }
    const allowVisible = isTextFilterActive() || gTextProcessingForceVisible;
    if (!allowVisible || gTextProcessingDismissed) {
      clearFooterProgress('text');
      el.hidden = true;
      return;
    }
    const displayLabel = gTextProcessingWaiting
      ? (gTextProcessingStage || 'Detecting Text')
      : gTextProcessingPaused
      ? `${gTextProcessingStage || 'Detecting Text'} (Paused)`
      : (gTextProcessingStage || 'Detecting Text');
    label.textContent = displayLabel;
    let detailText = 'Starting...';
    let progressPercent = 0;
    if (gTextProcessingTotal > 0) {
      detailText = `${gTextProcessingCurrent} / ${gTextProcessingTotal}`;
      progressPercent = Math.max(0, Math.min(100, Math.round((gTextProcessingCurrent / gTextProcessingTotal) * 100)));
    } else {
      detailText = 'Starting...';
      progressPercent = 0;
    }
    file.textContent = detailText;
    bar.style.width = `${progressPercent}%`;
    const useFooter = !gScanActive && !gScanManuallyHidden;
    if (useFooter && setFooterProgress('text', `${displayLabel}:`, detailText, progressPercent)) {
      el.hidden = true;
    } else {
      el.hidden = false;
      if (gFooterProgressOwner === 'text') clearFooterProgress('text');
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

