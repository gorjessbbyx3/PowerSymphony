// PowerSymphony Agent Browser Controller - Content Script
// Injected into every page to assist with DOM inspection and interaction

(function() {
  if (window.__powersymphonyAgentInjected) return;
  window.__powersymphonyAgentInjected = true;

  // Listen for messages from the background service worker
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === 'highlight_element') {
      highlightElement(msg.selector);
      sendResponse({ ok: true });
    }
    if (msg.type === 'get_clickable_elements') {
      sendResponse({ elements: getClickableElements() });
    }
  });

  function highlightElement(selector) {
    const prev = document.querySelector('.__powersymphony_highlight');
    if (prev) prev.remove();

    const el = document.querySelector(selector);
    if (!el) return;

    const rect = el.getBoundingClientRect();
    const overlay = document.createElement('div');
    overlay.className = '__powersymphony_highlight';
    overlay.style.cssText = `
      position: fixed;
      top: ${rect.top}px;
      left: ${rect.left}px;
      width: ${rect.width}px;
      height: ${rect.height}px;
      border: 3px solid #ff6b35;
      background: rgba(255, 107, 53, 0.15);
      z-index: 2147483647;
      pointer-events: none;
      transition: all 0.2s ease;
      border-radius: 4px;
    `;
    document.body.appendChild(overlay);
    setTimeout(() => overlay.remove(), 3000);
  }

  function getClickableElements() {
    const selectors = 'a, button, input, textarea, select, [role="button"], [onclick], [tabindex]';
    const elements = Array.from(document.querySelectorAll(selectors)).slice(0, 100);
    return elements.map(el => {
      const rect = el.getBoundingClientRect();
      return {
        tag: el.tagName.toLowerCase(),
        type: el.type || null,
        text: (el.innerText || el.value || el.placeholder || el.alt || '').slice(0, 80),
        selector: getUniqueSelector(el),
        rect: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) },
        visible: rect.width > 0 && rect.height > 0,
      };
    }).filter(e => e.visible);
  }

  function getUniqueSelector(el) {
    if (el.id) return `#${CSS.escape(el.id)}`;
    if (el.name) return `[name="${el.name}"]`;

    const parts = [];
    let current = el;
    while (current && current !== document.body) {
      let part = current.tagName.toLowerCase();
      if (current.className) {
        const classes = Array.from(current.classList).slice(0, 2).map(c => `.${CSS.escape(c)}`).join('');
        part += classes;
      }
      const siblings = current.parentElement
        ? Array.from(current.parentElement.children).filter(c => c.tagName === current.tagName)
        : [];
      if (siblings.length > 1) {
        part += `:nth-of-type(${siblings.indexOf(current) + 1})`;
      }
      parts.unshift(part);
      current = current.parentElement;
      if (parts.length >= 4) break;
    }
    return parts.join(' > ');
  }
})();
