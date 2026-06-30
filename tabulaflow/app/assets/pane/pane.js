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

function syncRecordHeader(bar) {
  if (!bar || !bar.classList.contains('multi-record') || !bar.offsetWidth) return;
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
    document.querySelectorAll('.cardbar.multi-record').forEach(syncRecordHeader);
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
  return turn.source === 'manual' && (turn.records || []).length === 1;
}

function buildManualArtifactTitle(turn) {
  var title = el('div', 'manual-artifact-title');
  title.textContent = turn.title || 'table preview';
  return title;
}

function turnMeta(turn) {
  var counts = { chart: 0, table: 0 };
  (turn.records || []).forEach(function (record) {
    var kinds = record.views || [];
    if (kinds.indexOf('chart') !== -1) counts.chart += 1;
    else if (kinds.indexOf('data') !== -1) counts.table += 1;
  });
  if (turn.source === 'manual' && counts.table === 1 && counts.chart === 0) return 'table preview';
  var parts = [];
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

function buildRecordTabs(records, activeIndex, onSelect) {
  var tabs = el('div', 'rectabs');
  records.forEach(function (record, i) {
    var tab = el('button', 'rectab');
    tab.textContent = record.label || ('result ' + (i + 1));
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

var turns = [];
var activeTurn = -1;
var recordDataCache = {};
var viewCache = {};
var lru = [];
var CACHE_LIMIT = 24;

function cacheTouch(key) {
  var idx = lru.indexOf(key);
  if (idx !== -1) lru.splice(idx, 1);
  lru.push(key);
  while (lru.length > CACHE_LIMIT) {
    var evict = lru.shift();
    var entry = viewCache[evict];
    if (!entry) continue;
    if (entry.handle && entry.handle.destroy) entry.handle.destroy();
    if (entry.node && entry.node.parentNode) entry.node.parentNode.removeChild(entry.node);
    delete viewCache[evict];
  }
}

function fetchRecordData(record) {
  if (recordDataCache[record.id]) return recordDataCache[record.id];
  recordDataCache[record.id] = fetch('/' + record.id + '.data.json').then(function (response) {
    if (!response.ok) throw new Error('HTTP ' + response.status);
    return response.json();
  });
  return recordDataCache[record.id];
}

function renderKind(node, kind, data) {
  if (kind === 'chart') return TF.renderChart(node, data);
  if (kind === 'data') return TF.renderTable(node, data);
  if (kind === 'query') return TF.renderQuery(node, data);
  node.textContent = 'Unknown view: ' + kind;
  return { destroy: function () {} };
}

function mountView(record, kind, shell, meta) {
  var key = record.id + ':' + kind;
  var entry = viewCache[key];
  shell.className = 'view-shell view-' + kind;
  meta.textContent = '';
  if (entry) {
    shell.replaceChildren(entry.node);
    cacheTouch(key);
    if (entry.data && kind === 'data' && entry.data.table) meta.textContent = entry.data.table.meta || '';
    return;
  }
  var node = el('div', 'tf-view loading');
  node.textContent = 'Loading...';
  entry = { node: node, handle: null, data: null };
  viewCache[key] = entry;
  cacheTouch(key);
  shell.replaceChildren(node);
  fetchRecordData(record).then(function (data) {
    entry.data = data;
    node.textContent = '';
    entry.handle = renderKind(node, kind, data);
    if (kind === 'data' && data.table) meta.textContent = data.table.meta || '';
  }).catch(function (err) {
    node.className = 'tf-view error';
    node.textContent = 'Failed to load view: ' + String(err);
  });
}

function buildRecord(record, opts) {
  var pane = el('div', 'recordpane');
  var bar = el('div', 'cardbar');
  var views = record.views || [];
  var activeKind = views[0] || 'data';
  var shell = el('div', 'view-shell view-' + activeKind);
  var meta = el('div', 'viewmeta');
  var switcher = null;

  function showView(kind, opt) {
    activeKind = kind;
    if (switcher) {
      switcher.opts.forEach(function (x) { x.classList.remove('active'); });
      if (opt) {
        opt.classList.add('active');
        moveThumb(switcher.thumb, opt);
      }
    }
    mountView(record, kind, shell, meta);
  }

  if (opts && opts.records) {
    bar.classList.add('multi-record');
    if (views.length <= 1) bar.classList.add('no-view-menu');
    bar.appendChild(buildRecordTabs(opts.records, opts.activeIndex, opts.onSelect));
  } else if (record.label) {
    var label = el('span', 'cardlabel');
    label.textContent = record.label;
    bar.appendChild(label);
  }
  if (views.length > 1) {
    switcher = buildViewSwitcher(views, activeKind, showView);
    bar.appendChild(switcher.seg);
  }
  if (bar.children.length) pane.appendChild(bar);
  pane.appendChild(shell);
  pane.appendChild(meta);
  if (views.length) showView(activeKind, switcher ? switcher.opts[0] : null);
  requestAnimationFrame(function () { syncRecordHeader(bar); });
  return pane;
}

function renderTurn(turn) {
  var view = el('div', 'turnview');
  var transcript = buildTranscript(turn);
  var records = turn.records || [];
  if (isManualPreview(turn)) {
    view.classList.add('manual-preview');
    view.appendChild(buildManualArtifactTitle(turn));
  } else if (transcript) {
    view.appendChild(transcript);
  }
  if (!records.length) return view;
  if (records.length <= 1) {
    view.appendChild(buildRecord(records[0], null));
    return view;
  }
  var box = el('div', 'panesbox');
  var activeRecord = 0;
  function renderActiveRecord() {
    box.replaceChildren(buildRecord(records[activeRecord], {
      records: records,
      activeIndex: activeRecord,
      onSelect: function (i) {
        activeRecord = i;
        renderActiveRecord();
      }
    }));
  }
  renderActiveRecord();
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
  inner.appendChild(renderTurn(turns[i]));
  if (!isManualPreview(turns[i])) inner.appendChild(el('div', 'scroll-pad'));
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
  var source = new EventSource('/events');
  source.addEventListener('turn', function (event) {
    appendTurn(JSON.parse(event.data));
  });
}

startEvents();
