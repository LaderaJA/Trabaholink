/**
 * TrabahoLink Service Worker
 * Caches landing page, job listing, and static assets for offline access
 * Version: 1.0.0
 */

const CACHE_NAME = 'trabaholink-cache-v1';
const STATIC_CACHE_NAME = 'trabaholink-static-v1';

// Files to cache immediately on install
const STATIC_ASSETS = [
    '/static/css/base.css',
    '/static/css/bootstrap.min.css',
    '/static/css/mobile-fixes.css',
    '/static/css/offline.css',
    '/static/js/base.js',
    '/static/js/offline-cache.js',
    '/static/js/offline-ui.js',
    '/static/js/offline-prefetch.js',
    '/static/images/favicon.png',
    '/static/images/logobrand.png',
    '/static/images/default_avatar.svg'
];

// Pages to cache (will be cached when first visited)
const PAGES_TO_CACHE = [
    '/',                    // Landing page
    '/jobs/',              // Job listing
    '/jobs/?tab=services'  // Service listing
];

/**
 * Install Event - Cache static assets
 */
self.addEventListener('install', (event) => {
    console.log('[ServiceWorker] Installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE_NAME)
            .then((cache) => {
                console.log('[ServiceWorker] Caching static assets');
                // Cache static assets, but don't fail if some don't exist
                return Promise.allSettled(
                    STATIC_ASSETS.map(url => 
                        cache.add(url).catch(err => {
                            console.warn(`[ServiceWorker] Failed to cache: ${url}`, err);
                        })
                    )
                );
            })
            .then(() => {
                console.log('[ServiceWorker] Installation complete');
                return self.skipWaiting(); // Activate immediately
            })
    );
});

/**
 * Activate Event - Clean up old caches
 */
self.addEventListener('activate', (event) => {
    console.log('[ServiceWorker] Activating...');
    
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    // Delete old caches
                    if (cacheName !== CACHE_NAME && cacheName !== STATIC_CACHE_NAME) {
                        console.log('[ServiceWorker] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => {
            console.log('[ServiceWorker] Activation complete');
            return self.clients.claim(); // Take control immediately
        })
    );
});

/**
 * Fetch Event - Network first with cache fallback strategy
 */
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }

    // Skip chrome extensions and other protocols
    if (!url.protocol.startsWith('http')) {
        return;
    }

    // Skip admin pages
    if (url.pathname.startsWith('/admin')) {
        return;
    }

    // Skip API calls that need fresh data (unless offline)
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(request).catch(() => {
                return new Response(
                    JSON.stringify({ error: 'Offline', message: 'No internet connection' }),
                    { 
                        headers: { 'Content-Type': 'application/json' },
                        status: 503
                    }
                );
            })
        );
        return;
    }

    // Handle static assets (CSS, JS, images) - Cache First
    if (isStaticAsset(url.pathname)) {
        event.respondWith(cacheFirstStrategy(request));
        return;
    }

    // Handle HTML pages - Network First with Cache Fallback
    if (isHTMLPage(request)) {
        event.respondWith(networkFirstStrategy(request));
        return;
    }

    // Default: Network only
    event.respondWith(fetch(request));
});

/**
 * Cache First Strategy (for static assets)
 * Try cache first, then network, then cache again
 */
async function cacheFirstStrategy(request) {
    try {
        // Check cache first
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            console.log('[ServiceWorker] Serving from cache:', request.url);
            return cachedResponse;
        }

        // Not in cache, fetch from network
        console.log('[ServiceWorker] Fetching from network:', request.url);
        const networkResponse = await fetch(request);

        // Cache the new response
        if (networkResponse.ok) {
            const cache = await caches.open(STATIC_CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }

        return networkResponse;
    } catch (error) {
        console.error('[ServiceWorker] Cache first failed:', error);
        
        // Last resort: try cache again
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }

        // Return offline message
        return new Response('Offline - Asset not cached', { 
            status: 503,
            statusText: 'Service Unavailable'
        });
    }
}

/**
 * Network First Strategy (for HTML pages)
 * Try network first, fallback to cache if offline
 */
async function networkFirstStrategy(request) {
    try {
        // Try network first
        console.log('[ServiceWorker] Fetching page from network:', request.url);
        const networkResponse = await fetch(request);

        // If successful, cache the page
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
            console.log('[ServiceWorker] Cached page:', request.url);
        }

        return networkResponse;
    } catch (error) {
        // Network failed, try cache
        console.log('[ServiceWorker] Network failed, trying cache:', request.url);
        const cachedResponse = await caches.match(request);

        if (cachedResponse) {
            console.log('[ServiceWorker] Serving page from cache:', request.url);
            return cachedResponse;
        }

        // No cache available, show offline page
        console.error('[ServiceWorker] No cached version available:', request.url);
        return getOfflineFallback();
    }
}

/**
 * Check if request is for a static asset
 */
function isStaticAsset(pathname) {
    const staticExtensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.woff', '.woff2', '.ttf'];
    return staticExtensions.some(ext => pathname.endsWith(ext)) || pathname.startsWith('/static/');
}

/**
 * Check if request is for an HTML page
 */
function isHTMLPage(request) {
    const accept = request.headers.get('Accept');
    return accept && accept.includes('text/html');
}

/**
 * Get offline fallback page
 */
function getOfflineFallback() {
    const offlineHTML = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Offline - TrabahoLink</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                }
                .offline-container {
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    max-width: 500px;
                    text-align: center;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                }
                .offline-icon {
                    font-size: 80px;
                    margin-bottom: 20px;
                }
                h1 {
                    color: #1e293b;
                    font-size: 28px;
                    margin-bottom: 16px;
                }
                p {
                    color: #64748b;
                    font-size: 16px;
                    line-height: 1.6;
                    margin-bottom: 24px;
                }
                .retry-button {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    padding: 14px 32px;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: transform 0.2s;
                }
                .retry-button:hover {
                    transform: translateY(-2px);
                }
                .cached-note {
                    margin-top: 24px;
                    padding: 16px;
                    background: #f1f5f9;
                    border-radius: 12px;
                    font-size: 14px;
                    color: #64748b;
                }
            </style>
        </head>
        <body>
            <div class="offline-container">
                <div class="offline-icon">📡</div>
                <h1>You're Offline</h1>
                <p>This page isn't cached yet. Please check your internet connection and try again.</p>
                <button class="retry-button" onclick="location.reload()">Try Again</button>
                <div class="cached-note">
                    💡 <strong>Tip:</strong> Visit the home page and job listings while online to save them for offline viewing.
                </div>
            </div>
        </body>
        </html>
    `;

    return new Response(offlineHTML, {
        headers: { 'Content-Type': 'text/html' },
        status: 503,
        statusText: 'Service Unavailable'
    });
}

/**
 * Listen for messages from the page
 */
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }

    if (event.data && event.data.type === 'CACHE_URLS') {
        const urls = event.data.urls || [];
        caches.open(CACHE_NAME).then(cache => {
            urls.forEach(url => {
                cache.add(url).catch(err => {
                    console.warn('[ServiceWorker] Failed to cache URL:', url, err);
                });
            });
        });
    }
});

console.log('[ServiceWorker] Script loaded');
