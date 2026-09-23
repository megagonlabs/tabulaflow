// @ts-check

import { asUrls, cssVar, displayValue, escapeAttr, escapeHtml, fieldValue, numberOr, numberValue, tooltipLink } from './shared.js';
import { stableColorDomain } from './color-domains.js';

const maplibregl = window.maplibregl;

var mapDefaultColor = cssVar('--map-default', '#4285f4');
var mapRouteColor = cssVar('--map-route', '#1558d6');
var mapPalette = [
  cssVar('--map-category-0', mapDefaultColor),
  cssVar('--map-category-1', '#ea4335'),
  cssVar('--map-category-2', '#fbbc04'),
  cssVar('--map-category-3', '#34a853'),
  cssVar('--map-category-4', '#a142f4'),
  cssVar('--map-category-5', '#d81b60'),
  cssVar('--map-category-6', '#46bdc6'),
  cssVar('--map-category-7', '#7cb342')
];
var mapPinDefaultColor = cssVar('--map-pin-default', '#ea4335');
var mapPinHighlight = cssVar('--map-pin-highlight', '#ffb4ae');
var mapPinTop = cssVar('--map-pin-top', '#ff6f61');
var mapPinBottom = cssVar('--map-pin-bottom', '#d93025');
var mapPinDark = cssVar('--map-pin-dark', '#a91f19');
var mapPinOutline = cssVar('--map-pin-outline', '#a52714');
var mapCircleStroke = mixHex(mapDefaultColor, '#000000', 0.26);
var mapStyleUrl = '/assets/vendor/maplibre/shortbread-light.json';
var mapStyleSpriteUrl = '/assets/vendor/maplibre/osm-bright-sprite';
var mapStyleRouteSpriteUrl = '/assets/vendor/maplibre/tf-route-sprite';
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

function circleStrokeColor(color) {
  return mixHex(color, '#000000', 0.26);
}

function pinColorRamp(color) {
  var base = hexRgb(color) ? String(color).trim() : mapPinBottom;
  if (!hexRgb(base)) {
    return {
      highlight: mapPinHighlight,
      top: mapPinTop,
      bottom: mapPinBottom,
      dark: mapPinDark,
      outline: mapPinOutline
    };
  }
  return {
    highlight: mixHex(base, '#ffffff', 0.66),
    top: mixHex(base, '#ffffff', 0.28),
    bottom: base,
    dark: mixHex(base, '#000000', 0.26),
    outline: mixHex(base, '#000000', 0.4)
  };
}

function mapPinSvg(color) {
  var ramp = pinColorRamp(color);
  var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="35" viewBox="0 0 22 35">'
    + '<defs><radialGradient id="head" cx="34%" cy="27%" r="72%">'
    + '<stop offset="0" stop-color="' + ramp.highlight + '"/>'
    + '<stop offset=".2" stop-color="' + ramp.top + '"/>'
    + '<stop offset=".58" stop-color="' + ramp.bottom + '"/>'
    + '<stop offset="1" stop-color="' + ramp.dark + '"/></radialGradient>'
    + '<linearGradient id="stem" x1="0" y1="0" x2="1" y2="0">'
    + '<stop stop-color="#515861"/><stop offset=".25" stop-color="#aeb6bf"/>'
    + '<stop offset=".52" stop-color="#eef1f4"/><stop offset=".75" stop-color="#929ba5"/>'
    + '<stop offset="1" stop-color="#414851"/></linearGradient></defs>'
    + '<ellipse cx="12.5" cy="33.2" rx="4.5" ry="1.15" fill="rgba(31,41,55,.2)"/>'
    + '<path d="M10.25 12.5h1.5v18.7L11 34.4l-.75-3.2Z" fill="url(#stem)" stroke="#535b64" stroke-width=".45" stroke-linejoin="round"/>'
    + '<circle cx="11" cy="8" r="6.65" fill="url(#head)" stroke="' + ramp.outline + '" stroke-width="1.15"/>'
    + '<ellipse cx="8.85" cy="5.25" rx="2.15" ry="1.45" fill="rgba(255,255,255,.56)"/>'
    + '<path d="M6.1 10.2c1.1 2.8 4.7 4.1 7.5 2.7" fill="none" stroke="rgba(96,12,8,.24)" stroke-width=".75" stroke-linecap="round"/>'
    + '</svg>';
  return 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg);
}

