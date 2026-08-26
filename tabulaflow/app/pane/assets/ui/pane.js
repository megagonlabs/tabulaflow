// @ts-check

import { renderTable } from './render/table.js';
import { renderChart } from './render/chart.js';
import { renderMap } from './render/map.js';
import { renderGraph } from './render/graph.js';
import { renderQuery } from './render/query.js';
import { renderMarkdown } from './render/markdown.js';
import { artifactIconSpecs, wireCopyButton } from './render/shared.js';

function el(tag, cls) {
  var e = document.createElement(tag);
  if (cls) { e.className = cls; }
  return e;
}

function hasText(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function setFavicon() {
  var svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" shape-rendering="crispEdges">'
    + '<rect width="64" height="64" fill="#283629"/>'
    + '<rect x="8" y="0" width="48" height="14" fill="#3EB489"/>'
    + '<rect x="8" y="14" width="48" height="14" fill="#121212"/>'
    + '<rect x="25" y="14" width="14" height="36" fill="#3EB489"/>'
    + '<rect x="25" y="50" width="14" height="14" fill="#121212"/>'
    + '</svg>';
  var link = document.querySelector('link[rel="icon"]');
  if (!link) {
    link = document.createElement('link');
    link.rel = 'icon';
    document.head.appendChild(link);
  }
  link.type = 'image/svg+xml';
  link.href = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
}

function applyPageStatus(status) {
  document.title = status === 'ready' ? '◆ tabulaflow' : 'tabulaflow';
}

function startPageStatus() {
  setFavicon();
  applyPageStatus('idle');
  window.addEventListener('focus', function () {
    applyPageStatus('idle');
  });
}

function moveThumb(thumb, opt) {
  thumb.style.width = opt.offsetWidth + 'px';
  thumb.style.transform = 'translateX(' + opt.offsetLeft + 'px)';
}

function syncSegment(seg) {
  var thumb = seg ? seg.querySelector('.seg-thumb') : null;
  var opt = seg ? seg.querySelector('.seg-opt.active') : null;
  if (thumb && opt) { moveThumb(thumb, opt); }
}

function balancedTabRows(widths, available, gap) {
  var rowCount = 1;
  var used = 0;
  for (var i = 0; i < widths.length; i++) {
    if (widths[i] > available) return null;
    var next = used ? used + gap + widths[i] : widths[i];
    if (used && next > available + 0.5) {
      rowCount++;
      used = widths[i];
    } else {
      used = next;
    }
  }
  if (rowCount === 1) return null;

  var costs = Array.from({ length: rowCount + 1 }, function () {
    return Array(widths.length + 1).fill(Infinity);
  });
  var breaks = Array.from({ length: rowCount + 1 }, function () {
    return Array(widths.length + 1).fill(-1);
  });
  costs[0][0] = 0;
  for (var row = 1; row <= rowCount; row++) {
    for (var end = row; end <= widths.length; end++) {
      used = 0;
      for (var start = end - 1; start >= row - 1; start--) {
        used = widths[start] + (used ? gap + used : 0);
        if (used > available + 0.5) break;
        var remainder = available - used;
        var cost = costs[row - 1][start] + remainder * remainder;
        if (cost < costs[row][end]) {
          costs[row][end] = cost;
          breaks[row][end] = start;
        }
      }
    }
  }

  var rows = [];
  var end = widths.length;
  for (row = rowCount; row > 0; row--) {
    var start = breaks[row][end];
    if (start < 0) return null;
    rows.unshift([start, end]);
    end = start;
  }
  return rows;
}

function resetTabWidths(tabs) {
  tabs.querySelectorAll('.rectab').forEach(function (item) { item.style.removeProperty('flex'); });
  tabs.classList.remove('full-width');
  tabs.parentElement.classList.remove('full-width-tabs');
}

function layoutTabs(tabs, forceFullWidth) {
  var items = Array.from(tabs.querySelectorAll('.rectab'));
  resetTabWidths(tabs);
  if (items.length < 2) return;

  var style = getComputedStyle(tabs);
  var available = tabs.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
  var gap = parseFloat(style.columnGap) || 0;
  var widths = items.map(function (item) { return item.getBoundingClientRect().width; });
  var rows = balancedTabRows(widths, available, gap);
  if (!forceFullWidth && !rows) return;

  tabs.classList.add('full-width');
  tabs.parentElement.classList.add('full-width-tabs');
  available = tabs.clientWidth;
  rows = balancedTabRows(widths, available, gap) || [[0, items.length]];

  rows.forEach(function (bounds) {
    var count = bounds[1] - bounds[0];
    var used = widths.slice(bounds[0], bounds[1]).reduce(function (sum, width) { return sum + width; }, 0);
    var extra = (available - used - gap * (count - 1)) / count;
    for (var i = bounds[0]; i < bounds[1]; i++) {
      items[i].style.flex = '0 0 ' + (widths[i] + extra) + 'px';
    }
  });
}

function syncCardHeader(bar) {
  if (!bar || !bar.classList.contains('multi-card') || !bar.offsetWidth) return;
  var tabs = bar.querySelector('.rectabs');
  var slot = bar.querySelector('.view-slot');
  if (!tabs) return;
  resetTabWidths(tabs);
  if (!slot) {
    bar.classList.remove('stacked');
    layoutTabs(tabs, false);
    return;
  }
  bar.classList.remove('stacked');
  var gap = parseFloat(getComputedStyle(bar).columnGap || getComputedStyle(bar).gap || '0') || 0;
  var required = tabs.scrollWidth + slot.offsetWidth + gap;
  if (required > bar.clientWidth + 1) bar.classList.add('stacked');
  if (bar.classList.contains('stacked')) layoutTabs(tabs, true);
  syncSegment(slot.querySelector('.seg:not(.view-slot-measure)'));
}

window.addEventListener('resize', function () {
  requestAnimationFrame(function () {
    document.querySelectorAll('.cardbar.multi-card').forEach(syncCardHeader);
  });
});

function buildMessage(role, text, codeBlocks) {
  var msg = el('div', 'message ' + role);
  var label = el('div', 'message-label');
  var body = el('div', 'message-body');
  label.textContent = role === 'user' ? 'user' : 'tabulaflow';
  if (role === 'assistant') renderMarkdown(body, text, codeBlocks);
  else body.textContent = text;
  msg.appendChild(label);
  msg.appendChild(body);
  return msg;
}

function buildTranscript(turn) {
  var wrap = el('section', 'transcript');
  if (hasText(turn.user)) wrap.appendChild(buildMessage('user', turn.user));
  if (hasText(turn.assistant)) wrap.appendChild(buildMessage('assistant', turn.assistant, turn.assistantCodeBlocks || []));
  return wrap.children.length ? wrap : null;
}

function answerControls(turn) {
  var panel = turn && turn.panel;
  var controls = panel && Array.isArray(panel.controls) ? panel.controls : [];
  return controls.filter(function (control) {
    return control && (
      (control.kind === 'choice' && Array.isArray(control.choices) && control.choices.length) ||
      (control.kind === 'number' && isFiniteNumber(control.min) && isFiniteNumber(control.max) && isFiniteNumber(control.step))
    );
  });
}

function isFiniteNumber(value) {
  return typeof value === 'number' && Number.isFinite(value);
}

function controlNumberValue(control, selection) {
  var raw = selection && selection[control.id];
  var value = typeof raw === 'number' ? raw : Number(raw);
  if (!Number.isFinite(value)) value = isFiniteNumber(control.default) ? control.default : control.min;
  return Math.min(control.max, Math.max(control.min, value));
}

function formatNumberControlValue(control, value) {
  var text = String(value);
  return control.unit ? text + ' ' + control.unit : text;
}

function updateNumberControl(input, value) {
  var control = input._tfControl;
  var progress = 100 * (value - control.min) / (control.max - control.min);
  input.value = String(value);
  input.style.setProperty('--answer-control-progress', progress + '%');
  input._tfValueLabel.textContent = formatNumberControlValue(control, value);
}

function updateAnswerControls(panel, state) {
  panel.querySelectorAll('.answer-control-option').forEach(function (btn) {
    var active = String(state.selection[btn._tfControlId]) === String(btn._tfChoiceId);
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-pressed', active ? 'true' : 'false');
  });
  panel.querySelectorAll('.answer-control-number-input').forEach(function (input) {
    if (document.activeElement === input) return;
    var value = controlNumberValue(input._tfControl, state.selection);
    updateNumberControl(input, value);
  });
  if (state.resolving) panel.setAttribute('aria-busy', 'true');
  else panel.removeAttribute('aria-busy');
  var status = panel.querySelector('.answer-control-status');
  status.classList.toggle('error', !!state.resolveError);
  status.textContent = state.resolving ? 'Updating results…' : (state.resolveError || '');
}

function applyControlSelection(turn, state, index, id, value) {
  var next = Object.assign({}, state.selection);
  if (String(next[id]) === String(value)) return;
  next[id] = value;
  state.selection = next;
  resolveTurnSelection(turn, index, Object.assign({}, state.selection));
}

function defaultSelection(turn) {
  var panel = turn && turn.panel;
  return Object.assign({}, panel && panel.default_selection ? panel.default_selection : {});
}

function sameSelection(a, b) {
  var ak = Object.keys(a || {}).sort();
  var bk = Object.keys(b || {}).sort();
  if (ak.length !== bk.length) return false;
  for (var i = 0; i < ak.length; i++) {
    if (ak[i] !== bk[i] || String(a[ak[i]]) !== String(b[bk[i]])) return false;
  }
  return true;
}

function resolveTurnSelection(turn, index, selection) {
  if (turn.id == null) return;
  var state = getTurnState(turn, index);
  var seq = (state.resolveSeq || 0) + 1;
  state.resolveSeq = seq;
  if (state.resolveTimer) window.clearTimeout(state.resolveTimer);
  state.resolving = false;
  state.resolveError = '';
  refreshActiveTurnControls(index);
  setActiveTurnArtifactsLoading(index, false);
  state.resolveTimer = window.setTimeout(function () {
    if (state.resolveSeq !== seq) return;
    state.resolving = true;
    refreshActiveTurnControls(index);
    setActiveTurnArtifactsLoading(index, true);
  }, ANSWER_LOADING_DELAY_MS);
  fetch('resolve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ turn_id: turn.id, selection: selection })
  }).then(function (response) {
    if (!response.ok) throw new Error('resolve failed');
    return response.json();
  }).then(function (payload) {
    if (state.resolveSeq !== seq || !sameSelection(selection, state.selection || {})) return;
    if (state.resolveTimer) window.clearTimeout(state.resolveTimer);
    state.resolveTimer = null;
    turn.cards = Array.isArray(payload.cards) ? payload.cards : [];
    state.activeCard = Math.min(state.activeCard || 0, Math.max(turn.cards.length - 1, 0));
    state.resolving = false;
    refreshActiveTurnControls(index);
    refreshActiveTurnArtifacts(index);
  }).catch(function () {
    if (state.resolveSeq !== seq) return;
    if (state.resolveTimer) window.clearTimeout(state.resolveTimer);
    state.resolveTimer = null;
    state.resolving = false;
    state.resolveError = 'Could not update results for this selection.';
    refreshActiveTurnControls(index);
    setActiveTurnArtifactsLoading(index, false);
  });
}

