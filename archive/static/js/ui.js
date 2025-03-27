/**
 * UI rendering module for the dashboard
 * Handles all UI rendering and updates
 */

import { getElement, clearContainer, createElement, createFragment, formatMetricName, formatMetricValue, formatTimestamp } from './utils.js';
import { createErrorOverlay } from './api.js';
import { getState, getSelector } from './state.js';

// DOM Elements cache
let elements = {};

/**
 * Initialize element references
 * @returns {Object} The elements object
 */
export function initElementReferences() {
    try {
        console.log('Initializing element references...');
        
        const state = getState();
        
        // Initialize by ID elements
        for (const [key, selector] of Object.entries(state.selectors.ids)) {
            elements[key] = getElement(`#${selector}`);
            if (!elements[key]) {
                console.warn(`Element with ID '${selector}' not found`);
            }
        }
        
        // Initialize tab elements
        elements.healthTab = getElement('#health-tab');
        elements.metricsTab = getElement('#metrics-tab');
        
        // Initialize panel elements
        elements.healthPanel = getElement('#health-panel');
        elements.metricsPanel = getElement('#metrics-panel');
        
        // Initialize container elements
        elements.healthBindingsContainer = getElement('#health-bindings-container') || 
                                          getElement('#health-container') ||
                                          getElement('.health-bindings-container');
                                          
        elements.metricsBindingsContainer = getElement('#metrics-bindings-container') || 
                                          getElement('#metrics-container') ||
                                          getElement('.metrics-bindings-container');
        
        // Initialize templates
        elements.bindingHealthTemplate = getElement('#binding-health-template');
        elements.bindingMetricsTemplate = getElement(state.selectors.classes.bindingMetricsTemplate);
        elements.metricItemTemplate = getElement(state.selectors.classes.metricItemTemplate);
        
        // Initialize status elements
        elements.healthStatusIndicator = getElement('#health-status-indicator');
        elements.healthyCount = getElement('#healthy-count');
        elements.unhealthyCount = getElement('#unhealthy-count');
        elements.totalBindings = getElement('#total-bindings');
        
        // Log initialization status
        console.log('Dashboard element references initialized');
        
        return elements;
    } catch (error) {
        console.error('Error initializing element references:', error);
        return {};
    }
}

/**
 * Get the elements object
 * @returns {Object} The elements object
 */
export function getElements() {
    return elements;
}

/**
 * Set active tab and show corresponding panel
 * @param {string} tabId - The ID of the tab to activate
 */
export function setActiveTab(tabId) {
    try {
        console.log(`Setting active tab: ${tabId}`);
        
        // Cache tab elements to avoid repeated DOM lookups
        const allTabs = document.querySelectorAll('.tab-btn');
        const allPanels = document.querySelectorAll('.panel');
        
        if (!allTabs || !allPanels) {
            console.error('Tabs or panels not found');
            return;
        }
        
        // Remove active class from all tabs
        allTabs.forEach(tab => tab.classList.remove('active'));
        
        // Hide all panels
        allPanels.forEach(panel => panel.style.display = 'none');
        
        // Add active class to selected tab
        const selectedTab = document.getElementById(tabId);
        if (selectedTab) {
            selectedTab.classList.add('active');
            
            // Show corresponding panel
            const panelId = selectedTab.getAttribute('data-panel');
            const panel = document.getElementById(panelId);
            
            if (panel) {
                panel.style.display = 'block';
                
                // If switching to metrics tab and we have cached data, update metrics UI
                if (panelId === 'metrics-panel' && getState().cachedMetricsData) {
                    console.log('Using cached metrics data when switching to metrics tab');
                    updateMetricsData(getState().cachedMetricsData);
                    
                    // Clear the cache after using it
                    getState().cachedMetricsData = null;
                }
            } else {
                console.error(`Panel not found: ${panelId}`);
            }
        } else {
            console.error(`Tab not found: ${tabId}`);
        }
    } catch (error) {
        console.error('Error setting active tab:', error);
    }
}

/**
 * Show a global error message
 * @param {string} message - Error message to display
 */
