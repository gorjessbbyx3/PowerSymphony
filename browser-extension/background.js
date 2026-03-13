// PowerSymphony Agent Browser Controller - Background Service Worker
// Manages WebSocket connection to PowerSymphony server and relays commands to content scripts

let ws = null;
let serverUrl = 'ws://localhost:8000/ws/browser-agent';
let sessionId = null;
let reconnectTimer = null;
let isConnected = false;
let pendingCommands = new Map(); // commandId -> resolve/reject

// Load saved server URL from storage
chrome.storage.local.get(['serverUrl', 'sessionId'], (result) => {
  if (result.serverUrl) serverUrl = result.serverUrl;
  if (result.sessionId) sessionId = result.sessionId;
  connectToServer();
});

function generateId() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

function connectToServer() {
  if (ws) {
    ws.close();
    ws = null;
  }

  try {
    ws = new WebSocket(serverUrl);

    ws.onopen = () => {
      isConnected = true;
      console.log('[PowerSymphony] Connected to server');
      if (!sessionId) sessionId = generateId();
      chrome.storage.local.set({ sessionId });
      ws.send(JSON.stringify({
        type: 'browser_agent_register',
        session_id: sessionId,
        user_agent: navigator.userAgent,
      }));
      broadcastStatus('connected');
    };

    ws.onmessage = async (event) => {
      let msg;
      try { msg = JSON.parse(event.data); } catch { return; }
      await handleServerMessage(msg);
    };

    ws.onclose = () => {
      isConnected = false;
      broadcastStatus('disconnected');
      scheduleReconnect();
    };

    ws.onerror = (err) => {
      console.error('[PowerSymphony] WebSocket error', err);
      isConnected = false;
      broadcastStatus('error');
    };

  } catch (e) {
    console.error('[PowerSymphony] Failed to connect', e);
    scheduleReconnect();
  }
}

function scheduleReconnect() {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(connectToServer, 5000);
}

function broadcastStatus(status) {
  chrome.runtime.sendMessage({ type: 'status_update', status, sessionId }).catch(() => {});
}

async function handleServerMessage(msg) {
  const { type, command_id, tab_id } = msg;

  // Send command result back to server
  const respond = (result, error = null) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'command_result',
        command_id,
        session_id: sessionId,
        result,
        error,
      }));
    }
  };

  try {
    switch (type) {
      case 'open_tab': {
        const tab = await chrome.tabs.create({ url: msg.url, active: msg.active !== false });
        respond({ tab_id: tab.id, url: tab.url });
        break;
      }

      case 'close_tab': {
        await chrome.tabs.remove(msg.tab_id);
        respond({ closed: true });
        break;
      }

      case 'get_tabs': {
        const tabs = await chrome.tabs.query({});
        respond({ tabs: tabs.map(t => ({ id: t.id, url: t.url, title: t.title, active: t.active })) });
        break;
      }

      case 'screenshot': {
        const targetTab = msg.tab_id
          ? await chrome.tabs.get(msg.tab_id)
          : (await chrome.tabs.query({ active: true, currentWindow: true }))[0];
        if (!targetTab) { respond(null, 'No tab found'); break; }
        const dataUrl = await chrome.tabs.captureVisibleTab(targetTab.windowId, { format: 'png' });
        respond({ screenshot: dataUrl, tab_id: targetTab.id });
        break;
      }

      case 'get_page_content': {
        const result = await executeInTab(msg.tab_id, getPageContentFn);
        respond(result);
        break;
      }

      case 'click': {
        const result = await executeInTab(msg.tab_id, clickFn, [msg.selector, msg.x, msg.y]);
        respond(result);
        break;
      }

      case 'type': {
        const result = await executeInTab(msg.tab_id, typeFn, [msg.selector, msg.text, msg.clear]);
        respond(result);
        break;
      }

      case 'scroll': {
        const result = await executeInTab(msg.tab_id, scrollFn, [msg.selector, msg.x, msg.y]);
        respond(result);
        break;
      }

      case 'wait_for_selector': {
        const result = await executeInTab(msg.tab_id, waitForSelectorFn, [msg.selector, msg.timeout]);
        respond(result);
        break;
      }

      case 'get_element_text': {
        const result = await executeInTab(msg.tab_id, getElementTextFn, [msg.selector]);
        respond(result);
        break;
      }

      case 'fill_form': {
        const result = await executeInTab(msg.tab_id, fillFormFn, [msg.fields]);
        respond(result);
        break;
      }

      case 'navigate': {
        const targetTabId = msg.tab_id || (await chrome.tabs.query({ active: true, currentWindow: true }))[0]?.id;
        if (!targetTabId) { respond(null, 'No tab'); break; }
        await chrome.tabs.update(targetTabId, { url: msg.url });
        await waitForTabLoad(targetTabId);
        const tab = await chrome.tabs.get(targetTabId);
        respond({ url: tab.url, title: tab.title });
        break;
      }

      case 'eval': {
        const results = await chrome.scripting.executeScript({
          target: { tabId: msg.tab_id },
          func: (code) => { try { return eval(code); } catch(e) { return { error: e.message }; } },
          args: [msg.code],
        });
        respond({ result: results[0]?.result });
        break;
      }

      case 'ping': {
        respond({ pong: true, session_id: sessionId });
        break;
      }

      default:
        respond(null, `Unknown command type: ${type}`);
    }
  } catch (e) {
    respond(null, e.message || String(e));
  }
}

