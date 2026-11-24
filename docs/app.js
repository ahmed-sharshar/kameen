/* Kameen shared helpers.
   Classic script: every function declared here is a global (and on window, so voice.js can use api()).
   Rule for this file and every page: server and user text goes in through textContent, never innerHTML. */
'use strict';

/* ------------------------------------------------------------------ storage */

function getStored(key) {
  try { return sessionStorage.getItem(key); } catch (e) { return null; }
}

function setStored(key, value) {
  try { sessionStorage.setItem(key, value); } catch (e) { /* storage blocked */ }
}

function dropStored(key) {
  try { sessionStorage.removeItem(key); } catch (e) { /* storage blocked */ }
}

/* Open demo: default the access code in so the link is usable with no unlock step. */
try {
  if (typeof DEFAULT_CODE === 'string' && !sessionStorage.getItem('code')) sessionStorage.setItem('code', DEFAULT_CODE);
} catch (e) { /* storage blocked */ }

/* ------------------------------------------------------------------ server */

var WAKE_TRIES = 30;
var WAKE_GAP_MS = 3000;
var WAKE_TIMEOUT_MS = 10000;

function sleep(ms) {
  return new Promise(function (resolve) { setTimeout(resolve, ms); });
}

/* Polls /health until the server answers. Returns true when ready, false after 30 tries. */
async function wakeServer(statusEl) {
  function show(text, state) {
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.dataset.state = state;
  }
  show('Waking up Kameen...', 'waking');
  for (var i = 0; i < WAKE_TRIES; i++) {
    var ctrl = new AbortController();
    var timeout = setTimeout(function () { ctrl.abort(); }, WAKE_TIMEOUT_MS);
    try {
      var res = await fetch(API_BASE + '/health', { signal: ctrl.signal, cache: 'no-store' });
      if (res.ok) {
        show('Ready', 'ready');
        return true;
      }
    } catch (e) {
      /* still asleep or unreachable: try again */
    } finally {
      clearTimeout(timeout);
    }
    if (i < WAKE_TRIES - 1) await sleep(WAKE_GAP_MS);
  }
  show('Server not reachable', 'down');
  return false;
}

function requestHeaders() {
  return {
    'Content-Type': 'application/json',
    'X-Access-Code': getStored('code') || (typeof DEFAULT_CODE === 'string' ? DEFAULT_CODE : '')
  };
}

function detailToText(detail) {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map(function (item) {
      if (item && typeof item === 'object' && item.msg) return String(item.msg);
      return typeof item === 'string' ? item : JSON.stringify(item);
    }).join('; ');
  }
  if (detail && typeof detail === 'object') {
    return detail.message ? String(detail.message) : JSON.stringify(detail);
  }
  return String(detail);
}

async function failureFrom(res) {
  var text = '';
  try { text = await res.text(); } catch (e) { /* no body */ }
  var message = text.trim();
  try {
    var data = JSON.parse(text);
    if (data && data.detail != null) message = detailToText(data.detail);
  } catch (e) { /* not JSON: keep the text */ }
  if (!message || message.charAt(0) === '<') message = 'The server returned an error (' + res.status + ').';
  if (message.length > 400) message = message.slice(0, 400) + '...';
  var err = new Error(message);
  err.status = res.status;
  return err;
}

async function sendRequest(path, options) {
  var res;
  try {
    res = await fetch(API_BASE + path, options);
  } catch (e) {
    var offline = new Error('Could not reach the server. Check the connection and try again.');
    offline.status = 0;
    throw offline;
  }
  if (!res.ok) throw await failureFrom(res);
  var text = await res.text();
  if (!text) return {};
  try { return JSON.parse(text); } catch (e) { return {}; }
}

/* POST JSON. Throws an Error whose message is the server's `detail`; err.status holds the HTTP status. */
async function api(path, body) {
  return sendRequest(path, {
    method: 'POST',
    headers: requestHeaders(),
    body: JSON.stringify(body == null ? {} : body)
  });
}

/* GET JSON with the same headers and error behaviour as api(). */
async function apiGet(path) {
  return sendRequest(path, { method: 'GET', headers: requestHeaders() });
}

