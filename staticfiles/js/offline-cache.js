/**
 * TrabahoLink Offline Cache Manager
 * Mobile-first offline caching with LocalStorage
 * Version: 1.0.0
 */

class OfflineCacheManager {
    constructor() {
        this.CACHE_PREFIX = 'tl_cache_';
        this.CACHE_VERSION = 'v1';
        this.MAX_CACHE_SIZE = 5 * 1024 * 1024; // 5MB max
        this.CACHE_EXPIRY_DAYS = 7; // Cache expires after 7 days
        this.MAX_ITEMS_PER_TYPE = 50; // Maximum cached items per type
        
        // Cache keys for different content types
        this.CACHE_KEYS = {
            JOBS: `${this.CACHE_PREFIX}jobs_${this.CACHE_VERSION}`,
            SERVICES: `${this.CACHE_PREFIX}services_${this.CACHE_VERSION}`,
            PROFILES: `${this.CACHE_PREFIX}profiles_${this.CACHE_VERSION}`,
            APPLICATIONS: `${this.CACHE_PREFIX}applications_${this.CACHE_VERSION}`,
            MESSAGES: `${this.CACHE_PREFIX}messages_${this.CACHE_VERSION}`,
            METADATA: `${this.CACHE_PREFIX}metadata_${this.CACHE_VERSION}`
        };

        this.init();
    }

    /**
     * Initialize cache manager
     */
    init() {
        this.checkStorageSupport();
        this.cleanExpiredCache();
        this.monitorStorage();
        console.log('[OfflineCache] Initialized successfully');
    }

    /**
     * Check if LocalStorage is supported
     */
    checkStorageSupport() {
        try {
            const test = '__storage_test__';
            localStorage.setItem(test, test);
            localStorage.removeItem(test);
            return true;
        } catch (e) {
            console.error('[OfflineCache] LocalStorage not supported:', e);
            return false;
        }
    }

    /**
     * Get current storage usage
     */
    getStorageUsage() {
        let total = 0;
        for (let key in localStorage) {
            if (localStorage.hasOwnProperty(key) && key.startsWith(this.CACHE_PREFIX)) {
                total += localStorage[key].length + key.length;
            }
        }
        return total;
    }

    /**
     * Monitor storage and clean if needed
     */
    monitorStorage() {
        const usage = this.getStorageUsage();
        if (usage > this.MAX_CACHE_SIZE * 0.9) { // 90% full
            console.warn('[OfflineCache] Storage nearly full, cleaning old items...');
            this.cleanOldestItems();
        }
    }

    /**
     * Cache a job listing
     */
    cacheJob(jobId, jobData) {
        try {
            const jobs = this.getCachedItems(this.CACHE_KEYS.JOBS);
            const timestamp = new Date().toISOString();
            
            jobs[jobId] = {
                data: jobData,
                cached_at: timestamp,
                expires_at: this.getExpiryDate()
            };

            // Limit cache size
            this.limitCacheSize(jobs, this.MAX_ITEMS_PER_TYPE);
            
            localStorage.setItem(this.CACHE_KEYS.JOBS, JSON.stringify(jobs));
            this.updateMetadata('jobs', Object.keys(jobs).length);
            
            console.log(`[OfflineCache] Cached job: ${jobId}`);
            return true;
        } catch (e) {
            console.error('[OfflineCache] Failed to cache job:', e);
            return false;
        }
    }

    /**
     * Cache a service post
     */
    cacheService(serviceId, serviceData) {
        try {
            const services = this.getCachedItems(this.CACHE_KEYS.SERVICES);
            const timestamp = new Date().toISOString();
            
            services[serviceId] = {
                data: serviceData,
                cached_at: timestamp,
                expires_at: this.getExpiryDate()
            };

            this.limitCacheSize(services, this.MAX_ITEMS_PER_TYPE);
            
            localStorage.setItem(this.CACHE_KEYS.SERVICES, JSON.stringify(services));
            this.updateMetadata('services', Object.keys(services).length);
            
            console.log(`[OfflineCache] Cached service: ${serviceId}`);
            return true;
        } catch (e) {
            console.error('[OfflineCache] Failed to cache service:', e);
            return false;
        }
    }

    /**
     * Cache user profile
     */
    cacheProfile(userId, profileData) {
        try {
            const profiles = this.getCachedItems(this.CACHE_KEYS.PROFILES);
            const timestamp = new Date().toISOString();
            
            profiles[userId] = {
                data: profileData,
                cached_at: timestamp,
                expires_at: this.getExpiryDate()
            };

            this.limitCacheSize(profiles, 20); // Less profiles cached
            
            localStorage.setItem(this.CACHE_KEYS.PROFILES, JSON.stringify(profiles));
            this.updateMetadata('profiles', Object.keys(profiles).length);
            
            console.log(`[OfflineCache] Cached profile: ${userId}`);
            return true;
        } catch (e) {
            console.error('[OfflineCache] Failed to cache profile:', e);
            return false;
        }
    }

