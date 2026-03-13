// DevAll Agent - Popup Script

const logArea = document.getElementById('logArea');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const sessionIdEl = document.getElementById('sessionId');
const serverUrlInput = document.getElementById('serverUrl');

let currentStatus = 'disconnected';

function log(text, type = '') {
  const entry = document.createElement('div');
  entry.className = `log-entry ${type}`;
  entry.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
  logArea.appendChild(entry);
  logArea.scrollTop = logArea.scrollHeight;
  if (logArea.children.length > 50) logArea.removeChild(logArea.firstChild);
}

function setStatus(status, sid) {
  currentStatus = status;
  statusDot.className = `status-dot ${status}`;
  const labels = { connected: 'Connected to DevAll', disconnected: 'Disconnected', error: 'Connection error', connecting: 'Connecting...' };
  statusText.textContent = labels[status] || status;
  if (sid) sessionIdEl.textContent = sid.slice(0, 8) + '...';
}

// Load saved server URL
chrome.storage.local.get(['serverUrl', 'sessionId'], (result) => {
  if (result.serverUrl) serverUrlInput.value = result.serverUrl;
  if (result.sessionId) sessionIdEl.textContent = result.sessionId.slice(0, 8) + '...';
});

// Listen for status updates from background
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'status_update') {
    setStatus(msg.status, msg.sessionId);
    log(`Status: ${msg.status}`, msg.status === 'connected' ? 'ok' : 'err');
  }
  if (msg.type === 'command_received') {
    log(`← ${msg.command}`, 'cmd');
  }
  if (msg.type === 'command_result') {
    log(`→ ${msg.result}`, 'ok');
  }
});

function saveAndReconnect() {
  const url = serverUrlInput.value.trim();
  if (!url) return;
  chrome.storage.local.set({ serverUrl: url }, () => {
    log('Saving URL and reconnecting...', 'cmd');
    chrome.runtime.sendMessage({ type: 'reconnect', serverUrl: url });
  });
}

function takeScreenshot() {
  log('Taking screenshot...', 'cmd');
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs[0]) { log('No active tab', 'err'); return; }
    chrome.tabs.captureVisibleTab(tabs[0].windowId, { format: 'png' }, (dataUrl) => {
      if (chrome.runtime.lastError) { log(`Error: ${chrome.runtime.lastError.message}`, 'err'); return; }
      log(`Screenshot captured (${Math.round(dataUrl.length / 1024)}KB)`, 'ok');
    });
  });
}

function getPageContent() {
  log('Getting page content...', 'cmd');
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs[0]) { log('No active tab', 'err'); return; }
    chrome.scripting.executeScript({
      target: { tabId: tabs[0].id },
      func: () => ({ url: location.href, title: document.title, textLength: document.body?.innerText?.length }),
    }, (results) => {
      if (chrome.runtime.lastError) { log(`Error: ${chrome.runtime.lastError.message}`, 'err'); return; }
      const r = results[0]?.result;
      log(`Page: ${r?.title} | ${r?.textLength} chars | ${r?.url?.slice(0, 40)}`, 'ok');
    });
  });
}

function getElements() {
  log('Finding clickable elements...', 'cmd');
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs[0]) { log('No active tab', 'err'); return; }
    chrome.scripting.executeScript({
      target: { tabId: tabs[0].id },
      func: () => {
        const els = document.querySelectorAll('a, button, input, textarea, select');
        return Array.from(els).slice(0, 20).map(e => ({
          tag: e.tagName.toLowerCase(),
          text: (e.innerText || e.value || e.placeholder || '').slice(0, 40),
        }));
      },
    }, (results) => {
      if (chrome.runtime.lastError) { log(`Error: ${chrome.runtime.lastError.message}`, 'err'); return; }
      const els = results[0]?.result || [];
      log(`Found ${els.length} elements`, 'ok');
      els.slice(0, 5).forEach(e => log(`  <${e.tag}> ${e.text}`));
    });
  });
}

function clearLog() {
  logArea.innerHTML = '';
  log('Log cleared');
}

function openDevAll() {
  chrome.tabs.create({ url: 'http://localhost:5000' });
}