export function showGlobalError(message) {
    try {
        // Create temporary floating error
        const errorDiv = createElement('div', { className: 'floating-error' });
        const errorMessageDiv = createElement('div', { className: 'error-message' });
        const icon = createElement('i', { className: 'fas fa-exclamation-circle' });
        const errorText = createElement('p', {}, message);
        const closeBtn = createElement('button', { className: 'close-btn' }, '×');
        
        errorMessageDiv.appendChild(icon);
        errorMessageDiv.appendChild(errorText);
        errorMessageDiv.appendChild(closeBtn);
        errorDiv.appendChild(errorMessageDiv);
        
        // Add close button functionality
        closeBtn.addEventListener('click', () => {
            document.body.removeChild(errorDiv);
        });
        
        // Style the floating error
        Object.assign(errorDiv.style, {
            position: 'fixed',
            top: '20px',
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: '9999',
            backgroundColor: '#f8d7da',
            color: '#721c24',
            padding: '10px 20px',
            borderRadius: '4px',
            boxShadow: '0 2px 10px rgba(0,0,0,0.2)'
        });
        
        // Add to body and auto-remove after 5 seconds
        document.body.appendChild(errorDiv);
        setTimeout(() => {
            if (document.body.contains(errorDiv)) {
                document.body.removeChild(errorDiv);
            }
        }, 5000);
    } catch (error) {
        // Last resort: console error
        console.error('Error displaying error message:', error);
        console.error('Original error:', message);
    }
}

/**
 * Create an error element
 * @param {string} message - Error message
 * @returns {HTMLElement} Error element
 */
export function createErrorElement(message) {
    const errorElement = createElement('div', { className: 'error-message' });
    const icon = createElement('i', { className: 'fas fa-exclamation-circle' });
    const errorText = createElement('p', {}, message);
    
    errorElement.appendChild(icon);
    errorElement.appendChild(errorText);
    return errorElement;
}

/**
 * Update the health dashboard with new data
 * @param {Object} healthData - Health data from the API
 */
