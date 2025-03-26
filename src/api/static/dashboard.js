/**
 * IBM MQ - KubeMQ Dashboard
 * 
 * This script handles fetching data from the API and 
 * updating the dashboard with health and metrics information.
 */

// Dashboard state
const state = {
    refreshInterval: null,
    activeTab: 'health',
    lastRefreshTime: null
};

// DOM elements
const elements = {
    // Tabs
    healthTab: document.getElementById('health-tab'),
    metricsTab: document.getElementById('metrics-tab'),
    healthPanel: document.getElementById('health-panel'),
    metricsPanel: document.getElementById('metrics-panel'),
    
    // Overview stats
    healthyCount: document.getElementById('healthy-count'),
    unhealthyCount: document.getElementById('unhealthy-count'),
    totalBindings: document.getElementById('total-bindings'),
    
    // Health
    healthStatusIndicator: document.getElementById('health-status-indicator'),
    healthBindingsContainer: document.getElementById('health-bindings-container'),
    
    // Metrics
    metricsBindingsContainer: document.getElementById('metrics-bindings-container'),
    
    // Controls
    refreshBtn: document.getElementById('refresh-btn'),
    autoRefreshSelect: document.getElementById('auto-refresh'),
    
    // Footer
    currentYear: document.getElementById('current-year'),
    lastRefreshed: document.getElementById('last-refreshed'),
    
    // Templates
    bindingHealthTemplate: document.getElementById('binding-health-template'),
    bindingMetricsTemplate: document.getElementById('binding-metrics-template'),
    metricItemTemplate: document.getElementById('metric-item-template')
};

/**
 * Initialize the dashboard
 */
function initDashboard() {
    // Set current year in footer
    elements.currentYear.textContent = new Date().getFullYear();
    
    // Add event listeners
    setupEventListeners();
    
    // Initial data load
    refreshData();
    
    // Set default auto-refresh interval
    setAutoRefresh(parseInt(elements.autoRefreshSelect.value));
}

/**
 * Setup event listeners for the dashboard
 */
function setupEventListeners() {
    // Tab switching
    elements.healthTab.addEventListener('click', () => setActiveTab('health'));
    elements.metricsTab.addEventListener('click', () => setActiveTab('metrics'));
    
    // Refresh button
    elements.refreshBtn.addEventListener('click', refreshData);
    
    // Auto-refresh select
    elements.autoRefreshSelect.addEventListener('change', (e) => {
        setAutoRefresh(parseInt(e.target.value));
    });
}

/**
 * Set the active tab
 * @param {string} tabName - The name of the tab to activate
 */
function setActiveTab(tabName) {
    state.activeTab = tabName;
    
    // Update tab buttons
    elements.healthTab.classList.toggle('active', tabName === 'health');
    elements.metricsTab.classList.toggle('active', tabName === 'metrics');
    
    // Update panels
    elements.healthPanel.classList.toggle('active', tabName === 'health');
    elements.metricsPanel.classList.toggle('active', tabName === 'metrics');
}

/**
 * Set auto-refresh interval
 * @param {number} interval - Interval in milliseconds
 */
function setAutoRefresh(interval) {
    // Clear existing interval
    if (state.refreshInterval) {
        clearInterval(state.refreshInterval);
        state.refreshInterval = null;
    }
    
    // Set new interval if not 0
    if (interval > 0) {
        state.refreshInterval = setInterval(refreshData, interval);
    }
}

/**
 * Refresh all dashboard data
 */
function refreshData() {
    // Fetch health data
    fetchHealthData();
    
    // Fetch metrics data
    fetchMetricsData();
    
    // Update last refreshed time
    state.lastRefreshTime = new Date();
    elements.lastRefreshed.textContent = state.lastRefreshTime.toLocaleTimeString();
}

/**
 * Fetch health data from the API
 */
async function fetchHealthData() {
    try {
        const response = await fetch('/health/');
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data && data.data) {
            updateHealthData(data.data);
        }
    } catch (error) {
        console.error('Error fetching health data:', error);
        showError(elements.healthBindingsContainer, 'Failed to load health data');
    }
}

/**
 * Fetch metrics data from the API
 */
async function fetchMetricsData() {
    try {
        const response = await fetch('/metrics/');
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data && data.data) {
            updateMetricsData(data.data);
        }
    } catch (error) {
        console.error('Error fetching metrics data:', error);
        showError(elements.metricsBindingsContainer, 'Failed to load metrics data');
    }
}

/**
 * Update the health dashboard with new data
 * @param {Object} healthData - Health data from the API
 */
