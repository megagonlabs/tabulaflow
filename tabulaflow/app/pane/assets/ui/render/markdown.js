// @ts-check

import { renderCodeCard } from './code.js';
import { escapeAttr, escapeHtml } from './shared.js';

var imageIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"'
  + ' stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
  + '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>'
  + '<circle cx="8.5" cy="8.5" r="1.5"/>'
  + '<path d="M21 15l-5-5L5 21"/></svg>';

function imageParts(token) {
  var alt = String(token.content || '').trim();
  var src = typeof token.attrGet === 'function' ? String(token.attrGet('src') || '').trim() : '';
  return {
    label: alt || shortImageSrc(src) || 'Image',
    src: src
  };
}

function shortImageSrc(src) {
  var text = String(src || '').trim();
  if (!text || /^data:/i.test(text)) return '';
  text = text.replace(/^https?:\/\//i, '');
  if (text.length <= 56) return text;
  return text.slice(0, 40) + '...' + text.slice(-13);
}

function isInsideLink(tokens, idx) {
  var depth = 0;
  for (var i = 0; i < idx; i++) {
    if (tokens[i].type === 'link_open') depth += 1;
    else if (tokens[i].type === 'link_close' && depth > 0) depth -= 1;
  }
  return depth > 0;
}

function isClickableImageSrc(renderer, src) {
  return src && !/^data:/i.test(src) && renderer.validateLink(src);
}

function renderImageReference(renderer, token, mode) {
  var parts = imageParts(token);
  var title = parts.src ? ' title="' + escapeAttr(parts.src) + '"' : '';
  var aria = ' aria-label="' + escapeAttr('Open image: ' + parts.label) + '"';
  var inner = '<span class="md-image-icon">' + imageIcon + '</span>'
    + '<span class="md-image-label">' + escapeHtml(parts.label) + '</span>';
  if (mode === 'link' && isClickableImageSrc(renderer, parts.src)) {
    return '<a class="md-image-ref" href="' + escapeAttr(parts.src) + '"' + title + aria + '>' + inner + '</a>';
  }
  if (mode === 'nested') return '<span class="md-image-ref md-image-ref-nested"' + title + '>' + inner + '</span>';
  return '<span class="md-image-ref md-image-ref-static"' + title + '>' + inner + '</span>';
}

function buildMarkdownRenderer() {
  if (typeof window.markdownit !== 'function') return null;
  var renderer = window.markdownit({ html: false, linkify: true, typographer: false });
  renderer.renderer.rules.image = function (tokens, idx) {
    return renderImageReference(renderer, tokens[idx], isInsideLink(tokens, idx) ? 'nested' : 'link');
  };
  if (typeof window.texmath === 'function' && window.katex && typeof window.katex.renderToString === 'function') {
    renderer.use(window.texmath, {
      engine: window.katex,
      delimiters: 'brackets',
      katexOptions: { throwOnError: false, strict: 'ignore', trust: false }
    });
  }
  return renderer;
}

var markdownRenderer = buildMarkdownRenderer();

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
