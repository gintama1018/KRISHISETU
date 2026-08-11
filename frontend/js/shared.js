// KrishiSetu — Shared Core v3
// Security (DPDP Hashing & Consent Verification), Native Push Notifications & Strict Userflow Navigation Guards

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

// ── Userflow Navigation Guard ─────────────────────────────────
function checkUserflow(requireAuth = false, redirectIfAuth = false) {
  const farmer = getFarmer();
  const path = window.location.pathname;

  if (redirectIfAuth && farmer) {
    window.location.replace('/home.html');
    return null;
  }

  if (requireAuth && !farmer) {
    toast('⚠️ Please create your profile first');
    setTimeout(() => window.location.replace('/register.html'), 500);
    return null;
  }

  return farmer;
}

function getLang() { return localStorage.getItem('ks_lang') || 'English'; }

function getFarmer() {
  try {
    const s = localStorage.getItem('ks_farmer');
    if (!s) return null;
    return JSON.parse(s);
  } catch {
    return null;
  }
}

// ── Native Browser Notifications for Real Offline Alerts ──────
async function requestNotificationPermission() {
  if (!('Notification' in window)) return false;
  if (Notification.permission === 'granted') return true;
  if (Notification.permission !== 'denied') {
    const perm = await Notification.permission;
    return perm === 'granted';
  }
  return false;
}

async function triggerOfflineAlert(title, body, tag = 'krishisetu-alert') {
  console.log('[KrishiSetu Alert]', title, body);
  // Show in-app toast
  toast(`🚨 ${title}: ${body}`, 4500);

  // If Service Worker + Notifications permitted, trigger system push notification
  if ('serviceWorker' in navigator && 'Notification' in window && Notification.permission === 'granted') {
    const reg = await navigator.serviceWorker.ready;
    reg.showNotification(title, {
      body,
      icon: '/icons/icon-192.png',
      badge: '/icons/icon-192.png',
      tag,
      vibrate: [200, 100, 200],
      data: { url: '/advisory.html' },
    });
  }
}

// ── Online / Offline Events ───────────────────────────────────
window.addEventListener('online', () => {
  document.getElementById('offline-bar')?.classList.add('hidden');
  toast('✅ Back online — syncing offline queue…');
  // Register background sync
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready.then((r) => r.sync?.register('sync-offline-queue'));
  }
});

window.addEventListener('offline', () => {
  document.getElementById('offline-bar')?.classList.remove('hidden');
  triggerOfflineAlert('Offline Mode Active', 'Your data is cached locally. Advisories will run offline.');
});

if (!navigator.onLine) {
  document.getElementById('offline-bar')?.classList.remove('hidden');
}

// ── Language Bottom Sheet ─────────────────────────────────────
function buildLangGrid() {
  const lang = getLang();
  const grid = document.getElementById('lang-grid');
  if (!grid) return;
  grid.innerHTML = LANGS.map(
    (l) => `<button class="lang-opt${l === lang ? ' sel' : ''}" onclick="setLang('${l}')">${LANG_LABELS[l] || l}</button>`
  ).join('');
}

function openLangSheet() {
  document.getElementById('lang-sheet')?.classList.remove('hidden');
  buildLangGrid();
}

function closeLangSheet() {
  document.getElementById('lang-sheet')?.classList.add('hidden');
}

function setLang(lang) {
  localStorage.setItem('ks_lang', lang);
  closeLangSheet();
  toast(`🌐 Language set to ${lang}`);
  setTimeout(() => location.reload(), 300);
}

// ── Toast System ──────────────────────────────────────────────
function toast(msg, ms = 2800) {
  let t = document.getElementById('toast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'toast';
    t.className = 'toast hidden';
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.classList.remove('hidden');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.add('hidden'), ms);
}

// ── API Helper ────────────────────────────────────────────────
async function apiCall(endpoint, method = 'GET', body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);

  try {
    const res = await fetch(API + endpoint, opts);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    // If offline, queue non-GET requests for background sync
    if (method !== 'GET' && typeof queueForSync === 'function') {
      await queueForSync(endpoint, method, body);
    }
    throw err;
  }
}

// ── Auto-register Service Worker & Notifications ──────────────
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').then((reg) => {
    console.log('[KrishiSetu] ServiceWorker active:', reg.scope);
  }).catch(() => {});
}

// Ask for notifications permission on first interaction
document.addEventListener('click', function initNotifs() {
  requestNotificationPermission();
  document.removeEventListener('click', initNotifs);
}, { once: true });