function updateHealthData(healthData) {
    // Clear existing content
    elements.healthBindingsContainer.innerHTML = '';
    
    // Update overall status indicator with CAPITALIZED text
    const overallStatus = healthData.overall_status;
    elements.healthStatusIndicator.textContent = overallStatus.toUpperCase();
    elements.healthStatusIndicator.className = 'status-badge ' + overallStatus;
    
    // Count different statuses
    let healthyCnt = 0;
    let unhealthyCnt = 0;
    
    // Process each binding
    if (healthData.bindings) {
        const bindingsData = healthData.bindings;
        const totalBindings = Object.keys(bindingsData).length;
        
        // Update stat counters
        elements.totalBindings.textContent = totalBindings;
        
        // Create binding cards
        Object.entries(bindingsData).forEach(([bindingName, binding], index) => {
            // Update counts
            if (binding.status === 'healthy') healthyCnt++;
            else if (binding.status === 'unhealthy') unhealthyCnt++;
            
            // Create binding card with sequence number
            const bindingCard = createHealthBindingCard(bindingName, binding, index + 1);
            elements.healthBindingsContainer.appendChild(bindingCard);
        });
    }
    
    // Update status counts
    elements.healthyCount.textContent = healthyCnt;
    elements.unhealthyCount.textContent = unhealthyCnt;
}

/**
 * Create a binding health card
 * @param {string} bindingName - Name of the binding
 * @param {Object} binding - Binding health data
 * @param {number} seqNum - Sequence number of the binding
 * @returns {HTMLElement} The binding card element
 */
function createHealthBindingCard(bindingName, binding, seqNum) {
    const template = elements.bindingHealthTemplate.content.cloneNode(true);
    
    // Create sequence number badge and name container
    const nameContainer = document.createElement('div');
    nameContainer.className = 'binding-name-container';
    
    const seqBadge = document.createElement('div');
    seqBadge.className = 'binding-seq';
    seqBadge.textContent = seqNum;
    
    // Get the binding name element and replace it with container
    const nameElement = template.querySelector('.binding-name');
    const nameText = nameElement.textContent;
    nameElement.textContent = '';
    
    // Assemble components
    nameContainer.appendChild(seqBadge);
    nameContainer.appendChild(nameElement);
    
    // Replace the binding-name with the container
    const headerElement = template.querySelector('.binding-header');
    headerElement.insertBefore(nameContainer, headerElement.firstChild);
    
    // Set binding name
    nameElement.textContent = bindingName;
    
    // Set binding status - CAPITALIZE status text
    const statusElement = template.querySelector('.binding-status');
    statusElement.textContent = binding.status.toUpperCase();
    statusElement.classList.add(binding.status);
    
    // Set binding type
    template.querySelector('.binding-type').textContent = `Type: ${binding.binding_type}`;
    
    // Set source component details
    if (binding.source) {
        // Update component header to include status label
        const sourceHeader = template.querySelector('.component.source h4');
        const sourceStatusElem = template.querySelector('.component.source .component-status');
        
        // Configure status badge with CAPITALIZED text
        sourceStatusElem.textContent = (binding.source.status || 'unknown').toUpperCase();
        sourceStatusElem.classList.add(binding.source.status || 'unknown');
        
        // Move status badge next to component header
        sourceHeader.textContent = 'Source: ';
        sourceHeader.appendChild(sourceStatusElem);
        
        // Process source details
        const sourceDetailsElem = template.querySelector('.component.source .component-details');
        renderComponentDetails(sourceDetailsElem, binding.source);
    }
    
    // Set target component details
    if (binding.target) {
        // Update component header to include status label
        const targetHeader = template.querySelector('.component.target h4');
        const targetStatusElem = template.querySelector('.component.target .component-status');
        
        // Configure status badge with CAPITALIZED text
        targetStatusElem.textContent = (binding.target.status || 'unknown').toUpperCase();
        targetStatusElem.classList.add(binding.target.status || 'unknown');
        
        // Move status badge next to component header
        targetHeader.textContent = 'Target: ';
        targetHeader.appendChild(targetStatusElem);
        
        // Process target details
        const targetDetailsElem = template.querySelector('.component.target .component-details');
        renderComponentDetails(targetDetailsElem, binding.target);
    }
    
    return template;
}

/**
 * Render component details
 * @param {HTMLElement} element - Element to render details into
 * @param {Object} component - Component data
 */
