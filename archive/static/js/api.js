/**
 * API communication module for the dashboard
 * Handles all API requests and responses
 */

import { getRetryConfig } from './state.js';

/**
 * Fetch data with retry capability
 * @param {string} url - The URL to fetch from
 * @param {Object} options - Fetch options
 * @param {number} maxRetries - Maximum number of retries
 * @param {number} retryDelay - Initial delay between retries in ms
 * @param {number} backoffFactor - Factor to increase delay with each retry
 * @param {number} timeout - Request timeout in milliseconds
 * @returns {Promise<Object>} - Promise that resolves with the fetched data
 */
export async function fetchWithRetry(url, options = {}, maxRetries = null, retryDelay = null, backoffFactor = null, timeout = 10000) {
    // Get retry config from state if not provided
    const config = getRetryConfig();
    maxRetries = maxRetries ?? config.maxRetries;
    retryDelay = retryDelay ?? config.retryDelay;
    backoffFactor = backoffFactor ?? config.backoffFactor;
    
    let lastError;
    let currentDelay = retryDelay;
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            console.log(`Fetch attempt ${attempt + 1}/${maxRetries + 1} for ${url}`);
            
            // Create an AbortController for timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), timeout);
            
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            
            // Clear the timeout
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                const errorText = await response.text().catch(() => 'No error details available');
                throw new Error(`HTTP error ${response.status}: ${response.statusText}. Details: ${errorText}`);
            }
            
            const data = await response.json();
            
            // If we got here, the request was successful
            if (attempt > 0) {
                console.log(`Successfully recovered after ${attempt} retries`);
            }
            
            return data;
        } catch (error) {
            lastError = error;
            
            // Handle timeout specifically
            if (error.name === 'AbortError') {
                console.error(`Request timed out after ${timeout}ms`);
                throw new Error(`Request timed out after ${timeout}ms`);
            }
            
            // If this was the last attempt, throw the error
            if (attempt === maxRetries) {
                console.error(`Failed after ${maxRetries + 1} attempts:`, error);
                throw new Error(`Failed to fetch data after ${maxRetries + 1} attempts: ${error.message}`);
            }
            
            // Otherwise, wait and try again
            console.warn(`Attempt ${attempt + 1} failed: ${error.message}. Retrying in ${currentDelay}ms...`);
            await new Promise(resolve => setTimeout(resolve, currentDelay));
            
            // Increase the delay for the next attempt (exponential backoff)
            currentDelay = Math.min(currentDelay * backoffFactor, 10000); // Cap at 10 seconds
        }
    }
    
    // This should never be reached due to the throw in the loop, but just in case
    throw lastError;
}

/**
 * Fetch health data from the API
 * @returns {Promise<Object>} - Promise that resolves with health data
 */
export async function fetchHealthData() {
    return fetchWithRetry('/health/');
}

/**
 * Fetch health data for a specific binding
 * @param {string} bindingName - The name of the binding
 * @returns {Promise<Object>} - Promise that resolves with binding health data
 */
export async function fetchBindingHealthData(bindingName) {
    return fetchWithRetry(`/health/${encodeURIComponent(bindingName)}`);
}

/**
 * Fetch metrics data from the API
 * @returns {Promise<Object>} - Promise that resolves with metrics data
 */
export async function fetchMetricsData() {
    return fetchWithRetry('/metrics/');
}

/**
 * Fetch metrics data for a specific binding
 * @param {string} bindingName - The name of the binding
 * @returns {Promise<Object>} - Promise that resolves with binding metrics data
 */
export async function fetchBindingMetricsData(bindingName) {
    return fetchWithRetry(`/metrics/${encodeURIComponent(bindingName)}`);
}

/**
 * Fetch health data asynchronously with loading overlay
 * @param {HTMLElement} container - The container to show loading overlay in
 * @returns {Promise<Object>} - Promise that resolves with health data
 */
