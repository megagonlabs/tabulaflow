// @ts-check

import { escapeHtml, wireCopyButton } from './shared.js';

function highlightedHtml(codeData) {
  if (codeData && codeData.html) return String(codeData.html);
  return '<div class="highlight"><pre>' + escapeHtml(copyText(codeData)) + '</pre></div>';
}

function copyText(codeData) {
  return String((codeData && (codeData.code || codeData['sql'])) || '');
}

function languageLabel(codeData, defaultLanguage) {
  return String((codeData && (codeData.language || codeData.lexer)) || defaultLanguage || 'Text');
}

function copyLabels(options) {
  return {
    copy: options && options.copyLabel ? options.copyLabel : 'Copy code',
    copied: options && options.copiedLabel ? options.copiedLabel : 'Copied code',
  };
}

/** @param {HTMLElement} container @param {import('../contract').CodeData} codeData @param {{ defaultLanguage?: string, copyLabel?: string, copiedLabel?: string }=} options */
export function renderCodeCard(container, codeData, options) {
  var label = languageLabel(codeData, options && options.defaultLanguage);
  var labels = copyLabels(options);
  container.innerHTML = '<section class="query-card code-card"><div class="query-bar">'
    + '<span class="query-lang">' + escapeHtml(label) + '</span>'
    + '<button class="query-copy" type="button" data-copy-code aria-label="' + escapeHtml(labels.copy) + '" title="' + escapeHtml(labels.copy) + '">'
    + '<span class="copy-icon" aria-hidden="true"></span></button></div>'
    + highlightedHtml(codeData) + '</section>';
  wireCopyButton(container.querySelector('[data-copy-code]'), copyText(codeData), labels);
}
