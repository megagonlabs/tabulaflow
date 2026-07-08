// @ts-check

import { clone, cssVar, displayValue, escapeHtml } from './shared.js';

const cytoscape = window.cytoscape;
const GRAPH_FIT_PADDING = 64;
const GRAPH_MAX_AUTO_ZOOM = 1.05;

function graphElements(graphData) {
  var elements = graphData.elements || {};
  return {
    nodes: Array.isArray(elements.nodes) ? elements.nodes : [],
    edges: Array.isArray(elements.edges) ? elements.edges : []
  };
}

function graphLayoutOptions(layout) {
  if (layout === 'layered') {
    return { name: 'dagre', rankDir: 'TB', nodeSep: 74, rankSep: 112, edgeSep: 22, fit: false, animate: false };
  }
  if (layout === 'tree') {
    return { name: 'breadthfirst', directed: true, spacingFactor: 1.65, fit: false, animate: false };
  }
  return {
    name: 'cose',
    randomize: false,
    animate: false,
    fit: false,
    numIter: 1000,
    idealEdgeLength: 132,
    nodeOverlap: 14,
    nodeRepulsion: 9200,
    componentSpacing: 96,
    gravity: 0.09
  };
}

function graphStyles() {
  return [
    {
      selector: 'node',
      style: {
        'background-color': 'data(color)',
        'border-color': '#111923',
        'border-opacity': 0.92,
        'border-width': 2.25,
        'color': '#f8fafc',
        'font-size': 10.25,
        'font-weight': 650,
        'height': 'mapData(size, 14, 44, 38, 58)',
        'label': 'data(label)',
        'min-zoomed-font-size': 7.5,
        'overlay-opacity': 0,
        'shadow-blur': 7,
        'shadow-color': '#05080d',
        'shadow-offset-x': 0,
        'shadow-offset-y': 1,
        'shadow-opacity': 0.28,
        'text-halign': 'center',
        'text-max-width': 46,
        'text-outline-opacity': 0,
        'text-outline-width': 0,
        'text-overflow-wrap': 'anywhere',
        'text-valign': 'center',
        'text-wrap': 'wrap',
        'width': 'mapData(size, 14, 44, 38, 58)'
      }
    },
    {
      selector: 'edge',
      style: {
        'color': '#cbd5e1',
        'curve-style': 'bezier',
        'font-size': 9,
        'font-weight': 700,
        'label': 'data(label)',
        'line-color': '#798494',
        'min-zoomed-font-size': 7,
        'opacity': 0.78,
        'arrow-scale': 0.9,
        'target-arrow-color': '#798494',
        'text-background-opacity': 0,
        'text-background-padding': 0,
        'text-margin-y': -8,
        'text-outline-opacity': 0,
        'text-outline-width': 0,
        'text-rotation': 'autorotate',
        'width': 1.4
      }
    },
    {
      selector: 'edge[directed]',
      style: {
        'target-arrow-shape': 'triangle'
      }
    },
    {
      selector: 'node:selected',
      style: {
        'border-color': '#ffffff',
        'border-width': 4
      }
    },
    {
      selector: 'edge:selected',
      style: {
        'line-color': cssVar('--accent', '#3eb489'),
        'target-arrow-color': cssVar('--accent', '#3eb489'),
        'width': 2.4
      }
    }
  ];
}

function fitGraph(cy, graphNode) {
  if (!cy || !cy.elements().length || !graphNode) return;
  cy.resize();
  cy.fit(cy.elements(), GRAPH_FIT_PADDING);
  if (cy.zoom() > GRAPH_MAX_AUTO_ZOOM) {
    cy.zoom({
      level: GRAPH_MAX_AUTO_ZOOM,
      renderedPosition: {
        x: graphNode.clientWidth / 2,
        y: graphNode.clientHeight / 2
      }
    });
    cy.center(cy.elements());
  }
}