function buildAnswerControls(turn, state, index) {
  var controls = answerControls(turn);
  if (!controls.length) return null;
  if (!state.selection) state.selection = defaultSelection(turn);
  var panel = el('section', 'answer-controls');
  controls.forEach(function (control) {
    var group = el('div', 'answer-control');
    var label = el('div', 'answer-control-label');
    label.textContent = control.label || control.id;
    group.appendChild(label);
    if (control.kind === 'choice') {
      var opts = el('div', 'answer-control-options');
      control.choices.forEach(function (choice) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'answer-control-option';
        btn.textContent = choice.label || choice.id;
        btn._tfControlId = control.id;
        btn._tfChoiceId = choice.id;
        btn.onclick = function () {
          if (String(state.selection[control.id]) === String(choice.id)) return;
          applyControlSelection(turn, state, index, control.id, choice.id);
        };
        opts.appendChild(btn);
      });
      group.appendChild(opts);
    } else if (control.kind === 'number') {
      var row = el('div', 'answer-control-number');
      var input = document.createElement('input');
      input.type = 'range';
      input.className = 'answer-control-number-input';
      input.min = String(control.min);
      input.max = String(control.max);
      input.step = String(control.step);
      input.setAttribute('aria-label', control.label || control.id);
      var value = controlNumberValue(control, state.selection);
      var valueLabel = el('output', 'answer-control-number-value');
      input._tfControl = control;
      input._tfValueLabel = valueLabel;
      updateNumberControl(input, value);
      input.oninput = function () {
        var live = Number(input.value);
        if (Number.isFinite(live)) updateNumberControl(input, live);
      };
      input.onchange = function () {
        var nextValue = Number(input.value);
        if (!Number.isFinite(nextValue)) return;
        nextValue = Math.min(control.max, Math.max(control.min, nextValue));
        updateNumberControl(input, nextValue);
        applyControlSelection(turn, state, index, control.id, nextValue);
      };
      input.onkeydown = function (event) {
        if (event.key === 'Enter') input.dispatchEvent(new Event('change'));
      };
      row.appendChild(input);
      row.appendChild(valueLabel);
      group.appendChild(row);
    }
    panel.appendChild(group);
  });
  var status = el('div', 'answer-control-status');
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  panel.appendChild(status);
  updateAnswerControls(panel, state);
  return panel;
}

