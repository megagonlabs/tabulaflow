// @ts-check

import { renderTable } from './render/table.js';
import { renderChart } from './render/chart.js';
import { renderMap } from './render/map.js';
import { renderGraph } from './render/graph.js';
import { renderQuery } from './render/query.js';

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
  body.textContent = text;
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

function cacheEntryWeight(entry) {
  if (!entry) return 0;
  if (entry.kind === 'map') return 3;
  if (entry.kind === 'graph') return 3;
  return 1;
}

function cacheWeight() {
  var total = 0;
  for (var i = 0; i < lru.length; i++) total += cacheEntryWeight(viewCache[lru[i]]);
  return total;
}

function cacheTouch(key) {
  var idx = lru.indexOf(key);
  if (idx !== -1) lru.splice(idx, 1);
  lru.push(key);
  while (cacheWeight() > CACHE_WEIGHT_LIMIT) {
    var evict = lru.shift();
    var entry = viewCache[evict];
    if (!entry) continue;
    if (entry.handle && entry.handle.destroy) entry.handle.destroy();
    if (entry.node && entry.node.parentNode) entry.node.parentNode.removeChild(entry.node);
    delete viewCache[evict];
  }
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

function afterVisible(entry) {
  if (!entry || !entry.handle || !entry.handle.afterVisible) return;
  requestAnimationFrame(function () { entry.handle.afterVisible(); });
}

function afterHidden(entry) {
  if (!entry || !entry.handle || !entry.handle.afterHidden) return;
  entry.handle.afterHidden();
}

function setActiveShellView(shell, activeNode) {
  Array.prototype.forEach.call(shell.children, function (node) {
    var active = node === activeNode;
    node.classList.toggle('view-active', active);
    node.classList.toggle('view-hidden', !active);
    node.classList.remove('view-pending');
    node.toggleAttribute('inert', !active);
    node.setAttribute('aria-hidden', active ? 'false' : 'true');
    if (active) afterVisible(node._tfViewEntry);
    else afterHidden(node._tfViewEntry);
  });
}

function hideViewNode(node) {
  node.classList.remove('view-active');
  node.classList.remove('view-pending');
  node.classList.add('view-hidden');
  node.setAttribute('inert', '');
  node.setAttribute('aria-hidden', 'true');
  afterHidden(node._tfViewEntry);
}

function stageViewNode(node) {
  node.classList.remove('view-active');
  node.classList.remove('view-hidden');
  node.classList.add('view-pending');
  node.setAttribute('inert', '');
  node.setAttribute('aria-hidden', 'true');
  afterHidden(node._tfViewEntry);
}

function blurHiddenFocus(node) {
  var active = document.activeElement;
  if (active && node.contains(active) && active.blur) active.blur();
}

function syncActiveShellView(shell) {
  var entry = viewCache[shell.dataset.activeViewKey];
  if (entry && entry.node.parentNode === shell) {
    setActiveShellView(shell, entry.node);
    return;
  }
  var activeNode = shell.querySelector('.tf-view.view-active');
  if (activeNode) setActiveShellView(shell, activeNode);
}

function attachView(shell, node) {
  if (node.parentNode !== shell) shell.appendChild(node);
  setActiveShellView(shell, node);
}

function stageShellView(shell, pendingNode) {
  Array.prototype.forEach.call(shell.children, function (node) {
    if (node === pendingNode) stageViewNode(node);
    else hideViewNode(node);
  });
}

function stageView(shell, node) {
  if (node.parentNode !== shell) shell.appendChild(node);
  stageShellView(shell, node);
}

function isActiveShellView(shell, key) {
  return shell.dataset.activeViewKey === key;
}

function renderLoadedView(entry, kind, data, meta) {
  entry.data = data;
  entry.node.textContent = '';
  entry.handle = renderKind(entry.node, kind, data);
  entry.node._tfViewEntry = entry;
  if (kind === 'data' && data.table) meta.textContent = data.table.meta || '';
}

function renderHiddenDataView(entry, data) {
  hideViewNode(entry.node);
  renderLoadedView(entry, 'data', data, { textContent: '' });
  hideViewNode(entry.node);
  blurHiddenFocus(entry.node);
}

function revealStagedView(shell, key, node) {
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      if (isActiveShellView(shell, key) && node.parentNode === shell) setActiveShellView(shell, node);
    });
  });
}

function stageDataView(entry, shell, key, meta) {
  stageView(shell, entry.node);
  cacheTouch(key);
  if (entry.data && !entry.handle) renderLoadedView(entry, 'data', entry.data, meta);
  else if (entry.data && entry.data.table) meta.textContent = entry.data.table.meta || '';
  stageShellView(shell, entry.node);
  revealStagedView(shell, key, entry.node);
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
      var entry = { node: node, handle: null, data: data, kind: 'data' };
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
  shell.className = 'view-shell view-' + kind;
  shell.dataset.activeViewKey = key;
  meta.textContent = '';
  if (entry) {
    if (kind === 'data') {
      stageDataView(entry, shell, key, meta);
      return;
    }
    attachView(shell, entry.node);
    cacheTouch(key);
    if (entry.data && !entry.handle) {
      renderLoadedView(entry, kind, entry.data, meta);
      afterVisible(entry);
    }
    else if (entry.data && kind === 'data' && entry.data.table) meta.textContent = entry.data.table.meta || '';
    return;
  }
  var node = el('div', 'tf-view loading');
  node.textContent = 'Loading...';
  entry = { node: node, handle: null, data: null, kind: kind };
  node._tfViewEntry = entry;
  viewCache[key] = entry;
  cacheTouch(key);
  attachView(shell, node);
  var cachedData = getCachedCardData(card);
  if (cachedData) {
    if (kind === 'data') {
      entry.data = cachedData;
      stageDataView(entry, shell, key, meta);
    } else {
      renderLoadedView(entry, kind, cachedData, meta);
      setActiveShellView(shell, node);
    }
    return;
  }
  fetchCardData(card).then(function (data) {
    entry.data = data;
    if (isActiveShellView(shell, key)) {
      if (kind === 'data') {
        stageDataView(entry, shell, key, meta);
      } else {
        renderLoadedView(entry, kind, data, meta);
        setActiveShellView(shell, node);
      }
    }
  }).catch(function (err) {
    node.className = 'tf-view error';
    node.textContent = 'Failed to load view: ' + String(err);
    if (isActiveShellView(shell, key)) setActiveShellView(shell, node);
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
