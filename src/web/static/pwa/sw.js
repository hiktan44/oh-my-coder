// Yalnız herkese açık statik dosyalar çevrimdışı saklanır.
const CACHE = 'oh-my-coder-static-v2';
const PRECACHE = ['/manifest.webmanifest', '/icons/icon-192.png', '/icons/icon-512.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  // Eski sürümün sakladığı özel sayfalar bu uygulamanın önbelleğinden çıkar.
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k.startsWith('oh-my-coder-') && k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  // Özel sayfa, API ve SSE istekleri doğrudan sunucuda doğrulanır.
  if (req.mode === 'navigate' || req.destination === 'document') return;
  const publicAsset = url.pathname.startsWith('/static/') || url.pathname.startsWith('/icons/') ||
    url.pathname === '/manifest.webmanifest' || url.pathname === '/favicon.ico';
  if (!publicAsset) return;
  e.respondWith(caches.match(req).then((cached) => cached || fetch(req).then((res) => {
    if (res.ok && !/no-store|private/i.test(res.headers.get('cache-control') || '')) {
      const copy = res.clone();
      e.waitUntil(caches.open(CACHE).then((cache) => cache.put(req, copy)));
    }
    return res;
  })));
});
