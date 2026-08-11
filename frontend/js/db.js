// KrishiSetu — IndexedDB Manager (Layer 0: Offline-First)
const DB_NAME = 'krishisetu-db';
const DB_VERSION = 1;

let _db = null;

async function getDB() {
  if (_db) return _db;
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);

    req.onupgradeneeded = (e) => {
      const db = e.target.result;

      // Farmer profiles store
      if (!db.objectStoreNames.contains('farmers')) {
        db.createObjectStore('farmers', { keyPath: 'farmer_id' });
      }
      // Advisory cache store
      if (!db.objectStoreNames.contains('advisories')) {
        const store = db.createObjectStore('advisories', { keyPath: 'id', autoIncrement: true });
        store.createIndex('farmer_id', 'farmer_id', { unique: false });
        store.createIndex('timestamp', 'timestamp', { unique: false });
      }
      // Offline sync queue
      if (!db.objectStoreNames.contains('syncQueue')) {
        db.createObjectStore('syncQueue', { keyPath: 'id', autoIncrement: true });
      }
      // Insurance event log (local copy)
      if (!db.objectStoreNames.contains('insuranceLog')) {
        const store = db.createObjectStore('insuranceLog', { keyPath: 'id', autoIncrement: true });
        store.createIndex('farmer_id', 'farmer_id', { unique: false });
      }
    };

    req.onsuccess = (e) => { _db = e.target.result; resolve(_db); };
    req.onerror = () => reject(req.error);
  });
}

async function dbPut(storeName, data) {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
    const req = tx.objectStore(storeName).put(data);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function dbGet(storeName, key) {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readonly');
    const req = tx.objectStore(storeName).get(key);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function dbGetAll(storeName) {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readonly');
    const req = tx.objectStore(storeName).getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function dbAdd(storeName, data) {
  const db = await getDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
    const req = tx.objectStore(storeName).add(data);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

// Queue an API call for background sync when offline
async function queueForSync(url, method, body) {
  await dbAdd('syncQueue', {
    url,
    method,
    body,
    queued_at: new Date().toISOString(),
  });
  // Register background sync if available
  if ('serviceWorker' in navigator && 'SyncManager' in window) {
    const reg = await navigator.serviceWorker.ready;
    await reg.sync.register('sync-offline-queue');
  }
}

// Save farmer profile to IndexedDB
async function saveFarmerLocally(farmer) {
  await dbPut('farmers', farmer);
}

// Load farmer from IndexedDB
async function loadFarmerLocally(farmerId) {
  return await dbGet('farmers', farmerId);
}

// Save advisory to local cache
async function saveAdvisoryLocally(farmerId, advisory) {
  await dbAdd('advisories', {
    farmer_id: farmerId,
    ...advisory,
    timestamp: new Date().toISOString(),
  });
}

// Get pending sync count
async function getPendingSyncCount() {
  const items = await dbGetAll('syncQueue');
  return items.length;
}
