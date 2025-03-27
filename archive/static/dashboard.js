/**
 * IBM MQ - KubeMQ Dashboard
 * 
 * This script handles fetching data from the API and 
 * updating the dashboard with health and metrics information.
 * 
 * This file has been refactored to use a modular approach with
 * separate files for different concerns:
 * - api.js: API communication
 * - ui.js: UI rendering and updates
 * - utils.js: Utility functions
 * - state.js: State management
 */

// Import modules
import * as api from './js/api.js';
import * as ui from './js/ui.js';
import * as utils from './js/utils.js';
import * as state from './js/state.js';
import * as dashboard from './js/dashboard.js';

// Initialize the dashboard when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    try {
        console.log('Initializing dashboard from main entry point...');
        dashboard.initDashboard();
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

// Export modules for potential external use
export {
    api,
    ui,
    utils,
    state,
    dashboard
};