/* Live events for one conversation. EventSource cannot send headers; the stream is open by design. */
function watch(conversationId, onEvent) {
  var source = new EventSource(API_BASE + '/events/stream?conversation_id=' + encodeURIComponent(conversationId));
  source.onmessage = function (message) {
    var data;
    try { data = JSON.parse(message.data); } catch (e) { return; }
    onEvent(data);
  };
  return source;
}

/* Pages other than index.html call this first. */
function requireCode() {
  if (!getStored('code')) {
    location.replace('index.html');
    return false;
  }
  return true;
}

/* A 401 means the stored code is wrong: forget it and go back to the front door. */
function authFailed(err) {
  if (err && err.status === 401) {
    dropStored('code');
    setStored('code_rejected', '1');
    location.replace('index.html');
    return true;
  }
  return false;
}

function sessionPath(id, tail) {
  return '/sessions/' + encodeURIComponent(String(id)) + (tail || '');
}

function evidenceUrl(id) {
  return API_BASE + '/sessions/' + encodeURIComponent(String(id)) + '/evidence';
}

/* ------------------------------------------------------------------ DOM helpers */

function $(selector, root) {
  return (root || document).querySelector(selector);
}

function $all(selector, root) {
  return Array.prototype.slice.call((root || document).querySelectorAll(selector));
}

function escapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/* Builds an element. Text always lands in text nodes, so nothing passed here is parsed as HTML. */
function h(tag, attrs, children) {
  var node = document.createElement(tag);
  if (attrs) {
    Object.keys(attrs).forEach(function (key) {
      var value = attrs[key];
      if (value == null || value === false) return;
      if (key === 'class') node.className = value;
      else if (key === 'text') node.textContent = String(value);
      else if (key.slice(0, 2) === 'on' && typeof value === 'function') node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? '' : String(value));
    });
  }
  if (children != null) {
    (Array.isArray(children) ? children : [children]).forEach(function (child) {
      if (child == null || child === false) return;
      node.appendChild(typeof child === 'object' ? child : document.createTextNode(String(child)));
    });
  }
  return node;
}

