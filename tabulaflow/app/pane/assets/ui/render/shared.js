// @ts-check

function escapeHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function escapeAttr(s) {
  return escapeHtml(s).replace(/"/g, '&quot;');
}
function clone(value) {
  return JSON.parse(JSON.stringify(value));
}
function cssVar(name, fallback) {
  var styles = window.getComputedStyle ? window.getComputedStyle(document.documentElement) : null;
  var value = styles ? styles.getPropertyValue(name).trim() : '';
  return value || fallback;
}
function fmtSize(n) {
  if (n < 1024) return n + ' B';
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
  return (n / (1024 * 1024)).toFixed(1) + ' MB';
}
var fileIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"'
  + ' stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
  + '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
  + '<polyline points="14 2 14 8 20 8"/></svg>';

var artifactIconSpecs = {
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

function artifactIconMarkup(kind, className) {
  var specs = artifactIconSpecs[kind] || [];
  var cls = className ? ' class="' + escapeAttr(className) + '"' : '';
  var body = specs.map(function (spec) {
    var attrs = Object.keys(spec[1]).map(function (key) {
      return ' ' + key + '="' + escapeAttr(spec[1][key]) + '"';
    }).join('');
    return '<' + spec[0] + attrs + '/>';
  }).join('');
  return '<svg' + cls + ' viewBox="0 0 24 24" aria-hidden="true">' + body + '</svg>';
}

function fileLink(src, label, size, newTab) {
  var target = newTab ? ' target="_blank" rel="noopener"' : '';
  return '<a class="file-link" href="' + escapeAttr(src) + '"' + target + '>'
    + fileIcon + '<span>' + escapeHtml(label) + '</span>'
    + '<span class="file-size">' + escapeHtml(fmtSize(size || 0)) + '</span></a>';
}

function renderMedia(v) {
  if (!v || typeof v !== 'object' || v.kind !== 'media') {
    return v == null ? '' : escapeHtml(v);
  }
  var mime = String(v.mime || '');
  var src = String(v.src || '');
  var size = Number(v.size || 0);
  if (mime.indexOf('image/') === 0) return '<img src="' + escapeAttr(src) + '">';
  if (mime.indexOf('audio/') === 0) return '<audio controls preload="none" src="' + escapeAttr(src) + '"></audio>';
  if (mime.indexOf('video/') === 0) return '<video controls preload="none" src="' + escapeAttr(src) + '"></video>';
  if (mime === 'application/pdf') return fileLink(src, 'PDF', size, true);
  return fileLink(src, 'binary', size, false);
}

function asUrls(s) {
  var t = String(s).trim();
  function isUrl(u) { return /^https?:\/\/\S+$/.test(u); }
  if (t.charAt(0) === '[') {
    var arr;
    try { arr = JSON.parse(t); } catch (e) { return null; }
    if (!Array.isArray(arr) || !arr.length) return null;
    var out = [];
    for (var j = 0; j < arr.length; j++) {
      if (typeof arr[j] !== 'string' || !isUrl(arr[j].trim())) return null;
      out.push(arr[j].trim());
    }
    return out;
  }
  var toks = t.split(/\s+/);
  var urls = [];
  for (var i = 0; i < toks.length; i++) {
    var u = toks[i].replace(/[;,]+$/, '');
    if (u === '') continue;
    if (!isUrl(u)) return null;
    urls.push(u);
  }
  return urls.length ? urls : null;
}

function link(href, text) {
  return '<a class="cell-link" href="' + escapeAttr(href)
    + '" target="_blank" rel="noopener">' + escapeHtml(text) + '</a>';
}

function tooltipUrlLabel(url) {
  var text = String(url);
  if (text.length <= 56) return text;
  return text.slice(0, 40) + '...' + text.slice(-13);
}

function tooltipLink(href) {
  return '<a class="cell-link" href="' + escapeAttr(href)
    + '" title="' + escapeAttr(href)
    + '" target="_blank" rel="noopener">' + escapeHtml(tooltipUrlLabel(href)) + '</a>';
}

function numberValue(value) {
  if (value == null || typeof value === 'boolean') return null;
  if (typeof value === 'string' && value.trim() === '') return null;
  var n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function formatNumber(value) {
  var n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  if (Object.is(n, -0)) return '0';
  if (Number.isInteger(n)) return String(n);
  var abs = Math.abs(n);
  var text = abs !== 0 && (abs < 0.0001 || abs >= 1000000000)
    ? n.toExponential(6)
    : n.toPrecision(7);
  return text
    .replace(/(\.\d*?[1-9])0+(e[+-]?\d+)?$/, '$1$2')
    .replace(/\.0+(e[+-]?\d+)?$/, '$1')
    .replace(/e\+/, 'e');
}

function displayValue(value) {
  if (typeof value === 'number') return formatNumber(value);
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  return value == null ? '' : String(value);
}

function numberOr(value, fallback) {
  var n = numberValue(value);
  return n == null ? fallback : n;
}

function fieldValue(row, field) {
  if (!field || !row || typeof row !== 'object') return null;
  return row[field];
}

function maybeFormatJson(text) {
  if (typeof text !== 'string') return text;
  var trimmed = text.trim();
  if (trimmed.length < 2) return text;
  var first = trimmed[0];
  var last = trimmed[trimmed.length - 1];
  if ((first === '{' && last === '}') || (first === '[' && last === ']')) {
    try { return JSON.stringify(JSON.parse(trimmed), null, 2); } catch (e) { return text; }
  }
  return text;
}

function deepMerge(base, override) {
  var out = {};
  var key;
  for (key in base) {
    if (Object.prototype.hasOwnProperty.call(base, key)) out[key] = clone(base[key]);
  }
  for (key in override || {}) {
    if (!Object.prototype.hasOwnProperty.call(override, key)) continue;
    var left = out[key];
    var right = override[key];
    if (right && typeof right === 'object' && !Array.isArray(right)
        && left && typeof left === 'object' && !Array.isArray(left)) {
      out[key] = deepMerge(left, right);
    } else {
      out[key] = clone(right);
    }
  }
  return out;
}

export {
  artifactIconSpecs,
  artifactIconMarkup,
  escapeHtml,
  escapeAttr,
  clone,
  cssVar,
  fmtSize,
  fileLink,
  renderMedia,
  asUrls,
  link,
  tooltipUrlLabel,
  tooltipLink,
  numberValue,
  formatNumber,
  displayValue,
  numberOr,
  fieldValue,
  maybeFormatJson,
  deepMerge
};
