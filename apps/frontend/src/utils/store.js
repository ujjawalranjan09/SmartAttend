// Simple reactive store — in-memory state with subscriber pattern
const _state = {
  user: null,
  role: null,
  currentView: 'dashboard',
  notifications: [],
  sessions: [],
  students: [],
  analytics: null,
  offlineQueue: [],
  isOffline: false,
};

const _subs = {};

export const store = {
  get: (key) => _state[key],
  set: (key, val) => {
    _state[key] = val;
    (_subs[key] || []).forEach(fn => fn(val));
  },
  update: (key, updater) => store.set(key, updater(_state[key])),
  subscribe: (key, fn) => {
    _subs[key] = _subs[key] || [];
    _subs[key].push(fn);
    return () => { _subs[key] = _subs[key].filter(f => f !== fn); };
  },
  getAll: () => ({ ..._state }),
};

// Offline queue — IndexedDB wrapper for background sync
export const offlineQueue = {
  db: null,
  async init() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open('smartattend-offline', 1);
      req.onupgradeneeded = (e) => {
        e.target.result.createObjectStore('queue', { keyPath: 'id', autoIncrement: true });
      };
      req.onsuccess = (e) => { this.db = e.target.result; resolve(); };
      req.onerror = reject;
    });
  },
  async push(record) {
    if (!this.db) await this.init();
    return new Promise((resolve, reject) => {
      const tx = this.db.transaction('queue', 'readwrite');
      tx.objectStore('queue').add({ ...record, timestamp: Date.now() });
      tx.oncomplete = resolve;
      tx.onerror = reject;
    });
  },
  async getAll() {
    if (!this.db) await this.init();
    return new Promise((resolve) => {
      const tx = this.db.transaction('queue', 'readonly');
      const req = tx.objectStore('queue').getAll();
      req.onsuccess = () => resolve(req.result);
    });
  },
  async clear() {
    if (!this.db) await this.init();
    return new Promise((resolve) => {
      const tx = this.db.transaction('queue', 'readwrite');
      tx.objectStore('queue').clear();
      tx.oncomplete = resolve;
    });
  },
};
