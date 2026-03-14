/*
 * Next PMS — Service Worker
 * Caching strategies:
 *   - App shell (/next-pms): network-first, fallback to cache
 *   - Hashed assets (/assets/next_pms/frontend/assets/*): cache-first
 *   - Icons & static (/assets/next_pms/icons/*): cache-first
 *   - API calls (/api/*): network-only
 */

const CACHE_NAME = 'next-pms-shell-v1';
const ASSETS_CACHE = 'next-pms-assets-v1';

// Pre-cache the app shell on install
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(['/next-pms/']);
    })
  );
  self.skipWaiting();
});

// Clean up old caches on activate
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME && key !== ASSETS_CACHE)
          .map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// Fetch handler with per-request strategies
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Only handle same-origin requests
  if (url.origin !== self.location.origin) return;

  // API calls — network only (let them fail when offline)
  if (url.pathname.startsWith('/api/')) {
    return;
  }

  // Hashed static assets (JS/CSS bundles) — cache-first
  if (url.pathname.startsWith('/assets/next_pms/frontend/assets/')) {
    event.respondWith(cacheFirst(event.request, ASSETS_CACHE));
    return;
  }

  // Icons and other static files — cache-first
  if (url.pathname.startsWith('/assets/next_pms/icons/') ||
      url.pathname.startsWith('/assets/next_pms/manifest.json')) {
    event.respondWith(cacheFirst(event.request, ASSETS_CACHE));
    return;
  }

  // App shell (navigation to /next-pms/*) — network-first
  if (event.request.mode === 'navigate' && url.pathname.startsWith('/next-pms')) {
    event.respondWith(networkFirstShell(event.request));
    return;
  }
});

/**
 * Cache-first: serve from cache if available, otherwise fetch and cache.
 */
async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    // If network fails and nothing cached, return a basic offline response
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

/**
 * Network-first for app shell: try network, update cache, fallback to cached shell.
 */
async function networkFirstShell(request) {
  try {
    const response = await fetch(request);
    // Cache the fresh shell
    const cache = await caches.open(CACHE_NAME);
    cache.put('/next-pms/', response.clone());
    return response;
  } catch (err) {
    // Network failed — serve cached shell
    const cached = await caches.match('/next-pms/');
    if (cached) return cached;
    return new Response('Offline — please check your connection.', {
      status: 503,
      statusText: 'Service Unavailable',
      headers: { 'Content-Type': 'text/html' },
    });
  }
}
