/**
 * TrabahoLink Offline UI Manager
 * Mobile-first offline detection and UI components
 * Version: 1.0.0
 */

class OfflineUIManager {
    constructor() {
        this.isOnline = navigator.onLine;
        this.bannerId = 'tl-offline-banner';
        this.statusIndicatorId = 'tl-connection-status';
        this.offlineOverlayClass = 'tl-offline-overlay';
        
        this.init();
    }

    /**
     * Initialize offline UI manager
     */
    init() {
        this.createOfflineBanner();
        this.createConnectionStatus();
        this.setupEventListeners();
        this.updateUI();
        
        console.log('[OfflineUI] Initialized successfully');
    }

    /**
     * Create offline banner (mobile-optimized)
     */
    createOfflineBanner() {
        // Check if banner already exists
        if (document.getElementById(this.bannerId)) {
            return;
        }

        const banner = document.createElement('div');
        banner.id = this.bannerId;
        banner.className = 'tl-offline-banner';
        banner.setAttribute('role', 'alert');
        banner.setAttribute('aria-live', 'assertive');
        
        banner.innerHTML = `
            <div class="tl-offline-banner-content">
                <div class="tl-offline-icon">
                    <i class="bi bi-wifi-off"></i>
                </div>
                <div class="tl-offline-text">
                    <span class="tl-offline-title">You're Offline</span>
                    <span class="tl-offline-subtitle">Viewing cached content</span>
                </div>
                <button class="tl-offline-close" aria-label="Close notification">
                    <i class="bi bi-x"></i>
                </button>
            </div>
        `;

        // Insert at the beginning of body
        document.body.insertBefore(banner, document.body.firstChild);

        // Add close functionality
        const closeBtn = banner.querySelector('.tl-offline-close');
        closeBtn.addEventListener('click', () => {
            banner.classList.add('tl-offline-banner-minimized');
        });

        // Add expand on tap for minimized banner
        banner.addEventListener('click', (e) => {
            if (banner.classList.contains('tl-offline-banner-minimized') && 
                !e.target.closest('.tl-offline-close')) {
                banner.classList.remove('tl-offline-banner-minimized');
            }
        });
    }

    /**
     * Create connection status indicator for navbar
     */
    createConnectionStatus() {
        // Check if status indicator already exists
        if (document.getElementById(this.statusIndicatorId)) {
            return;
        }

        const statusIndicator = document.createElement('div');
        statusIndicator.id = this.statusIndicatorId;
        statusIndicator.className = 'tl-connection-status';
        statusIndicator.setAttribute('title', 'Connection Status');
        
        statusIndicator.innerHTML = `
            <span class="tl-status-dot"></span>
            <span class="tl-status-text">Online</span>
        `;

        // Try to add to navbar
        const navbar = document.querySelector('.navbar .container-fluid, .navbar .container');
        if (navbar) {
            navbar.appendChild(statusIndicator);
        }
    }

    /**
     * Setup event listeners for online/offline detection
     */
    setupEventListeners() {
        // Listen for online/offline events
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());

        // Periodic connectivity check (every 30 seconds)
        setInterval(() => this.checkConnectivity(), 30000);