function activeTurnView(index) {
  if (index !== activeTurn) return null;
  var inner = document.getElementById('content-inner');
  return inner ? inner.querySelector('.turnview') : null;
}

function refreshActiveTurnControls(index) {
  var turnView = activeTurnView(index);
  if (!turnView) return;
  var turn = turns[index];
  var state = getTurnState(turn, index);
  var current = turnView.querySelector('.answer-controls');
  if (current) {
    if (answerControls(turn).length) updateAnswerControls(current, state);
    else current.remove();
    return;
  }
  var next = buildAnswerControls(turn, state, index);
  if (next) {
    var artifacts = turnView.querySelector('.artifacts-region');
    if (artifacts) turnView.insertBefore(next, artifacts);
    else turnView.appendChild(next);
  }
}

function renderArtifactsInto(region, turn, state) {
  deactivateViewTree(region, true);
  region.replaceChildren();
  region.removeAttribute('aria-busy');
  var cards = turn.cards || [];
  if (!cards.length) {
    trimCache();
    return;
  }
  if (cards.length <= 1) {
    region.appendChild(buildCard(cards[0], { state: state, cardIndex: 0 }));
    return;
  }
  var box = el('div', 'panesbox');
  box.appendChild(buildMultiCard(cards, state));
  region.appendChild(box);
}

function refreshActiveTurnArtifacts(index) {
  var turnView = activeTurnView(index);
  if (!turnView) return;
  var region = turnView.querySelector('.artifacts-region');
  if (!region) return;
  var turn = turns[index];
  renderArtifactsInto(region, turn, getTurnState(turn, index));
}

function setActiveTurnArtifactsLoading(index, loading) {
  var turnView = activeTurnView(index);
  if (!turnView) return;
  var region = turnView.querySelector('.artifacts-region');
  if (!region) return;
  if (loading) region.setAttribute('aria-busy', 'true');
  else region.removeAttribute('aria-busy');
}

function isManualPreview(turn) {
  return turn.source === 'manual' && (turn.cards || []).length === 1;
}

function buildManualArtifactTitle(turn) {
  var title = el('div', 'manual-artifact-title');
  title.textContent = turn.title || 'table preview';
  return title;
}

var MANUAL_TURN_ICON = [
  ['circle', { cx: '12', cy: '8', r: '3' }],
  ['path', { d: 'M6 19c.7-3.2 2.8-5 6-5s5.3 1.8 6 5' }]
];

function artifactCounts(turn) {
  var counts = { map: 0, graph: 0, chart: 0, table: 0 };
  var order = [];
  (turn.cards || []).forEach(function (card) {
    var kinds = card.views || [];
    var kind = null;
    if (kinds.indexOf('map') !== -1) kind = 'map';
    else if (kinds.indexOf('graph') !== -1) kind = 'graph';
    else if (kinds.indexOf('chart') !== -1) kind = 'chart';
    else if (kinds.indexOf('data') !== -1) kind = 'table';
    if (!kind) return;
    if (counts[kind] === 0) order.push(kind);
    counts[kind] += 1;
  });
  return { counts: counts, order: order };
}

function artifactLabel(kind, count) {
  return count + ' ' + (count === 1 ? kind : kind + 's');
}

function turnMeta(turn) {
  var summary = artifactCounts(turn);
  var counts = summary.counts;
  if (turn.source === 'manual' && counts.table === 1 && counts.chart === 0 && counts.map === 0 && counts.graph === 0) {
    return { text: '', items: [{ kind: 'table', count: 1, label: 'table preview' }], label: 'table preview' };
  }
  var items = [];
  summary.order.forEach(function (kind) {
    if (counts[kind]) items.push({ kind: kind, count: counts[kind], label: artifactLabel(kind, counts[kind]) });
  });
  return { text: '', items: items, label: items.map(function (item) { return item.label; }).join(' · ') };
}

function buildMetaIcon(kind) {
  var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('aria-hidden', 'true');
  (artifactIconSpecs[kind] || []).forEach(function (spec) {
    var node = document.createElementNS('http://www.w3.org/2000/svg', spec[0]);
    Object.keys(spec[1]).forEach(function (key) { node.setAttribute(key, spec[1][key]); });
    svg.appendChild(node);
  });
  return svg;
}

function buildManualTurnIcon() {
  var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('aria-hidden', 'true');
  MANUAL_TURN_ICON.forEach(function (spec) {
    var node = document.createElementNS('http://www.w3.org/2000/svg', spec[0]);
    Object.keys(spec[1]).forEach(function (key) { node.setAttribute(key, spec[1][key]); });
    svg.appendChild(node);
  });
  return svg;
}

function buildTurnMeta(metaData) {
  var meta = el('div', 'turnmeta');
  if (metaData.text) {
    meta.textContent = metaData.text;
    return meta;
  }
  meta.classList.add('turnmeta-icons');
  meta.setAttribute('aria-label', metaData.label);
  metaData.items.forEach(function (item) {
    var badge = el('span', 'turnmeta-item');
    badge.title = item.label;
    badge.appendChild(buildMetaIcon(item.kind));
    if (item.count > 1) {
      var count = el('span', 'turnmeta-count');
      count.textContent = String(item.count);
      badge.appendChild(count);
    }
    meta.appendChild(badge);
  });
  return meta;
}