function graphDetailHtml(ele) {
  if (!ele || !ele.data) return '';
  var data = ele.data();
  var label = data.label || data.id || '';
  var tooltip = data.tooltip;
  var html = '<div class="tf-graph-popup">';
  if (label) html += '<div class="tf-graph-popup-title">' + escapeHtml(label) + '</div>';
  if (tooltip && typeof tooltip === 'object') {
    html += '<table><tbody>';
    Object.keys(tooltip).forEach(function (key) {
      var value = tooltip[key];
      html += '<tr><th>' + escapeHtml(key) + '</th><td>' + escapeHtml(displayValue(value)) + '</td></tr>';
    });
    html += '</tbody></table>';
  } else if (ele.isEdge && ele.isEdge()) {
    html += '<table><tbody>'
      + '<tr><th>source</th><td>' + escapeHtml(data.source || '') + '</td></tr>'
      + '<tr><th>target</th><td>' + escapeHtml(data.target || '') + '</td></tr>'
      + '</tbody></table>';
  }
  html += '</div>';
  return html;
}

export function renderGraph(container, cardData) {
  var graphData = cardData.graph || {};
  var elements = graphElements(graphData);
  container.className = 'tf-view tf-graph-view';
  container.innerHTML = '<div class="tf-graph-stage"><div class="tf-graph"></div><div class="tf-graph-empty"></div><div class="tf-graph-detail"></div></div>';
  var stageNode = container.querySelector('.tf-graph-stage');
  var graphNode = container.querySelector('.tf-graph');
  var emptyNode = container.querySelector('.tf-graph-empty');
  var detailNode = container.querySelector('.tf-graph-detail');

  function showEmpty(message) {
    emptyNode.textContent = message;
    emptyNode.classList.add('show');
  }

  if (!window.cytoscape) {
    showEmpty('Cytoscape.js is not available.');
    return { destroy: function () { container.innerHTML = ''; } };
  }
  if (!elements.nodes.length || !elements.edges.length) {
    showEmpty('Graph needs at least one node and one edge.');
    return { destroy: function () { container.innerHTML = ''; } };
  }

  var cy = null;
  var initPending = false;
  var initToken = 0;
  var lockedDetail = null;

  function hideDetail() {
    if (lockedDetail) return;
    detailNode.classList.remove('show');
    detailNode.innerHTML = '';
  }

  function showDetail(ele, lock) {
    if (!ele || !stageNode) return;
    var html = graphDetailHtml(ele);
    if (!html) return;
    if (lock) lockedDetail = ele.id();
    var pos = ele.renderedPosition ? ele.renderedPosition() : { x: 0, y: 0 };
    detailNode.innerHTML = html;
    detailNode.style.left = Math.max(10, Math.min(stageNode.clientWidth - 260, pos.x + 14)) + 'px';
    detailNode.style.top = Math.max(10, Math.min(stageNode.clientHeight - 120, pos.y + 14)) + 'px';
    detailNode.classList.add('show');
  }

  function destroyGraph() {
    initToken += 1;
    initPending = false;
    lockedDetail = null;
    if (cy) {
      cy.destroy();
      cy = null;
    }
    container._tfCy = null;
    detailNode.classList.remove('show');
    detailNode.innerHTML = '';
    graphNode.innerHTML = '';
  }

  function initGraph() {
    if (cy || initPending) return;
    initPending = true;
    var token = ++initToken;
    requestAnimationFrame(function () {
      initPending = false;
      if (token !== initToken || cy || !container.isConnected) return;
      cy = cytoscape({
        container: graphNode,
        elements: clone(elements),
        style: graphStyles(),
        layout: graphLayoutOptions(graphData.layout),
        hideEdgesOnViewport: true,
        textureOnViewport: true,
        wheelSensitivity: 0.18,
        minZoom: 0.08,
        maxZoom: 2.25
      });
      container._tfCy = cy;
      cy.on('layoutstop', function () {
        fitGraph(cy, graphNode);
      });
      cy.on('mouseover', 'node, edge', function (event) {
        graphNode.style.cursor = 'pointer';
        showDetail(event.target, false);
      });
      cy.on('mouseout', 'node, edge', function () {
        graphNode.style.cursor = '';
        hideDetail();
      });
      cy.on('tap', 'node, edge', function (event) {
        lockedDetail = null;
        showDetail(event.target, true);
      });
      cy.on('tap', function (event) {
        if (event.target === cy) {
          lockedDetail = null;
          hideDetail();
        }
      });
    });
  }

  return {
    afterVisible: function () {
      initGraph();
      requestAnimationFrame(function () {
        if (cy) {
          fitGraph(cy, graphNode);
        }
      });
    },
    afterHidden: destroyGraph,
    destroy: function () {
      destroyGraph();
      container.innerHTML = '';
    }
  };
}
