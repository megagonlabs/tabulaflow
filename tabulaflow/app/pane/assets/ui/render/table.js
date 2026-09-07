// @ts-check

import { asUrls, escapeAttr, escapeHtml, formatNumber, link, maybeFormatJson, renderMedia } from './shared.js';

const Tabulator = window.Tabulator;

function copyValue(value) {
  if (value == null) return '';
  if (typeof value === 'object') {
    if (value.kind === 'media-list') {
      var items = Array.isArray(value.items) ? value.items : [];
      var counts = {};
      items.forEach(function (item) {
        var mime = item && item.kind === 'media' ? String(item.mime || '') : '';
        var type = mime === 'application/pdf' ? 'PDF' : (mime.split('/', 1)[0] || 'file');
        counts[type] = (counts[type] || 0) + 1;
      });
      var summary = Object.keys(counts).map(function (type) {
        var count = counts[type];
        var label = type === 'PDF' ? 'PDF' + (count === 1 ? '' : 's') : type + (count === 1 ? '' : 's');
        return count + ' ' + label;
      });
      return '[' + items.length + ' media item' + (items.length === 1 ? '' : 's')
        + (summary.length ? ': ' + summary.join(', ') : '') + ']';
    }
    if (value.kind === 'media') {
      var mime = String(value.mime || 'binary');
      var size = value.size == null ? NaN : Number(value.size);
      return Number.isFinite(size) ? '[Media: ' + mime + ', ' + size + ' bytes]' : '[Media: ' + mime + ']';
    }
    return JSON.stringify(value);
  }
  return String(value);
}

function mediaTile(item, index) {
  var mime = item && item.kind === 'media' ? String(item.mime || '') : '';
  var label = mime === 'application/pdf' ? 'PDF' : (mime.split('/', 1)[0] || 'File');
  label = label.charAt(0).toUpperCase() + label.slice(1);
  var content = mime.indexOf('image/') === 0
    ? '<img src="' + escapeAttr(String(item.src || '')) + '" alt="">'
    : '<span class="tf-media-tile-label">' + escapeHtml(label) + '</span>';
  return '<button class="tf-media-tile" type="button" data-media-index="' + index
    + '" aria-label="Open ' + escapeAttr(label) + '">' + content + '</button>';
}

function renderMediaCell(value) {
  if (!value || value.kind !== 'media-list') return renderMedia(value);
  var items = Array.isArray(value.items) ? value.items : [];
  if (items.length === 1) return renderMedia(items[0]);
  var visibleCount = items.length > 3 ? 2 : items.length;
  var html = items.slice(0, visibleCount).map(mediaTile).join('');
  if (visibleCount < items.length) {
    html += '<button class="tf-media-tile tf-media-more" type="button" data-media-index="' + visibleCount
      + '" aria-label="Open ' + (items.length - visibleCount) + ' more media items">+'
      + (items.length - visibleCount) + '</button>';
  }
  return '<div class="tf-media-list">' + html + '</div>';
}