function buildTurnItem(turn, index, displayIndex) {
  var it = el('div', 'turnitem');
  var idx = el('div', 'turnindex');
  var text = el('div', 'turntext');
  var title = el('div', 'turntitle');
  title.textContent = turn.title || ('Turn ' + (index + 1));
  if (isManualPreview(turn)) {
    idx.classList.add('manual-turnindex');
    idx.title = 'Manual preview · row ' + String(index + 1).padStart(2, '0');
    idx.setAttribute('aria-label', idx.title);
    idx.appendChild(buildManualTurnIcon());
  } else {
    idx.textContent = String(displayIndex).padStart(2, '0');
  }
  var metaData = turnMeta(turn);
  it.title = metaData.label ? title.textContent + ' · ' + metaData.label : title.textContent;
  text.appendChild(title);
  if (metaData.label) text.appendChild(buildTurnMeta(metaData));
  it.appendChild(idx);
  it.appendChild(text);
  return it;
}

function buildCardTabs(cards, activeIndex, onSelect) {
  var tabs = el('div', 'rectabs');
  cards.forEach(function (card, i) {
    var tab = el('button', 'rectab');
    tab.textContent = card.label || ('result ' + (i + 1));
    tab.title = tab.textContent;
    tab.classList.toggle('active', i === activeIndex);
    tab.onclick = function () { onSelect(i); };
    tabs.appendChild(tab);
  });
  return tabs;
}

function buildViewSwitcher(views, activeKind, showView) {
  var seg = el('div', 'seg');
  var thumb = el('span', 'seg-thumb');
  var opts = [];
  seg.appendChild(thumb);
  views.forEach(function (kind) {
    var opt = el('button', 'seg-opt');
    opt.textContent = kind;
    opt.dataset.kind = kind;
    opt.classList.toggle('active', kind === activeKind);
    opt.onclick = function () { showView(kind, opt); };
    opts.push(opt);
    seg.appendChild(opt);
  });
  requestAnimationFrame(function () {
    syncSegment(seg);
    requestAnimationFrame(function () { thumb.classList.add('ready'); });
  });
  return { seg: seg, thumb: thumb, opts: opts };
}

function buildViewSlot(cards) {
  var slot = el('div', 'view-slot');
  var menus = new Map();
  cards.forEach(function (card) {
    var views = card.views || [];
    if (views.length > 1) menus.set(views.join('\u0000'), views);
  });
  menus.forEach(function (views) {
    var measure = el('div', 'seg view-slot-measure');
    views.forEach(function (kind) {
      var opt = el('span', 'seg-opt');
      opt.textContent = kind;
      measure.appendChild(opt);
    });
    slot.appendChild(measure);
  });
  return menus.size ? slot : null;
}

function viewOptionForKind(switcher, kind) {
  if (!switcher) return null;
  for (var i = 0; i < switcher.opts.length; i++) {
    if (switcher.opts[i].dataset.kind === kind) return switcher.opts[i];
  }
  return null;
}

var turns = [];
var activeTurn = -1;
var cardDataCache = {};
var viewCache = {};
var navState = {};
var lru = [];
var CACHE_WEIGHT_LIMIT = 24;
var LOADING_DELAY_MS = 120;
var ANSWER_LOADING_DELAY_MS = 220;
var suppressScrollMemory = false;
var scrollRestoreVersion = 0;
var activeTurnTransition = null;
var agentTurnCount = 0;

function turnStateKey(turn, index) {
  return String(turn.id == null ? index : turn.id);
}

function getTurnState(turn, index) {
  var key = turnStateKey(turn, index);
  if (!navState[key]) navState[key] = { key: key, activeCard: 0, views: {}, scrollTop: 0 };
  return navState[key];
}

function cardStateKey(card, cardIndex) {
  return card.artifact_id || card.id || String(cardIndex);
}

function viewStateKey(state, card, cardIndex, kind) {
  return state.key + ':' + cardStateKey(card, cardIndex) + ':' + kind;
}

function savedViewKind(state, card, cardIndex, views) {
  var saved = state.views[cardStateKey(card, cardIndex)];
  if (saved && views.indexOf(saved) !== -1) return saved;
  return views[0] || 'data';
}

function rememberViewKind(state, card, cardIndex, kind) {
  state.views[cardStateKey(card, cardIndex)] = kind;
}

function contentScroller() {
  return document.getElementById('content');
}

function rememberTurnScroll(state) {
  var scroller = contentScroller();
  if (!state || !scroller) return;
  state.scrollTop = scroller.scrollTop;
}

function restoreTurnScroll(state) {
  var version = ++scrollRestoreVersion;
  var scroller = contentScroller();
  if (!state || !scroller) {
    suppressScrollMemory = false;
    return Promise.resolve();
  }
  var scrollTop = state.scrollTop || 0;
  suppressScrollMemory = true;
  return new Promise(function (resolve) {
    requestAnimationFrame(function () {
      if (version !== scrollRestoreVersion) {
        resolve();
        return;
      }
      scroller.scrollTop = scrollTop;
      requestAnimationFrame(function () {
        if (version !== scrollRestoreVersion) {
          resolve();
          return;
        }
        scroller.scrollTop = scrollTop;
        requestAnimationFrame(function () {
          if (version === scrollRestoreVersion) suppressScrollMemory = false;
          resolve();
        });
      });
    });
  });
}

function restoreTurnScrollImmediately(state) {
  var version = ++scrollRestoreVersion;
  var scroller = contentScroller();
  if (!state || !scroller) {
    suppressScrollMemory = false;
    return;
  }
  suppressScrollMemory = true;
  scroller.scrollTop = state.scrollTop || 0;
  queueMicrotask(function () {
    if (version === scrollRestoreVersion) suppressScrollMemory = false;
  });
}

function rememberActiveContentScroll() {
  if (suppressScrollMemory) return;
  if (activeTurn < 0 || activeTurn >= turns.length) return;
  var turn = turns[activeTurn];
  var state = getTurnState(turn, activeTurn);
  rememberTurnScroll(state);
}

function watchContentScroll() {
  var scroller = contentScroller();
  if (!scroller) return;
  scroller.addEventListener('scroll', rememberActiveContentScroll, { passive: true });
}

