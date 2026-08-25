// @ts-check

import { asUrls, escapeHtml, formatNumber, link, maybeFormatJson, renderMedia } from './shared.js';

const Tabulator = window.Tabulator;

/** @param {HTMLElement} container @param {import('../contract').CardData} cardData */
export function renderTable(container, cardData) {
  var tableData = cardData.table || {};
  var rows = (cardData.dataset && cardData.dataset.rows) || [];
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

  function headerMinWidth(title) {
    return Math.min(260, Math.max(96, String(title || '').length * 9 + 56));
  }

  function sampleTextWidth(field, title) {
    var longest = 0;
    var seen = 0;
    rows.some(function (row) {
      if (!row || row[field] == null) return false;
      longest = Math.max(longest, String(row[field]).length);
      seen += 1;
      return seen >= 50;
    });
    if (!seen) return 120;
    if (longest > 80) return 260;
    if (longest > 32) return 220;
    if (longest > 18) return 160;
    return 120;
  }

  function buildColumn(col) {
    var title = String(col.title || col.field || '');
    var field = String(col.field || '');
    var role = col.role || col.formatter || 'text';
    if (role === 'num') role = 'number';
    var headerWidth = headerMinWidth(title);
    var out = {
      title: title,
      field: field,
      resizable: true,
      sorterParams: { alignEmptyValues: 'bottom' }
    };
    if (role === 'media') {
      out.formatter = formatters.media;
      out.headerSort = false;
      out.minWidth = Math.max(220, headerWidth);
      out.widthGrow = 1;
      out.cellClick = function (e, cell) {
        var value = cell.getValue();
        if (value && value.kind === 'media' && String(value.mime || '').indexOf('image/') === 0) {
          openModalImage(cell.getColumn().getDefinition().title, value.src);
        }
      };
    } else if (role === 'bool') {
      out.formatter = formatters.bool;
      out.sorter = boolNullLastSorter;
      out.hozAlign = 'center';
      out.minWidth = Math.max(96, headerWidth);
      out.widthGrow = 1;
    } else if (role === 'number') {
      out.formatter = formatters.num;
      out.hozAlign = 'right';
      out.sorter = 'number';
      out.minWidth = Math.max(96, headerWidth);
      out.widthGrow = 1;
    } else {
      var minWidth = Math.max(sampleTextWidth(field, title), headerWidth);
      out.formatter = formatters.text;
      out.minWidth = minWidth;
      out.widthGrow = minWidth >= 160 ? 2 : 1;
      out.cellClick = function (e, cell) {
        var v = cell.getValue();
        if (typeof v !== 'string' || asUrls(v)) return;
        if (v.length > displayCap || v.indexOf('\n') >= 0) {
          openModal(cell.getColumn().getDefinition().title, v);
        }
      };
    }
    return out;
  }

  var cols = (tableData.columns || []).map(buildColumn);

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
      width: Math.max(44, String(Math.max(rows.length, 1)).length * 10 + 28),
      cssClass: 'tabulator-row-header'
    }
  };
  var shouldConstrainHeight = panelHeight > 0 || rows.length > 100 || (fixedMax != null && estimatedTableHeight > viewportCap);
  if (shouldConstrainHeight) opts.height = viewportCap;
  var table = new Tabulator(container.querySelector('.tf-table'), opts);
  var ready = new Promise(function (resolve) { table.on('tableBuilt', resolve); });
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
  return {
    ready: ready,
    canUpdate: function (nextData) {
      var nextTable = nextData.table || {};
      var nextRows = (nextData.dataset && nextData.dataset.rows) || [];
      var nextEstimatedHeight = 38 + nextRows.length * 29;
      var nextConstrained = panelHeight > 0 || nextRows.length > 100
        || (fixedMax != null && nextEstimatedHeight > viewportCap);
      return JSON.stringify(nextTable.columns || []) === JSON.stringify(tableData.columns || [])
        && nextConstrained === shouldConstrainHeight
        && nextTable.maxHeight === tableData.maxHeight
        && nextTable.displayCap === tableData.displayCap
        && !!nextTable.hasMedia === !!tableData.hasMedia;
    },
    update: function (nextData) {
      tableData = nextData.table || {};
      rows = (nextData.dataset && nextData.dataset.rows) || [];
      var wrapper = container.querySelector('.tf-table-wrap');
      if (wrapper) wrapper.classList.toggle('pane-short', rows.length <= 12);
      return table.replaceData(rows);
    },
    destroy: function () { table.destroy(); closeModal(); }
  };
}