async function executeInTab(tabId, fn, args = []) {
  const targetTabId = tabId || (await chrome.tabs.query({ active: true, currentWindow: true }))[0]?.id;
  if (!targetTabId) throw new Error('No tab available');
  const results = await chrome.scripting.executeScript({
    target: { tabId: targetTabId },
    func: fn,
    args,
  });
  return results[0]?.result;
}

function waitForTabLoad(tabId, timeout = 10000) {
  return new Promise((resolve) => {
    const listener = (updatedTabId, changeInfo) => {
      if (updatedTabId === tabId && changeInfo.status === 'complete') {
        chrome.tabs.onUpdated.removeListener(listener);
        resolve();
      }
    };
    chrome.tabs.onUpdated.addListener(listener);
    setTimeout(() => { chrome.tabs.onUpdated.removeListener(listener); resolve(); }, timeout);
  });
}

// Functions executed inside page context (must be self-contained)
function getPageContentFn() {
  return {
    url: window.location.href,
    title: document.title,
    text: document.body?.innerText?.slice(0, 50000) || '',
    html: document.documentElement.outerHTML.slice(0, 100000),
  };
}

function clickFn(selector, x, y) {
  let el;
  if (selector) {
    el = document.querySelector(selector);
    if (!el) return { error: `Selector not found: ${selector}` };
  } else if (x !== undefined && y !== undefined) {
    el = document.elementFromPoint(x, y);
    if (!el) return { error: `No element at (${x}, ${y})` };
  } else {
    return { error: 'Provide selector or coordinates' };
  }
  el.scrollIntoView({ behavior: 'instant', block: 'center' });
  el.click();
  const rect = el.getBoundingClientRect();
  return { clicked: true, tag: el.tagName, text: el.innerText?.slice(0, 100), rect: { x: rect.x, y: rect.y, w: rect.width, h: rect.height } };
}

function typeFn(selector, text, clear) {
  const el = selector ? document.querySelector(selector) : document.activeElement;
  if (!el) return { error: `Element not found: ${selector}` };
  el.focus();
  if (clear) {
    el.value = '';
    el.dispatchEvent(new Event('input', { bubbles: true }));
  }
  for (const char of text) {
    el.dispatchEvent(new KeyboardEvent('keydown', { key: char, bubbles: true }));
    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable) {
      if (el.isContentEditable) {
        el.textContent += char;
      } else {
        el.value += char;
      }
    }
    el.dispatchEvent(new KeyboardEvent('keypress', { key: char, bubbles: true }));
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new KeyboardEvent('keyup', { key: char, bubbles: true }));
  }
  el.dispatchEvent(new Event('change', { bubbles: true }));
  return { typed: true, length: text.length };
}

function scrollFn(selector, x, y) {
  const el = selector ? document.querySelector(selector) : window;
  if (!el) return { error: `Element not found: ${selector}` };
  if (el === window) {
    window.scrollBy(x || 0, y || 0);
  } else {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  return { scrolled: true };
}

function waitForSelectorFn(selector, timeout) {
  return new Promise((resolve) => {
    const el = document.querySelector(selector);
    if (el) { resolve({ found: true, tag: el.tagName }); return; }
    const observer = new MutationObserver(() => {
      const found = document.querySelector(selector);
      if (found) {
        observer.disconnect();
        clearTimeout(timer);
        resolve({ found: true, tag: found.tagName });
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    const timer = setTimeout(() => {
      observer.disconnect();
      resolve({ found: false, error: `Timeout waiting for ${selector}` });
    }, timeout || 10000);
  });
}

function getElementTextFn(selector) {
  const el = document.querySelector(selector);
  if (!el) return { error: `Not found: ${selector}` };
  return { text: el.innerText || el.textContent, html: el.innerHTML?.slice(0, 5000) };
}

function fillFormFn(fields) {
  const results = [];
  for (const [selector, value] of Object.entries(fields)) {
    const el = document.querySelector(selector);
    if (!el) { results.push({ selector, error: 'not found' }); continue; }
    el.focus();
    el.value = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    results.push({ selector, filled: true });
  }
  return { results };
}
