const cacheName = "bilim-static-" + BUILD_VERSION;
const assets = new Set(STATIC_FILES);

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(cacheName).then((cache) => cache.addAll([...assets])));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(
    keys.filter((key) => key.startsWith("bilim-static-") && key !== cacheName).map((key) => caches.delete(key))
  )).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (event) => {
  const {request} = event;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname === "/api" || url.pathname.startsWith("/api/") || /^\/health\/?$/.test(url.pathname)) return;
  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(async () => {
      const cache = await caches.open(cacheName);
      return (await cache.match("/offline.html")) || Response.error();
    }));
  } else if (assets.has(url.pathname) && !url.search) {
    event.respondWith(caches.open(cacheName).then(async (cache) => {
      return (await cache.match(request)) || fetch(request);
    }));
  }
});
