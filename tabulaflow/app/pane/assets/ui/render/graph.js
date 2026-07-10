// @ts-check

import { asUrls, clone, cssVar, displayValue, escapeHtml, tooltipLink } from './shared.js';

const cytoscape = window.cytoscape;
const GRAPH_FIT_PADDING = 64;
const GRAPH_MAX_AUTO_ZOOM = 1.25;
const GRAPH_DEFAULT_NODE_BORDER = '#253447';
const GRAPH_LIVE_PHYSICS_MIN_ALPHA = 0.012;
const GRAPH_NODE_LABEL_LINE_CHARS = 8;
const GRAPH_NODE_LABEL_MAX_LINES = 2;

function normalizeHexColor(color) {
  if (typeof color !== 'string') return null;
  var match = color.trim().match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (!match) return null;
  var hex = match[1];
  if (hex.length === 3) {
    hex = hex.split('').map(function (char) { return char + char; }).join('');
  }
  return hex.toLowerCase();
}

function nodeBorderColor(color) {
  var hex = normalizeHexColor(color);
  if (!hex) return GRAPH_DEFAULT_NODE_BORDER;
  var factor = 0.56;
  var out = [0, 2, 4].map(function (offset) {
    var value = Math.round(parseInt(hex.slice(offset, offset + 2), 16) * factor);
    return value.toString(16).padStart(2, '0');
  });
  return '#' + out.join('');
}

function truncateGraphLabel(text, maxChars) {
  if (text.length <= maxChars) return text;
  return text.slice(0, Math.max(0, maxChars - 3)).trimEnd() + '...';
}

function ellipsizeGraphLabel(text, maxChars) {
  if (text.endsWith('...')) return text;
  var limit = Math.max(1, maxChars - 3);
  var value = text.length <= limit ? text : text.slice(0, limit).trimEnd();
  return value + '...';
}

function graphNodeDisplayLabel(value) {
  var text = String(value || '').replace(/\s+/g, ' ').trim();
  if (!text) return '';
  if (text.length <= GRAPH_NODE_LABEL_LINE_CHARS) return text;

  var words = text.split(' ');
  var lines = [];
  var line = '';
  var truncated = false;
  for (var i = 0; i < words.length; i += 1) {
    var word = words[i];
    if (word.length > GRAPH_NODE_LABEL_LINE_CHARS) {
      word = truncateGraphLabel(word, GRAPH_NODE_LABEL_LINE_CHARS);
      truncated = true;
    }
    var next = line ? line + ' ' + word : word;
    if (next.length <= GRAPH_NODE_LABEL_LINE_CHARS) {
      line = next;
      continue;
    }
    if (line) lines.push(line);
    line = word;
    if (lines.length === GRAPH_NODE_LABEL_MAX_LINES) {
      truncated = true;
      break;
    }
  }
  if (line && lines.length < GRAPH_NODE_LABEL_MAX_LINES) lines.push(line);
  if (i < words.length) truncated = true;
  if (truncated && lines.length) {
    var last = lines.length - 1;
    lines[last] = ellipsizeGraphLabel(lines[last], GRAPH_NODE_LABEL_LINE_CHARS);
  }
  return lines.join('\n');
}

function graphNodeElements(nodes) {
  return nodes.map(function (node) {
    var data = node && node.data ? node.data : {};
    return Object.assign({}, node, {
      data: Object.assign({}, data, {
        borderColor: data.borderColor || nodeBorderColor(data.color),
        displayLabel: graphNodeDisplayLabel(data.label || data.id)
      })
    });
  });
}

function graphElements(graphData) {
  var elements = graphData.elements || {};
  return {
    nodes: Array.isArray(elements.nodes) ? graphNodeElements(elements.nodes) : [],
    edges: Array.isArray(elements.edges) ? elements.edges : []
  };
}

function seededForceNodes(nodes) {
  var count = nodes.length;
  if (!count) return [];
  var radius = Math.max(80, count * 18);
  return nodes
    .slice()
    .sort(function (a, b) {
      var aId = a && a.data ? String(a.data.id || '') : '';
      var bId = b && b.data ? String(b.data.id || '') : '';
      return aId.localeCompare(bId);
    })
    .map(function (node, index) {
      var angle = (Math.PI * 2 * index) / count - Math.PI / 2;
      return Object.assign({}, node, {
        position: {
          x: Math.round(Math.cos(angle) * radius * 100) / 100,
          y: Math.round(Math.sin(angle) * radius * 100) / 100
        }
      });
    });
}

