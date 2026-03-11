/**
 * TrabahoLink Offline Pre-fetch Manager
 * Smart caching strategy for jobs and services
 * Version: 1.0.0
 */

class OfflinePrefetchManager {
    constructor() {
        this.cacheManager = window.offlineCache;
        this.maxPrefetchItems = 20;
        this.prefetchRadius = 5000; // 5km radius for nearby content
        this.userLocation = null;
        
        this.init();
    }

    /**
     * Initialize prefetch manager
     */
    init() {
        this.loadUserLocation();
        this.setupEventListeners();
        console.log('[OfflinePrefetch] Initialized successfully');
    }

    /**
     * Load user location from localStorage or geolocation
     */
    loadUserLocation() {
        // Try to get from localStorage first
        const savedLocation = localStorage.getItem('user_location');
        if (savedLocation) {
            try {
                this.userLocation = JSON.parse(savedLocation);
                console.log('[OfflinePrefetch] Loaded user location from cache');
            } catch (e) {
                console.error('[OfflinePrefetch] Failed to parse saved location:', e);
            }
        }
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Prefetch when online
        window.addEventListener('tl-online', () => {
            console.log('[OfflinePrefetch] Device online, checking prefetch...');
            this.prefetchNearbyContent();
        });

        // Prefetch on page load if online
        if (navigator.onLine) {
            // Delay prefetch to not interfere with initial page load
            setTimeout(() => this.prefetchNearbyContent(), 2000);
        }
    }

    /**
     * Prefetch nearby jobs and services
     */
    async prefetchNearbyContent() {
        if (!navigator.onLine) {
            console.log('[OfflinePrefetch] Device offline, skipping prefetch');
            return;
        }

        console.log('[OfflinePrefetch] Starting prefetch...');

        try {
            // Prefetch jobs and services in parallel
            await Promise.all([
                this.prefetchJobs(),
                this.prefetchServices()
            ]);

            console.log('[OfflinePrefetch] Prefetch completed successfully');
        } catch (error) {
            console.error('[OfflinePrefetch] Prefetch failed:', error);
        }
    }

    /**
     * Add save toggle buttons to visible cards
     */
    async prefetchJobs() {
        try {
            // Get job cards from the page
            const jobCards = document.querySelectorAll('[data-job-id]');
            
            if (jobCards.length === 0) {
                console.log('[OfflinePrefetch] No jobs found on page');
                return;
            }

            // Add save toggle buttons to all job cards
            jobCards.forEach(card => {
                const jobId = card.getAttribute('data-job-id');
                if (jobId && window.offlineUI) {
                    window.offlineUI.addSaveToggleButton(card, jobId, 'job');
                }
            });

            console.log(`[OfflinePrefetch] Added save buttons to ${jobCards.length} jobs`);
        } catch (error) {
            console.error('[OfflinePrefetch] Failed to add save buttons:', error);
        }
    }

    /**
     * Add save toggle buttons to service cards
     */
    async prefetchServices() {
        try {
            // Get service cards from the page
            const serviceCards = document.querySelectorAll('[data-service-id]');
            
            if (serviceCards.length === 0) {
                console.log('[OfflinePrefetch] No services found on page');
                return;
            }

            // Add save toggle buttons to all service cards
            serviceCards.forEach(card => {
                const serviceId = card.getAttribute('data-service-id');
                if (serviceId && window.offlineUI) {
                    window.offlineUI.addSaveToggleButton(card, serviceId, 'service');
                }
            });

            console.log(`[OfflinePrefetch] Added save buttons to ${serviceCards.length} services`);
        } catch (error) {
            console.error('[OfflinePrefetch] Failed to add save buttons:', error);
        }
    }

    /**
     * Extract job data from DOM card element
     */
    extractJobDataFromCard(card) {
        try {
            const data = {
                id: card.getAttribute('data-job-id'),
                title: card.querySelector('.job-title, [data-job-title]')?.textContent.trim() || 'Untitled',
                description: card.querySelector('.job-description, [data-job-description]')?.textContent.trim() || '',
                location: card.querySelector('.job-location, [data-job-location]')?.textContent.trim() || '',
                category: card.querySelector('.job-category, [data-job-category]')?.textContent.trim() || '',
                employer: card.querySelector('.job-employer, [data-job-employer]')?.textContent.trim() || '',
                salary: card.querySelector('.job-salary, [data-job-salary]')?.textContent.trim() || '',
                posted_date: card.querySelector('.job-date, [data-job-date]')?.textContent.trim() || '',
                image: card.querySelector('img')?.src || null,
                url: card.querySelector('a')?.href || window.location.href
            };

            return data;
        } catch (error) {
            console.error('[OfflinePrefetch] Failed to extract job data:', error);
            return null;
        }
    }

