// SmartAttend Service Worker — Offline-first PWA
const CACHE_VERSION = 'v1.2.0';
const STATIC_CACHE = `smartattend-static-${CACHE_VERSION}`;
const API_CACHE = `smartattend-api-${CACHE_VERSION}`;
const OFFLINE_URL = '/offline.html';

const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/offline.html',
  '/src/styles/main.css',
  '/src/app.js',
  '/src/views/dashboard.js',
  '/src/views/attendance.js',
  '/src/views/sessions.js',
  '/src/views/students.js',
  '/src/views/analytics.js',
  '/src/views/reports.js',
  '/src/views/settings.js',
  '/src/utils/api.js',
  '/src/utils/store.js',
  '/src/utils/qr.js',
  '/manifest.json',
];

// Install — cache static shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => {
      return cache.addAll(STATIC_ASSETS).catch(() => {});
    }).then(() => self.skipWaiting())
  );
});

// Activate — clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k !== STATIC_CACHE && k !== API_CACHE)
          .map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// Fetch strategy:
// - API calls: Network-first, fall back to cache (stale data with banner)
// - Static assets: Cache-first, fall back to network
// - Navigation: Cache-first, fall back to offline page
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // API requests — network first with cache fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request.clone())
        .then(response => {
          if (response.ok && request.method === 'GET') {
            const clone = response.clone();
            caches.open(API_CACHE).then(cache => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => caches.match(request).then(cached => {
          if (cached) {
            // Inject stale header so app can show "offline data" banner
            const headers = new Headers(cached.headers);
            headers.set('X-From-Cache', 'true');
            return new Response(cached.body, { status: cached.status, headers });
          }
          return new Response(JSON.stringify({ error: 'offline', cached: false }), {
            status: 503, headers: { 'Content-Type': 'application/json' }
          });
        }))
    );
    return;
  }

  // Navigation — cache first, offline fallback
  if (request.mode === 'navigate') {
    event.respondWith(
      caches.match(request)
        .then(cached => cached || fetch(request))
        .catch(() => caches.match(OFFLINE_URL))
    );
    return;
  }

  // Static assets — cache first
  event.respondWith(
    caches.match(request)
      .then(cached => cached || fetch(request).then(response => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(STATIC_CACHE).then(cache => cache.put(request, clone));
        }
        return response;
      }))
      .catch(() => new Response('Not found', { status: 404 }))
  );
});

// Background sync — queue offline attendance marks
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-attendance') {
    event.waitUntil(syncOfflineAttendance());
  }
});

async function syncOfflineAttendance() {
  // Read queued records from IndexedDB and POST them
  // Actual IDB logic is in app.js offlineQueue module
  const clients = await self.clients.matchAll();
  clients.forEach(client => client.postMessage({ type: 'SYNC_ATTENDANCE' }));
}

// Push notifications
self.addEventListener('push', (event) => {
  const data = event.data?.json() || {};
  event.waitUntil(
    self.registration.showNotification(data.title || 'SmartAttend', {
      body: data.body || 'You have a new notification',
      icon: '/icons/icon-192.png',
      badge: '/icons/badge-72.png',
      data: data.url || '/',
      actions: [
        { action: 'view', title: 'View' },
        { action: 'dismiss', title: 'Dismiss' }
      ]
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  if (event.action !== 'dismiss') {
    event.waitUntil(
      self.clients.openWindow(event.notification.data || '/')
    );
  }
});
