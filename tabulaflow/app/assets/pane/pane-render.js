(function () {
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

  function renderTable(container, recordData) {
    var tableData = recordData.table || {};
    var rows = (recordData.dataset && recordData.dataset.rows) || [];
    var displayCap = tableData.displayCap || 120;
    var wrapClass = rows.length <= 12 ? 'tf-table-wrap pane-short' : 'tf-table-wrap';
    container.className = 'tf-view tf-table-view';
    container.innerHTML = '<div class="' + wrapClass + '"><div class="tf-table"></div></div>'
      + '<div class="tf-modal" role="dialog" aria-hidden="true">'
      + '<div class="tf-modal-card"><div class="tf-modal-header">'
      + '<span class="tf-modal-title"></span><button class="tf-modal-close" type="button" aria-label="Close">'
      + '<svg viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>'
      + '</button></div><div class="tf-modal-body"></div></div></div>';

    var modal = container.querySelector('.tf-modal');
    var modalBody = container.querySelector('.tf-modal-body');
    var modalTitle = container.querySelector('.tf-modal-title');
    var closeBtn = container.querySelector('.tf-modal-close');
    function openModal(title, text) {
      modalTitle.textContent = title || '';
      var pre = document.createElement('pre');
      pre.textContent = maybeFormatJson(text);
      modalBody.innerHTML = '';
      modalBody.appendChild(pre);
      modal.classList.add('open');
    }
    function openModalImage(title, src) {
      modalTitle.textContent = title || '';
      modalBody.innerHTML = '';
      var img = document.createElement('img');
      img.src = src;
      modalBody.appendChild(img);
      modal.classList.add('open');
    }
    function closeModal() {
      modal.classList.remove('open');
      modalBody.innerHTML = '';
    }
    modal.addEventListener('click', function (e) { if (e.target === modal) closeModal(); });
    closeBtn.addEventListener('click', closeModal);

    var formatters = {
      text: function (cell) {
        var v = cell.getValue();
        if (v == null) return '';
        if (typeof v === 'number') return escapeHtml(formatNumber(v));
        var s = String(v);
        var urls = asUrls(s);
        if (urls) {
          if (s.trim().charAt(0) === '[') {
            return '[' + urls.map(function (u) { return '"' + link(u, u) + '"'; }).join(', ') + ']';
          }
          if (urls.length === 1) {
            var u0 = urls[0];
            var label = u0.length <= displayCap ? u0 : u0.substring(0, displayCap) + '\u2026';
            return link(u0, label);
          }
          return urls.map(function (u) { return link(u, u); }).join(', ');
        }
        var hasNewline = s.indexOf('\n') >= 0;
        if (s.length <= displayCap && !hasNewline) return escapeHtml(s);
        var head = s.substring(0, displayCap).replace(/\n/g, ' ');
        if (s.length > displayCap) return '<div class="trunc">' + escapeHtml(head) + '</div>';
        return '<span class="multiline">' + escapeHtml(head) + '</span>';
      },
      media: function (cell) { return renderMedia(cell.getValue()); },
      num: function (cell) {
        var v = cell.getValue();
        return v == null ? '' : escapeHtml(formatNumber(v));
      },
      bool: function (cell) {
        var v = cell.getValue();
        if (v == null) return '';
        return v ? '<span class="bool-yes">\u2714</span>' : '<span class="bool-no">\u2718</span>';
      }
    };

    function boolNullLastSorter(a, b, aRow, bRow, column, dir) {
      var aNull = a == null, bNull = b == null;
      if (aNull && bNull) return 0;
      if (aNull) return dir === 'asc' ? 1 : -1;
      if (bNull) return dir === 'asc' ? -1 : 1;
      return (a === b) ? 0 : (a ? 1 : -1);
    }

    var cols = clone(tableData.columns || []);
    cols.forEach(function (col) {
      if (col.sorter === 'boolean') col.sorter = boolNullLastSorter;
      if (typeof col.formatter === 'string' && formatters[col.formatter]) {
        var name = col.formatter;
        col.formatter = formatters[name];
        if (name === 'text') {
          col.cellClick = function (e, cell) {
            var v = cell.getValue();
            if (typeof v !== 'string' || asUrls(v)) return;
            if (v.length > displayCap || v.indexOf('\n') >= 0) {
              openModal(cell.getColumn().getDefinition().title, v);
            }
          };
        }
        if (name === 'media') {
          col.cellClick = function (e, cell) {
            var value = cell.getValue();
            if (value && value.kind === 'media' && String(value.mime || '').indexOf('image/') === 0) {
              openModalImage(cell.getColumn().getDefinition().title, value.src);
            }
          };
        }
      }
    });

    var fixedMax = tableData.maxHeight == null ? null : tableData.maxHeight;
    var fixedPanel = container.closest && container.closest('.manual-preview');
    var panelShell = fixedPanel && container.closest('.view-shell');
    var panelHeight = panelShell ? Math.floor(panelShell.getBoundingClientRect().height) : 0;
    var viewportCap = panelHeight > 0 ? panelHeight : (fixedMax != null ? fixedMax : Math.max(240, window.innerHeight));
    var estimatedTableHeight = 38 + rows.length * 29;
    var opts = {
      data: rows,
      columns: cols,
      layout: 'fitColumns',
      renderVerticalBuffer: 600,
      movableColumns: false,
      selectableRange: 1,
      selectableRangeColumns: true,
      selectableRangeRows: true,
      selectableRangeClearCells: true,
      clipboard: true,
      clipboardCopyStyled: false,
      clipboardCopyRowRange: 'range',
      clipboardCopyConfig: { rowHeaders: false, columnHeaders: false },
      rowHeader: {
        resizable: false,
        frozen: true,
        headerSort: false,
        formatter: 'rownum',
        hozAlign: 'right',
        width: tableData.rowHeaderWidth || 44,
        cssClass: 'tabulator-row-header'
      }
    };
    var shouldConstrainHeight = panelHeight > 0 || rows.length > 100 || (fixedMax != null && estimatedTableHeight > viewportCap);
    if (shouldConstrainHeight) opts.height = viewportCap;
    var table = new Tabulator(container.querySelector('.tf-table'), opts);
    function fitFixedPanelHeight() {
      if (!panelShell || !table.setHeight) return;
      var height = Math.floor(panelShell.getBoundingClientRect().height);
      if (height > 0) table.setHeight(height);
    }
    if (panelShell) {
      requestAnimationFrame(function () {
        fitFixedPanelHeight();
        requestAnimationFrame(fitFixedPanelHeight);
      });
    }
    if (tableData.hasMedia) {
      window.setTimeout(function () { table.redraw(true); }, 0);
    }
    return { destroy: function () { table.destroy(); closeModal(); } };
  }

  function renderChart(container, recordData) {
    var chartData = recordData.chart || {};
    var rows = (recordData.dataset && recordData.dataset.rows) || [];
    var spec = clone(chartData.spec || {});
    spec.data = { values: rows };
    container.className = 'tf-view tf-chart-view';
    container.innerHTML = '<div class="tf-vis-stage"><div class="tf-vis-wrap '
      + escapeAttr(chartData.wrapClass || 'content') + '"><div class="tf-vis"></div></div></div>';
    var view = null;
    var disposed = false;
    vegaEmbed(container.querySelector('.tf-vis'), spec, {
      renderer: chartData.renderer || 'svg',
      tooltip: { theme: 'dark' },
      actions: { export: true, source: false, compiled: false, editor: false }
    }).then(function (result) {
      view = result.view;
      if (disposed && view) view.finalize();
    }).catch(function (err) {
      var pre = document.createElement('pre');
      pre.className = 'vis-error';
      pre.textContent = 'Chart error: ' + String(err);
      container.innerHTML = '';
      container.appendChild(pre);
    });
    return { destroy: function () { disposed = true; if (view) view.finalize(); } };
  }

  var mapDefaultColor = cssVar('--map-default', '#4285f4');
  var mapRouteColor = cssVar('--map-route', '#1558d6');
  var mapPalette = [
    cssVar('--map-category-0', mapDefaultColor),
    cssVar('--map-category-1', '#ea4335'),
    cssVar('--map-category-2', '#fbbc04'),
    cssVar('--map-category-3', '#34a853'),
    cssVar('--map-category-4', '#a142f4'),
    cssVar('--map-category-5', '#fbbc54'),
    cssVar('--map-category-6', '#46bdc6'),
    cssVar('--map-category-7', '#7cb342')
  ];
  var mapPinDefaultColor = cssVar('--map-pin-default', '#ea4335');
  var mapPinTop = cssVar('--map-pin-top', '#ff6f61');
  var mapPinBottom = cssVar('--map-pin-bottom', '#d93025');
  var mapPinOutline = cssVar('--map-pin-outline', '#a52714');
  var mapPinHole = cssVar('--map-pin-hole', '#f8fafc');
  var mapPinInner = cssVar('--map-pin-inner', '#fff4f2');
  var mapStyleUrl = '/assets/maplibre/shortbread-light.json';
  var mapStyleSpriteUrl = '/assets/maplibre/osm-bright-sprite';
  var mapStyleRouteSpriteUrl = '/assets/maplibre/tf-route-sprite';
  var maxLegendEntries = 12;

  function absoluteUrl(path) {
    return new URL(path, window.location.href).href;
  }

  function hexRgb(value) {
    var text = String(value || '').trim();
    var match = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(text);
    if (!match) return null;
    var hex = match[1];
    if (hex.length === 3) {
      hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
    }
    return {
      r: parseInt(hex.slice(0, 2), 16),
      g: parseInt(hex.slice(2, 4), 16),
      b: parseInt(hex.slice(4, 6), 16)
    };
  }

  function hexChannel(value) {
    var text = Math.round(Math.max(0, Math.min(255, value))).toString(16);
    return text.length === 1 ? '0' + text : text;
  }

  function mixHex(a, b, amount) {
    var left = hexRgb(a);
    var right = hexRgb(b);
    if (!left || !right) return a;
    return '#'
      + hexChannel(left.r + (right.r - left.r) * amount)
      + hexChannel(left.g + (right.g - left.g) * amount)
      + hexChannel(left.b + (right.b - left.b) * amount);
  }

  function pinColorRamp(color) {
    var base = hexRgb(color) ? String(color).trim() : mapPinBottom;
    if (!hexRgb(base)) {
      return { top: mapPinTop, bottom: mapPinBottom, outline: mapPinOutline };
    }
    return {
      top: mixHex(base, '#ffffff', 0.46),
      bottom: base,
      outline: mixHex(base, '#000000', 0.24)
    };
  }

  function mapPinSvg(color) {
    var ramp = pinColorRamp(color);
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="25" height="41" viewBox="0 0 25 41">'
      + '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
      + '<stop offset="0" stop-color="' + ramp.top + '"/><stop offset="1" stop-color="' + ramp.bottom + '"/></linearGradient></defs>'
      + '<path fill="' + ramp.outline + '" d="M12.5 0C5.6 0 0 5.6 0 12.5c0 8.9 12.5 28.5 12.5 28.5S25 21.4 25 12.5C25 5.6 19.4 0 12.5 0z"/>'
      + '<path fill="url(#g)" d="M12.5 1.25C6.3 1.25 1.25 6.3 1.25 12.5c0 7.9 8.9 22.6 11.25 26.2C14.85 35.1 23.75 20.4 23.75 12.5c0-6.2-5.05-11.25-11.25-11.25z"/>'
      + '<circle cx="12.5" cy="12.6" r="5.7" fill="' + mapPinHole + '"/>'
      + '<circle cx="12.5" cy="12.6" r="4.2" fill="' + mapPinInner + '"/>'
      + '</svg>';
    return 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg);
  }

  function mapPinElement(color, scale, title) {
    var node = document.createElement('div');
    var width = Math.round(25 * scale);
    var height = Math.round(41 * scale);
    node.className = 'tf-map-pin';
    node.style.width = width + 'px';
    node.style.height = height + 'px';
    node.style.backgroundImage = 'url("' + mapPinSvg(color) + '")';
    if (title) node.setAttribute('aria-label', title);
    return node;
  }

  function mapLayers(mapData) {
    if (Array.isArray(mapData.layers)) return mapData.layers;
    return [];
  }

  function fieldLabels(recordData) {
    var out = {};
    var cols = (recordData.table && recordData.table.columns) || [];
    cols.forEach(function (col) {
      if (col && col.field) out[String(col.field)] = String(col.title || col.field);
    });
    return out;
  }

  function safeScalar(value) {
    return value == null || ['string', 'number', 'boolean'].indexOf(typeof value) !== -1;
  }

  function tooltipFields(tooltip, row) {
    if (tooltip === true) {
      return Object.keys(row || {}).filter(function (key) { return safeScalar(row[key]); }).slice(0, 8);
    }
    if (Array.isArray(tooltip)) return tooltip.filter(function (field) { return typeof field === 'string' && field; });
    if (typeof tooltip === 'string' && tooltip) return [tooltip];
    return [];
  }

  function detailValueHtml(value) {
    var text = displayValue(value);
    var urls = typeof value === 'string' ? asUrls(text) : null;
    if (urls) {
      if (text.trim().charAt(0) === '[') {
        return '[' + urls.map(function (u) { return '"' + tooltipLink(u) + '"'; }).join(', ') + ']';
      }
      if (urls.length === 1) return tooltipLink(urls[0]);
      return urls.map(function (u) { return tooltipLink(u); }).join(' ');
    }
    return escapeHtml(text);
  }

  function detailHtml(row, tooltip, labels, fallback, labelField) {
    var fields = tooltipFields(tooltip, row);
    var label = fallback == null ? '' : displayValue(fallback);
    if (labelField) {
      fields = fields.filter(function (field) { return field !== labelField; });
    }
    var rows = '';
    fields.forEach(function (field) {
      var value = fieldValue(row, field);
      if (value == null || !safeScalar(value)) return;
      rows += '<tr><th>' + escapeHtml(labels[field] || field) + '</th><td>' + detailValueHtml(value) + '</td></tr>';
    });
    if (!label && !rows) return '';
    var html = '<div class="tf-map-popup">';
    if (label) html += '<div class="tf-map-popup-title">' + escapeHtml(label) + '</div>';
    if (rows) html += '<table>' + rows + '</table>';
    return html + '</div>';
  }

  function encodingField(encoding) {
    return encoding && typeof encoding === 'object' && !Array.isArray(encoding) && typeof encoding.field === 'string'
      ? encoding.field : '';
  }

  function colorFor(encoding, row, fallback) {
    if (!encoding || typeof encoding !== 'object' || Array.isArray(encoding)) return fallback;
    var field = encodingField(encoding);
    if (!field) return fallback;
    var value = fieldValue(row, field);
    if (Array.isArray(encoding.domain)) {
      var index = encoding.domain.map(String).indexOf(String(value));
      if (index >= 0) return mapPalette[index % mapPalette.length];
    }
    var text = String(value == null ? '' : value);
    var hash = 0;
    for (var i = 0; i < text.length; i++) hash = ((hash * 31) + text.charCodeAt(i)) >>> 0;
    return mapPalette[hash % mapPalette.length];
  }

  function legendValues(encoding, items) {
    var field = encodingField(encoding);
    if (!field) return null;
    var seen = {};
    var values = [];
    items.forEach(function (item) {
      var row = item && item.properties ? item.properties : item;
      var value = fieldValue(row, field);
      if (value == null) return;
      var key = String(value);
      if (seen[key]) return;
      seen[key] = true;
      values.push(value);
    });
    if (Array.isArray(encoding.domain)) {
      return encoding.domain.filter(function (value) { return seen[String(value)]; }).slice(0, maxLegendEntries + 1);
    }
    return values;
  }

  function legendSwatchTypeForFeatures(features) {
    var hasLine = false;
    var hasPolygon = false;
    var hasPoint = false;
    features.forEach(function (feature) {
      var type = geometryType(feature);
      if (type === 'LineString' || type === 'MultiLineString') hasLine = true;
      else if (type === 'Polygon' || type === 'MultiPolygon') hasPolygon = true;
      else if (type === 'Point' || type === 'MultiPoint') hasPoint = true;
    });
    var kinds = (hasLine ? 1 : 0) + (hasPolygon ? 1 : 0) + (hasPoint ? 1 : 0);
    if (kinds !== 1) return 'square';
    if (hasLine) return 'line';
    if (hasPolygon) return 'polygon';
    return 'circle';
  }

  function buildLegendSection(layer, items, labels, swatchType, fallbackColor) {
    var encoding = layer && layer.color;
    var field = encodingField(encoding);
    if (!field) return null;
    var values = legendValues(encoding, items);
    if (!values || values.length < 2 || values.length > maxLegendEntries) return null;
    var entries = values.map(function (value) {
      var row = {};
      row[field] = value;
      return {
        label: displayValue(value),
        color: colorFor(encoding, row, fallbackColor)
      };
    });
    return {
      title: labels[field] || field,
      swatchType: swatchType,
      entries: entries
    };
  }

  function clearLegend(container) {
    if (!container) return;
    container.querySelectorAll('.tf-map-legend').forEach(function (node) { node.remove(); });
  }

  function renderLegend(container, sections) {
    clearLegend(container);
    if (!sections.length) return;
    var html = '';
    sections.forEach(function (section) {
      html += '<section class="tf-map-legend-section"><div class="tf-map-legend-title">'
        + escapeHtml(section.title) + '</div>';
      section.entries.forEach(function (entry) {
        var swatch = '<span class="tf-map-legend-swatch tf-map-legend-swatch-' + section.swatchType
          + '" style="--legend-color:' + escapeHtml(entry.color) + '"></span>';
        html += '<div class="tf-map-legend-item">' + swatch + '<span class="tf-map-legend-label">'
          + escapeHtml(entry.label) + '</span></div>';
      });
      html += '</section>';
    });
    var node = document.createElement('div');
    node.className = 'tf-map-legend';
    node.innerHTML = html;
    container.appendChild(node);
  }

  function sizeFor(encoding, row, rows, fallback) {
    if (!encoding || typeof encoding !== 'object' || Array.isArray(encoding)) return fallback;
    var field = encodingField(encoding);
    if (!field) return fallback;
    var value = numberValue(fieldValue(row, field));
    if (value == null) return fallback;
    var minSize = 5;
    var maxSize = 18;
    var values = rows.map(function (r) { return numberValue(fieldValue(r, field)); })
      .filter(function (v) { return v != null; });
    if (!values.length) return fallback;
    var min = Math.min.apply(Math, values);
    var max = Math.max.apply(Math, values);
    if (max === min) return (minSize + maxSize) / 2;
    return minSize + ((value - min) / (max - min)) * (maxSize - minSize);
  }

  function parseGeoJson(value) {
    if (!value) return null;
    if (typeof value === 'string') {
      try { return JSON.parse(value); } catch (e) { return null; }
    }
    if (typeof value === 'object') return clone(value);
    return null;
  }

  function mergeFeatureProperties(geojson, row) {
    if (!geojson || typeof geojson !== 'object') return null;
    if (geojson.type === 'Feature') {
      geojson.properties = Object.assign({}, row || {}, geojson.properties || {});
      return geojson;
    }
    if (geojson.type === 'FeatureCollection' && Array.isArray(geojson.features)) {
      geojson.features = geojson.features.map(function (feature) {
        return mergeFeatureProperties(feature, row);
      }).filter(Boolean);
      return geojson;
    }
    if (geojson.type) {
      return { type: 'Feature', geometry: geojson, properties: Object.assign({}, row || {}) };
    }
    return null;
  }

  function geometryType(feature) {
    return feature && feature.geometry && typeof feature.geometry.type === 'string' ? feature.geometry.type : '';
  }

  function isLineFeature(feature) {
    var type = geometryType(feature);
    return type === 'LineString' || type === 'MultiLineString';
  }

  function featureCollection(features) {
    return { type: 'FeatureCollection', features: features };
  }

  function appendGeoJsonFeatures(out, geojson) {
    if (!geojson || typeof geojson !== 'object') return;
    if (geojson.type === 'FeatureCollection' && Array.isArray(geojson.features)) {
      geojson.features.forEach(function (feature) { appendGeoJsonFeatures(out, feature); });
      return;
    }
    if (geojson.type === 'Feature' && geojson.geometry) {
      out.push(geojson);
      return;
    }
    if (geojson.type && geojson.coordinates) {
      out.push({ type: 'Feature', geometry: geojson, properties: {} });
    }
  }

  function extendLngLat(bounds, lng, lat) {
    if (lat == null || lng == null) return false;
    if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return false;
    bounds.extend([lng, lat]);
    return true;
  }

  function extendCoordinateBounds(bounds, coords) {
    if (!Array.isArray(coords)) return false;
    if (coords.length >= 2 && typeof coords[0] !== 'object') {
      return extendLngLat(bounds, numberValue(coords[0]), numberValue(coords[1]));
    }
    var any = false;
    coords.forEach(function (item) {
      if (extendCoordinateBounds(bounds, item)) any = true;
    });
    return any;
  }

  function extendFeatureBounds(bounds, feature) {
    return !!(feature && feature.geometry && extendCoordinateBounds(bounds, feature.geometry.coordinates));
  }

  function collectCoordinateBounds(coords, state) {
    if (!Array.isArray(coords)) return false;
    if (coords.length >= 2 && typeof coords[0] !== 'object') {
      var lng = numberValue(coords[0]);
      var lat = numberValue(coords[1]);
      if (lat == null || lng == null) return false;
      if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return false;
      state.minLng = Math.min(state.minLng, lng);
      state.maxLng = Math.max(state.maxLng, lng);
      state.minLat = Math.min(state.minLat, lat);
      state.maxLat = Math.max(state.maxLat, lat);
      return true;
    }
    var any = false;
    coords.forEach(function (item) {
      if (collectCoordinateBounds(item, state)) any = true;
    });
    return any;
  }

  function geometryAnchor(geometry) {
    if (!geometry || !Array.isArray(geometry.coordinates)) return null;
    var state = { minLng: Infinity, maxLng: -Infinity, minLat: Infinity, maxLat: -Infinity };
    if (!collectCoordinateBounds(geometry.coordinates, state)) return null;
    return [(state.minLng + state.maxLng) / 2, (state.minLat + state.maxLat) / 2];
  }

  function buildPointFeatures(layer, rows, labels) {
    var pointRows = Array.isArray(layer.points) ? layer.points : rows;
    var latField = Array.isArray(layer.points) ? 'lat' : String(layer.lat || '');
    var lngField = Array.isArray(layer.points) ? 'lng' : String(layer.lng || '');
    var labelField = String(layer.label || '');
    var markerType = layer.marker && layer.marker.type === 'circle' ? 'circle' : 'pin';
    var features = [];
    if (!latField || !lngField) return { features: features, markerType: markerType, rows: pointRows };
    pointRows.forEach(function (row) {
      var lat = numberValue(fieldValue(row, latField));
      var lng = numberValue(fieldValue(row, lngField));
      if (lat == null || lng == null) return;
      if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return;
      var label = fieldValue(row, labelField);
      var tooltip = layer.tooltip || labelField;
      var popup = detailHtml(row, tooltip, labels, label, labelField);
      var color = colorFor(layer.color, row, markerType === 'pin' ? mapPinDefaultColor : mapDefaultColor);
      var radius = sizeFor(layer.size, row, pointRows, 6);
      var pinScale = Math.max(0.8, Math.min(1.45, radius / 6));
      features.push({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [lng, lat] },
        properties: Object.assign({}, row || {}, {
          __tfColor: color,
          __tfSize: radius,
          __tfPinScale: pinScale,
          __tfPinHitRadius: Math.max(24, 26 * pinScale),
          __tfPopup: popup,
          __tfTitle: label == null ? '' : displayValue(label),
          __tfMarker: markerType,
          __tfAnchorLng: lng,
          __tfAnchorLat: lat
        })
      });
    });
    return { features: features, markerType: markerType, rows: pointRows };
  }

  function buildGeoJsonFeatures(layer, rows, labels) {
    var raw = [];
    if (typeof layer.geojson === 'string') {
      rows.forEach(function (row) {
        var parsed = mergeFeatureProperties(parseGeoJson(fieldValue(row, layer.geojson)), row);
        appendGeoJsonFeatures(raw, parsed);
      });
    } else {
      appendGeoJsonFeatures(raw, mergeFeatureProperties(parseGeoJson(layer.geojson), {}));
    }
    return raw.map(function (feature) {
      var props = feature && feature.properties ? feature.properties : {};
      var line = isLineFeature(feature);
      var label = fieldValue(props, layer.label);
      var popup = detailHtml(props, layer.tooltip || layer.label, labels, label, layer.label);
      var color = colorFor(layer.color, props, line ? mapRouteColor : mapDefaultColor);
      var anchor = geometryAnchor(feature.geometry);
      return {
        type: 'Feature',
        geometry: feature.geometry,
        properties: Object.assign({}, props, {
          __tfColor: color,
          __tfLineWidth: line ? 5 : 2,
          __tfPopup: popup,
          __tfAnchorLng: anchor ? anchor[0] : null,
          __tfAnchorLat: anchor ? anchor[1] : null
        })
      };
    });
  }

  function mapFeaturePopup(feature) {
    return feature && feature.properties ? String(feature.properties.__tfPopup || '') : '';
  }

  function firstPopupFeature(features) {
    if (!Array.isArray(features)) return null;
    for (var i = 0; i < features.length; i++) {
      if (mapFeaturePopup(features[i])) return features[i];
    }
    return null;
  }

  function mapFeatureAnchor(feature, fallback) {
    var props = feature && feature.properties ? feature.properties : {};
    var lng = numberValue(props.__tfAnchorLng);
    var lat = numberValue(props.__tfAnchorLat);
    if (lng != null && lat != null) return [lng, lat];
    var anchor = feature && feature.geometry ? geometryAnchor(feature.geometry) : null;
    return anchor || fallback;
  }

  function renderMapPopup(map, lngLat, html, className, closeButton) {
    if (!html || !window.maplibregl) return null;
    return new maplibregl.Popup({
      closeButton: !!closeButton,
      closeOnClick: !!closeButton,
      className: className,
      maxWidth: '420px',
      offset: 12
    }).setLngLat(lngLat).setHTML(html).addTo(map);
  }

  function clearHoverPopup(map, popupState) {
    if (popupState.hoverCloseTimer) {
      clearTimeout(popupState.hoverCloseTimer);
      popupState.hoverCloseTimer = null;
    }
    map.getCanvas().style.cursor = '';
    if (popupState.hover) popupState.hover.remove();
    popupState.hover = null;
    popupState.hoverHtml = '';
    popupState.hoverAnchor = '';
    popupState.hoverOverFeature = false;
    popupState.hoverOverPopup = false;
  }

  function scheduleHoverPopupClose(map, popupState) {
    popupState.hoverOverFeature = false;
    if (popupState.hoverOverPopup) return;
    if (popupState.hoverCloseTimer) clearTimeout(popupState.hoverCloseTimer);
    popupState.hoverCloseTimer = setTimeout(function () {
      popupState.hoverCloseTimer = null;
      if (!popupState.hoverOverFeature && !popupState.hoverOverPopup) {
        clearHoverPopup(map, popupState);
      }
    }, 60);
  }

  function bindHoverPopupPointer(map, popup, popupState) {
    var element = popup && popup.getElement ? popup.getElement() : null;
    if (!element) return;
    element.addEventListener('mouseenter', function () {
      popupState.hoverOverPopup = true;
      if (popupState.hoverCloseTimer) {
        clearTimeout(popupState.hoverCloseTimer);
        popupState.hoverCloseTimer = null;
      }
    });
    element.addEventListener('mouseleave', function () {
      popupState.hoverOverPopup = false;
      scheduleHoverPopupClose(map, popupState);
    });
  }

  function syncHoverPopup(map, lngLat, html, popupState) {
    if (popupState.click) {
      clearHoverPopup(map, popupState);
      return;
    }
    map.getCanvas().style.cursor = 'pointer';
    popupState.hoverOverFeature = true;
    if (popupState.hoverCloseTimer) {
      clearTimeout(popupState.hoverCloseTimer);
      popupState.hoverCloseTimer = null;
    }
    var hoverAnchor = JSON.stringify(lngLat);
    if (!popupState.hover || popupState.hoverHtml !== html || popupState.hoverAnchor !== hoverAnchor) {
      if (popupState.hover) popupState.hover.remove();
      popupState.hover = renderMapPopup(map, lngLat, html, 'tf-map-detail-tooltip', false);
      bindHoverPopupPointer(map, popupState.hover, popupState);
      popupState.hoverHtml = html;
      popupState.hoverAnchor = hoverAnchor;
      return;
    }
  }

  function setClickPopup(map, lngLat, html, popupState) {
    if (popupState.hoverCloseTimer) {
      clearTimeout(popupState.hoverCloseTimer);
      popupState.hoverCloseTimer = null;
    }
    if (popupState.hover) popupState.hover.remove();
    if (popupState.click) popupState.click.remove();
    popupState.hover = null;
    popupState.hoverHtml = '';
    popupState.hoverAnchor = '';
    popupState.hoverOverFeature = false;
    popupState.hoverOverPopup = false;
    var popup = renderMapPopup(map, lngLat, html, 'tf-map-detail-popup', true);
    popupState.click = popup;
    if (popup && popup.on) {
      popup.on('close', function () {
        if (popupState.click === popup) popupState.click = null;
      });
    }
  }

  function bindLayerDetails(map, layerIds, popupState) {
    if (!layerIds.length) return;
    map.on('mousemove', function (event) {
      var feature = firstPopupFeature(map.queryRenderedFeatures(event.point, { layers: layerIds }));
      var html = mapFeaturePopup(feature);
      if (!html) {
        scheduleHoverPopupClose(map, popupState);
        return;
      }
      syncHoverPopup(map, mapFeatureAnchor(feature, event.lngLat), html, popupState);
    });
    map.on('mouseleave', function () {
      scheduleHoverPopupClose(map, popupState);
    });
    map.on('click', function (event) {
      var feature = firstPopupFeature(map.queryRenderedFeatures(event.point, { layers: layerIds }));
      var html = mapFeaturePopup(feature);
      if (!html) return;
      setClickPopup(map, mapFeatureAnchor(feature, event.lngLat), html, popupState);
    });
  }

  function addCircleLayer(map, id, sourceId) {
    map.addLayer({
      id: id,
      type: 'circle',
      source: sourceId,
      paint: {
        'circle-radius': ['coalesce', ['get', '__tfSize'], 6],
        'circle-color': ['coalesce', ['get', '__tfColor'], mapDefaultColor],
        'circle-opacity': 0.86,
        'circle-stroke-color': '#ffffff',
        'circle-stroke-width': 1.2,
        'circle-stroke-opacity': 0.9
      }
    });
  }

  function addPinHitLayer(map, id, sourceId) {
    map.addLayer({
      id: id,
      type: 'circle',
      source: sourceId,
      paint: {
        'circle-radius': ['coalesce', ['get', '__tfPinHitRadius'], 26],
        'circle-color': '#000000',
        'circle-opacity': 0,
        'circle-stroke-opacity': 0,
        'circle-translate': [0, -20]
      }
    });
  }

  function addGeoJsonLayers(map, id, sourceId) {
    map.addLayer({
      id: id + '-fill',
      type: 'fill',
      source: sourceId,
      filter: ['match', ['geometry-type'], ['Polygon', 'MultiPolygon'], true, false],
      paint: {
        'fill-color': ['coalesce', ['get', '__tfColor'], mapDefaultColor],
        'fill-opacity': 0.24
      }
    });
    map.addLayer({
      id: id + '-outline',
      type: 'line',
      source: sourceId,
      filter: ['match', ['geometry-type'], ['Polygon', 'MultiPolygon'], true, false],
      paint: {
        'line-color': ['coalesce', ['get', '__tfColor'], mapDefaultColor],
        'line-opacity': 0.78,
        'line-width': 2
      }
    });
    map.addLayer({
      id: id + '-line',
      type: 'line',
      source: sourceId,
      filter: ['match', ['geometry-type'], ['LineString', 'MultiLineString'], true, false],
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: {
        'line-color': ['coalesce', ['get', '__tfColor'], mapRouteColor],
        'line-opacity': 0.95,
        'line-width': ['coalesce', ['get', '__tfLineWidth'], 5]
      }
    });
    map.addLayer({
      id: id + '-point',
      type: 'circle',
      source: sourceId,
      filter: ['match', ['geometry-type'], ['Point', 'MultiPoint'], true, false],
      paint: {
        'circle-radius': 6,
        'circle-color': ['coalesce', ['get', '__tfColor'], mapDefaultColor],
        'circle-opacity': 0.86,
        'circle-stroke-color': '#ffffff',
        'circle-stroke-width': 1.2
      }
    });
    return [id + '-fill', id + '-outline', id + '-line', id + '-point'];
  }

  function renderMap(container, recordData) {
    var mapData = recordData.map || {};
    var rows = (recordData.dataset && recordData.dataset.rows) || [];
    var layers = mapLayers(mapData);
    var labels = fieldLabels(recordData);
    container.className = 'tf-view tf-map-view';
    container.innerHTML = '<div class="tf-map-stage"><div class="tf-map"></div><div class="tf-map-empty"></div></div>';
    var mapNode = container.querySelector('.tf-map');
    var emptyNode = container.querySelector('.tf-map-empty');
    var stageNode = container.querySelector('.tf-map-stage');

    function showEmpty(message) {
      emptyNode.textContent = message;
      emptyNode.classList.add('show');
    }

    function hideEmpty() {
      emptyNode.textContent = '';
      emptyNode.classList.remove('show');
    }

    if (!window.maplibregl) {
      showEmpty('MapLibre GL is not available.');
      return { destroy: function () { container.innerHTML = ''; } };
    }
    if (!layers.length) {
      showEmpty('Map needs at least one layer.');
      return { destroy: function () { container.innerHTML = ''; } };
    }

    var map = null;
    var mapLoaded = false;
    var mapInitPending = false;
    var mapInitToken = 0;
    var markers = [];
    var dataBounds = null;
    var popupState = {
      hover: null,
      hoverHtml: '',
      hoverAnchor: '',
      hoverOverFeature: false,
      hoverOverPopup: false,
      hoverCloseTimer: null,
      click: null
    };
    var detailLayerIds = [];
    var legendSections = [];

    function addDataLayers() {
      dataBounds = new maplibregl.LngLatBounds();
      detailLayerIds = [];
      legendSections = [];
      clearLegend(stageNode);
      var hasBounds = false;
      layers.forEach(function (layer, index) {
        if (!layer || layer.type === 'points') {
          var pointData = buildPointFeatures(layer || {}, rows, labels);
          if (!pointData.features.length) return;
          var sourceId = 'tf-points-' + index;
          map.addSource(sourceId, { type: 'geojson', data: featureCollection(pointData.features) });
          pointData.features.forEach(function (feature) {
            if (extendFeatureBounds(dataBounds, feature)) hasBounds = true;
          });
          if (pointData.markerType === 'circle') {
            var circleId = sourceId + '-circle';
            addCircleLayer(map, circleId, sourceId);
            detailLayerIds.push(circleId);
          } else {
            var pinHitId = sourceId + '-pin-hit';
            addPinHitLayer(map, pinHitId, sourceId);
            detailLayerIds.push(pinHitId);
            pointData.features.forEach(function (feature) {
              var props = feature.properties || {};
              var lngLat = feature.geometry.coordinates;
              var node = mapPinElement(props.__tfColor, props.__tfPinScale || 1, props.__tfTitle);
              var marker = new maplibregl.Marker({ element: node, anchor: 'bottom' })
                .setLngLat(lngLat)
                .addTo(map);
              markers.push(marker);
            });
          }
          var pointLegend = buildLegendSection(
            layer || {},
            pointData.features,
            labels,
            pointData.markerType === 'pin' ? 'pin' : 'circle',
            pointData.markerType === 'pin' ? mapPinDefaultColor : mapDefaultColor
          );
          if (pointLegend) legendSections.push(pointLegend);
          return;
        }
        if (layer.type === 'geojson') {
          var features = buildGeoJsonFeatures(layer, rows, labels);
          if (!features.length) return;
          var geoSourceId = 'tf-geojson-' + index;
          map.addSource(geoSourceId, { type: 'geojson', data: featureCollection(features) });
          features.forEach(function (feature) {
            if (extendFeatureBounds(dataBounds, feature)) hasBounds = true;
          });
          addGeoJsonLayers(map, geoSourceId, geoSourceId).forEach(function (layerId) {
            detailLayerIds.push(layerId);
          });
          var geoLegend = buildLegendSection(
            layer,
            features,
            labels,
            legendSwatchTypeForFeatures(features),
            mapDefaultColor
          );
          if (geoLegend) legendSections.push(geoLegend);
        }
      });
      bindLayerDetails(map, detailLayerIds, popupState);
      renderLegend(stageNode, legendSections);
      if (!hasBounds) dataBounds = null;
    }

    function syncView() {
      if (!map) return;
      map.resize();
      if (!mapLoaded) return;
      var view = mapData.view && typeof mapData.view === 'object' ? mapData.view : {};
      var fit = view.fit !== false;
      if (fit && dataBounds && !dataBounds.isEmpty()) {
        var north = dataBounds.getNorth();
        var south = dataBounds.getSouth();
        var east = dataBounds.getEast();
        var west = dataBounds.getWest();
        if (north === south && east === west) {
          map.setCenter([west, south]);
          map.setZoom(numberOr(view.zoom, 12));
        } else {
          map.fitBounds(dataBounds, { padding: 24, maxZoom: numberOr(view.maxZoom, 14), duration: 0 });
        }
        hideEmpty();
        return;
      }
      var center = Array.isArray(view.center) ? view.center : null;
      var centerLat = center ? numberValue(center[0]) : null;
      var centerLng = center ? numberValue(center[1]) : null;
      if (centerLat != null && centerLng != null) {
        map.setCenter([centerLng, centerLat]);
        map.setZoom(numberOr(view.zoom, 10));
        hideEmpty();
        return;
      }
      map.setCenter([0, 0]);
      map.setZoom(2);
      showEmpty('No valid coordinates in this result.');
    }

    function destroyMap() {
      if (popupState.hoverCloseTimer) {
        clearTimeout(popupState.hoverCloseTimer);
        popupState.hoverCloseTimer = null;
      }
      if (popupState.hover) popupState.hover.remove();
      if (popupState.click) popupState.click.remove();
      popupState.hover = null;
      popupState.hoverHtml = '';
      popupState.hoverAnchor = '';
      popupState.hoverOverFeature = false;
      popupState.hoverOverPopup = false;
      popupState.click = null;
      clearLegend(stageNode);
      markers.forEach(function (marker) { marker.remove(); });
      markers = [];
      detailLayerIds = [];
      legendSections = [];
      if (map) map.remove();
      map = null;
      mapLoaded = false;
      mapInitPending = false;
      mapInitToken += 1;
      dataBounds = null;
    }

    function initMap() {
      if (map || mapInitPending) return;
      mapInitPending = true;
      var initToken = ++mapInitToken;
      hideEmpty();
      fetch(mapStyleUrl).then(function (response) {
        if (!response.ok) throw new Error('Failed to load map style.');
        return response.json();
      }).then(function (style) {
        mapInitPending = false;
        if (initToken !== mapInitToken || map || !container.isConnected) return;
        style.sprite = [
          { id: 'default', url: absoluteUrl(mapStyleSpriteUrl) },
          { id: 'tf', url: absoluteUrl(mapStyleRouteSpriteUrl) }
        ];
        map = new maplibregl.Map({
          container: mapNode,
          style: style,
          center: [0, 0],
          zoom: 2,
          attributionControl: false
        });
        map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left');
        map.addControl(new maplibregl.AttributionControl({ compact: false }), 'bottom-right');
        map.once('load', function () {
          if (!map) return;
          mapLoaded = true;
          addDataLayers();
          syncView();
        });
        map.on('error', function (event) {
          if (event && event.error) showEmpty('Map error: ' + String(event.error.message || event.error));
        });
      }).catch(function (error) {
        mapInitPending = false;
        if (initToken !== mapInitToken) return;
        showEmpty('Map error: ' + String(error && error.message ? error.message : error));
      });
    }

    return {
      afterVisible: function () {
        initMap();
        requestAnimationFrame(function () {
          syncView();
          requestAnimationFrame(syncView);
        });
      },
      afterHidden: destroyMap,
      destroy: function () {
        destroyMap();
        container.innerHTML = '';
      }
    };
  }

  function renderQuery(container, recordData) {
    var queryData = recordData.query || {};
    var sql = String(queryData.sql || '');
    container.className = 'tf-view tf-query-view';
    container.innerHTML = '<section class="query-card"><div class="query-bar">'
      + '<span class="query-lang">' + escapeHtml(queryData.language || queryData.lexer || 'SQL') + '</span>'
      + '<button class="query-copy" type="button" data-copy-query aria-label="Copy query" title="Copy query">'
      + '<span class="copy-icon" aria-hidden="true"></span></button></div>'
      + String(queryData.html || '') + '</section>';
    var button = container.querySelector('[data-copy-query]');
    if (button) {
      button.addEventListener('click', function () {
        function done(ok) {
          button.setAttribute('aria-label', ok ? 'Copied query' : 'Copy failed');
          button.title = ok ? 'Copied' : 'Copy failed';
          window.setTimeout(function () {
            button.setAttribute('aria-label', 'Copy query');
            button.title = 'Copy query';
          }, 1200);
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(sql).then(function () { done(true); }, function () { done(false); });
        } else {
          done(false);
        }
      });
    }
    return { destroy: function () { container.innerHTML = ''; } };
  }

  window.TF = {
    renderTable: renderTable,
    renderChart: renderChart,
    renderMap: renderMap,
    renderQuery: renderQuery
  };
})();
