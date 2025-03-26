/**
 * IBM MQ - KubeMQ Dashboard
 * 
 * This script handles fetching data from the API and 
 * updating the dashboard with health and metrics information.
 */

// Dashboard state
const state = {
    interval: null,
    refreshRate: 5000, // ms
    lastRefreshTime: null,
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

// DOM Elements
let elements = {};

/**
 * Initialize element references
 */
function initElementReferences() {
    try {
        console.log('Initializing element references...');
        
        // Initialize by ID elements
        for (const [key, selector] of Object.entries(state.selectors.ids)) {
            elements[key] = getElement(`#${selector}`);
        }
        
        // Initialize tab elements
        elements.healthTab = getElement('#health-tab');
        elements.metricsTab = getElement('#metrics-tab');
        
        // Initialize panel elements
        elements.healthPanel = getElement('#health-panel');
        elements.metricsPanel = getElement('#metrics-panel');
        
        // Initialize container elements
        elements.healthBindingsContainer = getElement('#health-bindings-container');
        elements.metricsBindingsContainer = getElement('#metrics-bindings-container');
        
        // Initialize templates
        elements.bindingHealthTemplate = getElement('#binding-health-template');
        elements.bindingMetricsTemplate = getElement(state.selectors.classes.bindingMetricsTemplate);
        elements.metricItemTemplate = getElement(state.selectors.classes.metricItemTemplate);
        
        // Initialize status elements
        elements.healthStatusIndicator = getElement('#health-status-indicator');
        elements.healthyCount = getElement('#healthy-count');
        elements.unhealthyCount = getElement('#unhealthy-count');
        elements.totalBindings = getElement('#total-bindings');
        
        if (!elements.bindingHealthTemplate) {
            console.error('Binding health template not found');
        }
        
        if (!elements.bindingMetricsTemplate) {
            console.error('Binding metrics template not found');
        }
        
        if (!elements.metricItemTemplate) {
            console.error('Metric item template not found');
        }
        
        if (!elements.healthPanel) {
            console.error('Health panel not found');
        }
        
        if (!elements.metricsPanel) {
            console.error('Metrics panel not found');
        }
        
        // Log initialization status
        console.log('Dashboard element references initialized:', {
            healthTab: !!elements.healthTab,
            metricsTab: !!elements.metricsTab,
            healthPanel: !!elements.healthPanel,
            metricsPanel: !!elements.metricsPanel,
            healthBindingsContainer: !!elements.healthBindingsContainer, 
            metricsBindingsContainer: !!elements.metricsBindingsContainer,
            healthTemplate: !!elements.bindingHealthTemplate,
            metricsTemplate: !!elements.bindingMetricsTemplate,
            metricItemTemplate: !!elements.metricItemTemplate
        });
    } catch (error) {
        console.error('Error initializing element references:', error);
        showGlobalError('Failed to initialize dashboard elements');
    }
}

/**
 * Safe helper to get DOM elements
 * @param {string} selector - CSS selector
 * @param {Node} context - The parent element to search within
 * @returns {Element|null} - The element if found, null otherwise
 */
function getElement(selector, context = document) {
    try {
        return context.querySelector(selector);
    } catch (error) {
        console.error(`Error querying for selector "${selector}":`, error);
        return null;
    }
}

/**
 * Initialize the dashboard
 */
function initDashboard() {
    try {
        console.log('Initializing dashboard...');
        
        // Initialize DOM element references
        initElementReferences();
        
        // Set current year for footer if it exists
        const currentYearElement = getElement('#current-year');
        if (currentYearElement) {
            currentYearElement.textContent = new Date().getFullYear();
        }
        
        // Setup event listeners
        setupEventListeners();
        
        // Set dashboard version if element exists
        const versionElement = getElement('#dashboard-version');
        if (versionElement) {
            versionElement.textContent = '1.2.0'; // Update version number when changing code
        }
        
        // Set app title if it exists
        const appTitle = getElement('#app-title');
        if (appTitle && !appTitle.textContent) {
            appTitle.textContent = 'IBM MQ - KubeMQ Dashboard';
        }
        
        // Initialize refresh interval based on settings
        let refreshInterval = 5000; // Default: 5 seconds
        
        // Try to get refresh interval from select element
        const refreshSelect = getElement('#auto-refresh');
        if (refreshSelect) {
            try {
                refreshInterval = parseInt(refreshSelect.value) || refreshInterval;
            } catch (error) {
                console.warn('Error parsing refresh interval, using default:', error);
            }
        }
        
        // Check if there's a refresh interval display element
        const refreshIntervalDisplay = getElement('#refresh-interval-display');
        if (refreshIntervalDisplay) {
            const seconds = Math.round(refreshInterval / 1000);
            refreshIntervalDisplay.textContent = seconds > 0 ? `${seconds}s` : 'Off';
        }
        
        // Set initial auto-refresh
        if (refreshInterval > 0) {
            setAutoRefresh(refreshInterval);
        }
        
        // Initial data load
        refreshData();
        
        console.log('Dashboard initialization complete');
    } catch (error) {
        console.error('Error initializing dashboard:', error);
        
        // Try to display error in a visible element
        const dashboardContainer = document.querySelector('.dashboard-container') || document.body;
        if (dashboardContainer) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'critical-error';
            errorDiv.innerHTML = `
                <h3>Dashboard Initialization Error</h3>
                <p>There was an error initializing the dashboard:</p>
                <code>${error.message || 'Unknown error'}</code>
                <p>Please try refreshing the page. If the problem persists, contact support.</p>
                <button onclick="location.reload()">Refresh Page</button>
            `;
            
            // Style the error message
            Object.assign(errorDiv.style, {
                margin: '20px auto',
                maxWidth: '600px',
                padding: '20px',
                backgroundColor: '#f8d7da',
                color: '#721c24',
                borderRadius: '4px',
                textAlign: 'center',
                boxShadow: '0 2px 10px rgba(0,0,0,0.2)'
            });
            
            // Try to insert at the beginning of the container
            try {
                dashboardContainer.insertBefore(errorDiv, dashboardContainer.firstChild);
            } catch (insertError) {
                // If insertion fails, try to append it
                try {
                    dashboardContainer.appendChild(errorDiv);
                } catch (appendError) {
                    // Last resort - try to add to body
                    document.body.appendChild(errorDiv);
                }
            }
        }
    }
}

/**
 * Setup event listeners for the dashboard
 */