export async function fetchHealthDataWithOverlay(container) {
    if (!container) {
        return fetchHealthData();
    }
    
    // Create and show loading overlay
    const { loadingOverlay, remove } = createLoadingOverlay(container, 'Loading health data...');
    
    try {
        // Fetch health data
        const data = await fetchHealthData();
        return data;
    } finally {
        // Remove loading overlay
        remove();
    }
}

/**
 * Fetch metrics data asynchronously with loading overlay
 * @param {HTMLElement} container - The container to show loading overlay in
 * @returns {Promise<Object>} - Promise that resolves with metrics data
 */
export async function fetchMetricsDataWithOverlay(container) {
    if (!container) {
        return fetchMetricsData();
    }
    
    // Create and show loading overlay
    const { loadingOverlay, remove } = createLoadingOverlay(container, 'Loading metrics data...');
    
    try {
        // Fetch metrics data
        const data = await fetchMetricsData();
        return data;
    } finally {
        // Remove loading overlay
        remove();
    }
}

/**
 * Create a loading overlay for a container
 * @param {HTMLElement} container - The container to add the overlay to
 * @param {string} message - The loading message to display
 * @returns {Object} - Object with the overlay element and a remove function
 */
function createLoadingOverlay(container, message = 'Loading...') {
    // Create loading overlay
    const loadingOverlay = document.createElement('div');
    loadingOverlay.className = 'loading-overlay';
    
    const spinner = document.createElement('div');
    spinner.className = 'spinner';
    
    const loadingMessage = document.createElement('div');
    loadingMessage.className = 'loading-message';
    loadingMessage.textContent = message;
    
    loadingOverlay.appendChild(spinner);
    loadingOverlay.appendChild(loadingMessage);
    
    // Add relative positioning to the container if not already set
    if (getComputedStyle(container).position === 'static') {
        container.style.position = 'relative';
    }
    
    // Append the loading overlay to the container
    container.appendChild(loadingOverlay);
    
    // Return the overlay and a function to remove it
    return {
        loadingOverlay,
        remove: () => {
            if (loadingOverlay && loadingOverlay.parentNode) {
                loadingOverlay.parentNode.removeChild(loadingOverlay);
            }
        }
    };
}

/**
 * Create an error overlay for a container
 * @param {HTMLElement} container - The container to add the overlay to
 * @param {string} title - The error title
 * @param {string} message - The error message
 * @returns {Object} - Object with the overlay element and a remove function
 */
export function createErrorOverlay(container, title, message) {
    // Create error overlay
    const errorOverlay = document.createElement('div');
    errorOverlay.className = 'error-overlay';
    
    const errorContent = document.createElement('div');
    errorContent.className = 'error-content';
    
    const errorTitle = document.createElement('h3');
    errorTitle.textContent = title;
    
    const errorMessage = document.createElement('p');
    errorMessage.textContent = message;
    
    const closeButton = document.createElement('button');
    closeButton.className = 'close-button';
    closeButton.textContent = 'Close';
    
    errorContent.appendChild(errorTitle);
    errorContent.appendChild(errorMessage);
    errorContent.appendChild(closeButton);
    errorOverlay.appendChild(errorContent);
    
    // Add relative positioning to the container if not already set
    if (getComputedStyle(container).position === 'static') {
        container.style.position = 'relative';
    }
    
    // Add close button functionality
    const remove = () => {
        if (errorOverlay && errorOverlay.parentNode) {
            errorOverlay.parentNode.removeChild(errorOverlay);
        }
    };
    
    closeButton.addEventListener('click', remove);
    
    // Append the error overlay to the container
    container.appendChild(errorOverlay);
    
    // Return the overlay and a function to remove it
    return {
        errorOverlay,
        remove
    };
}

// Export the API module
export default {
    fetchWithRetry,
    fetchHealthData,
    fetchBindingHealthData,
    fetchMetricsData,
    fetchBindingMetricsData,
    fetchHealthDataWithOverlay,
    fetchMetricsDataWithOverlay,
    createErrorOverlay
};
