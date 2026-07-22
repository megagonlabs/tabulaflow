// @ts-check

import { escapeHtml } from './shared.js';

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

function wireCopy(button, code, labels) {
  if (!button) return;
  var resetTimer = null;
  button.addEventListener('click', function () {
    function done(ok) {
      if (resetTimer !== null) window.clearTimeout(resetTimer);
      button.classList.toggle('copied', ok);
      button.classList.toggle('copy-failed', !ok);
      button.setAttribute('aria-label', ok ? labels.copied : 'Copy failed');
      button.title = ok ? 'Copied' : 'Copy failed';
      resetTimer = window.setTimeout(function () {
        button.classList.remove('copied');
        button.classList.remove('copy-failed');
        button.setAttribute('aria-label', labels.copy);
        button.title = labels.copy;
        resetTimer = null;
      }, 1200);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(code).then(function () { done(true); }, function () { done(false); });
    } else {
      done(false);
    }
  });
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
  wireCopy(container.querySelector('[data-copy-code]'), copyText(codeData), labels);
}