    /**
     * Extract service data from DOM card element
     */
    extractServiceDataFromCard(card) {
        try {
            const data = {
                id: card.getAttribute('data-service-id'),
                title: card.querySelector('.service-title, [data-service-title]')?.textContent.trim() || 'Untitled',
                description: card.querySelector('.service-description, [data-service-description]')?.textContent.trim() || '',
                location: card.querySelector('.service-location, [data-service-location]')?.textContent.trim() || '',
                category: card.querySelector('.service-category, [data-service-category]')?.textContent.trim() || '',
                provider: card.querySelector('.service-provider, [data-service-provider]')?.textContent.trim() || '',
                price: card.querySelector('.service-price, [data-service-price]')?.textContent.trim() || '',
                rating: card.querySelector('.service-rating, [data-service-rating]')?.textContent.trim() || '',
                image: card.querySelector('img')?.src || null,
                url: card.querySelector('a')?.href || window.location.href
            };

            return data;
        } catch (error) {
            console.error('[OfflinePrefetch] Failed to extract service data:', error);
            return null;
        }
    }

    /**
     * Cache current page content (job detail, service detail, profile)
     */
    cacheCurrentPage() {
        try {
            const path = window.location.pathname;

            // Check if it's a job detail page
            if (path.includes('/jobs/') && path.match(/\/jobs\/\d+/)) {
                this.cacheJobDetailPage();
                // Also add save button to detail page if needed
                this.addSaveButtonToDetailPage('job');
            }
            // Check if it's a service detail page
            else if (path.includes('/services/') && path.match(/\/services\/\d+/)) {
                this.cacheServiceDetailPage();
                // Also add save button to detail page if needed
                this.addSaveButtonToDetailPage('service');
            }
            // Check if it's a profile page
            else if (path.includes('/profile/')) {
                this.cacheProfilePage();
            }

        } catch (error) {
            console.error('[OfflinePrefetch] Failed to cache current page:', error);
        }
    }

    /**
     * Add save button to detail page
     */
    addSaveButtonToDetailPage(type) {
        try {
            const path = window.location.pathname;
            const idMatch = path.match(/\/(?:jobs|services)\/(\d+)/);
            
            if (!idMatch) return;
            
            const itemId = idMatch[1];
            
            // Find a good place to add the button (near title or header)
            const container = document.querySelector('.job-header, .service-header, h1, .page-header');
            
            if (container && window.offlineUI && !document.querySelector('.tl-save-toggle')) {
                // Create a wrapper for the button
                const buttonWrapper = document.createElement('div');
                buttonWrapper.style.display = 'inline-block';
                buttonWrapper.style.marginLeft = '1rem';
                buttonWrapper.style.verticalAlign = 'middle';
                
                window.offlineUI.addSaveToggleButton(buttonWrapper, itemId, type);
                
                // Add to container
                if (container.tagName === 'H1') {
                    container.appendChild(buttonWrapper);
                } else {
                    container.querySelector('h1, h2')?.appendChild(buttonWrapper);
                }
                
                console.log(`[OfflinePrefetch] Added save button to ${type} detail page`);
            }
        } catch (error) {
            console.error('[OfflinePrefetch] Failed to add save button to detail page:', error);
        }
    }

    /**
     * Cache job detail page
     */
    cacheJobDetailPage() {
        try {
            const jobId = window.location.pathname.match(/\/jobs\/(\d+)/)?.[1];
            if (!jobId) return;

            const jobData = {
                id: jobId,
                title: document.querySelector('.job-title, h1')?.textContent.trim() || '',
                description: document.querySelector('.job-description, .description')?.textContent.trim() || '',
                location: document.querySelector('.job-location')?.textContent.trim() || '',
                category: document.querySelector('.job-category')?.textContent.trim() || '',
                employer: document.querySelector('.employer-name')?.textContent.trim() || '',
                salary: document.querySelector('.job-salary')?.textContent.trim() || '',
                requirements: document.querySelector('.job-requirements')?.textContent.trim() || '',
                benefits: document.querySelector('.job-benefits')?.textContent.trim() || '',
                posted_date: document.querySelector('.posted-date')?.textContent.trim() || '',
                deadline: document.querySelector('.application-deadline')?.textContent.trim() || '',
                images: Array.from(document.querySelectorAll('.job-images img')).map(img => img.src),
                url: window.location.href
            };

            this.cacheManager.cacheJob(jobId, jobData);
            console.log(`[OfflinePrefetch] Cached job detail: ${jobId}`);

            // Show cached indicator
            this.showCachedIndicator();
        } catch (error) {
            console.error('[OfflinePrefetch] Failed to cache job detail:', error);
        }
    }