function tsvCell(value) {
  var text = copyValue(value);
  if (!/[\t\r\n"]/.test(text)) return text;
  return '"' + text.replace(/"/g, '""') + '"';
}

export function tableToTsv(columns, rows) {
  var lines = [columns.map(function (column) { return tsvCell(column.title || column.field || ''); }).join('\t')];
  rows.forEach(function (row) {
    lines.push(columns.map(function (column) { return tsvCell(row[column.field]); }).join('\t'));
  });
  return lines.join('\n');
}

/** @param {HTMLElement} container @param {import('../contract').CardData} cardData */
export function renderTable(container, cardData) {
  var tableData = cardData.table || {};
  var rows = (cardData.dataset && cardData.dataset.rows) || [];
  var displayCap = tableData.displayCap || 120;
  var wrapClass = rows.length <= 12 ? 'tf-table-wrap pane-short' : 'tf-table-wrap';
  container.className = 'tf-view tf-table-view';
  container.innerHTML = '<div class="' + wrapClass + '"><div class="tf-table"></div></div>'
    + '<dialog class="tf-modal">'
    + '<div class="tf-modal-card"><div class="tf-modal-header">'
    + '<span class="tf-modal-focus" tabindex="-1" aria-label="Media preview" hidden></span>'
    + '<span class="tf-modal-title"></span><span class="tf-media-count" aria-live="polite"></span>'
    + '<button class="tf-modal-close" type="button" aria-label="Close">'
    + '<svg viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>'
    + '</button></div><div class="tf-modal-body"></div></div></dialog>';

  var modal = container.querySelector('.tf-modal');
  var modalBody = container.querySelector('.tf-modal-body');
  var modalFocus = container.querySelector('.tf-modal-focus');
  var modalTitle = container.querySelector('.tf-modal-title');
  var mediaCount = container.querySelector('.tf-media-count');
  var closeBtn = container.querySelector('.tf-modal-close');
  var galleryStep = null;
  function clearMediaCount() {
    mediaCount.textContent = '';
    mediaCount.removeAttribute('aria-label');
  }
  function pauseModalMedia() {
    modalBody.querySelectorAll('audio, video').forEach(function (media) { media.pause(); });
  }
  function showModal() {
    if (!modal.open) modal.showModal();
    if (modal.classList.contains('tf-lightbox')) modalFocus.focus({ preventScroll: true });
  }
  function openModal(title, text) {
    galleryStep = null;
    modal.classList.remove('tf-lightbox');
    modalFocus.hidden = true;
    modalTitle.textContent = title || '';
    modalTitle.hidden = false;
    modal.setAttribute('aria-label', title || 'Table cell detail');
    clearMediaCount();
    var pre = document.createElement('pre');
    pre.textContent = maybeFormatJson(text);
    modalBody.innerHTML = '';
    modalBody.appendChild(pre);
    showModal();
  }
  function openMediaGallery(title, items, startIndex) {
    var index = Math.max(0, Math.min(startIndex || 0, items.length - 1));
    function showItem() {
      pauseModalMedia();
      var previous = items.length > 1
        ? '<button class="tf-media-step" type="button" data-gallery-step="-1" aria-label="Previous media item">'
          + '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg></button>'
        : '<span class="tf-media-step-placeholder"></span>';
      var next = items.length > 1
        ? '<button class="tf-media-step" type="button" data-gallery-step="1" aria-label="Next media item">'
          + '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg></button>'
        : '<span class="tf-media-step-placeholder"></span>';
      if (items.length > 1) {
        mediaCount.textContent = (index + 1) + ' / ' + items.length;
        mediaCount.setAttribute('aria-label', 'Item ' + (index + 1) + ' of ' + items.length);
      } else {
        clearMediaCount();
      }
      modalBody.innerHTML = '<div class="tf-media-lightbox">' + previous
        + '<div class="tf-media-stage">' + renderMedia(items[index], 'lightbox') + '</div>' + next + '</div>';
      modalBody.querySelectorAll('[data-gallery-step]').forEach(function (button) {
        button.addEventListener('click', function () { galleryStep(Number(button.dataset.galleryStep)); });
      });
    }
    galleryStep = function (delta) { index = (index + delta + items.length) % items.length; showItem(); };
    modal.classList.add('tf-lightbox');
    modalFocus.hidden = false;
    modalTitle.textContent = '';
    modalTitle.hidden = true;
    modal.setAttribute('aria-label', title || 'Media preview');
    showItem();
    showModal();
  }
  function closeModal() {
    if (modal.open) modal.close();
  }
  function clearModal() {
    pauseModalMedia();
    galleryStep = null;
    modal.classList.remove('tf-lightbox');
    modalFocus.hidden = true;
    clearMediaCount();
    modalBody.innerHTML = '';
  }
  modal.addEventListener('click', function (e) {
    if (!modal.classList.contains('tf-lightbox')) {
      if (e.target === modal) closeModal();
      return;
    }
    var target = e.target;
    var protectedTarget = target && target.closest
      ? target.closest('.tf-media-stage img, .tf-media-stage audio, .tf-media-stage video, .tf-media-stage a, button')
      : null;
    if (!protectedTarget) closeModal();
  });
  modal.addEventListener('keydown', function (e) {
    if (!galleryStep || (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight')) return;
    if (e.target && /^(AUDIO|VIDEO|INPUT)$/.test(e.target.tagName || '')) return;
    e.preventDefault();
    galleryStep(e.key === 'ArrowLeft' ? -1 : 1);
  });
  modal.addEventListener('close', clearModal);
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
    media: function (cell) { return renderMediaCell(cell.getValue()); },
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
        if (value && value.kind === 'media-list' && Array.isArray(value.items) && value.items.length) {
          var trigger = e.target && e.target.closest ? e.target.closest('[data-media-index]') : null;
          if (trigger) {
            openMediaGallery(
              cell.getColumn().getDefinition().title,
              value.items,
              Number(trigger.getAttribute('data-media-index'))
            );
          } else if (value.items.length === 1 && value.items[0] && value.items[0].kind === 'media'
              && String(value.items[0].mime || '').indexOf('image/') === 0) {
            openMediaGallery(cell.getColumn().getDefinition().title, value.items, 0);
          }
          return;
        }
        if (value && value.kind === 'media' && String(value.mime || '').indexOf('image/') === 0) {
          openMediaGallery(cell.getColumn().getDefinition().title, [value], 0);
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
    placeholder: 'No rows match this selection.',
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
    copy: {
      text: function () { return tableToTsv(tableData.columns || [], rows); },
      label: 'Copy table',
      copiedLabel: 'Copied table'
    },
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