function renderComponentDetails(element, component) {
    // Clear existing details
    element.innerHTML = '';
    
    // Handle errors
    if (component.errors && Object.keys(component.errors).length > 0) {
        const errorsList = document.createElement('div');
        errorsList.className = 'error-list';
        
        Object.entries(component.errors).forEach(([key, value]) => {
            const errorItem = document.createElement('div');
            errorItem.className = 'error-item';
            errorItem.textContent = `${key}: ${value}`;
            errorsList.appendChild(errorItem);
        });
        
        element.appendChild(errorsList);
    }
    
    // Handle details
    if (component.details && Object.keys(component.details).length > 0) {
        const detailsList = document.createElement('div');
        detailsList.className = 'details-list';
        
        Object.entries(component.details).forEach(([key, value]) => {
            const detailItem = document.createElement('div');
            detailItem.className = 'detail-item';
            
            // Format the key with spaces and capitalization
            const formattedKey = key.replace(/_/g, ' ')
                .replace(/\b\w/g, l => l.toUpperCase());
            
            // Create separate elements for key and value
            const keyElement = document.createElement('span');
            keyElement.className = 'detail-item-key';
            keyElement.textContent = `${formattedKey}: `;
            
            const valueElement = document.createElement('span');
            valueElement.className = 'detail-item-value';
            valueElement.textContent = value;
            
            // Add key and value to detail item
            detailItem.appendChild(keyElement);
            detailItem.appendChild(valueElement);
            
            detailsList.appendChild(detailItem);
        });
        
        element.appendChild(detailsList);
    }
}

/**
 * Update the metrics dashboard with new data
 * @param {Object} metricsData - Metrics data from the API
 */
function updateMetricsData(metricsData) {
    // Clear existing content
    elements.metricsBindingsContainer.innerHTML = '';
    
    // Process each binding
    if (metricsData.bindings) {
        const bindingsData = metricsData.bindings;
        
        // Create binding cards
        Object.entries(bindingsData).forEach(([bindingName, binding], index) => {
            const bindingCard = createMetricsBindingCard(bindingName, binding, index + 1);
            elements.metricsBindingsContainer.appendChild(bindingCard);
        });
    }
}

/**
 * Create a binding metrics card
 * @param {string} bindingName - Name of the binding
 * @param {Object} binding - Binding metrics data
 * @param {number} seqNum - Sequence number of the binding
 * @returns {HTMLElement} The binding card element
 */
function createMetricsBindingCard(bindingName, binding, seqNum) {
    const template = elements.bindingMetricsTemplate.content.cloneNode(true);
    
    // Create sequence number badge and name container
    const nameContainer = document.createElement('div');
    nameContainer.className = 'binding-name-container';
    
    const seqBadge = document.createElement('div');
    seqBadge.className = 'binding-seq';
    seqBadge.textContent = seqNum;
    
    // Get the binding name element and replace it with container
    const nameElement = template.querySelector('.binding-name');
    const nameText = nameElement.textContent;
    nameElement.textContent = '';
    
    // Assemble components
    nameContainer.appendChild(seqBadge);
    nameContainer.appendChild(nameElement);
    
    // Replace the binding-name with the container
    const headerElement = template.querySelector('.binding-header');
    headerElement.insertBefore(nameContainer, headerElement.firstChild);
    
    // Set binding name
    nameElement.textContent = bindingName;
    
    // Set binding type
    template.querySelector('.binding-type').textContent = `Type: ${binding.binding_type}`;
    
    // Process source and target metrics
    processComponentMetrics(binding, template);
    
    return template;
}

/**
 * Process component metrics (source/target)
 * @param {Object} binding - Binding metrics data
 * @param {DocumentFragment} template - The binding card template
 */
function processComponentMetrics(binding, template) {
    // Combined metrics from source and target
    const metrics = {
        operational: {},
        performance: {},
        state: {},
        errors: {}
    };
    
    // Process source metrics
    if (binding.source) {
        processMetricsGroup(binding.source, metrics, 'Source');
    }
    
    // Process target metrics
    if (binding.target) {
        processMetricsGroup(binding.target, metrics, 'Target');
    }
    
    // Populate metrics in the template
    populateMetricsInTemplate(metrics, template);
}

/**
 * Process metrics from a component
 * @param {Object} component - Component metrics data
 * @param {Object} metrics - Combined metrics object
 * @param {string} prefix - Prefix for the metric name
 */
