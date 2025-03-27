/**
 * State management module for the dashboard
 * Centralizes state management and provides methods to update state
 */

// Dashboard state object
const state = {
    interval: null,
    refreshRate: 5000, // ms
    lastRefreshTime: null,
    cachedMetricsData: null, // Cache for metrics data when tab is not active
    retryConfig: {
        maxRetries: 3,
        retryDelay: 1000, // ms
        backoffFactor: 1.5 // Exponential backoff factor
    },
    selectors: {
        ids: {
            refreshButton: 'refresh-button',
            refreshIndicator: 'refresh-indicator',
            bindings: 'bindings',
            bindingCount: 'binding-count',
            refreshInterval: 'refresh-interval',
            errorContainer: 'error-container',
            lastUpdated: 'last-updated'
        },
        classes: {
            bindingMetricsTemplate: '#binding-metrics-template',
            bindingCard: '.binding-card',
            bindingHeader: '.binding-header',
            bindingName: '.binding-name',
            bindingType: '.binding-type',
            metricsContainer: '.metrics-container',
            metricItemTemplate: '#metric-item-template',
            errorMessage: '.error-message'
        }
    }
};

/**
 * Get the current state
 * @returns {Object} The current state object
 */
export function getState() {
    return state;
}

/**
 * Update the refresh interval
 * @param {number} interval - The new interval in milliseconds
 * @param {Function} refreshCallback - The function to call on each interval
 */
export function setAutoRefresh(interval, refreshCallback) {
    // Clear existing interval
    if (state.refreshInterval) {
        clearInterval(state.refreshInterval);
        state.refreshInterval = null;
    }
    
    // Set new interval if not 0
    if (interval > 0 && refreshCallback) {
        state.refreshInterval = setInterval(refreshCallback, interval);
    }
}

/**
 * Update the last refresh time
 */
export function updateLastRefreshTime() {
    state.lastRefreshTime = new Date();
    return state.lastRefreshTime;
}

/**
 * Cache metrics data for later use
 * @param {Object} data - The metrics data to cache
 */
export function cacheMetricsData(data) {
    state.cachedMetricsData = data;
}

/**
 * Get cached metrics data and clear the cache
 * @returns {Object|null} The cached metrics data or null if no data is cached
 */
export function getCachedMetricsData() {
    const data = state.cachedMetricsData;
    state.cachedMetricsData = null;
    return data;
}

/**
 * Get retry configuration
 * @returns {Object} The retry configuration
 */
export function getRetryConfig() {
    return state.retryConfig;
}

/**
 * Get selector by type and name
 * @param {string} type - The selector type ('ids' or 'classes')
 * @param {string} name - The selector name
 * @returns {string} The selector
 */
export function getSelector(type, name) {
    if (type === 'ids') {
        return `#${state.selectors.ids[name]}`;
    } else if (type === 'classes') {
        return state.selectors.classes[name];
    }
    return null;
}

// Export the state module
export default {
    getState,
    setAutoRefresh,
    updateLastRefreshTime,
    cacheMetricsData,
    getCachedMetricsData,
    getRetryConfig,
    getSelector
};
