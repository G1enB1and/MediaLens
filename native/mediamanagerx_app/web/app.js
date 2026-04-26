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
    if (!closestGalleryCard(e.target)) {
      deselectAll();
      syncMetadataToBridge();
    }
  });

  main.addEventListener('contextmenu', (e) => {
    // If we right-click the background
    if (!closestGalleryCard(e.target)) {
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
        const previousSingleMode = isComparePanelReviewSingleMode();
        const previousGroupKey = compareReviewGroupKeyFromState() || String(gReviewSingleGroupKey || '');
        gCompareState = state || { visible: false, left: {}, right: {}, best_path: '', keep_paths: [], delete_paths: [] };
        const selectionRevision = Number(gCompareState && gCompareState.selection_revision);
        if (Number.isFinite(selectionRevision) && selectionRevision !== gLastCompareSelectionRevision) {
          gLastCompareSelectionRevision = selectionRevision;
        }
        maybeSeedCompareStateFromReview();
        const nextSingleMode = isComparePanelReviewSingleMode();
        const nextGroupKey = compareReviewGroupKeyFromState() || String(gReviewSingleGroupKey || '');
        if (isDuplicateModeActive() && (previousSingleMode !== nextSingleMode || (nextSingleMode && previousGroupKey !== nextGroupKey))) {
          gLastGalleryRenderSignature = '';
          renderMediaList(gMedia, false);
        }
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
        const statusText = document.getElementById('updateStatusText');
        if (newVer) {
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
      });
    }



    if (bridge.fileOpFinished) {
      bridge.fileOpFinished.connect(function (op, ok, oldPath, newPath) {
        setGlobalLoading(false);
        if (!ok) return;

        if (op === 'rename' && oldPath && newPath) {
          // ── In-place patch: update the card's data-path without reordering the gallery ──
          const oldCard = queryGalleryCardByPath(oldPath);
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
          // Stale-folder scanFinished (e.g. a prior in-flight scan completing
          // after the user changed scope, or Phase 3 finishing with zero
          // progress emissions). Clear scan-active so the toast can dismiss —
          // any newer scan still in flight will re-raise it via its own
          // scanStarted. Only skip the gallery refresh, not the flag reset.
          gScanActive = false;
          gAwaitingScanResults = false;
          if (gRenderScanToast) gRenderScanToast();
          return;
        }
        const currentReviewSignature = isDuplicateModeActive() ? computeReviewRenderSignature(gMedia) : '';
        if (isDuplicateModeActive() && currentReviewSignature) {
          gScanActive = false;
          gAwaitingScanResults = false;
          gTotal = count || gTotal || 0;
          refreshGalleryFileCountChip();
          if (gRenderScanToast) gRenderScanToast();
          return;
        }
        if (isDuplicateModeActive() && gReviewLoadingActive && !gAwaitingScanResults) {
          gScanActive = false;
          if (gRenderScanToast) gRenderScanToast();
          return;
        }
        if (isDuplicateModeActive() && !gReviewLoadingActive && !gAwaitingScanResults && Array.isArray(gMedia) && gMedia.length > 0) {
          gScanActive = false;
          gTotal = count || gTotal || 0;
          refreshGalleryFileCountChip();
          if (gRenderScanToast) gRenderScanToast();
          return;
        }
        if (gReviewLoadingActive && isDuplicateModeActive()) {
          updateReviewLoadingProgress(76, getReviewBuildStageText('group'));
        }
        gScanActive = false;
        gAwaitingScanResults = false;
        gTotal = count || 0;
        if (gRenderScanToast) gRenderScanToast();
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
      gIncludeNestedFiles = !s || s['gallery.include_nested_files'] !== false;
      gShowFoldersInGallery = !s || s['gallery.show_folders'] !== false;
      syncGalleryScopeToggles();

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

    if (bridge.mediaFileCounted) {
      bridge.mediaFileCounted.connect(function (requestId, count) {
        const pending = gPendingMediaFileCountRequests.get(requestId);
        if (!pending) return;
        gPendingMediaFileCountRequests.delete(requestId);
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

    if (bridge.galleryFilterSensitiveMetadataChanged) {
      bridge.galleryFilterSensitiveMetadataChanged.connect(function () {
        scheduleFilterSensitiveMetadataRefresh();
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
          const previousSingleMode = isComparePanelReviewSingleMode();
          gCompareState = Object.assign({}, gCompareState || {}, { visible: !!value });
          updateSidebarButtonIcons('bottom', !!value);
          if (isDuplicateModeActive() && previousSingleMode !== isComparePanelReviewSingleMode()) {
            gLastGalleryRenderSignature = '';
            renderMediaList(gMedia, false);
          } else {
            scheduleGalleryRelayout('ui.show_bottom_panel');
          }
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
        if (key === 'gallery.show_hidden' || key === 'gallery.include_nested_files' || key === 'gallery.show_folders' || key === 'gallery.view_mode' || key === 'gallery.group_by' || key === 'gallery.group_date_granularity' || key === 'gallery.similarity_threshold') {
          if (key === 'gallery.show_hidden') {
            gShowHidden = !!value;
            refreshAdvancedCollections();
          }
          if (key === 'gallery.include_nested_files') {
            gIncludeNestedFiles = !!value;
            syncGalleryScopeToggles();
          }
          if (key === 'gallery.show_folders') {
            gShowFoldersInGallery = !!value;
            syncGalleryScopeToggles();
          }
          if (key === 'gallery.view_mode' && bridge.get_settings) {
            bridge.get_settings(function (s) {
              gCachedSettings = s || {};
              applyGalleryViewMode((s && s['gallery.view_mode']) || 'masonry');
              const nextGroupBy = (s && s['gallery.group_by']) || 'none';
              gGroupBy = ['date', 'duplicates', 'similar', 'similar_only'].includes(nextGroupBy) ? nextGroupBy : 'none';
              gGroupDateGranularity = (s && s['gallery.group_date_granularity']) || 'day';
              gSimilarityThreshold = (s && s['gallery.similarity_threshold']) || 'low';
              gIncludeNestedFiles = !s || s['gallery.include_nested_files'] !== false;
              gShowFoldersInGallery = !s || s['gallery.show_folders'] !== false;
              syncGalleryScopeToggles();
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