    /**
     * Cache user's applications
     */
    cacheApplications(applications) {
        try {
            const timestamp = new Date().toISOString();
            const cacheData = {
                data: applications,
                cached_at: timestamp,
                expires_at: this.getExpiryDate()
            };
            
            localStorage.setItem(this.CACHE_KEYS.APPLICATIONS, JSON.stringify(cacheData));
            this.updateMetadata('applications', applications.length);
            
            console.log(`[OfflineCache] Cached ${applications.length} applications`);
            return true;
        } catch (e) {
            console.error('[OfflineCache] Failed to cache applications:', e);
            return false;
        }
    }

    /**
     * Cache messages/conversations
     */
    cacheMessages(conversationId, messages) {
        try {
            const allMessages = this.getCachedItems(this.CACHE_KEYS.MESSAGES);
            const timestamp = new Date().toISOString();
            
            allMessages[conversationId] = {
                data: messages,
                cached_at: timestamp,
                expires_at: this.getExpiryDate()
            };

            this.limitCacheSize(allMessages, 30); // Cache 30 conversations
            
            localStorage.setItem(this.CACHE_KEYS.MESSAGES, JSON.stringify(allMessages));
            this.updateMetadata('messages', Object.keys(allMessages).length);
            
            console.log(`[OfflineCache] Cached conversation: ${conversationId}`);
            return true;
        } catch (e) {
            console.error('[OfflineCache] Failed to cache messages:', e);
            return false;
        }
    }

    /**
     * Get cached job
     */
    getCachedJob(jobId) {
        const jobs = this.getCachedItems(this.CACHE_KEYS.JOBS);
        const cached = jobs[jobId];
        
        if (cached && !this.isExpired(cached.expires_at)) {
            console.log(`[OfflineCache] Retrieved cached job: ${jobId}`);
            return cached.data;
        }
        return null;
    }

    /**
     * Get cached service
     */
    getCachedService(serviceId) {
        const services = this.getCachedItems(this.CACHE_KEYS.SERVICES);
        const cached = services[serviceId];
        
        if (cached && !this.isExpired(cached.expires_at)) {
            console.log(`[OfflineCache] Retrieved cached service: ${serviceId}`);
            return cached.data;
        }
        return null;
    }

    /**
     * Get cached profile
     */
    getCachedProfile(userId) {
        const profiles = this.getCachedItems(this.CACHE_KEYS.PROFILES);
        const cached = profiles[userId];
        
        if (cached && !this.isExpired(cached.expires_at)) {
            console.log(`[OfflineCache] Retrieved cached profile: ${userId}`);
            return cached.data;
        }
        return null;
    }

    /**
     * Get cached applications
     */
    getCachedApplications() {
        const cached = this.getCachedItem(this.CACHE_KEYS.APPLICATIONS);
        
        if (cached && !this.isExpired(cached.expires_at)) {
            console.log(`[OfflineCache] Retrieved cached applications`);
            return cached.data;
        }
        return null;
    }

    /**
     * Get cached messages
     */
    getCachedMessages(conversationId) {
        const allMessages = this.getCachedItems(this.CACHE_KEYS.MESSAGES);
        const cached = allMessages[conversationId];
        
        if (cached && !this.isExpired(cached.expires_at)) {
            console.log(`[OfflineCache] Retrieved cached messages: ${conversationId}`);
            return cached.data;
        }
        return null;
    }

    /**
     * Get all cached jobs (for listing)
     */
    getAllCachedJobs() {
        const jobs = this.getCachedItems(this.CACHE_KEYS.JOBS);
        const validJobs = [];
        
        for (let jobId in jobs) {
            if (!this.isExpired(jobs[jobId].expires_at)) {
                validJobs.push({
                    id: jobId,
                    ...jobs[jobId].data,
                    _cached: true,
                    _cached_at: jobs[jobId].cached_at
                });
            }
        }
        
        console.log(`[OfflineCache] Retrieved ${validJobs.length} cached jobs`);
        return validJobs;
    }

    /**
     * Get all cached services (for listing)
     */
    getAllCachedServices() {
        const services = this.getCachedItems(this.CACHE_KEYS.SERVICES);
        const validServices = [];
        
        for (let serviceId in services) {
            if (!this.isExpired(services[serviceId].expires_at)) {
                validServices.push({
                    id: serviceId,
                    ...services[serviceId].data,
                    _cached: true,
                    _cached_at: services[serviceId].cached_at
                });
            }
        }
        
        console.log(`[OfflineCache] Retrieved ${validServices.length} cached services`);
        return validServices;
    }

    /**
     * Helper: Get cached items object
     */
    getCachedItems(key) {
        try {
            const data = localStorage.getItem(key);
            return data ? JSON.parse(data) : {};
        } catch (e) {
            console.error('[OfflineCache] Failed to parse cached items:', e);
            return {};
        }
    }

