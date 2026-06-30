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

  function numberValue(value) {
    var n = Number(value);
    return Number.isFinite(n) ? n : null;
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

  function mapMarkerIcon() {
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="25" height="41" viewBox="0 0 25 41">'
      + '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
      + '<stop offset="0" stop-color="#5bd0a8"/><stop offset="1" stop-color="#2f9a74"/></linearGradient></defs>'
      + '<path fill="#1f7c5d" d="M12.5 0C5.6 0 0 5.6 0 12.5c0 8.9 12.5 28.5 12.5 28.5S25 21.4 25 12.5C25 5.6 19.4 0 12.5 0z"/>'
      + '<path fill="url(#g)" d="M12.5 1.25C6.3 1.25 1.25 6.3 1.25 12.5c0 7.9 8.9 22.6 11.25 26.2C14.85 35.1 23.75 20.4 23.75 12.5c0-6.2-5.05-11.25-11.25-11.25z"/>'
      + '<circle cx="12.5" cy="12.6" r="5.7" fill="#f8fafc"/>'
      + '<circle cx="12.5" cy="12.6" r="4.2" fill="#e8fff6"/>'
      + '</svg>';
    return L.icon({
      iconUrl: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg),
      shadowUrl: '/assets/leaflet/images/marker-shadow.png',
      iconSize: [25, 41],
      iconAnchor: [12, 41],
      shadowSize: [41, 41],
      popupAnchor: [1, -34]
    });
  }

  function renderMap(container, recordData) {
    var mapData = recordData.map || {};
    var rows = (recordData.dataset && recordData.dataset.rows) || [];
    var latField = String(mapData.lat || '');
    var lngField = String(mapData.lng || '');
    var labelField = String(mapData.label || '');
    var tooltipField = String(mapData.tooltip || labelField || '');
    container.className = 'tf-view tf-map-view';
    container.innerHTML = '<div class="tf-map-stage"><div class="tf-map"></div><div class="tf-map-empty"></div></div>';
    var mapNode = container.querySelector('.tf-map');
    var emptyNode = container.querySelector('.tf-map-empty');
    if (!window.L) {
      emptyNode.textContent = 'Leaflet is not available.';
      emptyNode.classList.add('show');
      return { destroy: function () { container.innerHTML = ''; } };
    }
    if (!latField || !lngField) {
      emptyNode.textContent = 'Map needs latitude and longitude fields.';
      emptyNode.classList.add('show');
      return { destroy: function () { container.innerHTML = ''; } };
    }

    var map = L.map(mapNode, { zoomControl: true, attributionControl: true });
    L.tileLayer(String(mapData.tileUrl || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'), {
      maxZoom: numberOr(mapData.maxZoom, 19),
      attribution: escapeHtml(mapData.attribution || '© OpenStreetMap contributors')
    }).addTo(map);

    var bounds = [];
    var markerIcon = mapMarkerIcon();
    rows.forEach(function (row) {
      var lat = numberValue(fieldValue(row, latField));
      var lng = numberValue(fieldValue(row, lngField));
      if (lat == null || lng == null) return;
      if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return;
      var label = fieldValue(row, labelField);
      var tooltip = fieldValue(row, tooltipField);
      var text = label != null ? label : tooltip;
      var marker = L.marker([lat, lng], { icon: markerIcon, title: text == null ? '' : String(text) }).addTo(map);
      if (label != null || tooltip != null) {
        marker.bindPopup('<div class="tf-map-popup">' + escapeHtml(text) + '</div>');
      }
      bounds.push([lat, lng]);
    });

    function syncView() {
      map.invalidateSize();
      if (bounds.length > 1) {
        map.fitBounds(bounds, { padding: [24, 24], maxZoom: numberOr(mapData.zoom, 14) });
        return;
      }
      if (bounds.length === 1) {
        map.setView(bounds[0], numberOr(mapData.zoom, 12));
        return;
      }
      var center = Array.isArray(mapData.center) ? mapData.center : null;
      var centerLat = center ? numberValue(center[0]) : null;
      var centerLng = center ? numberValue(center[1]) : null;
      if (centerLat != null && centerLng != null) {
        map.setView([centerLat, centerLng], numberOr(mapData.zoom, 10));
        return;
      }
      map.setView([0, 0], 2);
      emptyNode.textContent = 'No valid coordinates in this result.';
      emptyNode.classList.add('show');
    }

    requestAnimationFrame(function () {
      syncView();
      requestAnimationFrame(syncView);
    });
    return {
      afterVisible: syncView,
      destroy: function () {
        map.remove();
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
