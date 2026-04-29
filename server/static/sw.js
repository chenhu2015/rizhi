const CACHE = 'rizhi-v1';
const SHELL = ['/', '/app.js', '/manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.url.includes('/api/') || e.request.url.includes('/internal/')) return;
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request)));
});

self.addEventListener('push', e => {
  const text = e.data ? e.data.text() : 'New papers available';
  e.waitUntil(
    self.registration.showNotification('rizhi 日知', {
      body: text,
      icon: '/icon-192.png',
      badge: '/icon-192.png',
      tag: 'rizhi-digest',
      renotify: true,
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(
    clients.matchAll({ type: 'window' }).then(list => {
      for (const c of list) {
        if (c.url.startsWith(self.location.origin) && 'focus' in c) return c.focus();
      }
      if (clients.openWindow) return clients.openWindow('/');
    })
  );
});