export function updateHealthData(healthData) {
    try {
        // Validate health data
        if (!healthData) {
            throw new Error('No health data available');
        }
        
        // Check if the data has a nested 'data' property (API response format)
        const data = healthData.data || healthData;
        
        // Get the health bindings container
        const container = elements.healthBindingsContainer || 
                          getElement('#health-bindings-container');
        
        if (!container) {
            throw new Error('Health bindings container not found');
        }
        
        // Clear existing content
        clearContainer(container);
        
        // Update overall status indicator if it exists
        if (elements.healthStatusIndicator) {
            try {
                const overallStatus = data.overall_status || 'unknown';
                elements.healthStatusIndicator.textContent = overallStatus.toUpperCase();
                elements.healthStatusIndicator.className = 'status-badge ' + overallStatus;
            } catch (statusError) {
                console.error('Error updating health status indicator:', statusError);
            }
        }
        
        // Initialize counters
        let healthyCnt = 0;
        let unhealthyCnt = 0;
        
        // Process bindings if available
        if (data.bindings) {
            try {
                const bindingsData = data.bindings;
                const totalBindings = Object.keys(bindingsData).length;
                
                // Debug log to see what bindings are available
                console.log('Bindings data:', JSON.stringify(bindingsData, null, 2));
                console.log('Total bindings:', totalBindings);
                console.log('Binding names:', Object.keys(bindingsData));
                
                // Update binding count if element exists
                if (elements.bindingCount) {
                    elements.bindingCount.textContent = totalBindings;
                }
                
                // Create binding cards
                Object.entries(bindingsData).forEach(([bindingName, binding], index) => {
                    try {
                        console.log(`Processing binding ${index + 1}/${totalBindings}: ${bindingName}`);
                        console.log(`Binding details:`, JSON.stringify(binding, null, 2));
                        
                        // Count statuses
                        if (binding.status === 'healthy') healthyCnt++;
                        else if (binding.status === 'unhealthy') unhealthyCnt++;
                        
                        // Create a detailed binding card
                        const bindingCard = createElement('div', { className: 'binding-card' });
                        const header = createElement('div', { className: 'binding-header' });
                        const name = createElement('h3', { className: 'binding-name' }, bindingName);
                        const status = createElement('div', 
                            { className: `binding-status ${binding.status}` }, 
                            binding.status.toUpperCase()
                        );
                        
                        header.appendChild(name);
                        header.appendChild(status);
                        bindingCard.appendChild(header);
                        
                        // Create binding body
                        const body = createElement('div', { className: 'binding-body' });
                        
                        // Add binding type if available
                        if (binding.binding_type) {
                            const typeElement = createElement('div', { className: 'binding-type' }, 
                                `Type: ${binding.binding_type}`);
                            body.appendChild(typeElement);
                        }
                        
                        // Create components container
                        const components = createElement('div', { className: 'components' });
                        
                        // Add source component if available
                        if (binding.source) {
                            const sourceComponent = createElement('div', { className: 'component source' });
                            const sourceHeader = createElement('h4', {}, 'Source: ');
                            const sourceStatus = createElement('span', 
                                { className: `component-status ${binding.source.status || 'unknown'}` },
                                (binding.source.status || 'UNKNOWN').toUpperCase()
                            );
                            sourceHeader.appendChild(sourceStatus);
                            sourceComponent.appendChild(sourceHeader);
                            
                            // Add source details
                            const sourceDetails = createElement('div', { className: 'component-details' });
                            if (binding.source.details && Object.keys(binding.source.details).length > 0) {
                                const detailsList = createElement('div', { className: 'details-list' });
                                
                                Object.entries(binding.source.details).forEach(([key, value]) => {
                                    const detailItem = createElement('div', { className: 'detail-item' });
                                    const formattedKey = key.replace(/_/g, ' ')
                                        .replace(/\b\w/g, l => l.toUpperCase());
                                    
                                    const keyElement = createElement('span', { className: 'detail-item-key' }, 
                                        `${formattedKey}: `);
                                    const valueElement = createElement('span', { className: 'detail-item-value' }, 
                                        value);
                                    
                                    detailItem.appendChild(keyElement);
                                    detailItem.appendChild(valueElement);
                                    detailsList.appendChild(detailItem);
                                });
                                
                                sourceDetails.appendChild(detailsList);
                            }
                            
                            // Add source errors if any
                            if (binding.source.errors && Object.keys(binding.source.errors).length > 0) {
                                const errorsList = createElement('div', { className: 'error-list' });
                                
                                Object.entries(binding.source.errors).forEach(([key, value]) => {
                                    const errorItem = createElement('div', { className: 'error-item' }, 
                                        `${key}: ${value}`);
                                    errorsList.appendChild(errorItem);
                                });
                                
                                sourceDetails.appendChild(errorsList);
                            }
                            
                            sourceComponent.appendChild(sourceDetails);
                            components.appendChild(sourceComponent);
                        }
                        
                        // Add target component if available
                        if (binding.target) {
                            const targetComponent = createElement('div', { className: 'component target' });
                            const targetHeader = createElement('h4', {}, 'Target: ');
                            const targetStatus = createElement('span', 
                                { className: `component-status ${binding.target.status || 'unknown'}` },
                                (binding.target.status || 'UNKNOWN').toUpperCase()
                            );
                            targetHeader.appendChild(targetStatus);
                            targetComponent.appendChild(targetHeader);
                            
                            // Add target details
                            const targetDetails = createElement('div', { className: 'component-details' });
                            if (binding.target.details && Object.keys(binding.target.details).length > 0) {
                                const detailsList = createElement('div', { className: 'details-list' });
                                
                                Object.entries(binding.target.details).forEach(([key, value]) => {
                                    const detailItem = createElement('div', { className: 'detail-item' });
                                    const formattedKey = key.replace(/_/g, ' ')
                                        .replace(/\b\w/g, l => l.toUpperCase());
                                    
                                    const keyElement = createElement('span', { className: 'detail-item-key' }, 
                                        `${formattedKey}: `);
                                    const valueElement = createElement('span', { className: 'detail-item-value' }, 
                                        value);
                                    
                                    detailItem.appendChild(keyElement);
                                    detailItem.appendChild(valueElement);
                                    detailsList.appendChild(detailItem);
                                });
                                
                                targetDetails.appendChild(detailsList);
                            }
                            
                            // Add target errors if any
                            if (binding.target.errors && Object.keys(binding.target.errors).length > 0) {
                                const errorsList = createElement('div', { className: 'error-list' });
                                
                                Object.entries(binding.target.errors).forEach(([key, value]) => {
                                    const errorItem = createElement('div', { className: 'error-item' }, 
                                        `${key}: ${value}`);
                                    errorsList.appendChild(errorItem);
                                });
                                
                                targetDetails.appendChild(errorsList);
                            }
                            
                            targetComponent.appendChild(targetDetails);
                            components.appendChild(targetComponent);
                        }
                        
                        // Add components to body
                        if (components.children.length > 0) {
                            body.appendChild(components);
                        }
                        
                        // Add body to card
                        bindingCard.appendChild(body);
                        
                        container.appendChild(bindingCard);
                    } catch (bindingError) {
                        console.error(`Error processing binding ${bindingName}:`, bindingError);
                        // Create error card for this binding
                        const errorCard = createErrorElement(`Error displaying binding: ${bindingName}`);
                        container.appendChild(errorCard);
                    }
                });
                
                // Show no bindings message if no bindings were processed
                if (container.children.length === 0) {
                    const noBindings = createElement('div', { className: 'no-data' }, 'No bindings available');
                    container.appendChild(noBindings);
                }
                
                // Log container children after processing
                console.log('Container children count:', container.children.length);
                console.log('Container children:', Array.from(container.children).map(child => child.outerHTML));
            } catch (bindingsError) {
                console.error('Error processing bindings:', bindingsError);
                const errorElement = createErrorElement('Error processing bindings data');
                container.appendChild(errorElement);
            }
        } else {
            // No bindings data
            const noBindings = createElement('div', { className: 'no-data' }, 'No bindings available');
            container.appendChild(noBindings);
        }
        
        // Update status counts if elements exist
        try {
            if (elements.healthyCount) {
                elements.healthyCount.textContent = healthyCnt;
            }
            
            if (elements.unhealthyCount) {
                elements.unhealthyCount.textContent = unhealthyCnt;
            }
            
            if (elements.totalBindings) {
                elements.totalBindings.textContent = Object.keys(data.bindings || {}).length;
            }
        } catch (statsError) {
            console.error('Error updating health statistics:', statsError);
        }
    } catch (error) {
        console.error('Error updating health data:', error);
        showGlobalError('Failed to update health data');
    }
}

