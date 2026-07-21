// @ts-check

import { renderCodeCard } from './code.js';

var markdownRenderer = typeof window.markdownit === 'function'
  ? window.markdownit({ html: false, linkify: true, typographer: false }).disable('image')
  : null;

/** @param {HTMLElement} node @param {string} text @param {import('../contract').CodeData[]=} codeBlocks */
export function renderMarkdown(node, text, codeBlocks) {
  node.classList.add('md');
  if (!markdownRenderer) {
    node.textContent = text;
    return;
  }
  node.innerHTML = markdownRenderer.render(text);
  var blocks = Array.isArray(codeBlocks) ? codeBlocks : [];
  node.querySelectorAll('pre > code').forEach(function (codeNode, index) {
    var codeData = blocks[index];
    if (!codeData) return;
    var pre = codeNode.parentElement;
    if (!pre) return;
    var holder = document.createElement('div');
    renderCodeCard(holder, codeData);
    if (holder.firstElementChild) pre.replaceWith(holder.firstElementChild);
  });
  node.querySelectorAll('a[href]').forEach(function (link) {
    link.setAttribute('target', '_blank');
    link.setAttribute('rel', 'noopener noreferrer');
  });
}
