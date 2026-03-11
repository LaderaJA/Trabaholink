/**
 * TrabahoLink Offline Link Handler
 * Intercepts link clicks when offline and prevents navigation to uncached pages
 * Version: 1.0.0
 */

class OfflineLinkHandler {
    constructor() {
        this.isOnline = navigator.onLine;
        this.init();
    }

    /**
     * Initialize link handler
     */
    init() {
        this.setupEventListeners();
        console.log('[OfflineLinkHandler] Initialized successfully');
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Listen for online/offline events
        window.addEventListener('online', () => {
            this.isOnline = true;
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
        });

        // Listen for custom online/offline events from offline-ui
        window.addEventListener('tl-online', () => {
            this.isOnline = true;
        });

        window.addEventListener('tl-offline', () => {
            this.isOnline = false;
        });

        // Intercept all link clicks
        document.addEventListener('click', (e) => {
            this.handleLinkClick(e);
        }, true); // Use capture phase to intercept early
    }

    /**
     * Handle link click events
     */
    async handleLinkClick(event) {
        // Only handle when offline
        if (this.isOnline) {
            return;
        }

        // Find the clicked link (might be nested in other elements)
        const link = event.target.closest('a');
        
        if (!link) {
            return; // Not a link click
        }

        // Get the href
        const href = link.getAttribute('href');
        
        // Ignore if no href, javascript:, mailto:, tel:, #anchors
        if (!href || 
            href.startsWith('javascript:') || 
            href.startsWith('mailto:') || 
            href.startsWith('tel:') ||
            href.startsWith('#')) {
            return;
        }

        // Ignore external links (let them fail naturally)
        try {
            const url = new URL(href, window.location.origin);
            if (url.origin !== window.location.origin) {
                return; // External link
            }
        } catch (e) {
            return; // Invalid URL
        }

        // Check if page is cached
        const isCached = await this.isPageCached(href);

        if (!isCached) {
            // Prevent navigation
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();

            // Show message
            this.showUncachedPageMessage(href);
            
            console.log('[OfflineLinkHandler] Blocked navigation to uncached page:', href);
        } else {
            console.log('[OfflineLinkHandler] Allowing navigation to cached page:', href);
        }
    }

    /**
     * Check if a page is cached
     */
    async isPageCached(url) {
        try {
            // Normalize URL
            const fullUrl = new URL(url, window.location.origin).toString();

            // Check both cache storages
            const cacheNames = ['trabaholink-cache-v1', 'trabaholink-static-v1'];
            
            for (const cacheName of cacheNames) {
                const cache = await caches.open(cacheName);
                const response = await cache.match(fullUrl);
                
                if (response) {
                    return true; // Found in cache
                }
            }

            // Also check if it's the current page
            if (fullUrl === window.location.href) {
                return true; // Current page is always "available"
            }

            return false; // Not cached
        } catch (error) {
            console.error('[OfflineLinkHandler] Error checking cache:', error);
            return false; // Assume not cached on error
        }
    }

    /**
     * Show message when user tries to access uncached page
     */
    showUncachedPageMessage(href) {
        // Use the offline UI toast if available
        if (window.offlineUI) {
            window.offlineUI.showToast(
                'Page Not Available Offline',
                'This page needs an internet connection. Please go online to view it.',
                'warning'
            );
        } else {
            // Fallback alert
            alert('This page is not available offline. Please check your internet connection.');
        }

        // Add a visual indicator to the link temporarily
        const link = document.querySelector(`a[href="${href}"]`);
        if (link) {
            link.style.opacity = '0.5';
            setTimeout(() => {
                link.style.opacity = '';
            }, 1000);
        }
    }

    /**
     * Get list of cached pages (for debugging)
     */
    async getCachedPages() {
        try {
            const cache = await caches.open('trabaholink-cache-v1');
            const requests = await cache.keys();
            return requests.map(request => request.url);
        } catch (error) {
            console.error('[OfflineLinkHandler] Error getting cached pages:', error);
            return [];
        }
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.offlineLinkHandler = new OfflineLinkHandler();
});

// Export for use in other scripts
window.OfflineLinkHandler = OfflineLinkHandler;
