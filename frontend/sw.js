// KrishiSetu — Service Worker v3 (Network-First for fresh dev reloads)
const CACHE_NAME = 'krishisetu-v3';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/home.html',
  '/advisory.html',
  '/market.html',
  '/register.html',
  '/profile.html',
  '/dashboard.html',
  '/manifest.json',
  '/css/app.css',
  '/js/shared.js',
  '/js/home.js',
  '/js/advisory.js',
  '/js/market.js',
  '/js/register.js',
  '/js/profile.js',
  '/js/dashboard.js',
  '/js/db.js',
];

// Install — pre-cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW v3] Pre-caching static assets');
      return cache.addAll(STATIC_ASSETS).catch((e) => console.log('[SW] Cache add warning:', e));
    })
  );
  self.skipWaiting();
});

// Activate — immediately delete ALL older caches (v1, v2) and take control of all clients
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => {
        console.log('[SW v3] Deleting old cache:', k);
        return caches.delete(k);
      }))
    ).then(() => self.clients.claim())
  );
});

// Fetch — Network-First for ALL requests (gets fresh files when connected, falls back to cache when offline)
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Skip non-GET requests
  if (event.request.method !== 'GET') return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // If valid response, update cache in background
        if (response && response.status === 200 && response.type === 'basic') {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseClone));
        }
        return response;
      })
      .catch(() => {
        // Offline fallback: match from cache
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

// Background Sync — flush offline queue when reconnected
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-offline-queue') {
    event.waitUntil(flushOfflineQueue());
  }
});

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
        console.log('[SW v3] Synced item:', item.id);
      }
    }
  } catch (e) {
    console.log('[SW v3] Queue sync error:', e);
  }
}

// Push notification click event handler
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || '/advisory.html';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes(targetUrl) && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});

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
