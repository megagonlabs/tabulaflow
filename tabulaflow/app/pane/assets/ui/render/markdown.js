// @ts-check

var markdownRenderer = typeof window.markdownit === 'function'
  ? window.markdownit({ html: false, linkify: true, typographer: false }).disable('image')
  : null;

/** @param {HTMLElement} node @param {string} text */
export function renderMarkdown(node, text) {
  node.classList.add('md');
  if (!markdownRenderer) {
    node.textContent = text;
    return;
  }
  node.innerHTML = markdownRenderer.render(text);
  node.querySelectorAll('a[href]').forEach(function (link) {
    link.setAttribute('target', '_blank');
    link.setAttribute('rel', 'noopener noreferrer');
  });
}