    /**
     * Helper: Get single cached item
     */
    getCachedItem(key) {
        try {
            const data = localStorage.getItem(key);
            return data ? JSON.parse(data) : null;
        } catch (e) {
            console.error('[OfflineCache] Failed to parse cached item:', e);
            return null;
        }
    }

    /**
     * Get expiry date (7 days from now)
     */
    getExpiryDate() {
        const date = new Date();
        date.setDate(date.getDate() + this.CACHE_EXPIRY_DAYS);
        return date.toISOString();
    }

    /**
     * Check if cache is expired
     */
    isExpired(expiryDate) {
        return new Date(expiryDate) < new Date();
    }

    /**
     * Limit cache size by removing oldest items
     */
    limitCacheSize(items, maxItems) {
        const itemsArray = Object.entries(items);
        if (itemsArray.length > maxItems) {
            // Sort by cached_at timestamp (oldest first)
            itemsArray.sort((a, b) => 
                new Date(a[1].cached_at) - new Date(b[1].cached_at)
            );
            
            // Keep only the newest maxItems
            const toKeep = itemsArray.slice(-maxItems);
            
            // Clear and rebuild object
            for (let key in items) {
                delete items[key];
            }
            toKeep.forEach(([key, value]) => {
                items[key] = value;
            });
        }
    }

    /**
     * Clean expired cache
     */
    cleanExpiredCache() {
        try {
            let cleaned = 0;
            
            Object.values(this.CACHE_KEYS).forEach(key => {
                const items = this.getCachedItems(key);
                let hasExpired = false;
                
                for (let itemKey in items) {
                    if (this.isExpired(items[itemKey].expires_at)) {
                        delete items[itemKey];
                        hasExpired = true;
                        cleaned++;
                    }
                }
                
                if (hasExpired) {
                    localStorage.setItem(key, JSON.stringify(items));
                }
            });
            
            if (cleaned > 0) {
                console.log(`[OfflineCache] Cleaned ${cleaned} expired items`);
            }
        } catch (e) {
            console.error('[OfflineCache] Failed to clean expired cache:', e);
        }
    }

    /**
     * Clean oldest items when storage is full
     */
    cleanOldestItems() {
        try {
            Object.values(this.CACHE_KEYS).forEach(key => {
                const items = this.getCachedItems(key);
                const itemsArray = Object.entries(items);
                
                if (itemsArray.length > 10) {
                    itemsArray.sort((a, b) => 
                        new Date(a[1].cached_at) - new Date(b[1].cached_at)
                    );
                    
                    // Keep only newest 10 items
                    const toKeep = itemsArray.slice(-10);
                    const newItems = {};
                    toKeep.forEach(([itemKey, value]) => {
                        newItems[itemKey] = value;
                    });
                    
                    localStorage.setItem(key, JSON.stringify(newItems));
                }
            });
            
            console.log('[OfflineCache] Cleaned oldest items to free space');
        } catch (e) {
            console.error('[OfflineCache] Failed to clean oldest items:', e);
        }
    }

    /**
     * Update metadata
     */
    updateMetadata(type, count) {
        try {
            const metadata = this.getCachedItem(this.CACHE_KEYS.METADATA) || {};
            metadata[type] = {
                count: count,
                updated_at: new Date().toISOString()
            };
            metadata.total_size = this.getStorageUsage();
            
            localStorage.setItem(this.CACHE_KEYS.METADATA, JSON.stringify(metadata));
        } catch (e) {
            console.error('[OfflineCache] Failed to update metadata:', e);
        }
    }

    /**
     * Get cache statistics
     */
    getStats() {
        const metadata = this.getCachedItem(this.CACHE_KEYS.METADATA) || {};
        const usage = this.getStorageUsage();
        const usagePercent = ((usage / this.MAX_CACHE_SIZE) * 100).toFixed(2);
        
        return {
            storage_used: usage,
            storage_max: this.MAX_CACHE_SIZE,
            storage_percent: usagePercent,
            metadata: metadata
        };
    }

    /**
     * Clear all cache
     */
    clearAll() {
        try {
            Object.values(this.CACHE_KEYS).forEach(key => {
                localStorage.removeItem(key);
            });
            console.log('[OfflineCache] Cleared all cache');
            return true;
        } catch (e) {
            console.error('[OfflineCache] Failed to clear cache:', e);
            return false;
        }
    }

    /**
     * Clear specific cache type
     */
    clearType(type) {
        try {
            const key = this.CACHE_KEYS[type.toUpperCase()];
            if (key) {
                localStorage.removeItem(key);
                console.log(`[OfflineCache] Cleared ${type} cache`);
                return true;
            }
            return false;
        } catch (e) {
            console.error(`[OfflineCache] Failed to clear ${type} cache:`, e);
            return false;
        }
    }
}

// Export singleton instance
window.offlineCache = new OfflineCacheManager();
