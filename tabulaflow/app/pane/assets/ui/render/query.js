// @ts-check

import { escapeHtml } from './shared.js';

/** @param {HTMLElement} container @param {import('../contract').CardData} cardData */
export function renderQuery(container, cardData) {
  var queryData = cardData.query || {};
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
