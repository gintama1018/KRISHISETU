// KrishiSetu — Shared Core v5 (Production Security Hardened)
const API = '';


const LANGS = ['English', 'Hindi', 'Bengali', 'Assamese', 'Tamil', 'Telugu', 'Marathi', 'Gujarati'];
const LANG_LABELS = {
  English: '🇬🇧 English',
  Hindi: '🇮🇳 हिन्दी',
  Bengali: 'বাংলা',
  Assamese: 'অসমীয়া',
  Tamil: 'தமிழ்',
  Telugu: 'తెలుగు',
  Marathi: 'मराठी',
  Gujarati: 'ગુજરાતી',
};

// ── Farmer Session ─────────────────────────────────────────────
function getLang()    { return localStorage.getItem('ks_lang') || 'English'; }
function getFarmer()  {
  try { const s = localStorage.getItem('ks_farmer'); return s ? JSON.parse(s) : null; }
  catch { return null; }
}

function checkUserflow(requireAuth = false, redirectIfAuth = false) {
  const farmer = getFarmer();
  if (redirectIfAuth && farmer) { window.location.replace('/home.html'); return null; }
  if (requireAuth && !farmer) {
    toast('Please create your profile first');
    setTimeout(() => window.location.replace('/register.html'), 500);
    return null;
  }
  return farmer;
}

// ══════════════════════════════════════════════════════════════════
//  WEB PUSH — Real VAPID subscription (free, no third-party service)
// ══════════════════════════════════════════════════════════════════

async function initPushNotifications() {
  // Only run if SW is supported
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;

  const farmer = getFarmer();

  // Ask for permission (on first meaningful user interaction)
  let permission = Notification.permission;
  if (permission === 'default') {
    permission = await Notification.requestPermission();
  }
  if (permission !== 'granted') return;

  try {
    const reg = await navigator.serviceWorker.ready;

    // Check if already subscribed
    let sub = await reg.pushManager.getSubscription();

    if (!sub) {
      // Fetch VAPID public key from backend
      const keyRes = await fetch('/api/v1/push/vapid-public-key');
      if (!keyRes.ok) return;
      const { publicKey } = await keyRes.json();

      // Convert base64url VAPID key to Uint8Array
      const appKey = urlBase64ToUint8Array(publicKey);

      // Create subscription
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: appKey,
      });
    }

    // POST subscription to backend (upsert by endpoint)
    const subJson = sub.toJSON();
    await fetch('/api/v1/push/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        endpoint: subJson.endpoint,
        keys: subJson.keys,
        farmer_id: farmer?.farmer_id || farmer?.id || null,
        village_code: farmer?.village_code || null,
      }),
    });

    console.log('[KrishiSetu] Push subscription active');
  } catch (err) {
    console.log('[KrishiSetu] Push setup failed (non-critical):', err.message);
  }
}

// Unsubscribe on sign-out
async function unsubscribePush() {
  if (!('serviceWorker' in navigator)) return;
  try {
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.getSubscription();
    if (sub) {
      await fetch('/api/v1/push/unsubscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ endpoint: sub.endpoint }),
      });
      await sub.unsubscribe();
    }
  } catch (e) { /* best-effort */ }
}

// VAPID key conversion helper
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = window.atob(base64);
  return Uint8Array.from([...raw].map(c => c.charCodeAt(0)));
}

// Local (in-app) notification — fallback for when push isn't set up yet
async function triggerOfflineAlert(title, body, tag = 'krishisetu-alert') {
  toast(`${title}: ${body}`, 4500);
  if ('serviceWorker' in navigator && Notification.permission === 'granted') {
    const reg = await navigator.serviceWorker.ready;
    reg.showNotification(title, {
      body,
      icon: '/icons/icon-192.png',
      badge: '/icons/icon-72.png',
      tag,
      vibrate: [200, 100, 200],
      data: { url: '/advisory.html' },
    });
  }
}

// ── Online / Offline events ────────────────────────────────────
window.addEventListener('online', () => {
  document.getElementById('offline-bar')?.classList.add('hidden');
  toast('Back online — syncing…');
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready.then((r) => r.sync?.register('sync-offline-queue'));
  }
});

window.addEventListener('offline', () => {
  document.getElementById('offline-bar')?.classList.remove('hidden');
  triggerOfflineAlert('Offline Mode', 'Advisories are cached locally.');
});

if (!navigator.onLine) {
  document.getElementById('offline-bar')?.classList.remove('hidden');
}

// ── Language Sheet ─────────────────────────────────────────────
function buildLangGrid() {
  const lang = getLang();
  const grid = document.getElementById('lang-grid');
  if (!grid) return;
  grid.innerHTML = LANGS.map(
    (l) => `<button class="lang-opt${l === lang ? ' sel' : ''}" onclick="setLang('${l}')">${LANG_LABELS[l] || l}</button>`
  ).join('');
}

function openLangSheet()  { document.getElementById('lang-sheet')?.classList.remove('hidden'); buildLangGrid(); }
function closeLangSheet() { document.getElementById('lang-sheet')?.classList.add('hidden'); }
function setLang(lang) {
  localStorage.setItem('ks_lang', lang);
  closeLangSheet();
  toast(`Language set to ${lang}`);
  setTimeout(() => location.reload(), 300);
}

// ── Toast ──────────────────────────────────────────────────────
function toast(msg, ms = 2800) {
  let t = document.getElementById('toast');
  if (!t) { t = document.createElement('div'); t.id = 'toast'; t.className = 'toast hidden'; document.body.appendChild(t); }
  t.textContent = msg;
  t.classList.remove('hidden');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.add('hidden'), ms);
}

// ── API Helper (offline-aware) ─────────────────────────────────
async function apiCall(endpoint, method = 'GET', body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  try {
    const res = await fetch(API + endpoint, opts);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    if (method !== 'GET' && typeof queueForSync === 'function') {
      await queueForSync(endpoint, method, body);
    }
    throw err;
  }
}

// ── PWA Install Prompt ─────────────────────────────────────────
let _deferredPrompt = null;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  _deferredPrompt = e;
  document.getElementById('install-bar')?.classList.remove('hidden');
});

function installPWA() {
  if (_deferredPrompt) {
    _deferredPrompt.prompt();
    _deferredPrompt.userChoice.then(() => {
      _deferredPrompt = null;
      document.getElementById('install-bar')?.classList.add('hidden');
    });
  }
}

// ── Boot ───────────────────────────────────────────────────────
// 1. Register Service Worker
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').then((reg) => {
    console.log('[KrishiSetu] SW v5 registered:', reg.scope);
  }).catch(() => {});
}

// 2. Init push on first user interaction (avoids permission prompt before any engagement)
let _pushInitDone = false;
document.addEventListener('click', async function initPushOnce() {
  if (_pushInitDone) return;
  _pushInitDone = true;
  await initPushNotifications();
}, { once: false });

// Also init if already registered farmer (returning user)
if (getFarmer()) {
  navigator.serviceWorker?.ready.then(() => {
    setTimeout(() => initPushNotifications(), 1500);
  });
}
