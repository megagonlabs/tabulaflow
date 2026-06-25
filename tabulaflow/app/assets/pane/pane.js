// Cards are served same-origin, so the parent tracks each iframe's content
// height (ResizeObserver) and resizes to fit as Tabulator/Vega render. Measure
// <body> (whose scrollHeight hugs the content) rather than documentElement
// (floored at the iframe viewport, so it can't shrink back for short content).
function autosize(frame) {
  var ro = null;
  frame.addEventListener('load', function () {
    try {
      var doc = frame.contentWindow.document;
      var fit = function () { frame.style.height = doc.body.scrollHeight + 'px'; };
      fit();
      if (ro) { ro.disconnect(); }
      if (window.ResizeObserver) { ro = new ResizeObserver(fit); ro.observe(doc.body); }
    } catch (e) { /* cross-origin / detached - keep the CSS height */ }
  });
}

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

function isHiddenRecordPane(node) {
  var pane = node.closest ? node.closest('.recordpane') : null;
  return pane && pane.classList.contains('hidden');
}

function syncRecordHeader(bar) {
  if (!bar || !bar.classList.contains('multi-record') || isHiddenRecordPane(bar) || !bar.offsetWidth) {
    return;
  }
  var tabs = bar.querySelector('.rectabs');
  var seg = bar.querySelector('.seg');
  if (!tabs) { return; }
  if (!seg) {
    bar.classList.remove('stacked');
    return;
  }
  bar.classList.remove('stacked');
  var gap = parseFloat(getComputedStyle(bar).columnGap || getComputedStyle(bar).gap || '0') || 0;
  var required = tabs.scrollWidth + seg.offsetWidth + gap;
  var available = bar.clientWidth;
  if (required > available + 1) {
    bar.classList.add('stacked');
  }
  syncSegment(seg);
}

function syncRecordHeaders(root) {
  (root || document).querySelectorAll('.cardbar.multi-record').forEach(syncRecordHeader);
}

window.addEventListener('resize', function () {
  requestAnimationFrame(function () { syncRecordHeaders(document); });
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
  if (hasText(turn.user)) { wrap.appendChild(buildMessage('user', turn.user)); }
  if (hasText(turn.assistant)) { wrap.appendChild(buildMessage('assistant', turn.assistant)); }
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
    var kinds = (record.views || []).map(function (view) { return (view.kind || '').toLowerCase(); });
    if (kinds.indexOf('chart') !== -1) {
      counts.chart += 1;
    } else if (kinds.indexOf('data') !== -1) {
      counts.table += 1;
    }
  });
  if (turn.source === 'manual' && counts.table === 1 && counts.chart === 0) {
    return 'table preview';
  }
  var parts = [];
  if (counts.chart) { parts.push(counts.chart + (counts.chart === 1 ? ' chart' : ' charts')); }
  if (counts.table) { parts.push(counts.table + (counts.table === 1 ? ' table' : ' tables')); }
  return parts.length ? parts.join(' · ') : 'text only';
}