function graphCacheWeight(entry) {
  var graph = entry && entry.data && entry.data.graph;
  var elements = graph && graph.elements;
  var nodes = elements && Array.isArray(elements.nodes) ? elements.nodes.length : 0;
  var edges = elements && Array.isArray(elements.edges) ? elements.edges.length : 0;
  return nodes > 50 || edges > 150 ? 6 : 3;
}

function cacheEntryWeight(entry) {
  if (!entry) return 0;
  if (entry.kind === 'map') return 6;
  if (entry.kind === 'graph') return graphCacheWeight(entry);
  return 1;
}

function cacheWeight() {
  var total = 0;
  for (var i = 0; i < lru.length; i++) {
    var entry = viewCache[lru[i]];
    if (entry && !entry.ownerShell) total += cacheEntryWeight(entry);
  }
  return total;
}

function trimCache() {
  while (cacheWeight() > CACHE_WEIGHT_LIMIT) {
    var index = lru.findIndex(function (key) {
      var entry = viewCache[key];
      return entry && !entry.ownerShell;
    });
    if (index === -1) return;
    var evict = lru.splice(index, 1)[0];
    var entry = viewCache[evict];
    if (!entry) continue;
    gateDeactivate(entry);
    if (entry.handle && entry.handle.destroy) entry.handle.destroy();
    if (entry.node && entry.node.parentNode) entry.node.parentNode.removeChild(entry.node);
    delete viewCache[evict];
  }
}

function cacheTouch(key) {
  var idx = lru.indexOf(key);
  if (idx !== -1) lru.splice(idx, 1);
  lru.push(key);
  trimCache();
}

function fetchCardData(card) {
  var cached = cardDataCache[card.id];
  if (cached) return cached.promise;
  cached = { data: null, promise: null };
  cached.promise = fetch(card.id + '.data.json').then(function (response) {
    if (!response.ok) throw new Error('HTTP ' + response.status);
    return response.json();
  }).then(function (data) {
    cached.data = data;
    return data;
  });
  cardDataCache[card.id] = cached;
  return cached.promise;
}

function getCachedCardData(card) {
  var cached = cardDataCache[card.id];
  return cached && cached.data ? cached.data : null;
}

function renderKind(node, kind, data) {
  if (kind === 'message') return renderMessage(node, data);
  if (kind === 'map') return renderMap(node, data);
  if (kind === 'graph') return renderGraph(node, data);
  if (kind === 'chart') return renderChart(node, data);
  if (kind === 'data') return renderTable(node, data);
  if (kind === 'query') return renderQuery(node, data);
  node.textContent = 'Unknown view: ' + kind;
  return { destroy: function () {} };
}

function renderMessage(node, data) {
  var message = data && data.message && typeof data.message === 'object' ? data.message : {};
  var status = ['error', 'not_applicable', 'no_result'].indexOf(message.status) === -1 ? 'error' : message.status;
  var tone = status === 'error' ? 'error' : 'info';
  node.className = 'tf-view tf-message-view tone-' + tone;
  var box = el('div', 'tf-message-card');
  var label = el('div', 'tf-message-label');
  label.textContent = status === 'error' ? 'Could not render artifact' : (status === 'no_result' ? 'No result' : 'Not applicable');
  var text = el('div', 'tf-message-text');
  text.textContent = typeof message.text === 'string' && message.text ? message.text : 'No message available.';
  box.appendChild(label);
  box.appendChild(text);
  node.appendChild(box);
  return { destroy: function () {} };
}

function measurable(node, requires) {
  if (!node || !node.isConnected) return false;
  var rect = node.getBoundingClientRect();
  if (requires && requires.width && !(rect.width > 0)) return false;
  if (requires && requires.height && !(rect.height > 0)) return false;
  return true;
}

function cancelGateFrame(entry) {
  if (entry && entry.gateFrame != null) {
    window.cancelAnimationFrame(entry.gateFrame);
    entry.gateFrame = null;
  }
}

function runGate(entry) {
  if (!entry || !entry.gated || !entry.handle || !entry.handle.mount) return;
  var handle = entry.handle;
  var requires = handle.requires || {};
  if (!entry.mounted) {
    if (!measurable(entry.node, requires)) {
      if (!entry.observer) scheduleGateCheck(entry);
      return;
    }
    entry.mounted = true;
    handle.mount();
    return;
  }
  if (handle.resize) handle.resize();
}

function scheduleGateCheck(entry) {
  cancelGateFrame(entry);
  if (!entry || !entry.gated) return;
  entry.gateFrame = window.requestAnimationFrame(function () {
    entry.gateFrame = null;
    runGate(entry);
  });
}

function gateActivate(entry) {
  if (!entry || !entry.handle || !entry.handle.mount || entry.gated) return;
  entry.gated = true;
  if (window.ResizeObserver) {
    entry.observer = new ResizeObserver(function () { runGate(entry); });
    entry.observer.observe(entry.node);
  }
  scheduleGateCheck(entry);
}

function gateDeactivate(entry) {
  if (!entry) return;
  cancelGateFrame(entry);
  if (entry.observer) {
    entry.observer.disconnect();
    entry.observer = null;
  }
  entry.gated = false;
}

function claimEntry(entry, shell) {
  entry.ownerShell = shell;
}

function releaseEntry(entry) {
  if (!entry) return;
  entry.ownerShell = null;
}

function deactivateViewTree(root, deferTrim) {
  if (!root) return;
  root.querySelectorAll('.view-shell').forEach(function (shell) {
    cancelShellLoading(shell);
    shell._tfPendingEntry = null;
  });
  root.querySelectorAll('.tf-view').forEach(function (node) {
    gateDeactivate(node._tfViewEntry);
    releaseEntry(node._tfViewEntry);
  });
  if (!deferTrim) trimCache();
}

function setActiveShellView(shell, activeNode) {
  Array.prototype.forEach.call(shell.children, function (node) {
    if (!node.classList.contains('tf-view')) return;
    var active = node === activeNode;
    node.classList.toggle('view-active', active);
    node.classList.toggle('view-hidden', !active);
    node.classList.remove('view-pending');
    node.toggleAttribute('inert', !active);
    node.setAttribute('aria-hidden', active ? 'false' : 'true');
    if (active) {
      claimEntry(node._tfViewEntry, shell);
      gateActivate(node._tfViewEntry);
    } else {
      gateDeactivate(node._tfViewEntry);
      releaseEntry(node._tfViewEntry);
    }
  });
  trimCache();
}

