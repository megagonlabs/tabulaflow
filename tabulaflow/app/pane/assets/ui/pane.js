// @ts-check

import { renderTable } from './render/table.js';
import { renderChart } from './render/chart.js';
import { renderMap } from './render/map.js';
import { renderGraph } from './render/graph.js';
import { renderQuery } from './render/query.js';
import { renderMarkdown } from './render/markdown.js';

function el(tag, cls) {
  var e = document.createElement(tag);
  if (cls) { e.className = cls; }
  return e;
}

function hasText(value) {
  return typeof value === 'string' && value.trim().length > 0;
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

function syncCardHeader(bar) {
  if (!bar || !bar.classList.contains('multi-card') || !bar.offsetWidth) return;
  var tabs = bar.querySelector('.rectabs');
  var seg = bar.querySelector('.seg');
  if (!tabs) return;
  if (!seg) {
    bar.classList.remove('stacked');
    return;
  }
  bar.classList.remove('stacked');
  var gap = parseFloat(getComputedStyle(bar).columnGap || getComputedStyle(bar).gap || '0') || 0;
  var required = tabs.scrollWidth + seg.offsetWidth + gap;
  if (required > bar.clientWidth + 1) bar.classList.add('stacked');
  syncSegment(seg);
}

window.addEventListener('resize', function () {
  requestAnimationFrame(function () {
    document.querySelectorAll('.cardbar.multi-card').forEach(syncCardHeader);
  });
});

function buildMessage(role, text) {
  var msg = el('div', 'message ' + role);
  var label = el('div', 'message-label');
  var body = el('div', 'message-body');
  label.textContent = role === 'user' ? 'user' : 'tabulaflow';
  if (role === 'assistant') renderMarkdown(body, text);
  else body.textContent = text;
  msg.appendChild(label);
  msg.appendChild(body);
  return msg;
}

function buildTranscript(turn) {
  var wrap = el('section', 'transcript');
  if (hasText(turn.user)) wrap.appendChild(buildMessage('user', turn.user));
  if (hasText(turn.assistant)) wrap.appendChild(buildMessage('assistant', turn.assistant));
  return wrap.children.length ? wrap : null;
}

function isManualPreview(turn) {
  return turn.source === 'manual' && (turn.cards || []).length === 1;
}

function buildManualArtifactTitle(turn) {
  var title = el('div', 'manual-artifact-title');
  title.textContent = turn.title || 'table preview';
  return title;
}

var META_ICONS = {
  map: [
    ['path', { d: 'M9 18l-6 3V6l6-3 6 3 6-3v15l-6 3-6-3z' }],
    ['path', { d: 'M9 3v15' }],
    ['path', { d: 'M15 6v15' }]
  ],
  graph: [
    ['circle', { cx: '6', cy: '7', r: '2' }],
    ['circle', { cx: '18', cy: '7', r: '2' }],
    ['circle', { cx: '12', cy: '18', r: '2' }],
    ['path', { d: 'M8 8l3 7' }],
    ['path', { d: 'M16 8l-3 7' }],
    ['path', { d: 'M8 7h8' }]
  ],
  chart: [
    ['path', { d: 'M4 19V5' }],
    ['path', { d: 'M4 19h16' }],
    ['path', { d: 'M8 16v-4' }],
    ['path', { d: 'M12 16V8' }],
    ['path', { d: 'M16 16v-7' }]
  ],
  table: [
    ['path', { d: 'M5 5h14v14H5z' }],
    ['path', { d: 'M5 10h14' }],
    ['path', { d: 'M10 5v14' }]
  ]
};

function artifactCounts(turn) {
  var counts = { map: 0, graph: 0, chart: 0, table: 0 };
  (turn.cards || []).forEach(function (card) {
    var kinds = card.views || [];
    if (kinds.indexOf('map') !== -1) counts.map += 1;
    else if (kinds.indexOf('graph') !== -1) counts.graph += 1;
    else if (kinds.indexOf('chart') !== -1) counts.chart += 1;
    else if (kinds.indexOf('data') !== -1) counts.table += 1;
  });
  return counts;
}

function artifactLabel(kind, count) {
  return count + ' ' + (count === 1 ? kind : kind + 's');
}

function turnMeta(turn) {
  var counts = artifactCounts(turn);
  if (turn.source === 'manual' && counts.table === 1 && counts.chart === 0 && counts.map === 0 && counts.graph === 0) {
    return { text: 'table preview', items: [], label: 'table preview' };
  }
  var items = [];
  ['map', 'graph', 'chart', 'table'].forEach(function (kind) {
    if (counts[kind]) items.push({ kind: kind, count: counts[kind], label: artifactLabel(kind, counts[kind]) });
  });
  return { text: '', items: items, label: items.map(function (item) { return item.label; }).join(' · ') };
}

function buildMetaIcon(kind) {
  var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('aria-hidden', 'true');
  (META_ICONS[kind] || []).forEach(function (spec) {
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

function buildTurnItem(turn, index) {
  var it = el('div', 'turnitem');
  var idx = el('div', 'turnindex');
  var text = el('div', 'turntext');
  var title = el('div', 'turntitle');
  title.textContent = turn.title || ('Turn ' + (index + 1));
  idx.textContent = String(index + 1).padStart(2, '0');
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
var HEIGHT_ANIMATION_MS = 160;
var suppressScrollMemory = false;
var scrollRestoreVersion = 0;
var activeTurnTransition = null;

function turnStateKey(turn, index) {
  return String(turn.id == null ? index : turn.id);
}

function getTurnState(turn, index) {
  var key = turnStateKey(turn, index);
  if (!navState[key]) navState[key] = { activeCard: 0, views: {}, scrollTop: 0 };
  return navState[key];
}

function cardStateKey(card, cardIndex) {
  return cardIndex + ':' + card.id;
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
  if (kind === 'map') return renderMap(node, data);
  if (kind === 'graph') return renderGraph(node, data);
  if (kind === 'chart') return renderChart(node, data);
  if (kind === 'data') return renderTable(node, data);
  if (kind === 'query') return renderQuery(node, data);
  node.textContent = 'Unknown view: ' + kind;
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

function deactivateViewTree(root) {
  if (!root) return;
  root.querySelectorAll('.view-shell').forEach(function (shell) {
    cancelShellLoading(shell);
    cancelShellHeightAnimation(shell, false);
    shell._tfPendingEntry = null;
  });
  root.querySelectorAll('.tf-view').forEach(function (node) {
    gateDeactivate(node._tfViewEntry);
    releaseEntry(node._tfViewEntry);
  });
  trimCache();
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

function cancelShellHeightAnimation(shell, preserveHeight) {
  var animation = shell._tfHeightAnimation;
  if (!animation) return;
  var height = shell.getBoundingClientRect().height;
  shell._tfHeightAnimation = null;
  animation.cancel();
  shell.style.height = preserveHeight ? height + 'px' : '';
}

function animateShellHeight(shell, fromHeight, toHeight) {
  if (
    Math.abs(fromHeight - toHeight) < 1
    || !shell.animate
    || window.matchMedia('(prefers-reduced-motion: reduce)').matches
  ) {
    shell.style.height = '';
    return;
  }
  shell.style.height = toHeight + 'px';
  var animation = shell.animate(
    [{ height: fromHeight + 'px' }, { height: toHeight + 'px' }],
    { duration: HEIGHT_ANIMATION_MS, easing: 'cubic-bezier(0.2, 0, 0, 1)' }
  );
  shell._tfHeightAnimation = animation;
  animation.finished.then(function () {
    if (shell._tfHeightAnimation !== animation) return;
    shell._tfHeightAnimation = null;
    shell.style.height = '';
  }).catch(function () {});
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
  shell._tfMeta.textContent = '';
}

function stageShellEntry(shell, entry) {
  cancelShellHeightAnimation(shell, true);
  var samePendingEntry = shell._tfPendingEntry === entry;
  if (!samePendingEntry) cancelShellLoading(shell);
  shell._tfPendingEntry = entry;
  var activeNode = shell.querySelector('.tf-view.view-active');
  var loadingVisible = shell.classList.contains('view-loading');
  var height = shell.getBoundingClientRect().height;
  if (!loadingVisible) shell.style.height = height > 0 ? height + 'px' : '';
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
  cancelShellHeightAnimation(shell, true);
  shell._tfPendingEntry = null;
  if (entry.node.parentNode !== shell) shell.appendChild(entry.node);
  var fromHeight = shell.getBoundingClientRect().height;
  var toHeight = entry.node.getBoundingClientRect().height;
  setActiveShellView(shell, entry.node);
  shellLoadingState(shell).hidden = true;
  shell.className = 'view-shell view-' + entry.kind;
  shell.removeAttribute('aria-busy');
  shell._tfMeta.textContent = entry.metaText || '';
  animateShellHeight(shell, fromHeight, toHeight);
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

function createViewEntry(kind, data) {
  var node = el('div', 'tf-view');
  var entry = {
    node: node,
    kind: kind,
    status: data == null ? 'fetching' : 'loaded',
    data: data,
    handle: null,
    readyPromise: null,
    metaText: '',
    ownerShell: null
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

function failViewEntry(entry, error) {
  entry.node.className = 'tf-view error';
  entry.node.textContent = 'Failed to load view: ' + String(error);
  entry.status = 'error';
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
      function (error) { failViewEntry(entry, error); }
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

function mountView(card, kind, shell, meta) {
  var key = card.id + ':' + kind;
  var entry = viewCache[key];
  shell.dataset.activeViewKey = key;
  shell._tfMeta = meta;
  if (entry) {
    claimEntry(entry, shell);
    cacheTouch(key);
    if (entry.status === 'ready' || entry.status === 'error') {
      commitShellView(shell, entry);
      return;
    }
    if (entry.status === 'fetching') {
      stageShellEntry(shell, entry);
      return;
    }
    if (entry.status === 'loaded') renderLoadedView(entry);
    prepareShellView(shell, key, entry);
    return;
  }
  entry = createViewEntry(kind, null);
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
    mountView(card, kind, shell, meta);
    if (!initial && state) restoreTurnScroll(state);
  }

  if (card.label) {
    var label = el('span', 'cardlabel');
    label.textContent = card.label;
    bar.appendChild(label);
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
    mountView(card, kind, shell, meta);
    if (!initial) restoreTurnScroll(state);
  }

  function rebuildViewSwitcher(views, activeKind) {
    if (switcher && switcher.seg.parentNode) switcher.seg.parentNode.removeChild(switcher.seg);
    switcher = null;
    bar.classList.toggle('no-view-menu', views.length <= 1);
    if (views.length > 1) {
      switcher = buildViewSwitcher(views, activeKind, showView);
      bar.appendChild(switcher.seg);
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
  pane.appendChild(bar);
  pane.appendChild(shell);
  pane.appendChild(meta);
  showCard(activeCard, true);
  return pane;
}

function renderTurn(turn, index) {
  var view = el('div', 'turnview');
  var transcript = buildTranscript(turn);
  var cards = turn.cards || [];
  var state = getTurnState(turn, index);
  if (isManualPreview(turn)) {
    view.classList.add('manual-preview');
    view.appendChild(buildManualArtifactTitle(turn));
  } else if (transcript) {
    view.appendChild(transcript);
  }
  if (!cards.length) return view;
  if (cards.length <= 1) {
    view.appendChild(buildCard(cards[0], { state: state, cardIndex: 0 }));
    return view;
  }
  var box = el('div', 'panesbox');
  box.appendChild(buildMultiCard(cards, state));
  view.appendChild(box);
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
  var it = buildTurnItem(turn, idx);
  it.onclick = function () { selectTurn(idx, true); };
  sidebar.appendChild(it);
  if (wasOnLatest) selectTurn(idx, false);
}

function startEvents() {
  var source = new EventSource('events');
  source.addEventListener('turn', function (event) {
    appendTurn(JSON.parse(event.data));
  });
}

startEvents();
watchContentScroll();
