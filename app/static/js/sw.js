/* Wardrobe AI service worker — app-shell caching for a fast, installable PWA. */
const CACHE = "wardrobe-ai-v3";
const SHELL = [
  "/static/icons/icon.svg",
  "/static/manifest.webmanifest",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);

  // Browser extensions cannot be written to Cache Storage.
  if (url.protocol !== "http:" && url.protocol !== "https:") return;

  // Always hit the network for pages, API, and app JS/CSS so tab navigation
  // does not serve a stale wardrobe.html / app.js (which broke delete + modal).
  const isAppAsset =
    url.origin === location.origin &&
    (url.pathname.startsWith("/api/") ||
      url.pathname.startsWith("/static/js/") ||
      url.pathname.startsWith("/static/css/") ||
      req.mode === "navigate" ||
      req.destination === "document");

  if (isAppAsset || url.origin !== location.origin) return;

  const isStatic =
    url.origin === location.origin && url.pathname.startsWith("/static/");

  if (isStatic) {
    event.respondWith(
      caches.match(req).then(
        (cached) =>
          cached ||
          fetch(req).then((res) => {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy));
            return res;
          })
      )
    );
  }
});
