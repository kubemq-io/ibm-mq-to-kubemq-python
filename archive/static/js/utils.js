/**
 * Utility functions for the dashboard
 * Contains helper functions for DOM manipulation, formatting, and other utilities
 */

/**
 * Safe helper to get DOM elements
 * @param {string} selector - CSS selector
 * @param {Node} context - The parent element to search within
 * @returns {Element|null} - The element if found, null otherwise
 */
export function getElement(selector, context = document) {
    try {
        return context.querySelector(selector);
    } catch (error) {
        console.error(`Error querying for selector "${selector}":`, error);
        return null;
    }
}

/**
 * Safe helper to get multiple DOM elements
 * @param {string} selector - CSS selector
 * @param {Node} context - The parent element to search within
 * @returns {NodeList|Array} - The elements if found, empty array otherwise
 */
export function getElements(selector, context = document) {
    try {
        return context.querySelectorAll(selector);
    } catch (error) {
        console.error(`Error querying for selector "${selector}":`, error);
        return [];
    }
}

/**
 * Safely clear a container's contents
 * @param {HTMLElement} container - The container to clear
 */
export function clearContainer(container) {
    if (!container) return;
    
    while (container.firstChild) {
        container.removeChild(container.firstChild);
    }
}

/**
 * Create an element with attributes and content
 * @param {string} tag - The HTML tag name
 * @param {Object} attributes - Key-value pairs of attributes
 * @param {string|Node|Array} content - Text content, child node, or array of child nodes
 * @returns {HTMLElement} The created element
 */
export function createElement(tag, attributes = {}, content = null) {
    const element = document.createElement(tag);
    
    // Set attributes
    Object.entries(attributes).forEach(([key, value]) => {
        if (key === 'className') {
            element.className = value;
        } else if (key === 'style' && typeof value === 'object') {
            Object.assign(element.style, value);
        } else {
            element.setAttribute(key, value);
        }
    });
    
    // Set content
    if (content !== null) {
        if (typeof content === 'string') {
            element.textContent = content;
        } else if (content instanceof Node) {
            element.appendChild(content);
        } else if (Array.isArray(content)) {
            content.forEach(child => {
                if (child instanceof Node) {
                    element.appendChild(child);
                }
            });
        }
    }
    
    return element;
}

/**
 * Create a document fragment from an array of elements
 * @param {Array} elements - Array of DOM elements (optional)
 * @returns {DocumentFragment} A document fragment containing the elements
 */
export function createFragment(elements = []) {
    const fragment = document.createDocumentFragment();
    if (Array.isArray(elements)) {
        elements.forEach(element => {
            if (element instanceof Node) {
                fragment.appendChild(element);
            }
        });
    }
    return fragment;
}

/**
 * Format a Unix timestamp into a UTC string + relative time
 * @param {number|string} timestamp - The Unix timestamp in milliseconds
 * @returns {string} The formatted date/time string
 */
export function formatTimestamp(timestamp) {
    try {
        // Handle undefined or null timestamps
        if (timestamp === undefined || timestamp === null) {
            return 'Never';
        }
        
        // Convert string timestamp to number if needed
        if (typeof timestamp === 'string') {
            timestamp = parseInt(timestamp, 10);
        }
        
        // Validate the timestamp
        if (isNaN(timestamp) || timestamp <= 0) {
            return 'Invalid timestamp';
        }
        
        // Format the date
        const date = new Date(timestamp);
        
        // Check if the date is valid
        if (isNaN(date.getTime())) {
            console.warn(`Invalid timestamp value: ${timestamp}`);
            return 'Invalid timestamp';
        }
        
        // Calculate relative time
        const now = new Date();
        const diffMs = now - date;
        const diffSeconds = Math.floor(diffMs / 1000);
        
        let relativeTime;
        if (diffSeconds < 60) {
            relativeTime = 'just now';
        } else if (diffSeconds < 3600) {
            const mins = Math.floor(diffSeconds / 60);
            relativeTime = `${mins}m ago`;
        } else if (diffSeconds < 86400) {
            const hours = Math.floor(diffSeconds / 3600);
            relativeTime = `${hours}h ago`;
        } else {
            const days = Math.floor(diffSeconds / 86400);
            relativeTime = `${days}d ago`;
        }
        
        // Format the date - user-friendly
        let dateStr;
        try {
            dateStr = date.toUTCString();
        } catch (error) {
            console.error('Error formatting date:', error);
            dateStr = 'Date format error';
        }
        
        return `${relativeTime} (${dateStr})`;
    } catch (error) {
        console.error('Error in formatTimestamp:', error);
        return 'Error formatting timestamp';
    }
}

