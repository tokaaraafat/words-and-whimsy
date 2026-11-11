// Words & Whimsy service worker: lets the installed app open offline.
const CACHE = "ww-v1";
const CORE = ["./", "index.html", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== "GET" || u.hostname === "api.dictionaryapi.dev") return;      // never cache dictionary lookups or audio sources
  if (r.mode === "navigate") {                                                    // pages: newest first, cached copy when offline
    e.respondWith(fetch(r).then(res => { const c = res.clone(); caches.open(CACHE).then(k => k.put("index.html", c)); return res; }).catch(() => caches.match("index.html")));
    return;
  }
  e.respondWith(caches.match(r).then(hit => hit || fetch(r).then(res => {        // files and fonts: cached after first use
    if (res && (res.ok || res.type === "opaque")) { const c = res.clone(); caches.open(CACHE).then(k => k.put(r, c)); }
    return res;
  }).catch(() => hit)));
});
