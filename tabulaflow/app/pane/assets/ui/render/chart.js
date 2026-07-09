// @ts-check

import { clone, cssVar, deepMerge, escapeAttr } from './shared.js';

const vegaEmbed = window.vegaEmbed;

function vegaDarkConfig() {
  var accent = cssVar('--accent', '#3EB489');
  var card = cssVar('--card', '#1a212c');
  var text = cssVar('--text', '#e4e4e7');
  var muted = cssVar('--text-muted', '#9aa4b2');
  var grid = cssVar('--chart-grid', '#3a4352');
  return {
    background: card,
    view: { stroke: 'transparent' },
    font: '-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif',
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

export function renderChart(container, cardData) {
  var chartData = cardData.chart || {};
  var rows = (cardData.dataset && cardData.dataset.rows) || [];
  var spec = clone(chartData.spec || {});
  var wrapClass = chartData.wrapClass || 'content';
  spec.config = deepMerge(vegaDarkConfig(), spec.config || {});
  spec.data = { values: rows };
  container.className = 'tf-view tf-chart-view';
  container.innerHTML = '<div class="tf-vis-stage"><div class="tf-vis-wrap '
    + escapeAttr(wrapClass) + '"><div class="tf-vis"></div></div></div>';
  var view = null;
  var disposed = false;
  var renderStarted = false;
  var pendingFrame = null;
  var measureAttempts = 0;

  function clearPendingFrame() {
    if (pendingFrame != null) window.cancelAnimationFrame(pendingFrame);
    pendingFrame = null;
  }

  function showError(err) {
    if (disposed) return;
    var pre = document.createElement('pre');
    pre.className = 'vis-error';
    pre.textContent = 'Chart error: ' + String(err);
    container.innerHTML = '';
    container.appendChild(pre);
  }

  function hasMeasurableTarget(target) {
    if (!target || !container.isConnected) return false;
    var rect = target.getBoundingClientRect();
    if (wrapClass === 'fill') return rect.width > 0 && rect.height > 0;
    return rect.width > 0;
  }

  function renderWhenReady() {
    clearPendingFrame();
    if (disposed || renderStarted) return;
    var target = container.querySelector('.tf-vis');
    if (!hasMeasurableTarget(target)) {
      measureAttempts += 1;
      if (measureAttempts <= 20) pendingFrame = window.requestAnimationFrame(renderWhenReady);
      return;
    }
    renderStarted = true;
    vegaEmbed(target, spec, {
      renderer: chartData.renderer || 'svg',
      tooltip: { theme: 'dark' },
      actions: { export: true, source: false, compiled: false, editor: false }
    }).then(function (result) {
      view = result.view;
      if (disposed && view) view.finalize();
    }).catch(showError);
  }

  function resizeView() {
    if (!view || !view.resize || disposed) return;
    view.resize().runAsync().catch(function () {});
  }

  return {
    afterVisible: function () {
      clearPendingFrame();
      if (renderStarted) {
        pendingFrame = window.requestAnimationFrame(resizeView);
        return;
      }
      measureAttempts = 0;
      pendingFrame = window.requestAnimationFrame(renderWhenReady);
    },
    afterHidden: clearPendingFrame,
    destroy: function () {
      disposed = true;
      clearPendingFrame();
      if (view) view.finalize();
    }
  };
}