/**
 * Format time into a user-friendly string (HH:MM:SS)
 * @param {Date} date - The date to format
 * @returns {string} Formatted time string
 */
export function formatTime(date) {
    if (!date) return 'Never';
    
    try {
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        const seconds = date.getSeconds().toString().padStart(2, '0');
        
        return `${hours}:${minutes}:${seconds}`;
    } catch (error) {
        console.error('Error formatting time:', error);
        return 'Invalid time';
    }
}

/**
 * Format a metric name for display
 * @param {string} name - The raw metric name
 * @returns {string} Formatted metric name
 */
export function formatMetricName(name) {
    // Handle timestamp metrics
    if (name.toLowerCase().includes('time')) {
        return name
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase());
    }
    
    // Handle variations of latency metrics
    if (name.toLowerCase().includes('ping') && name.toLowerCase().includes('latency') || 
        name.toLowerCase() === 'latency_msec') {
        return 'Latency (msec)';
    }
    
    // Handle volume metrics
    if (name.toLowerCase().includes('volume')) {
        return name
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase())
            .replace(/Volume/i, 'Volume (bytes)');
    }
    
    return name
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
}

/**
 * Format a metric value for display
 * @param {any} value - The metric value
 * @param {boolean} isTimestamp - Whether the value is a timestamp
 * @returns {string} Formatted metric value
 */
export function formatMetricValue(value, isTimestamp = false) {
    // Handle null or undefined values
    if (value === null || value === undefined) {
        return 'N/A';
    }
    
    // Handle timestamp values
    if (isTimestamp && value) {
        return formatTimestamp(value);
    }
    
    if (typeof value === 'number') {
        // Format percentages
        if (value > 0 && value <= 1) {
            return `${(value * 100).toFixed(2)}%`;
        }
        
        // Format large numbers
        if (value >= 1000) {
            return value.toLocaleString();
        }
        
        // Format decimal numbers - ensure max 2 decimal places
        if (value % 1 !== 0) {
            return value.toFixed(2);
        }
    }
    
    // Default formatting
    return String(value);
}

/**
 * Debounce a function to limit how often it can be called
 * @param {Function} func - The function to debounce
 * @param {number} wait - The debounce wait time in milliseconds
 * @returns {Function} The debounced function
 */
export function debounce(func, wait = 300) {
    let timeout;
    
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Add CSS styles to the document head
 * @param {string} css - The CSS string to add
 * @param {string} id - Optional ID for the style element
 * @returns {HTMLStyleElement} The created style element
 */
export function addStyles(css, id = null) {
    const styleElement = document.createElement('style');
    if (id) styleElement.id = id;
    styleElement.textContent = css;
    document.head.appendChild(styleElement);
    return styleElement;
}

/**
 * Check if the dashboard is ready and try to recover if not
 * @param {Object} elements - The elements object
 * @param {Function} initFn - The initialization function to call if needed
 * @returns {boolean} - Whether the dashboard is initialized and ready
 */
export function ensureDashboardReady(elements, initFn) {
    if (!document.body) {
        console.error('Document body not available yet');
        return false;
    }
    
    // If elements object is empty or critical elements are missing, try to re-initialize
    if (!elements || Object.keys(elements).length === 0) {
        console.warn('Dashboard elements not initialized, attempting to recover');
        if (typeof initFn === 'function') {
            initFn();
        }
        return Object.keys(elements).length > 0;
    }
    
    return true;
}

// Export the utils module
export default {
    getElement,
    getElements,
    clearContainer,
    createElement,
    createFragment,
    formatTimestamp,
    formatTime,
    formatMetricName,
    formatMetricValue,
    debounce,
    addStyles,
    ensureDashboardReady
};