function graphInitElements(elements, layout) {
  var cloned = clone(elements);
  if (layout === 'force' || !layout) {
    cloned.nodes = seededForceNodes(cloned.nodes);
  }
  return cloned;
}

function idealForceEdgeLength(edge) {
  var label = edge && edge.data ? String(edge.data('label') || '') : '';
  return Math.max(84, Math.min(150, 74 + label.length * 6));
}

function graphLayoutOptions(layout, graphData) {
  var meta = graphData && graphData.meta ? graphData.meta : {};
  if (meta.initialLayout === 'preset') {
    return { name: 'preset', fit: false, animate: false };
  }
  if (layout === 'layered') {
    return { name: 'dagre', rankDir: 'TB', nodeSep: 50, rankSep: 62, edgeSep: 14, fit: false, animate: false };
  }
  if (layout === 'tree') {
    return { name: 'breadthfirst', directed: true, spacingFactor: 1.2, fit: false, animate: false };
  }
  return {
    name: 'cose',
    randomize: false,
    animate: false,
    fit: false,
    numIter: 1000,
    idealEdgeLength: idealForceEdgeLength,
    edgeElasticity: 64,
    nodeOverlap: 10,
    nodeRepulsion: 2600,
    componentSpacing: 40,
    gravity: 0.55
  };
}

function createLivePhysics(cy) {
  var nodes = cy.nodes().toArray();
  var edges = cy.edges().toArray();

  var velocities = new Map();
  var frame = null;
  var destroyed = false;
  var alpha = 0;
  var center = { x: 0, y: 0 };

  function velocity(node) {
    var id = node.id();
    var value = velocities.get(id);
    if (!value) {
      value = { x: 0, y: 0 };
      velocities.set(id, value);
    }
    return value;
  }

  function isPinned(node) {
    return node.grabbed() || node.locked();
  }

  function hasGrabbedNode() {
    return cy.nodes(':grabbed').length > 0;
  }

  function updateCenter() {
    var box = cy.elements().boundingBox();
    center = { x: box.x1 + box.w / 2, y: box.y1 + box.h / 2 };
  }

  function schedule() {
    if (destroyed || frame !== null) return;
    frame = requestAnimationFrame(step);
  }

  function kick(value) {
    alpha = Math.max(alpha, value);
    schedule();
  }

  function applyForce(node, x, y) {
    if (isPinned(node)) return;
    var v = velocity(node);
    v.x += x;
    v.y += y;
  }

  function step() {
    frame = null;
    if (destroyed) return;

    var grabbed = hasGrabbedNode();
    if (!grabbed && alpha < GRAPH_LIVE_PHYSICS_MIN_ALPHA) return;
    updateCenter();

    var positions = nodes.map(function (node) {
      return node.position();
    });

    for (var i = 0; i < nodes.length; i += 1) {
      for (var j = i + 1; j < nodes.length; j += 1) {
        var a = positions[i];
        var b = positions[j];
        var dx = b.x - a.x;
        var dy = b.y - a.y;
        var distSq = dx * dx + dy * dy;
        if (distSq < 1) {
          dx = (j - i) * 0.37;
          dy = (i + j + 1) * 0.23;
          distSq = dx * dx + dy * dy;
        }
        var dist = Math.sqrt(distSq);
        var force = (4200 * alpha) / Math.max(distSq, 900);
        var fx = (dx / dist) * force;
        var fy = (dy / dist) * force;
        applyForce(nodes[i], -fx, -fy);
        applyForce(nodes[j], fx, fy);
      }
    }

    edges.forEach(function (edge) {
      var source = edge.source();
      var target = edge.target();
      var sourcePos = source.position();
      var targetPos = target.position();
      var dx = targetPos.x - sourcePos.x;
      var dy = targetPos.y - sourcePos.y;
      var dist = Math.max(1, Math.sqrt(dx * dx + dy * dy));
      var ideal = idealForceEdgeLength(edge);
      var force = (dist - ideal) * 0.018 * alpha;
      var fx = (dx / dist) * force;
      var fy = (dy / dist) * force;
      applyForce(source, fx, fy);
      applyForce(target, -fx, -fy);
    });

    cy.batch(function () {
      nodes.forEach(function (node) {
        var v = velocity(node);
        if (isPinned(node)) {
          v.x = 0;
          v.y = 0;
          return;
        }
        var pos = node.position();
        v.x += (center.x - pos.x) * 0.0014 * alpha;
        v.y += (center.y - pos.y) * 0.0014 * alpha;
        v.x *= 0.82;
        v.y *= 0.82;

        var speed = Math.sqrt(v.x * v.x + v.y * v.y);
        if (speed > 7) {
          v.x = (v.x / speed) * 7;
          v.y = (v.y / speed) * 7;
        }
        node.position({ x: pos.x + v.x, y: pos.y + v.y });
      });
    });

    alpha = grabbed ? Math.max(alpha * 0.985, 0.22) : alpha * 0.94;
    schedule();
  }

  cy.on('grab', 'node', function (event) {
    velocity(event.target).x = 0;
    velocity(event.target).y = 0;
    kick(0.9);
  });
  cy.on('drag', 'node', function () {
    kick(0.9);
  });
  cy.on('free', 'node', function () {
    kick(0.55);
  });
  kick(0.55);

  return {
    destroy: function () {
      destroyed = true;
      if (frame !== null) {
        cancelAnimationFrame(frame);
        frame = null;
      }
    }
  };
}