function buildTurnItem(turn, index) {
  var it = el('div', 'turnitem');
  var idx = el('div', 'turnindex');
  var text = el('div', 'turntext');
  var title = el('div', 'turntitle');
  var meta = el('div', 'turnmeta');
  title.textContent = turn.title || ('Turn ' + (index + 1));
  idx.textContent = String(index + 1).padStart(2, '0');
  meta.textContent = turnMeta(turn);
  it.title = title.textContent + ' · ' + meta.textContent;
  text.appendChild(title);
  text.appendChild(meta);
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

function buildViewSwitcher(views, showView) {
  var seg = el('div', 'seg');
  var thumb = el('span', 'seg-thumb');
  var opts = [];
  seg.appendChild(thumb);
  views.forEach(function (view) {
    var opt = el('button', 'seg-opt');
    opt.textContent = view.kind;
    opt.onclick = function () { showView(view, opt); };
    opts.push(opt);
    seg.appendChild(opt);
  });
  return { seg: seg, thumb: thumb, opts: opts };
}

// Build one record's pane: optional record tabs + optional Chart/Data/Query
// switcher + one iframe. The first view loads up front; other views load on
// click.
function buildRecord(record, recOpts, opts) {
  var pane = el('div', 'recordpane');
  var bar = el('div', 'cardbar');
  var views = record.views || [];
  var showViewMenu = views.length > 1;
  var switcher = null;
  var shell = el('div', 'cardframe-shell');
  var frame = el('iframe', 'cardframe');
  var meta = el('div', 'viewmeta');
  var fixedFrame = opts && opts.fixedFrame;

  frame.scrolling = fixedFrame ? 'auto' : 'no';
  if (!fixedFrame) { autosize(frame); }
  shell.appendChild(frame);

  function showView(view, opt) {
    var shellClasses = 'cardframe-shell view-' + (view.kind || '').toLowerCase();
    if (fixedFrame) { shellClasses += ' fixed-frame'; }
    frame.src = '/' + view.file;
    meta.textContent = view.meta || '';
    shell.className = shellClasses;
    if (switcher) {
      switcher.opts.forEach(function (x) { x.classList.remove('active'); });
    }
    if (opt && switcher) {
      opt.classList.add('active');
      moveThumb(switcher.thumb, opt);
    }
  }

  if (recOpts) {
    bar.classList.add('multi-record');
    if (!showViewMenu) { bar.classList.add('no-view-menu'); }
    bar.appendChild(buildRecordTabs(recOpts.records, recOpts.activeIndex, recOpts.onSelect));
  } else if (record.label) {
    var label = el('span', 'cardlabel');
    label.textContent = record.label;
    bar.appendChild(label);
  }

  if (showViewMenu) {
    switcher = buildViewSwitcher(views, showView);
    bar.appendChild(switcher.seg);
  }
  if (bar.children.length) {
    pane.appendChild(bar);
  }
  pane.appendChild(shell);
  pane.appendChild(meta);

  if (views.length) {
    showView(views[0], switcher ? switcher.opts[0] : null);
    requestAnimationFrame(function () {
      syncRecordHeader(bar);
      if (switcher && switcher.opts[0]) {
        moveThumb(switcher.thumb, switcher.opts[0]);
        requestAnimationFrame(function () { switcher.thumb.classList.add('ready'); });
      }
    });
  }
  return pane;
}

// Render the active turn: the record's pane(s) directly (no card frame). A
// multi-result turn carries record tabs in each pane's header (left of the view
// segmented); panes are pre-built and toggled by visibility (flicker-free switch).
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
  if (!records.length) {
    return view;
  }
  if (records.length <= 1) {
    view.appendChild(buildRecord(records[0], null, { fixedFrame: isManualPreview(turn) }));
    return view;
  }
  var box = el('div', 'panesbox');
  var panes = [];
  function onSelect(i) {
    panes.forEach(function (pane, j) { pane.classList.toggle('hidden', j !== i); });
    requestAnimationFrame(function () { syncRecordHeaders(box); });
  }
  records.forEach(function (record, i) {
    var pane = buildRecord(record, { records: records, activeIndex: i, onSelect: onSelect });
    if (i !== 0) { pane.classList.add('hidden'); }
    box.appendChild(pane);
    panes.push(pane);
  });
  view.appendChild(box);
  return view;
}

// Turn navigator: the sidebar lists every turn; only the selected turn is
// rendered (iframes never accumulate). New turns are appended, and auto-selected
// only when you're already on the latest (so navigating back isn't interrupted).
var turns = [];
var activeTurn = -1;

function selectTurn(i) {
  if (i < 0 || i >= turns.length) { return; }
  activeTurn = i;
  var items = document.querySelectorAll('#turns .turnitem');
  for (var k = 0; k < items.length; k++) { items[k].classList.toggle('active', k === i); }
  var inner = document.getElementById('content-inner');
  inner.innerHTML = '';
  inner.classList.toggle('manual-preview-content', isManualPreview(turns[i]));
  inner.appendChild(renderTurn(turns[i]));
  if (!isManualPreview(turns[i])) {
    inner.appendChild(el('div', 'scroll-pad'));
  }
}

function poll() {
  fetch('/__index__').then(function (response) {
    return response.json();
  }).then(function (server) {
    if (server.length <= turns.length) { return; }
    var wasOnLatest = activeTurn === turns.length - 1;
    var sidebar = document.getElementById('turns');
    var sidebarEmpty = sidebar.querySelector('.turns-empty');
    if (sidebarEmpty) { sidebarEmpty.remove(); }
    for (var i = turns.length; i < server.length; i++) {
      turns.push(server[i]);
      var it = buildTurnItem(server[i], i);
      (function (idx) { it.onclick = function () { selectTurn(idx); }; })(i);
      sidebar.appendChild(it);
    }
    if (wasOnLatest) { selectTurn(turns.length - 1); }
  }).catch(function () {});
}

setInterval(poll, 1000);
poll();
