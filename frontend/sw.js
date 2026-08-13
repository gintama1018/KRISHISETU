// KrishiSetu — Service Worker v6 (Network-First + Real Web Push + Login)
const CACHE_NAME = 'krishisetu-v6';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/home.html',
  '/advisory.html',
  '/market.html',
  '/register.html',
  '/login.html',
  '/profile.html',
  '/dashboard.html',
  '/manifest.json',
  '/css/app.css',
  '/js/shared.js',
  '/js/home.js',
  '/js/advisory.js',
  '/js/market.js',
  '/js/register.js',
  '/js/login.js',
  '/js/profile.js',
  '/js/dashboard.js',
  '/js/db.js',
];

// ── Install — pre-cache static assets ─────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW v5] Pre-caching static assets');
      return cache.addAll(STATIC_ASSETS).catch((e) => console.log('[SW] Cache warning:', e));
    })
  );
  self.skipWaiting();
});

// ── Activate — delete old caches, claim clients ────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => {
        console.log('[SW v5] Deleting old cache:', k);
        return caches.delete(k);
      }))
    ).then(() => self.clients.claim())
  );
});

// ── Fetch — Network-First ──────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response && response.status === 200 && response.type === 'basic') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => {
        return caches.match(event.request).then((cached) => {
          if (cached) return cached;
          if (event.request.headers.get('accept')?.includes('text/html')) {
            return caches.match('/home.html') || caches.match('/');
          }
          return new Response('Offline', { status: 503, statusText: 'Offline' });
        });
      })
  );
});

// ── Background Sync — flush offline queue on reconnect ────────────────────
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-offline-queue') {
    event.waitUntil(flushOfflineQueue());
  }
});

// ══════════════════════════════════════════════════════════════════════════
//  WEB PUSH — Receive & display native OS notification
//  Works even when app is closed / screen locked
// ══════════════════════════════════════════════════════════════════════════
self.addEventListener('push', (event) => {
  console.log('[SW v5] Push received');

  let payload = {
    title: '🌾 KrishiSetu Alert',
    body: 'New farm advisory available. Tap to view.',
    url: '/advisory.html',
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-72.png',
    tag: 'krishisetu-alert',
    vibrate: [200, 100, 200],
  };

  // Parse JSON payload from server
  if (event.data) {
    try {
      payload = { ...payload, ...JSON.parse(event.data.text()) };
    } catch (e) {
      payload.body = event.data.text();
    }
  }

  const options = {
    body: payload.body,
    icon: payload.icon,
    badge: payload.badge,
    tag: payload.tag,
    vibrate: payload.vibrate,
    data: { url: payload.url },
    actions: [
      { action: 'view', title: 'View Advisory' },
      { action: 'dismiss', title: 'Dismiss' },
    ],
    requireInteraction: false,    // auto-dismiss after ~4s on Android
    silent: false,
    timestamp: Date.now(),
  };

  event.waitUntil(
    self.registration.showNotification(payload.title, options)
  );
});

// ── Notification click — open / focus advisory page ───────────────────────
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  // action buttons
  if (event.action === 'dismiss') return;

  const targetUrl = event.notification.data?.url || '/advisory.html';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // Focus existing tab if already open
      for (const client of clientList) {
        if ('focus' in client) {
          client.navigate(targetUrl);
          return client.focus();
        }
      }
      // Otherwise open new tab
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});

// ── Notification close (analytics hook) ───────────────────────────────────
self.addEventListener('notificationclose', (event) => {
  console.log('[SW v5] Notification dismissed by user');
});

// ── IndexedDB helpers for offline queue ────────────────────────────────────
async function flushOfflineQueue() {
  try {
    const db = await openDB();
    const tx = db.transaction('syncQueue', 'readwrite');
    const store = tx.objectStore('syncQueue');
    const items = await getAllFromStore(store);
    for (const item of items) {
      const response = await fetch(item.url, {
        method: item.method,
        headers: { 'Content-Type': 'application/json' },
        body: item.body ? JSON.stringify(item.body) : undefined,
      });
      if (response.ok) {
        await deleteFromStore(db, 'syncQueue', item.id);
        console.log('[SW v5] Synced item:', item.id);
      }
    }
  } catch (e) {
    console.log('[SW v5] Queue sync error:', e);
  }
}

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('krishisetu-db', 1);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function getAllFromStore(store) {
  return new Promise((resolve, reject) => {
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function deleteFromStore(db, storeName, key) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
    const req = tx.objectStore(storeName).delete(key);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
