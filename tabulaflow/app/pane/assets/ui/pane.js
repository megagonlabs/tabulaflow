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

function turnMeta(turn) {
  var counts = { map: 0, graph: 0, chart: 0, table: 0 };
  (turn.cards || []).forEach(function (card) {
    var kinds = card.views || [];
    if (kinds.indexOf('map') !== -1) counts.map += 1;
    else if (kinds.indexOf('graph') !== -1) counts.graph += 1;
    else if (kinds.indexOf('chart') !== -1) counts.chart += 1;
    else if (kinds.indexOf('data') !== -1) counts.table += 1;
  });
  if (turn.source === 'manual' && counts.table === 1 && counts.chart === 0 && counts.map === 0 && counts.graph === 0) return 'table preview';
  var parts = [];
  if (counts.map) parts.push(counts.map + (counts.map === 1 ? ' map' : ' maps'));
  if (counts.graph) parts.push(counts.graph + (counts.graph === 1 ? ' graph' : ' graphs'));
  if (counts.chart) parts.push(counts.chart + (counts.chart === 1 ? ' chart' : ' charts'));
  if (counts.table) parts.push(counts.table + (counts.table === 1 ? ' table' : ' tables'));
  return parts.join(' · ');
}

function buildTurnItem(turn, index) {
  var it = el('div', 'turnitem');
  var idx = el('div', 'turnindex');
  var text = el('div', 'turntext');
  var title = el('div', 'turntitle');
  var meta = el('div', 'turnmeta');
  title.textContent = turn.title || ('Turn ' + (index + 1));
  idx.textContent = String(index + 1).padStart(2, '0');
  var metaText = turnMeta(turn);
  if (metaText) meta.textContent = metaText;
  it.title = metaText ? title.textContent + ' · ' + metaText : title.textContent;
  text.appendChild(title);
  if (metaText) text.appendChild(meta);
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
var suppressScrollMemory = false;

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
  var scroller = contentScroller();
  if (!state || !scroller) return;
  var scrollTop = state.scrollTop || 0;
  suppressScrollMemory = true;
  requestAnimationFrame(function () {
    scroller.scrollTop = scrollTop;
    requestAnimationFrame(function () {
      scroller.scrollTop = scrollTop;
      requestAnimationFrame(function () { suppressScrollMemory = false; });
    });
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

function scheduleIdle(fn) {
  if (window.requestIdleCallback) {
    return window.requestIdleCallback(fn, { timeout: 800 });
  }
  return window.setTimeout(fn, 80);
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
    if (entry && !entry.pinned) total += cacheEntryWeight(entry);
  }
  return total;
}

function trimCache() {
  while (cacheWeight() > CACHE_WEIGHT_LIMIT) {
    var index = lru.findIndex(function (key) {
      var entry = viewCache[key];
      return entry && !entry.pinned;
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

function pinEntry(entry, shell, meta) {
  entry.pinned = true;
  entry.ownerShell = shell;
  entry.ownerMeta = meta;
}

function releaseEntry(entry) {
  if (!entry) return;
  entry.pinned = false;
  entry.ownerShell = null;
  entry.ownerMeta = null;
}

function deactivateViewTree(root) {
  if (!root) return;
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
      pinEntry(node._tfViewEntry, shell, shell._tfMeta);
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

function showShellLoading(shell, kind, meta, pendingEntry) {
  var height = shell.getBoundingClientRect().height;
  if (!shell.classList.contains('view-loading')) shell.style.height = Math.max(220, height) + 'px';
  Array.prototype.forEach.call(shell.children, function (node) {
    if (!node.classList.contains('tf-view')) return;
    hideViewNode(node);
    if (node._tfViewEntry !== pendingEntry) releaseEntry(node._tfViewEntry);
  });
  pinEntry(pendingEntry, shell, meta);
  trimCache();
  var state = shellLoadingState(shell);
  state.textContent = 'Loading ' + kind + '\u2026';
  state.hidden = false;
  shell.className = 'view-shell view-' + kind + ' view-loading';
  shell.setAttribute('aria-busy', 'true');
  meta.textContent = '';
}

function commitShellView(shell, entry, meta) {
  if (entry.node.parentNode !== shell) shell.appendChild(entry.node);
  shell._tfMeta = meta;
  setActiveShellView(shell, entry.node);
  shellLoadingState(shell).hidden = true;
  shell.className = 'view-shell view-' + entry.kind;
  shell.style.height = '';
  shell.removeAttribute('aria-busy');
  meta.textContent = entry.metaText || '';
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

function blurHiddenFocus(node) {
  var active = document.activeElement;
  if (active && node.contains(active) && active.blur) active.blur();
}

function syncActiveShellView(shell) {
  if (shell.classList.contains('view-loading')) return;
  var entry = viewCache[shell.dataset.activeViewKey];
  if (entry && entry.node.parentNode === shell) {
    setActiveShellView(shell, entry.node);
    return;
  }
  var activeNode = shell.querySelector('.tf-view.view-active');
  if (activeNode) setActiveShellView(shell, activeNode);
}

function stageView(shell, node) {
  if (node.parentNode !== shell) shell.appendChild(node);
  stageViewNode(node);
}

function isActiveShellView(shell, key) {
  return shell.dataset.activeViewKey === key;
}

function renderLoadedView(entry, kind, data) {
  gateDeactivate(entry);
  entry.data = data;
  entry.node.textContent = '';
  entry.handle = renderKind(entry.node, kind, data);
  entry.node._tfViewEntry = entry;
  entry.metaText = kind === 'data' && data.table ? data.table.meta || '' : '';
}

function renderHiddenDataView(entry, data) {
  hideViewNode(entry.node);
  renderLoadedView(entry, 'data', data);
  hideViewNode(entry.node);
  blurHiddenFocus(entry.node);
}

function prepareShellView(shell, key, entry, meta) {
  if (entry.node.parentNode !== shell) shell.appendChild(entry.node);
  showShellLoading(shell, entry.kind, meta, entry);
  stageView(shell, entry.node);
  gateActivate(entry);

  if (!entry.readyPromise) {
    var rendererReady = entry.handle && entry.handle.ready;
    if (!rendererReady) {
      entry.ready = true;
      if (isActiveShellView(shell, key)) commitShellView(shell, entry, meta);
      return;
    }
    entry.readyPromise = Promise.resolve(rendererReady).catch(function () {}).then(function () {
      entry.ready = true;
    });
  }
  entry.readyPromise.then(function () {
    if (viewCache[key] !== entry || !isActiveShellView(shell, key) || entry.node.parentNode !== shell) return;
    requestAnimationFrame(function () {
      if (viewCache[key] === entry && isActiveShellView(shell, key) && entry.node.parentNode === shell) {
        commitShellView(shell, entry, meta);
      }
    });
  });
}

function prewarmDataView(card, views, activeKind, shell) {
  if (activeKind === 'data' || views.indexOf('data') === -1) return;
  var key = card.id + ':data';
  scheduleIdle(function () {
    if (!shell.isConnected) return;
    var entry = viewCache[key];
    if (entry) {
      if (entry.node.parentNode !== shell) shell.appendChild(entry.node);
      hideViewNode(entry.node);
      if (entry.data && !entry.handle) renderHiddenDataView(entry, entry.data);
      cacheTouch(key);
      syncActiveShellView(shell);
      return;
    }
    fetchCardData(card).then(function (data) {
      if (!shell.isConnected || viewCache[key]) return;
      var node = el('div', 'tf-view view-hidden');
      var entry = {
        node: node, handle: null, data: data, dataPromise: null, kind: 'data', metaText: '',
        ready: false, readyPromise: null, pinned: false, ownerShell: null, ownerMeta: null
      };
      viewCache[key] = entry;
      cacheTouch(key);
      shell.appendChild(node);
      renderHiddenDataView(entry, data);
      syncActiveShellView(shell);
    });
  });
}

function mountView(card, kind, shell, meta) {
  var key = card.id + ':' + kind;
  var entry = viewCache[key];
  shell.dataset.activeViewKey = key;
  shell._tfMeta = meta;
  if (entry) {
    pinEntry(entry, shell, meta);
    cacheTouch(key);
    if (entry.error) {
      commitShellView(shell, entry, meta);
      return;
    }
    if (!entry.data) {
      showShellLoading(shell, kind, meta, entry);
      stageView(shell, entry.node);
      return;
    }
    if (entry.data && !entry.handle) {
      renderLoadedView(entry, kind, entry.data);
    }
    if (entry.ready) commitShellView(shell, entry, meta);
    else prepareShellView(shell, key, entry, meta);
    return;
  }
  var node = el('div', 'tf-view');
  entry = {
    node: node, handle: null, data: null, dataPromise: null, kind: kind, metaText: '',
    ready: false, readyPromise: null, pinned: true, ownerShell: shell, ownerMeta: meta
  };
  node._tfViewEntry = entry;
  viewCache[key] = entry;
  cacheTouch(key);
  showShellLoading(shell, kind, meta, entry);
  stageView(shell, node);
  var cachedData = getCachedCardData(card);
  if (cachedData) {
    entry.data = cachedData;
    renderLoadedView(entry, kind, cachedData);
    prepareShellView(shell, key, entry, meta);
    return;
  }
  entry.dataPromise = fetchCardData(card);
  entry.dataPromise.then(function (data) {
    if (viewCache[key] !== entry) return;
    entry.data = data;
    var ownerShell = entry.ownerShell;
    var ownerMeta = entry.ownerMeta;
    if (entry.pinned && ownerShell && isActiveShellView(ownerShell, key)) {
      renderLoadedView(entry, kind, data);
      prepareShellView(ownerShell, key, entry, ownerMeta);
    }
  }).catch(function (err) {
    if (viewCache[key] !== entry) return;
    node.className = 'tf-view error';
    node.textContent = 'Failed to load view: ' + String(err);
    entry.error = true;
    entry.ready = true;
    var ownerShell = entry.ownerShell;
    var ownerMeta = entry.ownerMeta;
    if (entry.pinned && ownerShell && isActiveShellView(ownerShell, key)) commitShellView(ownerShell, entry, ownerMeta);
    else hideViewNode(node);
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
    prewarmDataView(card, views, kind, shell);
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
    var views = card.views || [];
    rememberViewKind(state, card, activeCard, kind);
    if (switcher) {
      switcher.opts.forEach(function (x) { x.classList.remove('active'); });
      if (opt) {
        opt.classList.add('active');
        moveThumb(switcher.thumb, opt);
      }
    }
    mountView(card, kind, shell, meta);
    prewarmDataView(card, views, kind, shell);
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

function selectTurn(i) {
  if (i < 0 || i >= turns.length) return;
  activeTurn = i;
  var items = document.querySelectorAll('#turns .turnitem');
  for (var k = 0; k < items.length; k++) items[k].classList.toggle('active', k === i);
  var inner = document.getElementById('content-inner');
  deactivateViewTree(inner);
  inner.replaceChildren();
  inner.classList.toggle('manual-preview-content', isManualPreview(turns[i]));
  inner.appendChild(renderTurn(turns[i], i));
  if (!isManualPreview(turns[i])) inner.appendChild(el('div', 'scroll-pad'));
  restoreTurnScroll(getTurnState(turns[i], i));
}

function appendTurn(turn) {
  var wasOnLatest = activeTurn === turns.length - 1;
  turns.push(turn);
  var sidebar = document.getElementById('turns');
  var sidebarEmpty = sidebar.querySelector('.turns-empty');
  if (sidebarEmpty) sidebarEmpty.remove();
  var idx = turns.length - 1;
  var it = buildTurnItem(turn, idx);
  it.onclick = function () { selectTurn(idx); };
  sidebar.appendChild(it);
  if (wasOnLatest) selectTurn(idx);
}

function startEvents() {
  var source = new EventSource('events');
  source.addEventListener('turn', function (event) {
    appendTurn(JSON.parse(event.data));
  });
}

startEvents();
watchContentScroll();