function mapPinElement(color, title) {
  var node = document.createElement('div');
  node.className = 'tf-map-pin';
  node.style.width = '22px';
  node.style.height = '35px';
  node.style.backgroundImage = 'url("' + mapPinSvg(color) + '")';
  if (title) node.setAttribute('aria-label', title);
  return node;
}

function mapLayers(mapData) {
  if (Array.isArray(mapData.layers)) return mapData.layers;
  return [];
}

function fieldLabelsFromColumns(cols) {
  var out = {};
  (cols || []).forEach(function (col) {
    if (col && col.field) out[String(col.field)] = String(col.title || col.field);
  });
  return out;
}

function fieldLabels(cardData) {
  return fieldLabelsFromColumns(cardData.dataset && cardData.dataset.columns);
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

function detailHtml(row, tooltip, labels, fallback) {
  var fields = tooltipFields(tooltip, row);
  var label = fallback == null ? '' : displayValue(fallback);
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

function withStableColorDomain(layer, rows, artifactKey, layerIndex) {
  var encoding = layer && layer.color;
  if (!encoding || typeof encoding !== 'object' || Array.isArray(encoding)) {
    return layer;
  }
  var field = encodingField(encoding);
  if (!field) return layer;
  var domain = stableColorDomain(
    artifactKey + ':color:' + layerIndex + ':' + field,
    Array.isArray(encoding.domain) ? encoding.domain : null,
    rows.map(function (row) { return fieldValue(row, field); })
  );
  if (!domain.length) return layer;
  var colorCopy = {};
  for (var ck in encoding) {
    if (Object.prototype.hasOwnProperty.call(encoding, ck)) colorCopy[ck] = encoding[ck];
  }
  colorCopy.domain = domain;
  var layerCopy = {};
  for (var lk in layer) {
    if (Object.prototype.hasOwnProperty.call(layer, lk)) layerCopy[lk] = layer[lk];
  }
  layerCopy.color = colorCopy;
  return layerCopy;
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
  if (!values || values.length === 0 || values.length > maxLegendEntries) return null;
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

function sizeDomain(encoding, rows, field) {
  if (Array.isArray(encoding.domain) && encoding.domain.length === 2) {
    var domainMin = numberValue(encoding.domain[0]);
    var domainMax = numberValue(encoding.domain[1]);
    if (domainMin != null && domainMax != null && domainMax > domainMin) return [domainMin, domainMax];
  }
  var values = rows.map(function (row) { return numberValue(fieldValue(row, field)); })
    .filter(function (value) { return value != null; });
  if (!values.length) return null;
  return [Math.min.apply(Math, values), Math.max.apply(Math, values)];
}

function buildSizeScale(encoding, rows, fallback) {
  var field = encodingField(encoding);
  var domain = field ? sizeDomain(encoding, rows, field) : null;
  var scalable = domain && domain[1] > domain[0];
  function radiusValue(value) {
    value = numberValue(value);
    if (value == null || !scalable) return fallback;
    var minSize = 5;
    var maxSize = 18;
    var normalized = Math.max(0, Math.min(1, (value - domain[0]) / (domain[1] - domain[0])));
    return Math.sqrt(minSize * minSize + normalized * (maxSize * maxSize - minSize * minSize));
  }
  return {
    field: field,
    domain: scalable ? domain : null,
    radius: function (row) { return field ? radiusValue(fieldValue(row, field)) : fallback; },
    radiusValue: radiusValue
  };
}

function buildSizeLegendSection(scale, labels) {
  if (!scale.field || !scale.domain) return null;
  var entries = scale.domain.map(function (value) {
    return { label: displayValue(value), size: Math.round(2 * scale.radiusValue(value)) };
  });
  return { title: labels[scale.field] || scale.field, swatchType: 'size', entries: entries };
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
    html += '<section class="tf-map-legend-section tf-map-legend-section-' + section.swatchType
      + '"><div class="tf-map-legend-title">'
      + escapeHtml(section.title) + '</div>';
    section.entries.forEach(function (entry) {
      var style = section.swatchType === 'size'
        ? '--legend-size:' + escapeHtml(entry.size) + 'px'
        : '--legend-color:' + escapeHtml(entry.color);
      var swatch = '<span class="tf-map-legend-swatch tf-map-legend-swatch-' + section.swatchType
        + '" style="' + style + '"></span>';
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
  var markerType = layer.marker && layer.marker.type
    ? layer.marker.type
    : (layer.size ? 'circle' : 'pin');
  var validRows = [];
  pointRows.forEach(function (row) {
    var lat = numberValue(fieldValue(row, latField));
    var lng = numberValue(fieldValue(row, lngField));
    if (lat == null || lng == null || lat < -90 || lat > 90 || lng < -180 || lng > 180) return;
    validRows.push({ row: row, lat: lat, lng: lng });
  });
  var sizeScale = buildSizeScale(layer.size, validRows.map(function (item) { return item.row; }), 6);
  var features = [];
  if (!latField || !lngField) return { features: features, markerType: markerType, sizeScale: sizeScale };
  validRows.forEach(function (item) {
    var row = item.row;
    var lat = item.lat;
    var lng = item.lng;
    var label = fieldValue(row, labelField);
    var popup = detailHtml(row, layer.tooltip, labels, label);
    var color = colorFor(layer.color, row, markerType === 'pin' ? mapPinDefaultColor : mapDefaultColor);
    var radius = sizeScale.radius(row);
    features.push({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [lng, lat] },
      properties: Object.assign({}, row || {}, {
        __tfColor: color,
        __tfStrokeColor: circleStrokeColor(color),
        __tfSize: radius,
        __tfPinHitRadius: 24,
        __tfPopup: popup,
        __tfTitle: label == null ? '' : displayValue(label),
        __tfMarker: markerType,
        __tfAnchorLng: lng,
        __tfAnchorLat: lat
      })
    });
  });
  return { features: features, markerType: markerType, sizeScale: sizeScale };
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
    var popup = detailHtml(props, layer.tooltip, labels, label);
    var color = colorFor(layer.color, props, line ? mapRouteColor : mapDefaultColor);
    var anchor = geometryAnchor(feature.geometry);
    return {
      type: 'Feature',
      geometry: feature.geometry,
      properties: Object.assign({}, props, {
        __tfColor: color,
        __tfStrokeColor: circleStrokeColor(color),
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
    focusAfterOpen: !!closeButton,
    className: className,
    maxWidth: '420px',
    offset: 12
  }).setLngLat(lngLat).setHTML(html).addTo(map);
}

function clearHoverPopup(map, popupState) {
  if (popupState.hoverOpenTimer) {
    clearTimeout(popupState.hoverOpenTimer);
    popupState.hoverOpenTimer = null;
  }
  if (popupState.hoverCloseTimer) {
    clearTimeout(popupState.hoverCloseTimer);
    popupState.hoverCloseTimer = null;
  }
  map.getCanvas().style.cursor = '';
  if (popupState.hover) popupState.hover.remove();
  popupState.hover = null;
  popupState.hoverHtml = '';
  popupState.hoverAnchor = '';
  popupState.pendingHoverKey = '';
  popupState.hoverOverFeature = false;
  popupState.hoverOverPopup = false;
}

function scheduleHoverPopupClose(map, popupState) {
  popupState.hoverOverFeature = false;
  if (popupState.hoverOpenTimer) {
    clearTimeout(popupState.hoverOpenTimer);
    popupState.hoverOpenTimer = null;
    popupState.pendingHoverKey = '';
  }
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
  var hoverKey = html + '\u0000' + hoverAnchor;
  if (popupState.hover && popupState.hoverHtml === html && popupState.hoverAnchor === hoverAnchor) return;
  if (popupState.hoverOpenTimer && popupState.pendingHoverKey === hoverKey) return;

  if (popupState.hover) popupState.hover.remove();
  popupState.hover = null;
  popupState.hoverHtml = '';
  popupState.hoverAnchor = '';
  if (popupState.hoverOpenTimer) clearTimeout(popupState.hoverOpenTimer);
  popupState.pendingHoverKey = hoverKey;
  popupState.hoverOpenTimer = setTimeout(function () {
    popupState.hoverOpenTimer = null;
    if (!popupState.hoverOverFeature || popupState.pendingHoverKey !== hoverKey || popupState.click) return;
    popupState.hover = renderMapPopup(map, lngLat, html, 'tf-map-detail-tooltip', false);
    bindHoverPopupPointer(map, popupState.hover, popupState);
    popupState.hoverHtml = html;
    popupState.hoverAnchor = hoverAnchor;
    popupState.pendingHoverKey = '';
  }, 200);
}

function setClickPopup(map, lngLat, html, popupState) {
  if (popupState.hoverCloseTimer) {
    clearTimeout(popupState.hoverCloseTimer);
    popupState.hoverCloseTimer = null;
  }
  if (popupState.hover) popupState.hover.remove();
  if (popupState.click) popupState.click.remove();
  if (popupState.hoverOpenTimer) {
    clearTimeout(popupState.hoverOpenTimer);
    popupState.hoverOpenTimer = null;
  }
  popupState.hover = null;
  popupState.hoverHtml = '';
  popupState.hoverAnchor = '';
  popupState.pendingHoverKey = '';
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
  function currentLayerIds() {
    return typeof layerIds === 'function' ? layerIds() : layerIds;
  }
  map.on('mousemove', function (event) {
    var ids = currentLayerIds();
    var feature = ids.length ? firstPopupFeature(map.queryRenderedFeatures(event.point, { layers: ids })) : null;
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
    var ids = currentLayerIds();
    var feature = ids.length ? firstPopupFeature(map.queryRenderedFeatures(event.point, { layers: ids })) : null;
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
    paint: circlePaint(['coalesce', ['get', '__tfSize'], 6])
  });
}

function circlePaint(radius) {
  return {
    'circle-radius': radius,
    'circle-color': ['coalesce', ['get', '__tfColor'], mapDefaultColor],
    'circle-opacity': 0.62,
    'circle-stroke-color': ['coalesce', ['get', '__tfStrokeColor'], mapCircleStroke],
    'circle-stroke-width': 1.5,
    'circle-stroke-opacity': 0.9
  };
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
    paint: circlePaint(6)
  });
  return [id + '-fill', id + '-outline', id + '-line', id + '-point'];
}

export function renderMap(container, cardData, artifactKey) {
  var mapData = cardData.map || {};
  var datasets = cardData.datasets || {};
  var fallbackRows = (cardData.dataset && cardData.dataset.rows) || [];
  var fallbackLabels = fieldLabels(cardData);
  var labelsCache = {};
  var layers = mapLayers(mapData);

  function rowsFor(layer) {
    var source = layer && layer.source;
    if (source && datasets[source]) return datasets[source].rows || [];
    return fallbackRows;
  }

  function labelsFor(layer) {
    var source = layer && layer.source;
    if (source && datasets[source]) {
      if (!labelsCache[source]) labelsCache[source] = fieldLabelsFromColumns(datasets[source].columns);
      return labelsCache[source];
    }
    return fallbackLabels;
  }

  container.className = 'tf-view tf-map-view';
  container.innerHTML = '<div class="tf-map-stage"><div class="tf-map"></div>'
    + '<div class="tf-map-empty" role="status" aria-live="polite"></div>'
    + '<div class="tf-map-error" role="alert"></div></div>';
  var mapNode = container.querySelector('.tf-map');
  var emptyNode = container.querySelector('.tf-map-empty');
  var errorNode = container.querySelector('.tf-map-error');
  var stageNode = container.querySelector('.tf-map-stage');

  function showDataEmpty(message) {
    emptyNode.textContent = message;
    emptyNode.classList.add('show');
  }

  function hideDataEmpty() {
    emptyNode.textContent = '';
    emptyNode.classList.remove('show');
  }

  function showFatal(message) {
    hideDataEmpty();
    errorNode.textContent = message;
    errorNode.classList.add('show');
  }

  function hideFatal() {
    errorNode.textContent = '';
    errorNode.classList.remove('show');
  }

  if (!window.maplibregl) {
    showFatal('MapLibre GL is not available.');
    return { destroy: function () { container.innerHTML = ''; } };
  }
  if (!layers.length) {
    showFatal('Map needs at least one layer.');
    return { destroy: function () { container.innerHTML = ''; } };
  }

  var map = null;
  var mapLoaded = false;
  var mapInitToken = 0;
  var hasShownData = false;
  var userMovedMap = false;
  var resolveReady;
  var ready = new Promise(function (resolve) { resolveReady = resolve; });
  var markers = [];
  var dataBounds = null;
  var popupState = {
    hover: null,
    hoverHtml: '',
    hoverAnchor: '',
    pendingHoverKey: '',
    hoverOverFeature: false,
    hoverOverPopup: false,
    hoverOpenTimer: null,
    hoverCloseTimer: null,
    click: null
  };
  var detailLayerIds = [];
  var legendSections = [];

  function syncDataLayers(initial) {
    dataBounds = new maplibregl.LngLatBounds();
    detailLayerIds = [];
    legendSections = [];
    clearLegend(stageNode);
    markers.forEach(function (marker) { marker.remove(); });
    markers = [];
    var hasBounds = false;
    layers.forEach(function (layer, index) {
      var rows = rowsFor(layer);
      var labels = labelsFor(layer);
      layer = withStableColorDomain(layer, rows, artifactKey || 'map', index);
      if (!layer || layer.type === 'points') {
        var pointData = buildPointFeatures(layer || {}, rows, labels);
        var sourceId = 'tf-points-' + index;
        var pointSource = map.getSource(sourceId);
        if (pointSource) pointSource.setData(featureCollection(pointData.features));
        if (!pointData.features.length) return;
        if (!pointSource) map.addSource(sourceId, { type: 'geojson', data: featureCollection(pointData.features) });
        pointData.features.forEach(function (feature) {
          if (extendFeatureBounds(dataBounds, feature)) hasBounds = true;
        });
        if (pointData.markerType === 'circle') {
          var circleId = sourceId + '-circle';
          if (!map.getLayer(circleId)) addCircleLayer(map, circleId, sourceId);
          detailLayerIds.push(circleId);
        } else {
          var pinHitId = sourceId + '-pin-hit';
          if (!map.getLayer(pinHitId)) addPinHitLayer(map, pinHitId, sourceId);
          detailLayerIds.push(pinHitId);
          pointData.features.forEach(function (feature) {
            var props = feature.properties || {};
            var lngLat = feature.geometry.coordinates;
            var node = mapPinElement(props.__tfColor, props.__tfTitle);
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
        var sizeLegend = pointData.markerType === 'circle'
          ? buildSizeLegendSection(pointData.sizeScale, labels) : null;
        if (sizeLegend) legendSections.push(sizeLegend);
        return;
      }
      if (layer.type === 'geojson') {
        var features = buildGeoJsonFeatures(layer, rows, labels);
        var geoSourceId = 'tf-geojson-' + index;
        var geoSource = map.getSource(geoSourceId);
        if (geoSource) geoSource.setData(featureCollection(features));
        if (!features.length) return;
        if (!geoSource) map.addSource(geoSourceId, { type: 'geojson', data: featureCollection(features) });
        features.forEach(function (feature) {
          if (extendFeatureBounds(dataBounds, feature)) hasBounds = true;
        });
        var geoLayerIds = map.getLayer(geoSourceId + '-fill')
          ? [geoSourceId + '-fill', geoSourceId + '-outline', geoSourceId + '-line', geoSourceId + '-point']
          : addGeoJsonLayers(map, geoSourceId, geoSourceId);
        geoLayerIds.forEach(function (layerId) {
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
    if (initial) bindLayerDetails(map, function () { return detailLayerIds; }, popupState);
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
      hideDataEmpty();
      hasShownData = true;
      return;
    }
    var center = Array.isArray(view.center) ? view.center : null;
    var centerLat = center ? numberValue(center[0]) : null;
    var centerLng = center ? numberValue(center[1]) : null;
    if (centerLat != null && centerLng != null) {
      map.setCenter([centerLng, centerLat]);
      map.setZoom(numberOr(view.zoom, 10));
      if (dataBounds && !dataBounds.isEmpty()) {
        hideDataEmpty();
        hasShownData = true;
      } else {
        showDataEmpty('No locations for this selection.');
      }
      return;
    }
    if (dataBounds && !dataBounds.isEmpty()) {
      hideDataEmpty();
      hasShownData = true;
      return;
    }
    map.setCenter([0, 0]);
    map.setZoom(2);
    showDataEmpty('No locations for this selection.');
  }

  function destroyMap() {
    clearHoverPopup(map, popupState);
    if (popupState.click) popupState.click.remove();
    popupState.click = null;
    clearLegend(stageNode);
    markers.forEach(function (marker) { marker.remove(); });
    markers = [];
    detailLayerIds = [];
    legendSections = [];
    if (map) map.remove();
    map = null;
    container._tfMap = null;
    mapLoaded = false;
    mapInitToken += 1;
    dataBounds = null;
  }

  function initMap() {
    if (map) return;
    var initToken = ++mapInitToken;
    hideDataEmpty();
    hideFatal();
    fetch(mapStyleUrl).then(function (response) {
      if (!response.ok) throw new Error('Failed to load map style.');
      return response.json();
    }).then(function (style) {
      if (initToken !== mapInitToken || map) return;
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
      container._tfMap = map;
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left');
      map.addControl(new maplibregl.AttributionControl({ compact: false }), 'bottom-right');
      ['dragstart', 'zoomstart', 'rotatestart', 'pitchstart'].forEach(function (eventName) {
        map.on(eventName, function (event) {
          if (event && event.originalEvent) userMovedMap = true;
        });
      });
      map.once('load', function () {
        if (!map) return;
        mapLoaded = true;
        syncDataLayers(true);
        syncView();
        requestAnimationFrame(resolveReady);
      });
      map.on('error', function (event) {
        if (event && event.error) showFatal('Map error: ' + String(event.error.message || event.error));
      });
    }).catch(function (error) {
      if (initToken !== mapInitToken) return;
      showFatal('Map error: ' + String(error && error.message ? error.message : error));
      resolveReady();
    });
  }

  return {
    ready: ready,
    requires: { width: true, height: true },
    mount: initMap,
    resize: function () {
      if (map) map.resize();
    },
    canUpdate: function (nextData) {
      return !!mapLoaded && JSON.stringify(nextData.map || {}) === JSON.stringify(mapData);
    },
    update: function (nextData) {
      mapData = nextData.map || {};
      datasets = nextData.datasets || {};
      fallbackRows = (nextData.dataset && nextData.dataset.rows) || [];
      fallbackLabels = fieldLabels(nextData);
      labelsCache = {};
      layers = mapLayers(mapData);
      clearHoverPopup(map, popupState);
      if (popupState.click) popupState.click.remove();
      popupState.click = null;
      syncDataLayers(false);
      if (dataBounds) {
        if (!hasShownData && !userMovedMap) syncView();
        else {
          hideDataEmpty();
          hasShownData = true;
        }
      } else {
        showDataEmpty('No locations for this selection.');
      }
      return new Promise(function (resolve) { requestAnimationFrame(resolve); });
    },
    destroy: function () {
      destroyMap();
      resolveReady();
      container.innerHTML = '';
    }
  };
}