function shellLoadingState(shell) {
  var state = shell.querySelector('.view-loading-state');
  if (state) return state;
  state = el('div', 'view-loading-state');
  state.setAttribute('role', 'status');
  state.setAttribute('aria-live', 'polite');
  state.hidden = true;
  shell.appendChild(state);
  return state;
}

function cancelShellLoading(shell) {
  if (shell._tfLoadingTimer == null) return;
  window.clearTimeout(shell._tfLoadingTimer);
  shell._tfLoadingTimer = null;
}

function revealShellLoading(shell, entry) {
  if (entry.ownerShell !== shell || viewCache[shell.dataset.activeViewKey] !== entry) return;
  Array.prototype.forEach.call(shell.children, function (node) {
    if (!node.classList.contains('tf-view') || node._tfViewEntry === entry) return;
    hideViewNode(node);
    releaseEntry(node._tfViewEntry);
  });
  trimCache();
  var state = shellLoadingState(shell);
  state.textContent = 'Loading ' + entry.kind + '\u2026';
  state.hidden = false;
  shell.className = 'view-shell view-' + entry.kind + ' view-loading';
  renderViewMeta(shell._tfMeta, null);
}

function stageShellEntry(shell, entry) {
  var samePendingEntry = shell._tfPendingEntry === entry;
  if (!samePendingEntry) cancelShellLoading(shell);
  shell._tfPendingEntry = entry;
  var activeNode = shell.querySelector('.tf-view.view-active');
  var loadingVisible = shell.classList.contains('view-loading');
  Array.prototype.forEach.call(shell.children, function (node) {
    if (!node.classList.contains('tf-view') || node._tfViewEntry === entry) return;
    if (node.classList.contains('view-pending')) {
      hideViewNode(node);
      releaseEntry(node._tfViewEntry);
    }
  });
  if (entry.node.parentNode !== shell) shell.appendChild(entry.node);
  stageViewNode(entry.node);
  claimEntry(entry, shell);
  gateActivate(entry);
  trimCache();
  shell.setAttribute('aria-busy', 'true');
  if (entry.replaces && activeNode) return;
  if (!activeNode || loadingVisible) {
    revealShellLoading(shell, entry);
  } else if (!samePendingEntry) {
    shell._tfLoadingTimer = window.setTimeout(function () {
      shell._tfLoadingTimer = null;
      revealShellLoading(shell, entry);
    }, LOADING_DELAY_MS);
  }
}

function commitShellView(shell, entry) {
  cancelShellLoading(shell);
  shell._tfPendingEntry = null;
  if (entry.node.parentNode !== shell) shell.appendChild(entry.node);
  setActiveShellView(shell, entry.node);
  shellLoadingState(shell).hidden = true;
  shell.className = 'view-shell view-' + entry.kind;
  shell.removeAttribute('aria-busy');
  renderViewMeta(shell._tfMeta, entry);
  var replaced = entry.replaces;
  entry.replaces = null;
  if (replaced) {
    gateDeactivate(replaced);
    releaseEntry(replaced);
    if (replaced.handle && replaced.handle.destroy) replaced.handle.destroy();
    if (replaced.node.parentNode) replaced.node.parentNode.removeChild(replaced.node);
  }
}

function hideViewNode(node) {
  node.classList.remove('view-active');
  node.classList.remove('view-pending');
  node.classList.add('view-hidden');
  node.setAttribute('inert', '');
  node.setAttribute('aria-hidden', 'true');
  gateDeactivate(node._tfViewEntry);
}

function stageViewNode(node) {
  node.classList.remove('view-active');
  node.classList.remove('view-hidden');
  node.classList.add('view-pending');
  node.setAttribute('inert', '');
  node.setAttribute('aria-hidden', 'true');
  gateDeactivate(node._tfViewEntry);
}

function isActiveShellView(shell, key) {
  return shell.dataset.activeViewKey === key;
}

function createViewEntry(kind, data, revision) {
  var node = el('div', 'tf-view');
  var entry = {
    node: node,
    kind: kind,
    status: data == null ? 'fetching' : 'loaded',
    data: data,
    handle: null,
    readyPromise: null,
    metaText: '',
    ownerShell: null,
    revision: revision,
    pendingRevision: null,
    pendingGeneration: null,
    replaces: null,
    queuedRevision: null,
    queuedRevisionScheduled: false
  };
  node._tfViewEntry = entry;
  return entry;
}

function renderLoadedView(entry) {
  gateDeactivate(entry);
  entry.node.textContent = '';
  entry.handle = renderKind(entry.node, entry.kind, entry.data);
  entry.node._tfViewEntry = entry;
  entry.metaText = entry.kind === 'data' && entry.data.table ? entry.data.table.meta || '' : '';
  entry.status = 'rendering';
}

function renderViewMeta(meta, entry) {
  meta.replaceChildren();
  if (!entry) return;
  if (entry.metaText) {
    var text = el('span', 'viewmeta-text');
    text.textContent = entry.metaText;
    meta.appendChild(text);
  }
  var copy = entry.handle && entry.handle.copy;
  if (!copy) return;
  var button = el('button', 'query-copy viewmeta-copy');
  button.type = 'button';
  button.setAttribute('aria-label', copy.label);
  button.title = copy.label;
  button.innerHTML = '<span class="copy-icon" aria-hidden="true"></span>';
  wireCopyButton(button, copy.text, { copy: copy.label, copied: copy.copiedLabel });
  meta.appendChild(button);
}

function failViewEntry(entry, error) {
  entry.node.className = 'tf-view error';
  entry.node.textContent = 'Failed to load view: ' + String(error);
  entry.status = 'error';
}

function restoreReplacedView(shell, key, entry) {
  var previous = entry.replaces;
  entry.replaces = null;
  if (!previous) return false;
  gateDeactivate(entry);
  releaseEntry(entry);
  if (entry.handle && entry.handle.destroy) entry.handle.destroy();
  if (entry.node.parentNode) entry.node.parentNode.removeChild(entry.node);
  viewCache[key] = previous;
  claimEntry(previous, shell);
  cacheTouch(key);
  commitShellView(shell, previous);
  return true;
}

