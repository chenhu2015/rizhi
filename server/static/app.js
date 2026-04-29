'use strict';

// --- auth ---

function getToken() {
  let t = localStorage.getItem('rizhi_token');
  if (!t) {
    t = prompt('Enter your access token:');
    if (t) localStorage.setItem('rizhi_token', t);
  }
  return t || '';
}

function api(path, opts = {}) {
  return fetch(path, {
    ...opts,
    headers: {
      Authorization: `Bearer ${getToken()}`,
      ...(opts.headers || {}),
    },
  }).then(r => {
    if (r.status === 401) { localStorage.removeItem('rizhi_token'); location.reload(); }
    return r;
  });
}

function postApi(path, body) {
  return api(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

// --- tab navigation ---

function showTab(btn) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
  const name = btn.dataset.tab;
  document.getElementById(`tab-${name}`).classList.add('active');
  btn.classList.add('active');
  if (name === 'today')    loadToday();
  if (name === 'history')  loadHistory();
  if (name === 'settings') loadSettings();
}

// --- paper rendering ---

function scoreClass(s) { return s >= 0.85 ? 'score-high' : 'score-mid'; }

function renderPaper(p) {
  const authors = p.authors.slice(0, 3).join(', ') + (p.authors.length > 3 ? ' et al.' : '');
  const tags = (p.matched_topics || []).map(t => `<span class="tag">${esc(t)}</span>`).join('');
  const pct = Math.round((p.score || 0) * 100);
  return `
    <div class="paper-card">
      <div class="paper-header">
        <div class="paper-title">${esc(p.title)}</div>
        <span class="score-badge ${scoreClass(p.score)}">${pct}%</span>
      </div>
      <div class="paper-authors">${esc(authors)}</div>
      <div class="paper-summary">${esc(p.summary || (p.abstract || '').slice(0, 280) + '…')}</div>
      ${tags ? `<div class="paper-tags">${tags}</div>` : ''}
      <a class="paper-link" href="${p.url}" target="_blank" rel="noopener noreferrer">Read on arXiv →</a>
    </div>`;
}

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// --- today ---

async function loadToday() {
  const el = document.getElementById('today-papers');
  el.innerHTML = '<div class="empty">Loading…</div>';
  try {
    const papers = await api('/api/results/latest').then(r => r.json());
    if (!Array.isArray(papers) || !papers.length) {
      el.innerHTML = '<div class="empty">No papers today yet.<br>Check back after the daily scan runs.</div>';
      return;
    }
    el.innerHTML = papers.map(renderPaper).join('');
    document.getElementById('header-date').textContent = papers[0]?.published || '';
  } catch {
    el.innerHTML = '<div class="empty">Could not load papers.</div>';
  }
}

// --- history ---

async function loadHistory() {
  const el = document.getElementById('history-papers');
  el.innerHTML = '<div class="empty">Loading…</div>';
  try {
    const history = await api('/api/results/history').then(r => r.json());
    if (!Array.isArray(history) || !history.length) {
      el.innerHTML = '<div class="empty">No history yet.</div>';
      return;
    }
    el.innerHTML = history.map(day => `
      <div class="date-group">
        <div class="date-label">${esc(day.date)}</div>
        ${day.papers.map(renderPaper).join('')}
      </div>`).join('');
  } catch {
    el.innerHTML = '<div class="empty">Could not load history.</div>';
  }
}

// --- settings ---

let _profile = null;

async function loadSettings() {
  try {
    _profile = await api('/api/config').then(r => r.json());

    document.getElementById('keyword-tags').innerHTML =
      (_profile.keywords || []).map(k => `
        <button class="tag-rm" onclick="removeItem('keyword','${esc(k)}')">${esc(k)} ×</button>
      `).join('');

    document.getElementById('topic-tags').innerHTML =
      (_profile.topics || []).map(t => `
        <button class="tag-rm" onclick="removeItem('topic','${esc(t)}')">${esc(t)} ×</button>
      `).join('');

    const scoreEl = document.getElementById('min-score');
    const val = _profile.min_score || 0.7;
    scoreEl.value = val;
    document.getElementById('score-label').textContent = parseFloat(val).toFixed(2);
    document.getElementById('max-papers').value = _profile.max_papers_per_run || 5;
  } catch (e) {
    console.error('loadSettings:', e);
  }
}

async function addItem(type) {
  const inputId = type === 'keyword' ? 'new-keyword' : 'new-topic';
  const input = document.getElementById(inputId);
  const value = input.value.trim();
  if (!value || !_profile) return;

  if (type === 'keyword') {
    await postApi('/api/config/keywords', { action: 'add', keyword: value });
  } else {
    _profile.topics = [...(_profile.topics || []), value];
    await postApi('/api/config', _profile);
  }
  input.value = '';
  loadSettings();
}

async function removeItem(type, value) {
  if (!_profile) return;
  if (type === 'keyword') {
    await postApi('/api/config/keywords', { action: 'remove', keyword: value });
  } else {
    _profile.topics = (_profile.topics || []).filter(t => t !== value);
    await postApi('/api/config', _profile);
  }
  loadSettings();
}

async function saveThresholds() {
  if (!_profile) return;
  _profile.min_score = parseFloat(document.getElementById('min-score').value);
  _profile.max_papers_per_run = parseInt(document.getElementById('max-papers').value, 10);
  await postApi('/api/config', _profile);
  const btn = event.target;
  btn.textContent = 'Saved ✓';
  setTimeout(() => { btn.textContent = 'Save'; }, 1500);
}

// --- manual scan ---

let _scanPoll = null;

async function triggerScan() {
  const btn = document.getElementById('scan-btn');
  const statusEl = document.getElementById('scan-status');
  btn.disabled = true;
  statusEl.innerHTML = '<span class="spinner"></span>Starting…';

  try {
    await postApi('/api/scan', {});
  } catch {
    btn.disabled = false;
    statusEl.textContent = 'Failed to start scan.';
    return;
  }

  _scanPoll = setInterval(async () => {
    try {
      const s = await api('/api/scan/status').then(r => r.json());
      if (s.running) {
        statusEl.innerHTML = '<span class="spinner"></span>Scanning…';
      } else {
        clearInterval(_scanPoll);
        btn.disabled = false;
        const ok = s.last_result === 'done';
        statusEl.textContent = ok ? 'Done — reload Today to see new papers.' : (s.last_result || 'Finished.');
        if (ok) loadToday();
      }
    } catch {
      clearInterval(_scanPoll);
      btn.disabled = false;
      statusEl.textContent = 'Lost contact with server.';
    }
  }, 5000);
}

// --- push notifications ---

async function enableNotifications() {
  if (!('Notification' in window) || !('serviceWorker' in navigator)) return;

  const permission = await Notification.requestPermission();
  if (permission !== 'granted') return;

  try {
    const { publicKey } = await fetch('/api/push/vapid-public-key').then(r => r.json());
    if (!publicKey) return;

    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: _urlB64ToUint8(publicKey),
    });

    await postApi('/api/push/subscribe', sub.toJSON());
    document.getElementById('notify-banner').style.display = 'none';
  } catch (e) {
    console.error('enableNotifications:', e);
  }
}

function _urlB64ToUint8(b64) {
  const pad = '='.repeat((4 - b64.length % 4) % 4);
  const raw = atob((b64 + pad).replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
}

// --- init ---

async function init() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(console.error);
  }

  if ('Notification' in window && Notification.permission === 'default') {
    document.getElementById('notify-banner').style.display = 'flex';
  }

  loadToday();
}

init();