    /**
     * Cache service detail page
     */
    cacheServiceDetailPage() {
        try {
            const serviceId = window.location.pathname.match(/\/services\/(\d+)/)?.[1];
            if (!serviceId) return;

            const serviceData = {
                id: serviceId,
                title: document.querySelector('.service-title, h1')?.textContent.trim() || '',
                description: document.querySelector('.service-description, .description')?.textContent.trim() || '',
                location: document.querySelector('.service-location')?.textContent.trim() || '',
                category: document.querySelector('.service-category')?.textContent.trim() || '',
                provider: document.querySelector('.provider-name')?.textContent.trim() || '',
                price: document.querySelector('.service-price')?.textContent.trim() || '',
                rating: document.querySelector('.service-rating')?.textContent.trim() || '',
                reviews: Array.from(document.querySelectorAll('.review')).map(review => ({
                    author: review.querySelector('.review-author')?.textContent.trim() || '',
                    rating: review.querySelector('.review-rating')?.textContent.trim() || '',
                    comment: review.querySelector('.review-comment')?.textContent.trim() || ''
                })),
                images: Array.from(document.querySelectorAll('.service-images img')).map(img => img.src),
                url: window.location.href
            };

            this.cacheManager.cacheService(serviceId, serviceData);
            console.log(`[OfflinePrefetch] Cached service detail: ${serviceId}`);

            // Show cached indicator
            this.showCachedIndicator();
        } catch (error) {
            console.error('[OfflinePrefetch] Failed to cache service detail:', error);
        }
    }

    /**
     * Cache profile page
     */
    cacheProfilePage() {
        try {
            const userId = window.location.pathname.match(/\/profile\/(\d+|[\w-]+)/)?.[1];
            if (!userId) return;

            const profileData = {
                id: userId,
                name: document.querySelector('.profile-name, h1')?.textContent.trim() || '',
                bio: document.querySelector('.profile-bio')?.textContent.trim() || '',
                location: document.querySelector('.profile-location')?.textContent.trim() || '',
                skills: Array.from(document.querySelectorAll('.skill')).map(skill => skill.textContent.trim()),
                rating: document.querySelector('.profile-rating')?.textContent.trim() || '',
                avatar: document.querySelector('.profile-avatar img')?.src || '',
                verified: document.querySelector('.verified-badge') !== null,
                url: window.location.href
            };

            this.cacheManager.cacheProfile(userId, profileData);
            console.log(`[OfflinePrefetch] Cached profile: ${userId}`);

            // Show cached indicator
            this.showCachedIndicator();
        } catch (error) {
            console.error('[OfflinePrefetch] Failed to cache profile:', error);
        }
    }

    /**
     * Add cached badge to card element (deprecated - now using toggle buttons)
     */
    addCachedBadgeToCard(card) {
        // Deprecated - toggle buttons are added automatically
    }

    /**
     * Show cached indicator on current page (deprecated - now using toggle buttons)
     */
    showCachedIndicator() {
        // This function is deprecated - toggle buttons show saved state automatically
        // Keeping for compatibility but no longer adds badges
        console.log('[OfflinePrefetch] Page cached successfully');
    }

    /**
     * Get cache statistics
     */
    getStats() {
        return this.cacheManager.getStats();
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Wait for cache manager to be ready
    if (window.offlineCache) {
        window.offlinePrefetch = new OfflinePrefetchManager();
        
        // Cache current page if viewing detail
        window.offlinePrefetch.cacheCurrentPage();
    } else {
        console.error('[OfflinePrefetch] Cache manager not available');
    }
});

// Export for use in other scripts
window.OfflinePrefetchManager = OfflinePrefetchManager;