function clearNode(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

var ARABIC_LETTERS = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/;

function hasArabic(text) {
  return ARABIC_LETTERS.test(String(text == null ? '' : text));
}

/* Sets text and, when it contains Arabic letters, dir="rtl" on the same node. */
function setText(node, text) {
  var value = String(text == null ? '' : text);
  node.textContent = value;
  if (hasArabic(value)) node.setAttribute('dir', 'rtl');
  else node.removeAttribute('dir');
  return node;
}

/* Inline message area. An empty text hides it. kind: 'error' | 'ok' | 'info'. */
function note(node, text, kind) {
  if (!node) return;
  var value = String(text == null ? '' : text);
  setText(node, value);
  node.hidden = !value;
  if (kind) node.dataset.kind = kind;
  else delete node.dataset.kind;
}

function humanize(value) {
  var text = String(value == null ? '' : value).replace(/[_-]+/g, ' ').trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : '';
}

function toDate(value) {
  if (value == null || value === '') return null;
  if (typeof value === 'number' || /^\d+(\.\d+)?$/.test(String(value))) {
    var n = Number(value);
    if (n < 1e12) n *= 1000;
    return new Date(n);
  }
  var parsed = new Date(value);
  return isNaN(parsed.getTime()) ? null : parsed;
}

function formatTime(value) {
  var date = toDate(value);
  return date ? date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
}

function formatDateTime(value) {
  var date = toDate(value);
  if (!date) return '';
  return date.toLocaleString([], { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

function clock(seconds) {
  var s = Math.max(0, Math.floor(seconds));
  var rest = s % 60;
  return Math.floor(s / 60) + ':' + (rest < 10 ? '0' : '') + rest;
}

/* ------------------------------------------------------------------ labels */

var INTEL_LABELS = {
  iban: 'IBAN', phone: 'Phone', phone_number: 'Phone', url: 'Link', link: 'Link',
  email: 'Email', card: 'Card', card_number: 'Card', wallet: 'Wallet', crypto_wallet: 'Wallet',
  name: 'Name', bank: 'Bank', account: 'Account', otp: 'OTP', upi: 'UPI'
};

var GUARD_LABELS = {
  unknown_number: 'Unknown number in a reply',
  role_leak: 'Role leak caught',
  asked_for_secret: 'Agent asked for a secret'
};

var OUTCOME_LABELS = {
  resisted: 'Resisted',
  hesitated: 'Hesitated',
  would_comply: 'Would comply',
  attempted_disclosure: 'Attempted disclosure',
  distress: 'Distress',
  stopped: 'Stopped',
  ignored: 'Ignored the message'
};

function labelFor(map, key) {
  var k = String(key == null ? '' : key);
  return Object.prototype.hasOwnProperty.call(map, k.toLowerCase()) ? map[k.toLowerCase()] : humanize(k);
}

/* ------------------------------------------------------------------ chat rendering */

function nearBottom(listEl) {
  return listEl.scrollHeight - listEl.scrollTop - listEl.clientHeight < 120;
}

/* Greyed line shown in an empty transcript. Removed by the first bubble. */
function setHint(listEl, text) {
  var old = listEl.querySelector('.transcript-hint');
  if (old) old.remove();
  if (text) listEl.insertBefore(h('p', { class: 'transcript-hint', text: text }), listEl.firstChild);
}

/* speaker: 'agent' (left), 'counterpart' (right) or 'marker' (centred system line). */
function addBubble(listEl, speaker, text, opts) {
  opts = opts || {};
  var kind = speaker === 'agent' ? 'agent' : (speaker === 'counterpart' ? 'counterpart' : 'marker');
  var hint = listEl.querySelector('.transcript-hint');
  if (hint) hint.remove();
  var row = h('div', { class: 'msg msg--' + kind });
  if (kind !== 'marker' && opts.name) row.appendChild(setText(h('span', { class: 'msg-meta' }), opts.name));
  row.appendChild(setText(h('p', { class: 'bubble' }), text));
  var stamp = opts.time ? formatTime(opts.time) : '';
  if (stamp) row.appendChild(h('span', { class: 'msg-time', text: stamp }));
  var stick = opts.stick || nearBottom(listEl);
  var typing = listEl.querySelector('.msg--typing');
  if (typing) listEl.insertBefore(row, typing);
  else listEl.appendChild(row);
  if (stick) listEl.scrollTop = listEl.scrollHeight;
  return row;
}

function setTyping(listEl, on) {
  var existing = listEl.querySelector('.msg--typing');
  if (!on) {
    if (existing) existing.remove();
    return;
  }
  if (existing) return;
  var row = h('div', { class: 'msg msg--agent msg--typing' }, [
    h('p', { class: 'bubble' }, [
      h('span', { class: 'dot' }), h('span', { class: 'dot' }), h('span', { class: 'dot' }),
      h('span', { class: 'sr-only', text: 'Typing' })
    ])
  ]);
  listEl.appendChild(row);
  listEl.scrollTop = listEl.scrollHeight;
}

function intelKey(intel) {
  return String(intel && intel.type).toLowerCase() + '|' + String(intel && intel.value);
}

/* One intel card: type, value, the quote it came from. opts.detail adds source and confidence. */
function renderIntelCard(intel, opts) {
  intel = intel || {};
  var value = String(intel.value == null ? '' : intel.value);
  var quote = String(intel.quote == null ? '' : intel.quote);
  var card = h('li', { class: 'intel-card' });
  if (hasArabic(value) || hasArabic(quote)) card.setAttribute('dir', 'rtl');
  card.appendChild(h('span', { class: 'intel-type', text: labelFor(INTEL_LABELS, intel.type || 'intel') }));
  card.appendChild(h('span', { class: 'intel-value', dir: 'auto', text: value }));
  if (quote) card.appendChild(h('q', { class: 'intel-quote', text: quote }));
  if (opts && opts.detail) {
    var bits = [];
    if (intel.source) bits.push('Source: ' + humanize(intel.source));
    if (intel.confidence != null && intel.confidence !== '') {
      var c = Number(intel.confidence);
      bits.push('Confidence: ' + (isNaN(c) ? String(intel.confidence) : (c <= 1 ? Math.round(c * 100) + '%' : String(c))));
    }
    if (bits.length) card.appendChild(h('span', { class: 'intel-foot', dir: 'ltr', text: bits.join(', ') }));
  }
  return card;
}

function renderCanary(canary) {
  canary = canary || {};
  return h('li', { class: 'canary' }, [
    h('span', { class: 'intel-type', text: labelFor(INTEL_LABELS, canary.kind || 'canary') }),
    h('span', { class: 'intel-value', dir: 'auto', text: String(canary.value == null ? '' : canary.value) })
  ]);
}

/* ------------------------------------------------------------------ chat session controller

   One conversation: creates it, listens to its live events, sends text, ends it.
   Bubbles are rendered ONLY from `message` events. The /chat response is used for `status`
   and to clear the typing indicator; the visitor's own text appears when the server echoes it
   (masked where needed), never optimistically.

   cfg: {
     listEl,                       transcript container
     names(): {agent, counterpart} display names (used by the email skin and screen readers)
     lingerMs,                     how long to keep the stream open after the session ends
     onStart(res, body),           after POST /sessions succeeds, before any event arrives
     onEvent(ev),                  every live event
     onEnded(reason),              once per session
     onStream('open' | 'lost')     live connection state while the session is active
   } */
function createChat(cfg) {
  var chat = { id: null, live: false, sending: false, stream: null };
  var opening = '';
  var openingPending = false;
  var closeTimer = null;
  var rows = [];   /* bubbles rendered from live events, newest last */

  function names() {
    return (cfg.names && cfg.names()) || {};
  }

  function closeStream() {
    clearTimeout(closeTimer);
    closeTimer = null;
    if (chat.stream) {
      chat.stream.close();
      chat.stream = null;
    }
  }

  function renderMessage(ev) {
    if (ev.speaker !== 'agent' && ev.speaker !== 'counterpart') return; /* markers are not shown live */
    var text = ev.text == null ? '' : String(ev.text);
    if (!text.trim()) return;
    if (openingPending) {
      /* The opening line is already on screen (from POST /sessions). Skip one identical echo of it. */
      openingPending = false;
      if (ev.speaker === 'agent' && text.trim() === opening) return;
    }
    if (ev.speaker === 'agent') setTyping(cfg.listEl, false);
    rows.push(addBubble(cfg.listEl, ev.speaker, text, {
      name: ev.speaker === 'agent' ? names().agent : names().counterpart,
      stick: ev.speaker === 'counterpart'
    }));
  }

  /* On a call, the voice platform can send a turn again when the caller keeps talking. The server
     then drops the earlier version and says how many messages went; remove the same bubbles. */
  function retract(count) {
    for (var i = 0; i < count && rows.length; i++) {
      var row = rows.pop();
      if (row && row.parentNode) row.parentNode.removeChild(row);
    }
  }

  chat.reset = function () {
    closeStream();
    chat.id = null;
    chat.live = false;
    chat.sending = false;
    opening = '';
    openingPending = false;
    rows = [];
    clearNode(cfg.listEl);
  };

  /* body goes to POST /sessions as is. showOpening: render opening_line as the first agent bubble. */
  chat.start = async function (body, showOpening) {
    var res = await api('/sessions', body);
    if (!res || res.conversation_id == null) throw new Error('The server did not return a session.');
    chat.reset();
    chat.id = res.conversation_id;
    chat.live = true;
    opening = String(res.opening_line || '').trim();
    if (showOpening && opening) {
      addBubble(cfg.listEl, 'agent', opening, { name: names().agent });
      openingPending = true;
    }
    if (cfg.onStart) cfg.onStart(res, body);
    var stream = watch(chat.id, function (ev) {
      if (chat.stream !== stream || !ev || typeof ev !== 'object') return;
      if (ev.type === 'message') renderMessage(ev);
      else if (ev.type === 'retract') retract(Number(ev.count) || 0);
      else if (ev.type === 'ended') chat.end(ev.reason || '');
      if (cfg.onEvent) cfg.onEvent(ev);
    });
    stream.onopen = function () {
      if (chat.stream === stream && cfg.onStream) cfg.onStream('open');
    };
    stream.onerror = function () {
      if (chat.stream === stream && chat.live && cfg.onStream) cfg.onStream('lost');
    };
    chat.stream = stream;
    return res;
  };

  chat.send = async function (text) {
    if (chat.id == null || !chat.live || chat.sending) return null;
    var id = chat.id;
    chat.sending = true;
    setTyping(cfg.listEl, true);
    try {
      var res = await api('/chat', { conversation_id: id, text: text });
      if (chat.id === id && res && res.status === 'ended') chat.end('');
      return res;
    } finally {
      if (chat.id === id) {
        chat.sending = false;
        setTyping(cfg.listEl, false);
      }
    }
  };

  chat.end = function (reason) {
    if (!chat.live) return;
    chat.live = false;
    setTyping(cfg.listEl, false);
    clearTimeout(closeTimer);
    closeTimer = setTimeout(closeStream, cfg.lingerMs || 6000);
    if (cfg.onStream) cfg.onStream('open');
    if (cfg.onEnded) cfg.onEnded(reason || '');
  };

  chat.kill = async function () {
    if (chat.id == null) return;
    var id = chat.id;
    await api(sessionPath(id, '/kill'), {});
    if (chat.id === id) chat.end('Ended by you');
  };

  chat.closeStream = closeStream;
  return chat;
}

/* ------------------------------------------------------------------ voice call bar

   Wraps window.kameenVoice (voice.js) with a visible timer.
   cfg: { barEl, timeEl, maxSeconds, onChange(state) }   state: 'idle' | 'connecting' | 'live' */
function createCallBar(cfg) {
  var bar = { state: 'idle' };
  var tick = null;
  var startedAt = 0;

  function set(state) {
    bar.state = state;
    cfg.barEl.hidden = state === 'idle';
    cfg.barEl.dataset.state = state;
    if (cfg.onChange) cfg.onChange(state);
  }

  function stopTick() {
    clearInterval(tick);
    tick = null;
  }

  function paint() {
    var elapsed = Math.min(cfg.maxSeconds, (Date.now() - startedAt) / 1000);
    cfg.timeEl.textContent = clock(elapsed) + ' of ' + clock(cfg.maxSeconds);
  }

  bar.start = async function (conversationId) {
    if (!window.kameenVoice) throw new Error('The voice module did not load.');
    cfg.timeEl.textContent = 'Connecting...';
    set('connecting');
    try {
      await window.kameenVoice.startCall(conversationId, cfg.maxSeconds);
    } catch (err) {
      stopTick();
      set('idle');
      throw err;
    }
    startedAt = Date.now();
    paint();
    stopTick();
    tick = setInterval(paint, 1000);
    set('live');
  };

  bar.stop = async function () {
    stopTick();
    if (window.kameenVoice) {
      try { await window.kameenVoice.endCall(); } catch (err) { /* nothing to end */ }
    }
    if (bar.state !== 'idle') set('idle');
  };

  window.addEventListener('kameen:call-ended', function () {
    if (bar.state === 'live') {
      stopTick();
      set('idle');
    }
  });

  return bar;
}

function voiceErrorText(err) {
  var name = err && err.name;
  if (name === 'NotAllowedError' || name === 'SecurityError') return 'Microphone access was blocked. Allow it in the browser and try again.';
  if (name === 'NotFoundError' || name === 'OverconstrainedError') return 'No microphone was found.';
  if (name === 'NotReadableError') return 'The microphone is in use by another app.';
  var message = err && err.message ? String(err.message) : String(err || 'Unknown error');
  return /[.!?]$/.test(message) ? message : message + '.';
}

/* Marks the current page in the top navigation. */
function markNav() {
  var here = location.pathname.split('/').pop() || 'index.html';
  $all('.topnav a').forEach(function (link) {
    if (link.getAttribute('href') === here) link.setAttribute('aria-current', 'page');
  });
}
