// @ts-check

var domains = Object.create(null);

function valueKey(value) {
  return typeof value + ':' + JSON.stringify(value);
}

export function stableColorDomain(key, explicitDomain, observedValues) {
  if (Array.isArray(explicitDomain)) return explicitDomain.slice();
  var domain = domains[key] || [];
  var seen = Object.create(null);
  domain.forEach(function (value) { seen[valueKey(value)] = true; });
  observedValues.forEach(function (value) {
    if (value == null || ['string', 'number', 'boolean'].indexOf(typeof value) === -1) return;
    var identity = valueKey(value);
    if (seen[identity]) return;
    seen[identity] = true;
    domain.push(value);
  });
  domains[key] = domain;
  return domain.slice();
}

export function resetColorDomains() {
  domains = Object.create(null);
}