/**
 * Update the metrics dashboard with new data
 * @param {Object} metricsData - Metrics data from the API
 */
export function updateMetricsData(metricsData) {
    try {
        console.log('Updating metrics display...');
        console.log('Metrics data:', JSON.stringify(metricsData, null, 2));
        
        // Validate metrics data
        if (!metricsData) {
            throw new Error('No metrics data available');
        }
        
        // Check if the data has a nested 'data' property (API response format)
        const data = metricsData.data || metricsData;
        console.log('Processed data:', JSON.stringify(data, null, 2));
        
        // Get the metrics bindings container
        const container = elements.metricsBindingsContainer || 
                          getElement('#metrics-bindings-container');
        
        if (!container) {
            throw new Error('Metrics bindings container not found');
        }
        
        // Clear existing content
        clearContainer(container);
        
        // Create a document fragment to batch DOM operations
        const fragment = createFragment();
        
        // Add system metrics if available
        if (data.system && Object.keys(data.system).length > 0) {
            try {
                console.log('Processing system metrics');
                
                // Create system metrics card
                const systemCard = createElement('div', { className: 'binding-card system-metrics-card' });
                const header = createElement('div', { className: 'binding-header' });
                const name = createElement('h3', { className: 'binding-name system-title' }, 'System Metrics');
                
                header.appendChild(name);
                systemCard.appendChild(header);
                
                // Add metrics
                const metricsContainer = createElement('div', { className: 'metrics-container' });
                
                // Group metrics by category
                const metricGroups = {
                    messages: {},
                    errors: {},
                    reconnection: {},
                    timestamps: {}
                };
                
                // Categorize metrics
                Object.entries(data.system).forEach(([metricName, metricValue]) => {
                    if (metricName.includes('message')) {
                        metricGroups.messages[metricName] = metricValue;
                    } else if (metricName.includes('error')) {
                        metricGroups.errors[metricName] = metricValue;
                    } else if (metricName.includes('reconnection')) {
                        metricGroups.reconnection[metricName] = metricValue;
                    } else if (metricName.includes('time') || metricName.includes('timestamp')) {
                        metricGroups.timestamps[metricName] = metricValue;
                    } else {
                        // Add to messages group by default
                        metricGroups.messages[metricName] = metricValue;
                    }
                });
                
                // Create sections for each group
                const groupTitles = {
                    messages: 'Message Statistics',
                    errors: 'Error Statistics',
                    reconnection: 'Reconnection Statistics',
                    timestamps: 'Timestamps'
                };
                
                Object.entries(metricGroups).forEach(([groupName, metrics]) => {
                    if (Object.keys(metrics).length > 0) {
                        const section = createElement('div', { className: 'metrics-section' });
                        const sectionHeader = createElement('div', { className: 'section-header' });
                        const sectionTitle = createElement('h4', {}, groupTitles[groupName] || groupName);
                        
                        sectionHeader.appendChild(sectionTitle);
                        section.appendChild(sectionHeader);
                        
                        const metricsList = createElement('div', { className: 'metrics-list' });
                        
                        Object.entries(metrics).forEach(([metricName, metricValue]) => {
                            const metricItem = createElement('div', { className: 'metric-item' });
                            const metricNameElem = createElement('div', { className: 'metric-name' }, 
                                formatMetricName(metricName));
                            const metricValueElem = createElement('div', { className: 'metric-value' }, 
                                formatMetricValue(metricValue, metricName.includes('time')));
                            
                            metricItem.appendChild(metricNameElem);
                            metricItem.appendChild(metricValueElem);
                            metricsList.appendChild(metricItem);
                        });
                        
                        section.appendChild(metricsList);
                        metricsContainer.appendChild(section);
                    }
                });
                
                systemCard.appendChild(metricsContainer);
                fragment.appendChild(systemCard);
                
            } catch (systemError) {
                console.error('Error processing system metrics:', systemError);
                const errorCard = createErrorElement('Error displaying system metrics');
                fragment.appendChild(errorCard);
            }
        }
        
        // Process bindings if available
        if (data.bindings && Object.keys(data.bindings).length > 0) {
            try {
                console.log('Processing binding metrics');
                
                // Add section divider
                const divider = createElement('div', { className: 'section-divider' });
                const dividerTitle = createElement('h3', {}, 'Binding Metrics');
                divider.appendChild(dividerTitle);
                fragment.appendChild(divider);
                
                // Create binding cards
                Object.entries(data.bindings).forEach(([bindingName, binding], index) => {
                    try {
                        // Create a binding card
                        const bindingCard = createElement('div', { className: 'binding-card' });
                        const header = createElement('div', { className: 'binding-header' });
                        const name = createElement('h3', { className: 'binding-name' }, bindingName);
                        
                        header.appendChild(name);
                        bindingCard.appendChild(header);
                        
                        // Add metrics
                        const metricsContainer = createElement('div', { className: 'metrics-container' });
                        
                        // Group metrics by category
                        const metricGroups = {
                            messages: {},
                            errors: {},
                            reconnection: {},
                            timestamps: {}
                        };
                        
                        // Add metrics data
                        if (binding && Object.keys(binding).length > 0) {
                            // Categorize metrics
                            Object.entries(binding).forEach(([metricName, metricValue]) => {
                                if (metricName.includes('message')) {
                                    metricGroups.messages[metricName] = metricValue;
                                } else if (metricName.includes('error')) {
                                    metricGroups.errors[metricName] = metricValue;
                                } else if (metricName.includes('reconnection')) {
                                    metricGroups.reconnection[metricName] = metricValue;
                                } else if (metricName.includes('time') || metricName.includes('timestamp')) {
                                    metricGroups.timestamps[metricName] = metricValue;
                                } else {
                                    // Add to messages group by default
                                    metricGroups.messages[metricName] = metricValue;
                                }
                            });
                            
                            // Create sections for each group
                            const groupTitles = {
                                messages: 'Message Statistics',
                                errors: 'Error Statistics',
                                reconnection: 'Reconnection Statistics',
                                timestamps: 'Timestamps'
                            };
                            
                            Object.entries(metricGroups).forEach(([groupName, metrics]) => {
                                if (Object.keys(metrics).length > 0) {
                                    const section = createElement('div', { className: 'metrics-section' });
                                    const sectionHeader = createElement('div', { className: 'section-header' });
                                    const sectionTitle = createElement('h4', {}, groupTitles[groupName] || groupName);
                                    
                                    sectionHeader.appendChild(sectionTitle);
                                    section.appendChild(sectionHeader);
                                    
                                    const metricsList = createElement('div', { className: 'metrics-list' });
                                    
                                    Object.entries(metrics).forEach(([metricName, metricValue]) => {
                                        const metricItem = createElement('div', { className: 'metric-item' });
                                        const metricNameElem = createElement('div', { className: 'metric-name' }, 
                                            formatMetricName(metricName));
                                        const metricValueElem = createElement('div', { className: 'metric-value' }, 
                                            formatMetricValue(metricValue, metricName.includes('time')));
                                        
                                        metricItem.appendChild(metricNameElem);
                                        metricItem.appendChild(metricValueElem);
                                        metricsList.appendChild(metricItem);
                                    });
                                    
                                    section.appendChild(metricsList);
                                    metricsContainer.appendChild(section);
                                }
                            });
                        } else {
                            const noMetrics = createElement('div', { className: 'no-data' }, 
                                'No metrics available for this binding');
                            metricsContainer.appendChild(noMetrics);
                        }
                        
                        bindingCard.appendChild(metricsContainer);
                        fragment.appendChild(bindingCard);
                    } catch (bindingError) {
                        console.error(`Error processing metrics for binding ${bindingName}:`, bindingError);
                        // Create error card for this binding
                        const errorCard = createErrorElement(`Error displaying metrics for binding: ${bindingName}`);
                        fragment.appendChild(errorCard);
                    }
                });
            } catch (bindingsError) {
                console.error('Error processing binding metrics:', bindingsError);
                const errorElement = createErrorElement('Error processing binding metrics data');
                fragment.appendChild(errorElement);
            }
        }
        
        // Check if we have any content
        if (fragment.children.length === 0) {
            const noMetrics = createElement('div', { className: 'no-data' }, 'No metrics data available');
            fragment.appendChild(noMetrics);
        }
        
        // Append the fragment to the container
        container.appendChild(fragment);
        
        console.log('Metrics update complete');
    } catch (error) {
        console.error('Error updating metrics data:', error);
        
        // Try to show error in the container
        try {
            const container = elements.metricsBindingsContainer || 
                              getElement('#metrics-bindings-container');
            
            if (container) {
                // Clear existing content
                clearContainer(container);
                
                // Create a more informative error message
                const errorCard = createElement('div', { className: 'error-card' });
                const errorHeader = createElement('h3', { className: 'error-title' }, 'Error Loading Metrics');
                const errorMessage = createElement('p', { className: 'error-message' }, 
                    `Failed to load metrics data: ${error.message}. Please try refreshing the page or check if the metrics service is running.`);
                const retryButton = createElement('button', { className: 'retry-button btn' }, 'Retry');
                
                // Add retry functionality
                retryButton.addEventListener('click', () => {
                    // Show loading indicator
                    clearContainer(container);
                    const loading = createElement('div', { className: 'loading' });
                    const spinner = createElement('div', { className: 'spinner' });
                    const loadingText = createElement('p', {}, 'Loading metrics data...');
                    loading.appendChild(spinner);
                    loading.appendChild(loadingText);
                    container.appendChild(loading);
                    
                    // Import and use the fetchMetricsData function
                    import('./api.js').then(api => {
                        // Retry fetching metrics
                        api.fetchMetricsData().then(data => {
                            updateMetricsData(data);
                        }).catch(e => {
                            console.error('Retry failed:', e);
                            updateMetricsData(null); // This will show the error again
                        });
                    });
                });
                
                errorCard.appendChild(errorHeader);
                errorCard.appendChild(errorMessage);
                errorCard.appendChild(retryButton);
                container.appendChild(errorCard);
            } else {
                showGlobalError(`Failed to update metrics data: ${error.message}`);
            }
        } catch (displayError) {
            console.error('Error displaying metrics error:', displayError);
            showGlobalError('Failed to update metrics data');
        }
    }
}

// Export the UI module
export default {
    initElementReferences,
    getElements,
    setActiveTab,
    showGlobalError,
    createErrorElement,
    updateHealthData,
    updateMetricsData
};