function prepareShellView(shell, key, entry) {
  stageShellEntry(shell, entry);
  if (!entry.readyPromise) {
    var rendererReady = entry.handle && entry.handle.ready;
    if (!rendererReady) {
      entry.status = 'ready';
      if (isActiveShellView(shell, key)) commitShellView(shell, entry);
      return;
    }
    entry.readyPromise = Promise.resolve(rendererReady).then(
      function () { entry.status = 'ready'; },
      function (error) {
        if (!restoreReplacedView(shell, key, entry)) failViewEntry(entry, error);
      }
    );
  }
  entry.readyPromise.then(function () {
    if (viewCache[key] !== entry || !isActiveShellView(shell, key) || entry.node.parentNode !== shell) return;
    requestAnimationFrame(function () {
      if (viewCache[key] === entry && isActiveShellView(shell, key) && entry.node.parentNode === shell) {
        commitShellView(shell, entry);
      }
    });
  });
}

function currentOwner(entry, key) {
  var shell = entry.ownerShell;
  return shell && isActiveShellView(shell, key) ? shell : null;
}

function stageViewReplacement(card, kind, shell, key, previous, data) {
  var entry = createViewEntry(kind, data, card.id);
  entry.replaces = previous;
  claimEntry(entry, shell);
  viewCache[key] = entry;
  cacheTouch(key);
  try {
    renderLoadedView(entry);
    prepareShellView(shell, key, entry);
  } catch (error) {
    if (!restoreReplacedView(shell, key, entry)) failViewEntry(entry, error);
  }
}

function applyViewRevision(card, kind, shell, key, entry, state, generation, data) {
  if (viewCache[key] !== entry || entry.pendingRevision !== card.id || state.resolveSeq !== generation) return;
  entry.pendingRevision = null;
  entry.pendingGeneration = null;
  var handle = entry.handle;
  if (!handle || !handle.canUpdate || !handle.update || !handle.canUpdate(data)) {
    stageViewReplacement(card, kind, shell, key, entry, data);
    return;
  }
  Promise.resolve(handle.update(data)).then(function () {
    if (viewCache[key] !== entry) return;
    entry.data = data;
    entry.revision = card.id;
    entry.metaText = kind === 'data' && data.table ? data.table.meta || '' : '';
    shell.removeAttribute('aria-busy');
    renderViewMeta(shell._tfMeta, entry);
  }).catch(function () {
    if (viewCache[key] === entry) stageViewReplacement(card, kind, shell, key, entry, data);
  });
}

function updateViewRevision(card, kind, shell, key, entry, state) {
  if (entry.pendingRevision === card.id) return;
  entry.pendingRevision = card.id;
  entry.pendingGeneration = state.resolveSeq;
  var generation = state.resolveSeq;
  shell.setAttribute('aria-busy', 'true');
  var cachedData = getCachedCardData(card);
  if (cachedData) {
    applyViewRevision(card, kind, shell, key, entry, state, generation, cachedData);
    return;
  }
  fetchCardData(card).then(function (data) {
    applyViewRevision(card, kind, shell, key, entry, state, generation, data);
  }).catch(function () {
    if (viewCache[key] !== entry || entry.pendingRevision !== card.id || entry.pendingGeneration !== generation) return;
    entry.pendingRevision = null;
    entry.pendingGeneration = null;
    shell.removeAttribute('aria-busy');
  });
}

function flushQueuedViewRevision(entry) {
  if (!entry.readyPromise || entry.queuedRevisionScheduled) return;
  entry.queuedRevisionScheduled = true;
  entry.readyPromise.then(function () {
    entry.queuedRevisionScheduled = false;
    var queued = entry.queuedRevision;
    entry.queuedRevision = null;
    if (!queued || viewCache[queued.key] !== entry || entry.revision === queued.card.id) return;
    updateViewRevision(queued.card, queued.kind, queued.shell, queued.key, entry, queued.state);
  });
}

function queueViewRevision(card, kind, shell, key, entry, state) {
  entry.queuedRevision = { card: card, kind: kind, shell: shell, key: key, state: state };
  flushQueuedViewRevision(entry);
}

function mountView(card, kind, shell, meta, state, cardIndex) {
  var key = viewStateKey(state, card, cardIndex, kind);
  var entry = viewCache[key];
  shell.dataset.activeViewKey = key;
  shell._tfMeta = meta;
  if (entry) {
    claimEntry(entry, shell);
    cacheTouch(key);
    if (entry.status === 'ready' || entry.status === 'error') {
      commitShellView(shell, entry);
      if (entry.revision !== card.id) updateViewRevision(card, kind, shell, key, entry, state);
      return;
    }
    if (entry.status === 'fetching') {
      stageShellEntry(shell, entry);
      if (entry.revision !== card.id) queueViewRevision(card, kind, shell, key, entry, state);
      return;
    }
    if (entry.status === 'loaded') renderLoadedView(entry);
    prepareShellView(shell, key, entry);
    if (entry.revision !== card.id) queueViewRevision(card, kind, shell, key, entry, state);
    return;
  }
  entry = createViewEntry(kind, null, card.id);
  claimEntry(entry, shell);
  viewCache[key] = entry;
  cacheTouch(key);
  stageShellEntry(shell, entry);
  var cachedData = getCachedCardData(card);
  if (cachedData) {
    entry.data = cachedData;
    entry.status = 'loaded';
    renderLoadedView(entry);
    prepareShellView(shell, key, entry);
    return;
  }
  fetchCardData(card).then(function (data) {
    if (viewCache[key] !== entry) return;
    entry.data = data;
    entry.status = 'loaded';
    var ownerShell = currentOwner(entry, key);
    if (ownerShell) {
      renderLoadedView(entry);
      prepareShellView(ownerShell, key, entry);
      flushQueuedViewRevision(entry);
    }
  }).catch(function (err) {
    if (viewCache[key] !== entry) return;
    failViewEntry(entry, err);
    var ownerShell = currentOwner(entry, key);
    if (ownerShell) commitShellView(ownerShell, entry);
    else hideViewNode(entry.node);
  });
}