function setupEventListeners() {
    try {
        // TAB NAVIGATION
        // Tab switching for health tab
        const healthTab = getElement('#health-tab');
        if (healthTab) {
            healthTab.addEventListener('click', (e) => {
                e.preventDefault();
                setActiveTab('health');
            });
        }
        
        // Tab switching for metrics tab
        const metricsTab = getElement('#metrics-tab');
        if (metricsTab) {
            metricsTab.addEventListener('click', (e) => {
                e.preventDefault();
                setActiveTab('metrics');
            });
        }
        
        // REFRESH CONTROLS
        // Manual refresh button
        const refreshButton = getElement('#refresh-btn') || getElement('#refresh-button');
        if (refreshButton) {
            refreshButton.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Add loading class to button
                refreshButton.classList.add('loading');
                
                // Remove loading class after refresh is complete (or after timeout)
                const removeLoading = () => refreshButton.classList.remove('loading');
                setTimeout(removeLoading, 1000);
                
                // Refresh data
                refreshData();
            });
        }
        
        // Auto-refresh interval selector
        const autoRefreshSelect = getElement('#auto-refresh');
        if (autoRefreshSelect) {
            autoRefreshSelect.addEventListener('change', () => {
                try {
                    const interval = parseInt(autoRefreshSelect.value) || 0;
                    setAutoRefresh(interval);
                    
                    // Update display if it exists
                    const refreshIntervalDisplay = getElement('#refresh-interval-display');
                    if (refreshIntervalDisplay) {
                        const seconds = Math.round(interval / 1000);
                        refreshIntervalDisplay.textContent = seconds > 0 ? `${seconds}s` : 'Off';
                    }
                } catch (error) {
                    console.error('Error setting auto-refresh interval:', error);
                }
            });
        }
        
        // Set up expandable sections
        setupExpandableSections();
        
        // Set up theme toggle if it exists
        setupThemeToggle();
    } catch (error) {
        console.error('Error setting up event listeners:', error);
    }
}

/**
 * Setup expandable sections in the dashboard
 */
function setupExpandableSections() {
    try {
        // Find all expandable section headers
        const expandableSections = document.querySelectorAll('.expandable-section-header');
        
        expandableSections.forEach(header => {
            // Find the content section
            const content = header.nextElementSibling;
            if (!content) return;
            
            // Create an indicator element if it doesn't exist
            let indicator = header.querySelector('.expand-indicator');
            if (!indicator) {
                indicator = document.createElement('span');
                indicator.className = 'expand-indicator';
                indicator.textContent = '+';
                header.appendChild(indicator);
            }
            
            // Set initial state
            const isExpanded = content.classList.contains('expanded');
            content.style.display = isExpanded ? 'block' : 'none';
            indicator.textContent = isExpanded ? '−' : '+';
            
            // Add click event
            header.addEventListener('click', () => {
                // Toggle expanded state
                const isNowExpanded = content.style.display !== 'block';
                content.style.display = isNowExpanded ? 'block' : 'none';
                indicator.textContent = isNowExpanded ? '−' : '+';
                content.classList.toggle('expanded', isNowExpanded);
            });
        });
    } catch (error) {
        console.error('Error setting up expandable sections:', error);
    }
}

/**
 * Setup theme toggle if it exists in the DOM
 */
function setupThemeToggle() {
    try {
        const themeToggle = getElement('#theme-toggle');
        if (!themeToggle) return;
        
        // Check for saved theme preference
        const savedTheme = localStorage.getItem('dashboard-theme');
        if (savedTheme) {
            document.body.classList.toggle('dark-theme', savedTheme === 'dark');
            themeToggle.checked = savedTheme === 'dark';
        }
        
        // Add event listener for theme toggle
        themeToggle.addEventListener('change', () => {
            const isDarkTheme = themeToggle.checked;
            document.body.classList.toggle('dark-theme', isDarkTheme);
            localStorage.setItem('dashboard-theme', isDarkTheme ? 'dark' : 'light');
        });
    } catch (error) {
        console.error('Error setting up theme toggle:', error);
    }
}

/**
 * Set the active tab
 * @param {string} tabName - The name of the tab to activate
 */
function setActiveTab(tabName) {
    try {
        console.log(`Setting active tab to: ${tabName}`);
        state.activeTab = tabName;
        
        // Get tab elements if not already cached
        const healthTab = elements.healthTab || getElement('#health-tab');
        const metricsTab = elements.metricsTab || getElement('#metrics-tab');
        const healthPanel = elements.healthPanel || getElement('#health-panel');
        const metricsPanel = elements.metricsPanel || getElement('#metrics-panel');
        
        // Cache elements for future use
        if (!elements.healthTab) elements.healthTab = healthTab;
        if (!elements.metricsTab) elements.metricsTab = metricsTab;
        if (!elements.healthPanel) elements.healthPanel = healthPanel;
        if (!elements.metricsPanel) elements.metricsPanel = metricsPanel;
        
        // Update tab buttons
        if (healthTab) {
            healthTab.classList.toggle('active', tabName === 'health');
        }
        
        if (metricsTab) {
            metricsTab.classList.toggle('active', tabName === 'metrics');
        }
        
        // Update panels
        if (healthPanel) {
            healthPanel.classList.toggle('active', tabName === 'health');
            healthPanel.style.display = tabName === 'health' ? 'block' : 'none';
        }
        
        if (metricsPanel) {
            metricsPanel.classList.toggle('active', tabName === 'metrics');
            metricsPanel.style.display = tabName === 'metrics' ? 'block' : 'none';
        }
        
        console.log(`Tab set to: ${tabName}, panels updated`);
    } catch (error) {
        console.error('Error setting active tab:', error);
    }
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
    try {
        // Show loading indicator if it exists
        if (elements.refreshIndicator) {
            elements.refreshIndicator.classList.add('loading');
        }
        
        // Fetch health data
        fetchHealthData();
        
        // Fetch metrics data
        fetchMetricsData();
        
        // Update last refreshed time
        state.lastRefreshTime = new Date();
        
        if (elements.lastUpdated) {
            elements.lastUpdated.textContent = state.lastRefreshTime.toLocaleTimeString();
        }
        
        // Hide loading indicator after a short delay
        setTimeout(() => {
            if (elements.refreshIndicator) {
                elements.refreshIndicator.classList.remove('loading');
            }
        }, 500);
    } catch (error) {
        console.error('Error refreshing data:', error);
        
        // Hide loading indicator if there was an error
        if (elements.refreshIndicator) {
            elements.refreshIndicator.classList.remove('loading');
        }
        
        // Show error message
        showGlobalError('Failed to refresh dashboard data');
    }
}

/**
 * Show a global error message
 * @param {string} message - Error message to display
 */