function processMetricsGroup(component, metrics, prefix) {
    // Process operational metrics
    if (component.operational) {
        Object.entries(component.operational).forEach(([key, value]) => {
            metrics.operational[`${prefix}: ${formatMetricName(key)}`] = formatMetricValue(value);
        });
    }
    
    // Process performance metrics
    if (component.performance) {
        Object.entries(component.performance).forEach(([key, value]) => {
            // Handle objects like histograms
            if (typeof value === 'object' && value !== null) {
                if (value.count) {
                    metrics.performance[`${prefix}: ${formatMetricName(key)} Count`] = value.count;
                }
                if (value.sum) {
                    metrics.performance[`${prefix}: ${formatMetricName(key)} Sum`] = formatMetricValue(value.sum);
                }
                if (value.percentiles) {
                    Object.entries(value.percentiles).forEach(([percentile, percentileValue]) => {
                        metrics.performance[`${prefix}: ${formatMetricName(key)} ${percentile.toUpperCase()}`] = formatMetricValue(percentileValue);
                    });
                }
            } else {
                metrics.performance[`${prefix}: ${formatMetricName(key)}`] = formatMetricValue(value);
            }
        });
    }
    
    // Process state metrics
    if (component.state) {
        Object.entries(component.state).forEach(([key, value]) => {
            metrics.state[`${prefix}: ${formatMetricName(key)}`] = formatMetricValue(value);
        });
    }
    
    // Process error metrics
    if (component.errors) {
        // Handle by_category
        if (component.errors.by_category) {
            Object.entries(component.errors.by_category).forEach(([category, count]) => {
                metrics.errors[`${prefix}: ${formatMetricName(category)} Errors`] = count;
            });
        }
        
        // Handle last error timestamp
        if (component.errors.last_error_timestamp) {
            const date = new Date(component.errors.last_error_timestamp * 1000);
            metrics.errors[`${prefix}: Last Error Time`] = date.toLocaleString();
        }
        
        // Handle last error message
        if (component.errors.last_error_message) {
            metrics.errors[`${prefix}: Last Error`] = component.errors.last_error_message;
        }
    }
}

/**
 * Populate metrics in the template
 * @param {Object} metrics - Combined metrics object
 * @param {DocumentFragment} template - The binding card template
 */
function populateMetricsInTemplate(metrics, template) {
    // Populate operational metrics
    populateMetricSection(
        template.querySelector('.operational-metrics'),
        metrics.operational
    );
    
    // Populate performance metrics
    populateMetricSection(
        template.querySelector('.performance-metrics'),
        metrics.performance
    );
    
    // Populate state metrics
    populateMetricSection(
        template.querySelector('.state-metrics'),
        metrics.state
    );
    
    // Populate error metrics
    populateMetricSection(
        template.querySelector('.error-metrics'),
        metrics.errors
    );
}

/**
 * Populate a metric section with metric items
 * @param {HTMLElement} container - The container element
 * @param {Object} metrics - Metrics data
 */
function populateMetricSection(container, metrics) {
    // Clear container
    container.innerHTML = '';
    
    if (Object.keys(metrics).length === 0) {
        const noData = document.createElement('div');
        noData.className = 'no-data';
        noData.textContent = 'No data available';
        container.appendChild(noData);
        return;
    }
    
    // Add each metric item
    Object.entries(metrics).forEach(([name, value]) => {
        const item = elements.metricItemTemplate.content.cloneNode(true);
        
        // Make the metric name bold
        const nameElement = item.querySelector('.metric-name');
        nameElement.className = 'metric-name detail-item-key';
        nameElement.textContent = name;
        
        item.querySelector('.metric-value').textContent = value;
        container.appendChild(item);
    });
}

/**
 * Format a metric name for display
 * @param {string} name - The raw metric name
 * @returns {string} Formatted metric name
 */
function formatMetricName(name) {
    // Handle variations of latency metrics
    if (name.toLowerCase().includes('ping') && name.toLowerCase().includes('latency') || 
        name.toLowerCase() === 'latency_msec') {
        return 'Latency (msec):';
    }
    
    return name
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
}

/**
 * Format a metric value for display
 * @param {any} value - The metric value
 * @returns {string} Formatted metric value
 */
function formatMetricValue(value) {
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
    return value;
}

/**
 * Show an error message in a container
 * @param {HTMLElement} container - The container element
 * @param {string} message - The error message
 */
function showError(container, message) {
    container.innerHTML = `
        <div class="error-message">
            <i class="fas fa-exclamation-circle"></i>
            <p>${message}</p>
        </div>
    `;
}

// Initialize the dashboard when the DOM is loaded
document.addEventListener('DOMContentLoaded', initDashboard); 