        // Check on page visibility change
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.checkConnectivity();
            }
        });
    }

    /**
     * Handle online event
     */
    handleOnline() {
        this.isOnline = true;
        this.updateUI();
        this.showToast('Back Online', 'You\'re connected to the internet', 'success');
        
        // Trigger event for other components
        window.dispatchEvent(new CustomEvent('tl-online'));
        
        console.log('[OfflineUI] Device is online');
    }

    /**
     * Handle offline event
     */
    handleOffline() {
        this.isOnline = false;
        this.updateUI();
        this.showToast('No Connection', 'You\'re offline. Viewing cached content', 'warning');
        
        // Trigger event for other components
        window.dispatchEvent(new CustomEvent('tl-offline'));
        
        console.log('[OfflineUI] Device is offline');
    }

    /**
     * Check connectivity by pinging server
     */
    async checkConnectivity() {
        try {
            // Try to fetch a small resource with no-cache
            const response = await fetch('/static/images/favicon.ico', {
                method: 'HEAD',
                cache: 'no-cache'
            });
            
            const newStatus = response.ok;
            
            // Only update if status changed
            if (newStatus !== this.isOnline) {
                if (newStatus) {
                    this.handleOnline();
                } else {
                    this.handleOffline();
                }
            }
        } catch (error) {
            // Fetch failed, likely offline
            if (this.isOnline) {
                this.handleOffline();
            }
        }
    }

    /**
     * Update UI based on connection status
     */
    updateUI() {
        const banner = document.getElementById(this.bannerId);
        const statusIndicator = document.getElementById(this.statusIndicatorId);

        if (this.isOnline) {
            // Hide offline banner
            if (banner) {
                banner.classList.remove('tl-offline-banner-visible');
            }

            // Update status indicator
            if (statusIndicator) {
                statusIndicator.classList.remove('tl-status-offline');
                statusIndicator.classList.add('tl-status-online');
                const text = statusIndicator.querySelector('.tl-status-text');
                if (text) text.textContent = 'Online';
            }

            // Remove offline overlays from disabled elements
            document.querySelectorAll(`.${this.offlineOverlayClass}`).forEach(el => {
                el.classList.remove(this.offlineOverlayClass);
            });

            // Enable forms and buttons
            this.enableInteractiveElements();

        } else {
            // Show offline banner
            if (banner) {
                banner.classList.add('tl-offline-banner-visible');
                banner.classList.remove('tl-offline-banner-minimized');
            }

            // Update status indicator
            if (statusIndicator) {
                statusIndicator.classList.remove('tl-status-online');
                statusIndicator.classList.add('tl-status-offline');
                const text = statusIndicator.querySelector('.tl-status-text');
                if (text) text.textContent = 'Offline';
            }

            // Disable forms and buttons that require connection
            this.disableInteractiveElements();
        }
    }

    /**
     * Disable interactive elements when offline
     */
    disableInteractiveElements() {
        // Disable submit buttons (except those marked as offline-capable)
        document.querySelectorAll('button[type="submit"]:not(.tl-offline-enabled)').forEach(btn => {
            if (!btn.hasAttribute('data-original-disabled')) {
                btn.setAttribute('data-original-disabled', btn.disabled);
                btn.disabled = true;
                btn.classList.add('tl-disabled-offline');
            }
        });

        // Disable forms (except those marked as offline-capable)
        document.querySelectorAll('form:not(.tl-offline-enabled)').forEach(form => {
            if (!form.querySelector(`.${this.offlineOverlayClass}`)) {
                form.style.position = 'relative';
                form.style.opacity = '0.6';
                form.style.pointerEvents = 'none';
                form.setAttribute('data-offline-disabled', 'true');
            }
        });

        // Add disabled appearance to links that require connection
        document.querySelectorAll('a.tl-requires-connection').forEach(link => {
            link.classList.add('tl-disabled-offline');
        });
    }

    /**
     * Enable interactive elements when online
     */
    enableInteractiveElements() {
        // Re-enable submit buttons
        document.querySelectorAll('button.tl-disabled-offline').forEach(btn => {
            const originalDisabled = btn.getAttribute('data-original-disabled');
            btn.disabled = originalDisabled === 'true';
            btn.removeAttribute('data-original-disabled');
            btn.classList.remove('tl-disabled-offline');
        });

        // Re-enable forms
        document.querySelectorAll('form[data-offline-disabled]').forEach(form => {
            form.style.opacity = '';
            form.style.pointerEvents = '';
            form.removeAttribute('data-offline-disabled');
        });

        // Remove disabled appearance from links
        document.querySelectorAll('a.tl-disabled-offline').forEach(link => {
            link.classList.remove('tl-disabled-offline');
        });
    }

    /**
     * Add manual save toggle button to card (mobile-optimized)
     */
    addSaveToggleButton(element, itemId, itemType = 'job') {
        if (!element || element.querySelector('.tl-save-toggle')) {
            return;
        }

        // Check if item is already saved
        const isSaved = itemType === 'job' 
            ? window.offlineCache.getCachedJob(itemId) !== null
            : window.offlineCache.getCachedService(itemId) !== null;

        const button = document.createElement('button');
        button.className = `tl-save-toggle ${isSaved ? 'tl-save-toggle-active' : ''}`;
        button.setAttribute('data-item-id', itemId);
        button.setAttribute('data-item-type', itemType);
        button.setAttribute('title', isSaved ? 'Saved for offline' : 'Save for offline');
        button.setAttribute('aria-label', isSaved ? 'Remove from offline storage' : 'Save for offline viewing');
        
        button.innerHTML = `
            <i class="bi ${isSaved ? 'bi-bookmark-fill' : 'bi-bookmark'}"></i>
        `;

        // Add click handler
        button.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.handleSaveToggle(button, element, itemId, itemType);
        });

        // Add button to status badges container
        const statusBadges = element.querySelector('.job-status-badges');
        if (statusBadges) {
            statusBadges.appendChild(button);
        } else {
            // Fallback: add to element if no status badges found
            element.style.position = 'relative';
            element.appendChild(button);
        }
    }

    /**
     * Handle save toggle button click
     */
    handleSaveToggle(button, element, itemId, itemType) {
        const isCurrentlySaved = button.classList.contains('tl-save-toggle-active');

        if (isCurrentlySaved) {
            // Unsave - remove from cache
            this.unsaveItem(itemId, itemType);
            button.classList.remove('tl-save-toggle-active');
            button.querySelector('i').className = 'bi bi-bookmark';
            button.setAttribute('title', 'Save for offline');
            this.showToast('Removed', 'Content removed from offline storage', 'info');
        } else {
            // Save - add to cache
            this.saveItem(element, itemId, itemType);
            button.classList.add('tl-save-toggle-active');
            button.querySelector('i').className = 'bi bi-bookmark-fill';
            button.setAttribute('title', 'Saved for offline');
            this.showToast('Saved', 'Content saved for offline viewing', 'success');
        }

        // Trigger event for stats update
        window.dispatchEvent(new CustomEvent('tl-cache-updated'));
    }

    /**
     * Save item to cache
     */
    saveItem(element, itemId, itemType) {
        const data = this.extractItemDataFromCard(element, itemType);
        
        if (itemType === 'job') {
            window.offlineCache.cacheJob(itemId, data);
            
            // Also try to cache the full detail page if user is on it
            this.cacheJobDetailPageIfAvailable(itemId);
        } else {
            window.offlineCache.cacheService(itemId, data);
        }
        
        // Trigger event so other buttons can sync
        window.dispatchEvent(new CustomEvent('tl-item-saved', { 
            detail: { itemId, itemType, action: 'save' }
        }));
    }
    
    /**
     * Cache job detail page via Service Worker
     */
    async cacheJobDetailPageIfAvailable(itemId) {
        try {
            // Pre-cache the detail page URL
            const detailUrl = `/jobs/${itemId}/`;
            
            // Use Service Worker to cache the page
            if ('caches' in window) {
                const cache = await caches.open('trabaholink-cache-v1');
                const response = await fetch(detailUrl, { credentials: 'same-origin' });
                if (response.ok) {
                    await cache.put(detailUrl, response.clone());
                    console.log(`[OfflineUI] Pre-cached job detail page: ${detailUrl}`);
                }
            }
        } catch (error) {
            // Silently fail - not critical
            console.log('[OfflineUI] Could not pre-cache detail page:', error.message);
        }
    }

    /**
     * Unsave item from cache
     */
    unsaveItem(itemId, itemType) {
        if (itemType === 'job') {
            const jobs = window.offlineCache.getCachedItems(window.offlineCache.CACHE_KEYS.JOBS);
            delete jobs[itemId];
            localStorage.setItem(window.offlineCache.CACHE_KEYS.JOBS, JSON.stringify(jobs));
        } else {
            const services = window.offlineCache.getCachedItems(window.offlineCache.CACHE_KEYS.SERVICES);
            delete services[itemId];
            localStorage.setItem(window.offlineCache.CACHE_KEYS.SERVICES, JSON.stringify(services));
        }
        
        // Trigger event so other buttons can sync
        window.dispatchEvent(new CustomEvent('tl-item-saved', { 
            detail: { itemId, itemType, action: 'unsave' }
        }));
    }

    /**
     * Extract item data from card element
     */
    extractItemDataFromCard(element, itemType) {
        if (itemType === 'job') {
            return {
                id: element.getAttribute('data-job-id'),
                title: element.getAttribute('data-job-title') || element.querySelector('.job-title, [data-job-title]')?.textContent.trim() || '',
                description: element.getAttribute('data-job-description') || element.querySelector('.job-description, [data-job-description]')?.textContent.trim() || '',
                location: element.getAttribute('data-job-location') || element.querySelector('.job-location, [data-job-location]')?.textContent.trim() || '',
                category: element.getAttribute('data-job-category') || element.querySelector('.job-category, [data-job-category]')?.textContent.trim() || '',
                employer: element.getAttribute('data-job-employer') || element.querySelector('.job-employer, [data-job-employer]')?.textContent.trim() || '',
                salary: element.getAttribute('data-job-salary') || element.querySelector('.job-salary, [data-job-salary]')?.textContent.trim() || '',
                posted_date: element.getAttribute('data-job-date') || element.querySelector('.job-date, [data-job-date]')?.textContent.trim() || '',
                image: element.querySelector('img')?.src || null,
                url: element.querySelector('a')?.href || window.location.href
            };
        } else {
            return {
                id: element.getAttribute('data-service-id'),
                title: element.getAttribute('data-service-title') || element.querySelector('.service-title, [data-service-title]')?.textContent.trim() || '',
                description: element.getAttribute('data-service-description') || element.querySelector('.service-description, [data-service-description]')?.textContent.trim() || '',
                category: element.getAttribute('data-service-category') || element.querySelector('.service-category, [data-service-category]')?.textContent.trim() || '',
                provider: element.getAttribute('data-service-provider') || element.querySelector('.service-provider, [data-service-provider]')?.textContent.trim() || '',
                image: element.querySelector('img')?.src || null,
                url: element.querySelector('a')?.href || window.location.href
            };
        }
    }

    /**
     * Remove cached badge from element (deprecated - kept for compatibility)
     */
    removeCachedBadge(element) {
        if (!element) return;
        
        const badge = element.querySelector('.tl-cached-badge, .tl-save-toggle');
        if (badge) {
            badge.remove();
        }
    }

    /**
     * Show toast notification (mobile-optimized)
     */
    showToast(title, message, type = 'info') {
        // Remove existing toast
        const existingToast = document.querySelector('.tl-toast');
        if (existingToast) {
            existingToast.remove();
        }

        const toast = document.createElement('div');
        toast.className = `tl-toast tl-toast-${type}`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'polite');
        
        const icon = {
            success: 'bi-check-circle-fill',
            warning: 'bi-exclamation-triangle-fill',
            error: 'bi-x-circle-fill',
            info: 'bi-info-circle-fill'
        }[type] || 'bi-info-circle-fill';

        toast.innerHTML = `
            <div class="tl-toast-content">
                <i class="bi ${icon}"></i>
                <div class="tl-toast-text">
                    <strong>${title}</strong>
                    <span>${message}</span>
                </div>
                <button class="tl-toast-close" aria-label="Close">
                    <i class="bi bi-x"></i>
                </button>
            </div>
        `;

        document.body.appendChild(toast);

        // Animate in
        setTimeout(() => {
            toast.classList.add('tl-toast-visible');
        }, 10);

        // Auto-hide after 5 seconds
        const autoHideTimeout = setTimeout(() => {
            this.hideToast(toast);
        }, 5000);

        // Close button
        toast.querySelector('.tl-toast-close').addEventListener('click', () => {
            clearTimeout(autoHideTimeout);
            this.hideToast(toast);
        });
    }

    /**
     * Hide toast notification
     */
    hideToast(toast) {
        toast.classList.remove('tl-toast-visible');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }

    /**
     * Show offline message for specific action
     */
    showOfflineMessage(actionName = 'action') {
        this.showToast(
            'Offline Mode',
            `Cannot ${actionName} while offline. Please connect to the internet.`,
            'warning'
        );
    }

    /**
     * Get connection status
     */
    getConnectionStatus() {
        return {
            online: this.isOnline,
            effectiveType: navigator.connection?.effectiveType || 'unknown',
            downlink: navigator.connection?.downlink || 'unknown',
            rtt: navigator.connection?.rtt || 'unknown'
        };
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.offlineUI = new OfflineUIManager();
});

// Export for use in other scripts
window.OfflineUIManager = OfflineUIManager;
