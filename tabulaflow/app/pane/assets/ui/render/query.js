// @ts-check

import { renderCodeCard } from './code.js';

/** @param {HTMLElement} container @param {import('../contract').CardData} cardData */
export function renderQuery(container, cardData) {
  var queryData = cardData.query || {};
  container.className = 'tf-view tf-query-view';
  renderCodeCard(container, queryData, {
    defaultLanguage: 'SQL',
    copyLabel: 'Copy query',
    copiedLabel: 'Copied query',
  });
  return { destroy: function () { container.innerHTML = ''; } };
}
