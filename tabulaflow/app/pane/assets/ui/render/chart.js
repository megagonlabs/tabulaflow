// @ts-check

import { artifactIconMarkup, clone, cssVar, deepMerge, escapeAttr, fieldValue } from './shared.js';
import { stableColorDomain } from './color-domains.js';

const vegaEmbed = window.vegaEmbed;
const vega = window.vega;
const DATASET_NAME = '__tf_data';
const EMPTY_STATE_HTML = '<div class="tf-empty-state tf-chart-empty" role="status" aria-live="polite" aria-hidden="true">'
  + artifactIconMarkup('chart', 'tf-empty-state-icon')
  + '<div class="tf-empty-state-title">No data</div>'
  + '<div class="tf-empty-state-copy">No rows match this selection.</div></div>';

function vegaDarkConfig() {
  var accent = cssVar('--accent', '#3EB489');
  var card = cssVar('--card', '#1a212c');
  var text = cssVar('--text', '#e4e4e7');
  var muted = cssVar('--text-muted', '#9aa4b2');
  var grid = cssVar('--chart-grid', '#3a4352');
  return {
    background: card,
    view: { stroke: 'transparent' },
    font: 'Figtree, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif',
    title: { color: text, subtitleColor: muted, fontSize: 17, fontWeight: 600 },
    axis: {
      labelColor: muted,
      titleColor: text,
      gridColor: grid,
      gridOpacity: 0.9,
      domainColor: grid,
      tickColor: grid,
      labelFontSize: 12,
      titleFontSize: 14,
      labelLimit: 160
    },
    legend: { labelColor: muted, titleColor: text, labelFontSize: 12, titleFontSize: 13 },
    header: { labelColor: text, titleColor: text, labelFontSize: 13, titleFontSize: 14 },
    range: {
      category: [
        cssVar('--chart-category-0', accent),
        cssVar('--chart-category-1', '#5ac8fa'),
        cssVar('--chart-category-2', '#f5a623'),
        cssVar('--chart-category-3', '#bd6cf0'),
        cssVar('--chart-category-4', '#f06292'),
        cssVar('--chart-category-5', '#4dd0e1'),
        cssVar('--chart-category-6', '#aed581'),
        cssVar('--chart-category-7', '#ff8a65')
      ],
      ramp: { scheme: 'greens' },
      heatmap: { scheme: 'greens' }
    },
    mark: { color: accent, tooltip: true },
    bar: { fill: accent },
    line: { stroke: accent },
    point: { fill: accent },
    area: { fill: accent },
    arc: { stroke: card }
  };
}

function withStableColorDomains(spec, rows, artifactKey) {
  function walk(node) {
    if (!node || typeof node !== 'object') return;
    if (Array.isArray(node)) {
      node.forEach(walk);
      return;
    }
    var encoding = node.encoding;
    var color = encoding && encoding.color;
    if (color && typeof color === 'object' && !Array.isArray(color) && typeof color.field === 'string') {
      var scale = color.scale;
      var explicitDomain = scale && typeof scale === 'object' && Array.isArray(scale.domain) ? scale.domain : null;
      var canSupplyDomain = explicitDomain || scale === undefined
        || (scale && typeof scale === 'object' && !Object.prototype.hasOwnProperty.call(scale, 'domain'));
      if (canSupplyDomain) {
        var values = rows.map(function (row) { return fieldValue(row, color.field); }).filter(function (value) {
          return value != null;
        });
        var categorical = color.type === 'nominal' || color.type === 'ordinal'
          || (color.type == null && values.every(function (value) {
            return typeof value === 'string' || typeof value === 'boolean';
          }));
        if (categorical) {
          var domain = stableColorDomain(artifactKey + ':color:' + color.field, explicitDomain, values);
          if (domain.length) color.scale = Object.assign({}, scale || {}, { domain: domain });
        }
      }
    }
    Object.keys(node).forEach(function (key) { walk(node[key]); });
  }
  walk(spec);
  return spec;
}

export function renderChart(container, cardData, artifactKey) {
  var chartData = clone(cardData.chart || {});
  var rows = (cardData.dataset && cardData.dataset.rows) || [];
  var spec = clone(chartData.spec || {});
  withStableColorDomains(spec, rows, artifactKey || 'chart');
  chartData.spec = spec;
  var wrapClass = chartData.wrapClass || 'content';
  spec.config = deepMerge(vegaDarkConfig(), spec.config || {});
  spec.data = { name: DATASET_NAME, values: rows };
  container.className = 'tf-view tf-chart-view';
  container.innerHTML = '<div class="tf-vis-stage"><div class="tf-vis-wrap '
    + escapeAttr(wrapClass) + '"><div class="tf-vis"></div></div>' + EMPTY_STATE_HTML + '</div>';
  var target = container.querySelector('.tf-vis');
  var stage = container.querySelector('.tf-vis-stage');
  var empty = container.querySelector('.tf-chart-empty');
  var view = null;
  var disposed = false;
  var renderStarted = false;
  var resolveReady;
  var ready = new Promise(function (resolve) { resolveReady = resolve; });

  function syncEmpty() {
    var isEmpty = rows.length === 0;
    stage.classList.toggle('empty', isEmpty);
    empty.classList.toggle('show', isEmpty);
    empty.setAttribute('aria-hidden', isEmpty ? 'false' : 'true');
  }

  syncEmpty();

  function showError(err) {
    if (disposed) return;
    var pre = document.createElement('pre');
    pre.className = 'vis-error';
    pre.textContent = 'Chart error: ' + String(err);
    container.innerHTML = '';
    container.appendChild(pre);
    resolveReady();
  }

  function mountView() {
    if (disposed || renderStarted) return;
    renderStarted = true;
    vegaEmbed(target, spec, {
      renderer: chartData.renderer || 'svg',
      tooltip: { theme: 'dark' },
      actions: { export: true, source: false, compiled: false, editor: false }
    }).then(function (result) {
      view = result.view;
      resolveReady();
      if (disposed && view) view.finalize();
    }).catch(showError);
  }

  function resizeView() {
    if (!view || !view.resize || disposed) return;
    view.resize().runAsync().catch(function () {});
  }

  return {
    ready: ready,
    requires: { width: true, height: wrapClass === 'fill' },
    mount: function () {
      if (renderStarted) resizeView();
      else mountView();
    },
    resize: resizeView,
    canUpdate: function (nextData) {
      var nextChart = clone(nextData.chart || {});
      var nextRows = (nextData.dataset && nextData.dataset.rows) || [];
      nextChart.spec = withStableColorDomains(clone(nextChart.spec || {}), nextRows, artifactKey || 'chart');
      return !!view && !!vega && JSON.stringify(nextChart) === JSON.stringify(chartData);
    },
    update: function (nextData) {
      rows = (nextData.dataset && nextData.dataset.rows) || [];
      syncEmpty();
      var changes = vega.changeset().remove(function () { return true; }).insert(rows);
      return view.change(DATASET_NAME, changes).runAsync();
    },
    destroy: function () {
      disposed = true;
      resolveReady();
      if (view) view.finalize();
    }
  };
}
