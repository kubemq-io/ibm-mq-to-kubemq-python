/**
 * Main dashboard application
 * Coordinates the interaction between different modules
 */

import * as api from './api.js';
import * as ui from './ui.js';
import * as utils from './utils.js';
import * as state from './state.js';

// Dashboard state
let isInitialized = false;
let activeTab = 'health-tab';
let refreshInterval = null;
let lastRefreshTime = null;

/**
 * Initialize the dashboard
 */
function initDashboard() {
    try {
        console.log('Initializing dashboard...');
        
        // Initialize UI elements
        const elements = ui.initElementReferences();
        
        // Set up event listeners
        setupEventListeners();
        
        // Set up auto-refresh
        setupAutoRefresh();
        
        // Load initial data
        refreshData();
        
        isInitialized = true;
        console.log('Dashboard initialized successfully');
    } catch (error) {
        console.error('Error initializing dashboard:', error);
        ui.showGlobalError('Failed to initialize dashboard. Please reload the page.');
    }
}

/**
 * Set up event listeners for dashboard elements
 */
function setupEventListeners() {
    try {
        console.log('Setting up event listeners...');
        
        // Get elements
        const elements = ui.getElements();
        
        // Tab switching
        if (elements.healthTab) {
            elements.healthTab.addEventListener('click', () => {
                console.log('Health tab clicked');
                ui.setActiveTab('health-tab');
                activeTab = 'health-tab';
            });
        }
        
        if (elements.metricsTab) {
            elements.metricsTab.addEventListener('click', () => {
                console.log('Metrics tab clicked');
                ui.setActiveTab('metrics-tab');
                activeTab = 'metrics-tab';
                // Fetch metrics data when tab is clicked
                fetchMetricsData();
            });
        }
        
        // Refresh button
        if (elements.refreshButton) {
            elements.refreshButton.addEventListener('click', (event) => {
                event.preventDefault();
                console.log('Manual refresh triggered');
                refreshData();
            });
        }
        
        // Auto-refresh interval selector
        if (elements.refreshInterval) {
            elements.refreshInterval.addEventListener('change', (event) => {
                const interval = parseInt(event.target.value, 10);
                console.log(`Auto-refresh interval changed to ${interval} seconds`);
                setupAutoRefresh(interval * 1000); // Convert to milliseconds
            });
        }
        
        console.log('Event listeners set up successfully');
    } catch (error) {
        console.error('Error setting up event listeners:', error);
    }
}

/**
 * Set up auto-refresh with the specified interval
 * @param {number} interval - Refresh interval in milliseconds
 */
function setupAutoRefresh(interval = null) {
    try {
        // Clear existing interval
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
        }
        
        // Get interval from select element if not provided
        if (interval === null) {
            const elements = ui.getElements();
            if (elements.refreshInterval) {
                interval = parseInt(elements.refreshInterval.value, 10) * 1000; // Convert to milliseconds
            } else {
                interval = 10000; // Default to 10 seconds
            }
        }
        
        // Set up new interval if greater than 0
        if (interval > 0) {
            console.log(`Setting up auto-refresh with interval: ${interval}ms`);
            refreshInterval = setInterval(refreshData, interval);
        } else {
            console.log('Auto-refresh disabled');
        }
    } catch (error) {
        console.error('Error setting up auto-refresh:', error);
    }
}

/**
 * Refresh dashboard data
 */
function refreshData() {
    try {
        console.log('Refreshing dashboard data...');
        
        // Show refresh indicator if available
        const elements = ui.getElements();
        if (elements.refreshIndicator) {
            elements.refreshIndicator.style.display = 'inline-block';
        }
        
        // Determine which data to fetch based on active tab
        if (activeTab === 'health-tab') {
            fetchHealthData();
        } else if (activeTab === 'metrics-tab') {
            fetchMetricsData();
        } else {
            // Default to health data
            fetchHealthData();
        }
        
        // Update last refresh time
        lastRefreshTime = new Date();
        if (elements.lastUpdated) {
            elements.lastUpdated.textContent = utils.formatTime(lastRefreshTime);
        }
        
        // Hide refresh indicator after a short delay
        setTimeout(() => {
            if (elements.refreshIndicator) {
                elements.refreshIndicator.style.display = 'none';
            }
        }, 500);
    } catch (error) {
        console.error('Error refreshing dashboard data:', error);
        
        // Hide refresh indicator
        const elements = ui.getElements();
        if (elements.refreshIndicator) {
            elements.refreshIndicator.style.display = 'none';
        }
        
        ui.showGlobalError('Failed to refresh dashboard data');
    }
}

/**
 * Fetch health data from the API
 */
async function fetchHealthData() {
    try {
        console.log('Fetching health data...');
        
        // Fetch health data with retry
        const healthData = await api.fetchHealthData();
        
        // Update UI with health data
        ui.updateHealthData(healthData);
        
        console.log('Health data updated successfully');
    } catch (error) {
        console.error('Error fetching health data:', error);
        ui.showGlobalError(`Failed to fetch health data: ${error.message}`);
    }
}

/**
 * Fetch metrics data from the API
 */
async function fetchMetricsData() {
    try {
        console.log('Fetching metrics data...');
        
        // Fetch metrics data with retry
        const metricsData = await api.fetchMetricsData();
        console.log('Metrics data received:', JSON.stringify(metricsData, null, 2));
        
        // If metrics tab is active, update UI directly
        if (activeTab === 'metrics-tab') {
            console.log('Metrics tab is active, updating UI directly');
            ui.updateMetricsData(metricsData);
        } else {
            // Otherwise, cache the data for when the tab becomes active
            console.log('Metrics tab is not active, caching data');
            state.cacheMetricsData(metricsData);
        }
        
        console.log('Metrics data updated successfully');
    } catch (error) {
        console.error('Error fetching metrics data:', error);
        ui.showGlobalError(`Failed to fetch metrics data: ${error.message}`);
    }
}

/**
 * Handle errors in the dashboard
 * @param {Error} error - The error object
 * @param {string} context - The context in which the error occurred
 */
function handleError(error, context = 'dashboard') {
    console.error(`Error in ${context}:`, error);
    ui.showGlobalError(`An error occurred in ${context}: ${error.message}`);
}

// Initialize the dashboard when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    try {
        initDashboard();
    } catch (error) {
        console.error('Critical error initializing dashboard:', error);
        // Try to show error even if dashboard initialization failed
        try {
            ui.showGlobalError('Critical error initializing dashboard. Please reload the page.');
        } catch (displayError) {
            console.error('Could not display error message:', displayError);
            // Last resort: create a basic error message
            const errorDiv = document.createElement('div');
            errorDiv.style.color = 'red';
            errorDiv.style.padding = '20px';
            errorDiv.style.margin = '20px';
            errorDiv.style.border = '1px solid red';
            errorDiv.textContent = 'Critical error initializing dashboard. Please reload the page.';
            document.body.prepend(errorDiv);
        }
    }
});

// Export dashboard functions for potential external use
export {
    initDashboard,
    refreshData,
    fetchHealthData,
    fetchMetricsData,
    handleError
};