function buildCard(card, opts) {
  var pane = el('div', 'cardpane');
  var bar = el('div', 'cardbar');
  var views = card.views || [];
  var state = opts && opts.state;
  var cardIndex = opts && opts.cardIndex != null ? opts.cardIndex : 0;
  var activeKind = state ? savedViewKind(state, card, cardIndex, views) : (views[0] || 'data');
  var shell = el('div', 'view-shell view-' + activeKind);
  var meta = el('div', 'viewmeta');
  var switcher = null;

  function showView(kind, opt, initial) {
    activeKind = kind;
    if (state) rememberViewKind(state, card, cardIndex, kind);
    if (switcher) {
      switcher.opts.forEach(function (x) { x.classList.remove('active'); });
      if (opt) {
        opt.classList.add('active');
        moveThumb(switcher.thumb, opt);
      }
    }
    mountView(card, kind, shell, meta, state, cardIndex);
    if (!initial && state) restoreTurnScroll(state);
  }

  if (views.length > 1) {
    switcher = buildViewSwitcher(views, activeKind, showView);
    bar.appendChild(switcher.seg);
  }
  if (bar.children.length) pane.appendChild(bar);
  pane.appendChild(shell);
  pane.appendChild(meta);
  if (views.length) showView(activeKind, viewOptionForKind(switcher, activeKind), true);
  requestAnimationFrame(function () { syncCardHeader(bar); });
  return pane;
}

function buildMultiCard(cards, state) {
  var pane = el('div', 'cardpane');
  var bar = el('div', 'cardbar multi-card');
  var viewSlot = buildViewSlot(cards);
  var shell = el('div', 'view-shell');
  var meta = el('div', 'viewmeta');
  var activeCard = Math.min(Math.max(state.activeCard || 0, 0), cards.length - 1);
  var switcher = null;

  function updateCardTabs() {
    var tabs = bar.querySelectorAll('.rectab');
    for (var i = 0; i < tabs.length; i++) tabs[i].classList.toggle('active', i === activeCard);
  }

  function currentCard() {
    return cards[activeCard];
  }

  function showView(kind, opt, initial) {
    var card = currentCard();
    rememberViewKind(state, card, activeCard, kind);
    if (switcher) {
      switcher.opts.forEach(function (x) { x.classList.remove('active'); });
      if (opt) {
        opt.classList.add('active');
        moveThumb(switcher.thumb, opt);
      }
    }
    mountView(card, kind, shell, meta, state, activeCard);
    if (!initial) restoreTurnScroll(state);
  }

  function rebuildViewSwitcher(views, activeKind) {
    if (switcher && switcher.seg.parentNode) switcher.seg.parentNode.removeChild(switcher.seg);
    switcher = null;
    if (viewSlot) viewSlot.classList.toggle('empty', views.length <= 1);
    if (views.length > 1 && viewSlot) {
      switcher = buildViewSwitcher(views, activeKind, showView);
      viewSlot.appendChild(switcher.seg);
    }
    requestAnimationFrame(function () { syncCardHeader(bar); });
  }

  function showCard(index, initial) {
    activeCard = Math.min(Math.max(index, 0), cards.length - 1);
    state.activeCard = activeCard;
    updateCardTabs();
    var card = currentCard();
    var views = card.views || [];
    var activeKind = savedViewKind(state, card, activeCard, views);
    rebuildViewSwitcher(views, activeKind);
    if (views.length) showView(activeKind, viewOptionForKind(switcher, activeKind), initial);
    else if (!initial) restoreTurnScroll(state);
  }

  bar.appendChild(buildCardTabs(cards, activeCard, function (i) { showCard(i, false); }));
  bar.classList.toggle('no-view-menu', !viewSlot);
  if (viewSlot) bar.appendChild(viewSlot);
  pane.appendChild(bar);
  pane.appendChild(shell);
  pane.appendChild(meta);
  showCard(activeCard, true);
  return pane;
}

function renderTurn(turn, index) {
  var view = el('div', 'turnview');
  var transcript = buildTranscript(turn);
  var state = getTurnState(turn, index);
  if (isManualPreview(turn)) {
    view.classList.add('manual-preview');
    view.appendChild(buildManualArtifactTitle(turn));
  } else if (transcript) {
    view.appendChild(transcript);
  }
  var controls = buildAnswerControls(turn, state, index);
  if (controls) view.appendChild(controls);
  var artifacts = el('section', 'artifacts-region');
  renderArtifactsInto(artifacts, turn, state);
  view.appendChild(artifacts);
  return view;
}

function updateSelectedTurn(i) {
  activeTurn = i;
  var items = document.querySelectorAll('#turns .turnitem');
  for (var k = 0; k < items.length; k++) items[k].classList.toggle('active', k === i);
  var inner = document.getElementById('content-inner');
  deactivateViewTree(inner);
  inner.replaceChildren();
  inner.classList.toggle('manual-preview-content', isManualPreview(turns[i]));
  inner.appendChild(renderTurn(turns[i], i));
  if (!isManualPreview(turns[i])) inner.appendChild(el('div', 'scroll-pad'));
  restoreTurnScrollImmediately(getTurnState(turns[i], i));
}

function selectTurn(i, animate) {
  if (i < 0 || i >= turns.length || i === activeTurn) return;
  var update = function () { return updateSelectedTurn(i); };
  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!animate || !document.startViewTransition || reducedMotion) {
    if (activeTurnTransition) activeTurnTransition.skipTransition();
    activeTurnTransition = null;
    update();
    return;
  }
  if (activeTurnTransition) activeTurnTransition.skipTransition();
  var transition = document.startViewTransition(update);
  activeTurnTransition = transition;
  var clearTransition = function () {
    if (activeTurnTransition === transition) activeTurnTransition = null;
  };
  transition.finished.then(clearTransition, clearTransition);
}

function appendTurn(turn) {
  var wasOnLatest = activeTurn === turns.length - 1;
  turns.push(turn);
  var sidebar = document.getElementById('turns');
  var sidebarEmpty = sidebar.querySelector('.turns-empty');
  if (sidebarEmpty) sidebarEmpty.remove();
  var idx = turns.length - 1;
  var displayIndex = isManualPreview(turn) ? null : ++agentTurnCount;
  var it = buildTurnItem(turn, idx, displayIndex);
  it.onclick = function () { selectTurn(idx, true); };
  sidebar.appendChild(it);
  if (wasOnLatest) selectTurn(idx, false);
}

function startEvents() {
  var source = new EventSource('events');
  source.addEventListener('turn', function (event) {
    appendTurn(JSON.parse(event.data));
    applyPageStatus(document.hasFocus() ? 'idle' : 'ready');
  });
}

startPageStatus();
startEvents();
watchContentScroll();