function graphStyles() {
  return [
    {
      selector: 'core',
      style: {
        'active-bg-opacity': 0,
        'selection-box-opacity': 0
      }
    },
    {
      selector: 'node',
      style: {
        'background-color': 'data(color)',
        'border-color': 'data(borderColor)',
        'border-opacity': 1,
        'border-width': 2,
        'color': '#f8fafc',
        'font-size': 10.25,
        'font-weight': 650,
        'height': 48,
        'label': 'data(displayLabel)',
        'min-zoomed-font-size': 7.5,
        'overlay-opacity': 0,
        'text-halign': 'center',
        'text-max-width': 46,
        'text-outline-opacity': 0,
        'text-outline-width': 0,
        'text-overflow-wrap': 'anywhere',
        'text-valign': 'center',
        'text-wrap': 'wrap',
        'width': 48
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
        'line-opacity': 0.78,
        'min-zoomed-font-size': 7,
        'arrow-scale': 0.9,
        'source-distance-from-node': 4,
        'target-arrow-color': '#798494',
        'target-distance-from-node': 4,
        'text-background-color': '#19212c',
        'text-background-opacity': 1,
        'text-background-padding': 1,
        'text-background-shape': 'rectangle',
        'text-margin-x': 0,
        'text-margin-y': 0,
        'text-outline-opacity': 0,
        'text-outline-width': 0,
        'text-opacity': 1,
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
      selector: 'node.tf-selected',
      style: {
        'border-color': 'data(borderColor)',
        'border-width': 3,
        'underlay-color': '#f8fafc',
        'underlay-opacity': 0.18,
        'underlay-padding': 4
      }
    },
    {
      selector: 'edge.tf-selected',
      style: {
        'line-color': '#9aa4b2',
        'line-opacity': 1,
        'overlay-color': '#f8fafc',
        'overlay-opacity': 0.18,
        'overlay-padding': 8,
        'target-arrow-color': '#9aa4b2',
        'width': 1.4
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

function graphDetailValueHtml(value) {
  var text = displayValue(value);
  var urls = typeof value === 'string' ? asUrls(text) : null;
  if (urls) {
    if (text.trim().charAt(0) === '[') {
      return '[' + urls.map(function (url) { return '"' + tooltipLink(url) + '"'; }).join(', ') + ']';
    }
    if (urls.length === 1) return tooltipLink(urls[0]);
    return urls.map(function (url) { return tooltipLink(url); }).join(' ');
  }
  return escapeHtml(text);
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
      html += '<tr><th>' + escapeHtml(key) + '</th><td>' + graphDetailValueHtml(value) + '</td></tr>';
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

function graphDetailPosition(ele) {
  if (!ele) return { x: 0, y: 0 };
  if (ele.isEdge && ele.isEdge() && ele.renderedMidpoint) return ele.renderedMidpoint();
  if (ele.renderedPosition) return ele.renderedPosition();
  return { x: 0, y: 0 };
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
  var livePhysics = null;
  var detailMode = null;
  var hoverCloseTimer = null;
  var hoverOverElement = false;
  var hoverOverDetail = false;
  var autoFitEnabled = true;
  var autoFitTimer = null;

  function clearHoverCloseTimer() {
    if (!hoverCloseTimer) return;
    clearTimeout(hoverCloseTimer);
    hoverCloseTimer = null;
  }

  function hideDetail(force) {
    if (!force && detailMode === 'pinned') return;
    clearHoverCloseTimer();
    detailMode = null;
    hoverOverElement = false;
    hoverOverDetail = false;
    detailNode.classList.remove('show');
    detailNode.innerHTML = '';
  }

  function scheduleHoverDetailClose() {
    hoverOverElement = false;
    if (detailMode !== 'hover' || hoverOverDetail) return;
    clearHoverCloseTimer();
    hoverCloseTimer = setTimeout(function () {
      hoverCloseTimer = null;
      if (detailMode === 'hover' && !hoverOverElement && !hoverOverDetail) {
        hideDetail(true);
      }
    }, 60);
  }

  function startLivePhysics() {
    if (!cy || livePhysics) return;
    livePhysics = createLivePhysics(cy);
  }

  function clearAutoFitTimer() {
    if (!autoFitTimer) return;
    clearTimeout(autoFitTimer);
    autoFitTimer = null;
  }

  function markUserViewportInteraction() {
    autoFitEnabled = false;
    clearAutoFitTimer();
  }

  function runAutoFit() {
    autoFitTimer = null;
    if (!autoFitEnabled || !cy) return;
    fitGraph(cy, graphNode);
  }

  function scheduleAutoFit() {
    if (!autoFitEnabled) return;
    clearAutoFitTimer();
    autoFitTimer = setTimeout(runAutoFit, 0);
  }

  function clearGraphSelection() {
    if (cy) cy.elements('.tf-selected').removeClass('tf-selected');
  }

  function selectGraphElement(ele) {
    clearGraphSelection();
    if (ele && ele.addClass) ele.addClass('tf-selected');
  }

  function showDetail(ele, mode) {
    if (!ele || !stageNode) return;
    if (detailMode === 'pinned' && mode !== 'pinned') return;
    var html = graphDetailHtml(ele);
    if (!html) return;
    clearHoverCloseTimer();
    detailMode = mode;
    var pos = graphDetailPosition(ele);
    detailNode.innerHTML = html;
    detailNode.style.left = Math.max(10, Math.min(stageNode.clientWidth - 260, pos.x + 14)) + 'px';
    detailNode.style.top = Math.max(10, Math.min(stageNode.clientHeight - 120, pos.y + 14)) + 'px';
    detailNode.classList.add('show');
  }

  function destroyGraph() {
    hideDetail(true);
    clearAutoFitTimer();
    if (cy) {
      if (livePhysics) {
        livePhysics.destroy();
        livePhysics = null;
      }
      cy.destroy();
      cy = null;
    }
    container._tfCy = null;
    graphNode.innerHTML = '';
  }

  function initGraph() {
    if (cy) return;
    cy = cytoscape({
      container: graphNode,
      elements: graphInitElements(elements, graphData.layout),
      style: graphStyles(),
      layout: graphLayoutOptions(graphData.layout, graphData),
      autounselectify: true,
      boxSelectionEnabled: false,
      hideEdgesOnViewport: false,
      textureOnViewport: false,
      userPanningEnabled: true,
      userZoomingEnabled: true,
      wheelSensitivity: 0.18,
      minZoom: 0.08,
      maxZoom: 2.25
    });
    container._tfCy = cy;
    cy.on('layoutstop', function () {
      scheduleAutoFit();
      startLivePhysics();
    });
    cy.ready(function () {
      scheduleAutoFit();
      startLivePhysics();
    });
    cy.on('grab', 'node', markUserViewportInteraction);
    cy.on('mouseover', 'node, edge', function (event) {
      hoverOverElement = true;
      clearHoverCloseTimer();
      graphNode.style.cursor = 'pointer';
      showDetail(event.target, 'hover');
    });
    cy.on('mouseout', 'node, edge', function () {
      graphNode.style.cursor = '';
      scheduleHoverDetailClose();
    });
    cy.on('tap', 'node, edge', function (event) {
      selectGraphElement(event.target);
      showDetail(event.target, 'pinned');
    });
    cy.on('tap', function (event) {
      if (event.target === cy) {
        clearGraphSelection();
        hideDetail(true);
      }
    });
  }

  detailNode.addEventListener('mouseenter', function () {
    hoverOverDetail = true;
    clearHoverCloseTimer();
  });
  detailNode.addEventListener('mouseleave', function () {
    hoverOverDetail = false;
    scheduleHoverDetailClose();
  });
  graphNode.addEventListener('wheel', markUserViewportInteraction, { passive: true });
  graphNode.addEventListener('touchstart', function (event) {
    if (event.touches && event.touches.length > 1) markUserViewportInteraction();
  }, { passive: true });

  return {
    requires: { width: true, height: true },
    mount: initGraph,
    resize: function () {
      if (!cy) return;
      cy.resize();
      scheduleAutoFit();
    },
    unmount: destroyGraph,
    destroy: function () {
      destroyGraph();
      container.innerHTML = '';
    }
  };
}