function showGlobalError(message) {
    try {
        // Try to show error in error container first
        if (elements.errorContainer) {
            elements.errorContainer.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>${message}</p>
                </div>
            `;
            elements.errorContainer.style.display = 'block';
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                elements.errorContainer.style.display = 'none';
            }, 5000);
            return;
        }
        
        // Fallback: create temporary floating error
        const errorDiv = document.createElement('div');
        errorDiv.className = 'floating-error';
        errorDiv.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-circle"></i>
                <p>${message}</p>
                <button class="close-btn">&times;</button>
            </div>
        `;
        
        // Add close button functionality
        const closeBtn = errorDiv.querySelector('.close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                document.body.removeChild(errorDiv);
            });
        }
        
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
 * Show an error message in a specific container
 * @param {HTMLElement} container - The container element
 * @param {string} message - The error message
 */
function showError(container, message) {
    try {
        // Check if container is valid
        if (!container || typeof container.innerHTML !== 'string') {
            console.error('Invalid container for error message:', container);
            showGlobalError(message);
            return;
        }
        
        // Show error in container
        container.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-circle"></i>
                <p>${message}</p>
            </div>
        `;
    } catch (error) {
        console.error('Error showing error message:', error);
        showGlobalError(message);
    }
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
        console.log('Fetching metrics data...');
        
        // Show loading indicator in the metrics container
        const metricsContainer = elements.metricsBindingsContainer || 
                                 getElement('#metrics-bindings-container');
        
        if (metricsContainer) {
            metricsContainer.innerHTML = `
                <div class="loading-indicator">
                    <div class="spinner"></div>
                    <p>Loading metrics data...</p>
                </div>
            `;
        }
        
        // Fetch metrics data from API
        const response = await fetch('/metrics/');
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        // Parse JSON response
        const data = await response.json();
        console.log('Metrics data received:', data ? 'yes' : 'no');
        
        // Check if data is valid
        if (data && data.data) {
            console.log('Updating metrics with data:', {
                hasSystem: !!data.data.system,
                bindingsCount: data.data.bindings ? Object.keys(data.data.bindings).length : 0
            });
            updateMetricsData(data.data);
        } else {
            throw new Error('Invalid metrics data format received');
        }
    } catch (error) {
        console.error('Error fetching metrics data:', error);
        
        // Get metrics container for error display
        const container = elements.metricsBindingsContainer || 
                          getElement('#metrics-bindings-container');
        
        if (container) {
            showError(container, `Failed to load metrics data: ${error.message}`);
        } else {
            showGlobalError(`Failed to load metrics data: ${error.message}`);
        }
    }
}

/**
 * Update the health dashboard with new data
 * @param {Object} healthData - Health data from the API
 */
function updateHealthData(healthData) {
    try {
        // Validate health data
        if (!healthData) {
            throw new Error('No health data available');
        }
        
        // Get the health bindings container
        const container = elements.bindings || 
                          document.getElementById('health-bindings-container') || 
                          document.querySelector('.health-bindings-container');
        
        if (!container) {
            throw new Error('Health bindings container not found');
        }
        
        // Clear existing content
        container.innerHTML = '';
        
        // Update overall status indicator if it exists
        if (elements.healthStatusIndicator) {
            try {
                const overallStatus = healthData.overall_status || 'unknown';
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
        if (healthData.bindings) {
            try {
                const bindingsData = healthData.bindings;
                const totalBindings = Object.keys(bindingsData).length;
                
                // Update binding count if element exists
                if (elements.bindingCount) {
                    elements.bindingCount.textContent = totalBindings;
                }
                
                // Create binding cards
                Object.entries(bindingsData).forEach(([bindingName, binding], index) => {
                    try {
                        // Count statuses
                        if (binding.status === 'healthy') healthyCnt++;
                        else if (binding.status === 'unhealthy') unhealthyCnt++;
                        
                        // Create and append binding card
                        const bindingCard = createHealthBindingCard(bindingName, binding, index + 1);
                        if (bindingCard) {
                            container.appendChild(bindingCard);
                        }
                    } catch (bindingError) {
                        console.error(`Error processing binding ${bindingName}:`, bindingError);
                        // Create error card for this binding
                        const errorCard = createErrorElement(`Error displaying binding: ${bindingName}`);
                        container.appendChild(errorCard);
                    }
                });
                
                // Show no bindings message if no bindings were processed
                if (container.children.length === 0) {
                    const noBindings = document.createElement('div');
                    noBindings.className = 'no-data';
                    noBindings.textContent = 'No bindings available';
                    container.appendChild(noBindings);
                }
            } catch (bindingsError) {
                console.error('Error processing bindings:', bindingsError);
                showError(container, 'Error processing bindings data');
            }
        } else {
            // No bindings data
            const noBindings = document.createElement('div');
            noBindings.className = 'no-data';
            noBindings.textContent = 'No bindings available';
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
                elements.totalBindings.textContent = Object.keys(healthData.bindings || {}).length;
            }
        } catch (statsError) {
            console.error('Error updating health statistics:', statsError);
        }
    } catch (error) {
        console.error('Error updating health data:', error);
        
        // Try to show error in the container
        try {
            const container = elements.bindings || 
                              document.getElementById('health-bindings-container') || 
                              document.querySelector('.health-bindings-container');
            
            if (container) {
                showError(container, 'Failed to update health data');
            } else {
                showGlobalError('Failed to update health data');
            }
        } catch (displayError) {
            console.error('Error displaying health error:', displayError);
            showGlobalError('Failed to update health data');
        }
    }
}

/**
 * Create a binding health card
 * @param {string} bindingName - Name of the binding
 * @param {Object} binding - Binding health data
 * @param {number} seqNum - Sequence number of the binding
 * @returns {HTMLElement} The binding card element
 */
function createHealthBindingCard(bindingName, binding, seqNum) {
    try {
        // Check if template exists
        if (!elements.bindingHealthTemplate) {
            console.warn('Binding health template not found, using fallback');
            return createFallbackHealthBindingCard(bindingName, binding, seqNum);
        }
        
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
    } catch (error) {
        console.error(`Error creating health card for binding ${bindingName}:`, error);
        return createFallbackHealthBindingCard(bindingName, binding, seqNum);
    }
}

/**
 * Create a fallback health binding card when template is not available
 * @param {string} bindingName - Name of the binding
 * @param {Object} binding - Binding health data 
 * @param {number} seqNum - Sequence number of the binding
 * @returns {HTMLElement} A basic binding health card
 */
function createFallbackHealthBindingCard(bindingName, binding, seqNum) {
    try {
        // Create main card container
        const cardDiv = document.createElement('div');
        cardDiv.className = 'binding-card';
        
        // Create header
        const header = document.createElement('div');
        header.className = 'binding-header';
        
        // Create name container with sequence badge
        const nameContainer = document.createElement('div');
        nameContainer.className = 'binding-name-container';
        
        const seqBadge = document.createElement('div');
        seqBadge.className = 'binding-seq';
        seqBadge.textContent = seqNum;
        
        const nameElement = document.createElement('h3');
        nameElement.className = 'binding-name';
        nameElement.textContent = bindingName;
        
        nameContainer.appendChild(seqBadge);
        nameContainer.appendChild(nameElement);
        
        // Create status badge
        const statusElement = document.createElement('div');
        statusElement.className = `binding-status ${binding.status || 'unknown'}`;
        statusElement.textContent = (binding.status || 'UNKNOWN').toUpperCase();
        
        // Create binding type
        const typeElement = document.createElement('div');
        typeElement.className = 'binding-type';
        typeElement.textContent = `Type: ${binding.binding_type || 'Unknown'}`;
        
        // Assemble header
        header.appendChild(nameContainer);
        header.appendChild(statusElement);
        header.appendChild(typeElement);
        cardDiv.appendChild(header);
        
        // Create card body
        const body = document.createElement('div');
        body.className = 'binding-body';
        
        // Add source component if available
        if (binding.source) {
            const sourceSection = createFallbackComponentSection(binding.source, 'Source');
            body.appendChild(sourceSection);
        }
        
        // Add target component if available
        if (binding.target) {
            const targetSection = createFallbackComponentSection(binding.target, 'Target');
            body.appendChild(targetSection);
        }
        
        // Add body to card
        cardDiv.appendChild(body);
        
        return cardDiv;
    } catch (error) {
        console.error(`Error creating fallback health card for ${bindingName}:`, error);
        return createErrorElement(`Error displaying binding: ${bindingName}`);
    }
}

/**
 * Create a fallback component section for health binding card
 * @param {Object} component - Component data (source or target)
 * @param {string} type - Component type ("Source" or "Target")
 * @returns {HTMLElement} Component section element
 */
function createFallbackComponentSection(component, type) {
    const section = document.createElement('div');
    section.className = `component ${type.toLowerCase()}`;
    
    // Create header with status
    const header = document.createElement('div');
    header.className = 'component-header';
    
    const title = document.createElement('h4');
    
    const statusBadge = document.createElement('span');
    statusBadge.className = `component-status ${component.status || 'unknown'}`;
    statusBadge.textContent = (component.status || 'UNKNOWN').toUpperCase();
    
    title.textContent = `${type}: `;
    title.appendChild(statusBadge);
    
    header.appendChild(title);
    section.appendChild(header);
    
    // Create details container
    const details = document.createElement('div');
    details.className = 'component-details';
    
    // Add component details
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
        
        details.appendChild(detailsList);
    }
    
    // Add component errors
    if (component.errors && Object.keys(component.errors).length > 0) {
        const errorsList = document.createElement('div');
        errorsList.className = 'error-list';
        
        Object.entries(component.errors).forEach(([key, value]) => {
            const errorItem = document.createElement('div');
            errorItem.className = 'error-item';
            errorItem.textContent = `${key}: ${value}`;
            errorsList.appendChild(errorItem);
        });
        
        details.appendChild(errorsList);
    }
    
    // Add details to section
    section.appendChild(details);
    
    return section;
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
    try {
        console.log('Updating metrics display...');
        
        // Validate metrics data
        if (!metricsData) {
            throw new Error('No metrics data available');
        }
        
        // Get the metrics bindings container
        const container = elements.metricsBindingsContainer || 
                          getElement('#metrics-bindings-container');
        
        if (!container) {
            throw new Error('Metrics bindings container not found');
        }
        
        // Clear existing content
        container.innerHTML = '';
        
        // Create system-level metrics card if available
        if (metricsData.system) {
            try {
                console.log('Processing system metrics');
                
                // Clone the system data to avoid modifying the original
                const systemData = JSON.parse(JSON.stringify(metricsData.system));
                
                // Create and append system metrics card
                const systemCard = createSystemMetricsCard(systemData);
                if (systemCard) {
                    container.appendChild(systemCard);
                    
                    // Add a divider if we have system metrics and will show bindings
                    if (metricsData.bindings && Object.keys(metricsData.bindings).length > 0) {
                        const divider = document.createElement('div');
                        divider.className = 'section-divider';
                        divider.innerHTML = '<h3>Binding Metrics</h3>';
                        container.appendChild(divider);
                    }
                } else {
                    console.warn('System card creation returned null');
                }
            } catch (systemError) {
                console.error('Error creating system metrics card:', systemError);
                const errorCard = createErrorElement(`Error displaying system metrics: ${systemError.message}`);
                container.appendChild(errorCard);
            }
        } else {
            console.log('No system metrics available');
        }
        
        // Process bindings if available
        if (metricsData.bindings) {
            try {
                console.log('Processing binding metrics');
                const bindingsData = metricsData.bindings;
                let bindingsProcessed = 0;
                
                // Create binding cards
                Object.entries(bindingsData).forEach(([bindingName, binding], index) => {
                    try {
                        // Create and append binding card
                        const bindingCard = createMetricsBindingCard(bindingName, binding, index + 1);
                        if (bindingCard) {
                            container.appendChild(bindingCard);
                            bindingsProcessed++;
                        }
                    } catch (bindingError) {
                        console.error(`Error processing metrics for binding ${bindingName}:`, bindingError);
                        // Create error card for this binding
                        const errorCard = createErrorElement(`Error displaying metrics for binding: ${bindingName}`);
                        container.appendChild(errorCard);
                    }
                });
                
                // Show no bindings message if no bindings were processed and no system metrics
                if (container.children.length === 0 || 
                    (container.children.length === 1 && container.querySelector('.section-divider'))) {
                    const noBindings = document.createElement('div');
                    noBindings.className = 'no-data';
                    noBindings.textContent = 'No binding metrics available';
                    container.appendChild(noBindings);
                }
            } catch (bindingsError) {
                console.error('Error processing binding metrics:', bindingsError);
                showError(container, 'Error processing binding metrics data');
            }
        } else if (!metricsData.system) {
            // No metrics data at all
            const noMetrics = document.createElement('div');
            noMetrics.className = 'no-data';
            noMetrics.textContent = 'No metrics data available';
            container.appendChild(noMetrics);
        }
        
        console.log('Metrics update complete');
    } catch (error) {
        console.error('Error updating metrics data:', error);
        
        // Try to show error in the container
        try {
            const container = elements.metricsBindingsContainer || 
                              getElement('#metrics-bindings-container');
            
            if (container) {
                showError(container, `Failed to update metrics data: ${error.message}`);
            } else {
                showGlobalError(`Failed to update metrics data: ${error.message}`);
            }
        } catch (displayError) {
            console.error('Error displaying metrics error:', displayError);
            showGlobalError('Failed to update metrics data');
        }
    }
}

/**
 * Create a system-level metrics card
 * @param {Object} systemData - System metrics data
 * @returns {HTMLElement} The system metrics card element
 */
function createSystemMetricsCard(systemData) {
    console.log('Creating system metrics card with data:', Object.keys(systemData));
    
    if (!systemData) {
        console.warn('No system metrics data provided');
        return createErrorElement('No system metrics data available');
    }
    
    try {
        // Check if template exists
        if (!elements.bindingMetricsTemplate) {
            console.warn('Binding metrics template not found, using fallback');
            return createFallbackSystemCard(systemData);
        }
        
        const template = elements.bindingMetricsTemplate.content.cloneNode(true);
        
        // Set system title and style
        const nameElement = getElement(state.selectors.classes.bindingName, template);
        if (nameElement) {
            nameElement.textContent = 'System Overview';
            nameElement.classList.add('system-title');
        } else {
            console.warn('Could not find binding name element in template');
        }
        
        // Remove binding type display
        const typeElement = getElement(state.selectors.classes.bindingType, template);
        if (typeElement) {
            typeElement.style.display = 'none';
        } else {
            console.warn('Could not find binding type element in template');
        }
        
        // Find the metrics container
        const container = getElement(state.selectors.classes.metricsContainer, template);
        if (!container) {
            console.error('Metrics container not found in template');
            throw new Error('Metrics container not found in template');
        }
        
        // Clear existing metric sections
        container.innerHTML = '';
        
        // Create a single section for all system metrics
        const sectionDiv = document.createElement('div');
        sectionDiv.className = 'metrics-section system-metrics-section';
        
        const metricsContainer = document.createElement('div');
        metricsContainer.className = 'metrics-list';
        
        // Log the metrics we're going to display
        console.log('System metrics to display:', 
            Object.entries(systemData)
                .filter(([key, value]) => 
                    !key.endsWith('timestamp') && 
                    key !== 'bindings' && 
                    value !== null)
                .map(([key]) => key)
        );
        
        // Process metrics manually if needed
        if (Object.keys(systemData).length === 0) {
            console.warn('System data has no keys');
            // Create a fallback metric to show something
            const emptyMetric = createMetricItem('Status', 'System running');
            metricsContainer.appendChild(emptyMetric);
        } else {
            // Process metrics in batch for better performance
            Object.entries(systemData).forEach(([key, value]) => {
                // Skip timestamps, bindings, and null values
                if (key.endsWith('timestamp') || key === 'bindings' || value === null) {
                    return;
                }
                
                // Handle timestamps specially
                if (key.includes('time') && systemData[key.replace('_time', '_timestamp')]) {
                    value = formatTimestamp(systemData[key.replace('_time', '_timestamp')]);
                }
                
                // Create and add metric item
                const metricItem = createMetricItem(formatMetricName(key), value);
                metricsContainer.appendChild(metricItem);
            });
        }
        
        // Only show the section if it has metrics
        if (metricsContainer.children.length > 0) {
            sectionDiv.appendChild(metricsContainer);
            container.appendChild(sectionDiv);
        } else {
            console.warn('No metrics to display for system');
            const noData = document.createElement('div');
            noData.className = 'no-data';
            noData.textContent = 'No system metrics available';
            container.appendChild(noData);
        }
        
        // Add system card class
        const card = getElement(state.selectors.classes.bindingCard, template);
        if (card) {
            card.classList.add('system-metrics-card');
        } else {
            console.warn('Could not find binding card element in template');
        }
        
        console.log('System metrics card created successfully');
        return template;
    } catch (error) {
        console.error('Error creating system metrics card:', error);
        return createErrorElement(`Error loading system metrics: ${error.message}`);
    }
}

/**
 * Create a fallback system card when template is not available
 * @param {Object} systemData - System metrics data
 * @returns {HTMLElement} A basic system metrics card
 */
function createFallbackSystemCard(systemData) {
    try {
        const cardDiv = document.createElement('div');
        cardDiv.className = 'binding-card system-metrics-card';
        
        const header = document.createElement('div');
        header.className = 'binding-header';
        
        const title = document.createElement('h3');
        title.className = 'binding-name system-title';
        title.textContent = 'System Overview';
        
        header.appendChild(title);
        cardDiv.appendChild(header);
        
        const body = document.createElement('div');
        body.className = 'binding-body';
        
        const metricsContainer = document.createElement('div');
        metricsContainer.className = 'metrics-container';
        
        const section = document.createElement('div');
        section.className = 'metrics-section system-metrics-section';
        
        const list = document.createElement('div');
        list.className = 'metrics-list';
        
        // Add metrics to the list
        Object.entries(systemData).forEach(([key, value]) => {
            if (key.endsWith('timestamp') || key === 'bindings' || value === null) {
                return;
            }
            
            if (key.includes('time') && systemData[key.replace('_time', '_timestamp')]) {
                value = formatTimestamp(systemData[key.replace('_time', '_timestamp')]);
            }
            
            const item = document.createElement('div');
            item.className = 'metric-item';
            
            const nameSpan = document.createElement('span');
            nameSpan.className = 'metric-name detail-item-key';
            nameSpan.textContent = formatMetricName(key);
            
            const valueSpan = document.createElement('span');
            valueSpan.className = 'metric-value';
            valueSpan.textContent = typeof value === 'number' ? formatMetricValue(value) : value;
            
            item.appendChild(nameSpan);
            item.appendChild(valueSpan);
            list.appendChild(item);
        });
        
        section.appendChild(list);
        metricsContainer.appendChild(section);
        body.appendChild(metricsContainer);
        cardDiv.appendChild(body);
        
        return cardDiv;
    } catch (error) {
        console.error('Error creating fallback system card:', error);
        return createErrorElement('Error creating system metrics');
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
    if (!binding) {
        return createErrorElement(`No metrics data for binding: ${bindingName}`);
    }
    
    try {
        // Check if template exists
        if (!elements.bindingMetricsTemplate) {
            return createFallbackBindingCard(bindingName, binding, seqNum);
        }
        
        const template = elements.bindingMetricsTemplate.content.cloneNode(true);
        
        // Create sequence number badge and name container
        const nameContainer = document.createElement('div');
        nameContainer.className = 'binding-name-container';
        
        const seqBadge = document.createElement('div');
        seqBadge.className = 'binding-seq';
        seqBadge.textContent = seqNum;
        
        // Get the binding name element
        const nameElement = getElement(state.selectors.classes.bindingName, template);
        if (nameElement) {
            nameElement.textContent = '';
            
            // Assemble components
            nameContainer.appendChild(seqBadge);
            nameContainer.appendChild(nameElement);
            
            // Replace the binding-name with the container
            const headerElement = getElement(state.selectors.classes.bindingHeader, template);
            if (headerElement) {
                headerElement.insertBefore(nameContainer, headerElement.firstChild);
            }
            
            // Set binding name
            nameElement.textContent = bindingName;
        }
        
        // Find the metrics container
        const container = getElement(state.selectors.classes.metricsContainer, template);
        if (!container) {
            throw new Error('Metrics container not found in template');
        }
        
        // Clear existing metric sections
        container.innerHTML = '';
        
        // Create summary section for binding metrics
        createBindingSummarySection(binding, container);
        
        // Create source component section
        if (binding.components && binding.components.source) {
            createComponentSection(binding.components.source, container, 'Source');
        }
        
        // Create target component section
        if (binding.components && binding.components.target) {
            createComponentSection(binding.components.target, container, 'Target');
        }
        
        return template;
    } catch (error) {
        console.error(`Error creating metrics card for binding ${bindingName}:`, error);
        return createErrorElement(`Error loading metrics for binding: ${bindingName}`);
    }
}

/**
 * Create a binding summary section
 * @param {Object} binding - Binding metrics data
 * @param {HTMLElement} container - Container to append to
 */
function createBindingSummarySection(binding, container) {
    // Create section container
    const sectionDiv = document.createElement('div');
    sectionDiv.className = 'metrics-section binding-summary-section';
    
    // Create section header
    const headerDiv = document.createElement('div');
    headerDiv.className = 'section-header';
    
    const headerTitle = document.createElement('h4');
    headerTitle.textContent = 'Binding Summary';
    headerDiv.appendChild(headerTitle);
    sectionDiv.appendChild(headerDiv);
    
    // Create metrics list
    const metricsContainer = document.createElement('div');
    metricsContainer.className = 'metrics-list';
    
    // Process metrics in batch for better performance
    const metricsFragment = batchProcessMetrics(
        binding,
        // Filter function
        (key, value) => {
            return key !== 'components' && 
                   key !== 'name' && 
                   !key.endsWith('timestamp') && 
                   value !== null;
        },
        // Transform function
        (key, value, data) => {
            if (key.includes('time') && data[key.replace('_time', '_timestamp')]) {
                return formatTimestamp(data[key.replace('_time', '_timestamp')]);
            }
            return value;
        }
    );
    
    // Add metrics to container
    metricsContainer.appendChild(metricsFragment);
    
    // Only show the section if it has metrics
    if (metricsContainer.children.length > 0) {
        sectionDiv.appendChild(metricsContainer);
        container.appendChild(sectionDiv);
    }
}

/**
 * Create a component metrics section
 * @param {Object} component - Component metrics data
 * @param {HTMLElement} container - Container to append to
 * @param {string} prefix - Component prefix (Source/Target)
 */
function createComponentSection(component, container, prefix) {
    if (!component) {
        return;
    }
    
    // Create section container
    const sectionDiv = document.createElement('div');
    sectionDiv.className = `metrics-section ${prefix.toLowerCase()}-component-section`;
    
    // Create section header
    const headerDiv = document.createElement('div');
    headerDiv.className = 'section-header';
    
    const headerTitle = document.createElement('h4');
    headerTitle.textContent = `${prefix}: ${component.type || 'Unknown'}`;
    headerDiv.appendChild(headerTitle);
    sectionDiv.appendChild(headerDiv);
    
    // Create metrics list
    const metricsContainer = document.createElement('div');
    metricsContainer.className = 'metrics-list';
    
    // Process metrics in batch for better performance
    const metricsFragment = batchProcessMetrics(
        component,
        // Filter function
        (key, value) => {
            return key !== 'name' && 
                   key !== 'type' && 
                   !key.endsWith('timestamp') && 
                   value !== null;
        },
        // Transform function
        (key, value, data) => {
            if (key.includes('time') && data[key.replace('_time', '_timestamp')]) {
                return formatTimestamp(data[key.replace('_time', '_timestamp')]);
            }
            return value;
        }
    );
    
    // Add metrics to container
    metricsContainer.appendChild(metricsFragment);
    
    // Only show the section if it has metrics
    if (metricsContainer.children.length > 0) {
        sectionDiv.appendChild(metricsContainer);
        container.appendChild(sectionDiv);
    }
}

/**
 * Create a fallback metrics section for when templates are not available
 * @param {Object} data - The metrics data
 * @param {string} title - Section title
 * @param {string} className - Additional class name for the section
 * @param {Function} filterFn - Function to filter metrics
 * @returns {HTMLElement|null} - The metrics section or null if no metrics
 */
function createFallbackSection(data, title, className, filterFn) {
    if (!data) return null;
    
    const section = document.createElement('div');
    section.className = `metrics-section ${className}`;
    
    const header = document.createElement('div');
    header.className = 'section-header';
    
    const headerTitle = document.createElement('h4');
    headerTitle.textContent = title;
    
    header.appendChild(headerTitle);
    section.appendChild(header);
    
    const list = document.createElement('div');
    list.className = 'metrics-list';
    
    let hasMetrics = false;
    
    // Add metrics to the list
    Object.entries(data).forEach(([key, value]) => {
        if (!filterFn(key, value) || value === null) {
            return;
        }
        
        hasMetrics = true;
        
        // Format timestamp metrics in real-time if raw timestamp is available
        if (key.includes('time')) {
            const rawTimestampKey = key.replace('_time', '_timestamp');
            if (data[rawTimestampKey]) {
                value = formatTimestamp(data[rawTimestampKey]);
            }
        }
        
        const item = document.createElement('div');
        item.className = 'metric-item';
        
        const nameSpan = document.createElement('span');
        nameSpan.className = 'metric-name detail-item-key';
        nameSpan.textContent = formatMetricName(key);
        
        const valueSpan = document.createElement('span');
        valueSpan.className = 'metric-value';
        valueSpan.textContent = typeof value === 'number' ? formatMetricValue(value) : value;
        
        item.appendChild(nameSpan);
        item.appendChild(valueSpan);
        list.appendChild(item);
    });
    
    if (hasMetrics) {
        section.appendChild(list);
        return section;
    }
    
    return null;
}

/**
 * Create an error element
 * @param {string} message - Error message
 * @returns {HTMLElement} Error element
 */
function createErrorElement(message) {
    const errorElement = document.createElement('div');
    errorElement.className = 'error-message';
    errorElement.innerHTML = `<i class="fas fa-exclamation-circle"></i><p>${message}</p>`;
    return errorElement;
}

/**
 * Helper function to batch process metrics for better performance
 * @param {Object} data - The metrics data object
 * @param {Function} filterFn - A function that returns true if the metric should be included
 * @param {Function} transformFn - A function to transform the metric value if needed
 * @returns {DocumentFragment} Fragment with all metric items
 */
function batchProcessMetrics(data, filterFn, transformFn) {
    // Create a document fragment for better performance
    const fragment = document.createDocumentFragment();
    
    // Process all metrics
    Object.entries(data).forEach(([key, value]) => {
        // Skip filtered metrics
        if (!filterFn(key, value)) {
            return;
        }
        
        // Transform value if needed
        if (transformFn) {
            value = transformFn(key, value, data);
        }
        
        try {
            // Create metric item - use template if available
            let item;
            if (elements.metricItemTemplate) {
                item = elements.metricItemTemplate.content.cloneNode(true);
                
                // Format the metric name
                const nameElement = getElement('.metric-name', item);
                if (nameElement) {
                    nameElement.className = 'metric-name detail-item-key';
                    nameElement.textContent = formatMetricName(key);
                }
                
                // Format the metric value
                const valueElement = getElement('.metric-value', item);
                if (valueElement) {
                    valueElement.textContent = typeof value === 'number' ? 
                        formatMetricValue(value) : value;
                }
            } else {
                // Fallback if template is not available
                item = document.createElement('div');
                item.className = 'metric-item';
                
                const nameSpan = document.createElement('span');
                nameSpan.className = 'metric-name detail-item-key';
                nameSpan.textContent = formatMetricName(key);
                
                const valueSpan = document.createElement('span');
                valueSpan.className = 'metric-value';
                valueSpan.textContent = typeof value === 'number' ? 
                    formatMetricValue(value) : value;
                
                item.appendChild(nameSpan);
                item.appendChild(valueSpan);
            }
            
            fragment.appendChild(item);
        } catch (error) {
            console.error(`Error creating metric item for ${key}:`, error);
            // Don't add this item if there was an error
        }
    });
    
    return fragment;
}

/**
 * Format a Unix timestamp into a UTC string + relative time
 * @param {number|string} timestamp - The Unix timestamp in milliseconds
 * @returns {string} The formatted date/time string
 */
function formatTimestamp(timestamp) {
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
 * Populate metrics in a binding template
 * @param {Object} metrics - Metrics data object
 * @param {DocumentFragment} template - The template to populate
 */
function populateMetricsInTemplate(metrics, template) {
    // Populate operational metrics
    populateMetricSection(
        metrics.operational,
        template.querySelector('.operational-metrics'),
        'Performance Counters'
    );
    
    // Populate performance metrics (timestamps)
    populateMetricSection(
        metrics.performance,
        template.querySelector('.performance-metrics'),
        'Timestamps'
    );
    
    // Hide unused sections
    const stateSection = template.querySelector('.state-metrics-section');
    if (stateSection) stateSection.style.display = 'none';
    
    const errorSection = template.querySelector('.error-metrics-section');
    if (errorSection) errorSection.style.display = 'none';
}

/**
 * Populate a metric section
 * @param {Object} metrics - Metrics data for this section
 * @param {HTMLElement} container - Container element for this section
 * @param {string} sectionTitle - Title for this metrics section
 */
function populateMetricSection(metrics, container, sectionTitle) {
    // Update section title if provided
    if (sectionTitle && container) {
        const titleElement = container.parentElement.querySelector('h4');
        if (titleElement) {
            titleElement.textContent = sectionTitle;
        }
    }
    
    // Check if we have metrics for this section
    if (!metrics || Object.keys(metrics).length === 0) {
        container.innerHTML = '';
        
        // Add "No data available" message
        const noData = document.createElement('div');
        noData.className = 'no-data';
        noData.textContent = 'No data available';
        container.appendChild(noData);
        return;
    }
    
    // Add each metric item
    container.innerHTML = '';
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
 * Process component metrics for both old and new formats
 * @param {Object} component - Component metrics data
 * @returns {Object} Processed metrics ready for display
 */
function processComponentMetrics(component) {
    try {
        if (!component) {
            return {};
        }
        
        // Handle both old and new metrics formats
        let result = {
            operational: {},
            performance: {},
            state: {},
            errors: {}
        };
        
        // For backward compatibility with old format
        const isOldFormat = !component.timestamps;
        
        // Process operational metrics from either format
        if (component.operational) {
            // New format: nested operational metrics
            result.operational = { ...component.operational };
        } else if (isOldFormat) {
            // Old format: metrics at root level
            const operationalKeys = [
                'messages_received_total',
                'messages_sent_total',
                'errors_received_total',
                'errors_sent_total',
                'reconnections_total'
            ];
            
            operationalKeys.forEach(key => {
                if (component[key] !== undefined) {
                    result.operational[key] = component[key];
                }
            });
        }
        
        // Process performance metrics (timestamps)
        if (component.timestamps) {
            // New format
            const performanceMap = {
                'last_message_received_time': component.timestamps.last_message_received,
                'last_message_sent_time': component.timestamps.last_message_sent,
                'last_reconnection_time': component.timestamps.last_reconnection
            };
            
            Object.entries(performanceMap).forEach(([displayKey, timestampValue]) => {
                if (timestampValue) {
                    result.performance[displayKey] = formatTimestamp(timestampValue);
                }
            });
        } else if (isOldFormat) {
            // Old format: direct timestamps
            const timestampKeys = [
                'last_message_received_time',
                'last_message_sent_time',
                'last_reconnection_time'
            ];
            
            timestampKeys.forEach(key => {
                const timestamp = component[key + '_timestamp'] || component[key];
                if (timestamp) {
                    result.performance[key] = formatTimestamp(timestamp);
                }
            });
        }
        
        // Process performance histograms (if available in either format)
        const histogramKeys = ['message_processing_time', 'message_delivery_time'];
        
        histogramKeys.forEach(key => {
            // Try to find histogram in various locations
            const histogram = component[key] || 
                             (component.performance && component.performance[key]) || 
                             null;
            
            if (histogram && typeof histogram === 'object') {
                // Process histogram metrics
                if (histogram.count !== undefined) {
                    result.performance[`${key}_count`] = histogram.count;
                }
                
                if (histogram.sum !== undefined) {
                    result.performance[`${key}_sum`] = histogram.sum;
                }
                
                // Process percentiles
                if (histogram.percentiles) {
                    Object.entries(histogram.percentiles).forEach(([percentile, value]) => {
                        result.performance[`${key}_p${percentile}`] = value;
                    });
                }
            }
        });
        
        // Process error metrics (if available)
        if (component.errors) {
            // New format
            if (component.errors.last_error) {
                result.errors['last_error'] = component.errors.last_error;
            }
            
            if (component.errors.last_error_time) {
                result.errors['last_error_time'] = formatTimestamp(component.errors.last_error_time);
            }
        } else if (isOldFormat) {
            // Old format
            if (component.last_error) {
                result.errors['last_error'] = component.last_error;
            }
            
            const errorTime = component.last_error_time_timestamp || component.last_error_time;
            if (errorTime) {
                result.errors['last_error_time'] = formatTimestamp(errorTime);
            }
        }
        
        // Only keep non-empty sections
        Object.keys(result).forEach(key => {
            if (Object.keys(result[key]).length === 0) {
                delete result[key];
            }
        });
        
        return result;
    } catch (error) {
        console.error('Error processing component metrics:', error);
        return {
            operational: {},
            performance: {},
            errors: {
                'processing_error': 'Error processing metrics'
            }
        };
    }
}

/**
 * Create a metric item element
 * @param {string} name - The metric name
 * @param {any} value - The metric value
 * @returns {HTMLElement} - The metric item element
 */
function createMetricItem(name, value) {
    try {
        let item;
        
        // Use template if available
        if (elements.metricItemTemplate) {
            item = elements.metricItemTemplate.content.cloneNode(true);
            
            // Format the metric name
            const nameElement = getElement('.metric-name', item);
            if (nameElement) {
                nameElement.className = 'metric-name detail-item-key';
                nameElement.textContent = formatMetricName(name);
            }
            
            // Format the metric value
            const valueElement = getElement('.metric-value', item);
            if (valueElement) {
                valueElement.textContent = typeof value === 'number' ? 
                    formatMetricValue(value) : value;
            }
        } else {
            // Fallback if template is not available
            item = document.createElement('div');
            item.className = 'metric-item';
            
            const nameSpan = document.createElement('span');
            nameSpan.className = 'metric-name detail-item-key';
            nameSpan.textContent = formatMetricName(name);
            
            const valueSpan = document.createElement('span');
            valueSpan.className = 'metric-value';
            valueSpan.textContent = typeof value === 'number' ? 
                formatMetricValue(value) : value;
            
            item.appendChild(nameSpan);
            item.appendChild(valueSpan);
        }
        
        return item;
    } catch (error) {
        console.error(`Error creating metric item for ${name}:`, error);
        const fallback = document.createElement('div');
        fallback.className = 'metric-item error';
        fallback.textContent = `${formatMetricName(name)}: Error`;
        return fallback;
    }
}

/**
 * Safe helper to set text content on DOM elements
 * @param {HTMLElement|null} element - The DOM element
 * @param {string|number} value - The value to set
 * @param {string} fallbackSelector - Selector to try if element is null
 * @returns {boolean} - True if successful, false otherwise
 */
function safeSetTextContent(element, value, fallbackSelector = null) {
    try {
        // If element is provided and valid
        if (element && typeof element.textContent !== 'undefined') {
            element.textContent = value;
            return true;
        }
        
        // Try fallback selector if provided
        if (fallbackSelector) {
            const fallbackElement = document.querySelector(fallbackSelector);
            if (fallbackElement) {
                fallbackElement.textContent = value;
                return true;
            }
        }
        
        return false;
    } catch (error) {
        console.error(`Error setting text content to ${value}:`, error);
        return false;
    }
}

/**
 * Safe helper to add or remove a class from an element
 * @param {HTMLElement|null} element - The DOM element
 * @param {string} className - Class to toggle
 * @param {boolean} force - Whether to add (true) or remove (false)
 * @param {string} fallbackSelector - Selector to try if element is null
 * @returns {boolean} - True if successful, false otherwise
 */
function safeToggleClass(element, className, force, fallbackSelector = null) {
    try {
        // If element is provided and valid
        if (element && element.classList) {
            element.classList.toggle(className, force);
            return true;
        }
        
        // Try fallback selector if provided
        if (fallbackSelector) {
            const fallbackElement = document.querySelector(fallbackSelector);
            if (fallbackElement && fallbackElement.classList) {
                fallbackElement.classList.toggle(className, force);
                return true;
            }
        }
        
        return false;
    } catch (error) {
        console.error(`Error toggling class ${className}:`, error);
        return false;
    }
}

/**
 * Safe helper to clear the contents of a container
 * @param {HTMLElement|null} container - The container to clear
 * @param {string} fallbackSelector - Selector to try if container is null
 * @returns {boolean} - True if successful, false otherwise
 */
function safeClearContainer(container, fallbackSelector = null) {
    try {
        // If container is provided and valid
        if (container && typeof container.innerHTML !== 'undefined') {
            container.innerHTML = '';
            return true;
        }
        
        // Try fallback selector if provided
        if (fallbackSelector) {
            const fallbackContainer = document.querySelector(fallbackSelector);
            if (fallbackContainer) {
                fallbackContainer.innerHTML = '';
                return true;
            }
        }
        
        return false;
    } catch (error) {
        console.error('Error clearing container:', error);
        return false;
    }
}

/**
 * Check if the dashboard is ready and try to recover if not
 * @returns {boolean} - Whether the dashboard is initialized and ready
 */
function ensureDashboardReady() {
    if (!document.body) {
        console.error('Document body not available yet');
        return false;
    }
    
    // If elements object is empty or critical elements are missing, try to re-initialize
    if (!elements || Object.keys(elements).length === 0) {
        console.warn('Dashboard elements not initialized, attempting to recover');
        initElementReferences();
        return Object.keys(elements).length > 0;
    }
    
    return true;
}

/**
 * Create a fallback binding card when template is not available
 * @param {string} bindingName - Name of the binding
 * @param {Object} binding - Binding metrics data
 * @param {number} seqNum - Sequence number of the binding
 * @returns {HTMLElement} A basic binding metrics card
 */
function createFallbackBindingCard(bindingName, binding, seqNum) {
    try {
        const cardDiv = document.createElement('div');
        cardDiv.className = 'binding-card';
        
        const header = document.createElement('div');
        header.className = 'binding-header';
        
        const nameContainer = document.createElement('div');
        nameContainer.className = 'binding-name-container';
        
        const seqBadge = document.createElement('div');
        seqBadge.className = 'binding-seq';
        seqBadge.textContent = seqNum;
        
        const title = document.createElement('h3');
        title.className = 'binding-name';
        title.textContent = bindingName;
        
        nameContainer.appendChild(seqBadge);
        nameContainer.appendChild(title);
        header.appendChild(nameContainer);
        cardDiv.appendChild(header);
        
        const body = document.createElement('div');
        body.className = 'binding-body';
        
        const metricsContainer = document.createElement('div');
        metricsContainer.className = 'metrics-container';
        
        // Add summary section
        const summarySection = createFallbackSection(binding, 'Binding Summary', 'binding-summary-section', 
            (key, value) => key !== 'components' && key !== 'name' && !key.endsWith('timestamp'));
        
        if (summarySection) {
            metricsContainer.appendChild(summarySection);
        }
        
        // Add source component section if available
        if (binding.components && binding.components.source) {
            const sourceType = binding.components.source.type || 'Unknown';
            const sourceSection = createFallbackSection(
                binding.components.source, 
                `Source: ${sourceType}`, 
                'source-component-section',
                (key, value) => key !== 'name' && key !== 'type' && !key.endsWith('timestamp')
            );
            
            if (sourceSection) {
                metricsContainer.appendChild(sourceSection);
            }
        }
        
        // Add target component section if available
        if (binding.components && binding.components.target) {
            const targetType = binding.components.target.type || 'Unknown';
            const targetSection = createFallbackSection(
                binding.components.target, 
                `Target: ${targetType}`, 
                'target-component-section',
                (key, value) => key !== 'name' && key !== 'type' && !key.endsWith('timestamp')
            );
            
            if (targetSection) {
                metricsContainer.appendChild(targetSection);
            }
        }
        
        body.appendChild(metricsContainer);
        cardDiv.appendChild(body);
        
        return cardDiv;
    } catch (error) {
        console.error(`Error creating fallback binding card for ${bindingName}:`, error);
        return createErrorElement(`Error creating binding card: ${bindingName}`);
    }
}

// Initialize the dashboard when the DOM is loaded
document.addEventListener('DOMContentLoaded', initDashboard); 