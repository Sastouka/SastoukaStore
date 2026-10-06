/* SastoukaStore PATCH 6.6.1 */
/* SastoukaStore PATCH 6.6 */
const CACHE_NAME="sastoukastore-header-v664";
const APP_SHELL=["/","/static/css/style.css","/static/js/app.js","/static/manifest.webmanifest","/static/icons/icon-192.png","/static/icons/icon-512.png","/static/css/sastoukastore_covers_global_2_8.css",,"/static/icons/favicon.ico","/static/icons/icon-512-maskable.png","/static/icons/apple-touch-icon.png"];
self.addEventListener("install",(event)=>{event.waitUntil(caches.open(CACHE_NAME).then(cache=>cache.addAll(APP_SHELL)).then(()=>self.skipWaiting()))});
self.addEventListener("activate",(event)=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE_NAME).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener("fetch",(event)=>{if(event.request.method!=="GET")return;event.respondWith(caches.match(event.request).then(cached=>cached||fetch(event.request).catch(()=>caches.match("/"))))});
