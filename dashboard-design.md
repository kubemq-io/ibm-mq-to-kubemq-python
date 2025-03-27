# Messaging Bridge Dashboard - Development Instructions

## Overview
Create a beautiful, responsive, single-page dashboard application to monitor the metrics and health status of the messaging bridge system. The dashboard will visualize the data from two API endpoints:
- Metrics data: `http://localhost:9000/metrics/`
- Health data: `http://localhost:9000/health/`

## Technology Stack
- HTML5, CSS3, JavaScript (ES6+)
- Tailwind CSS for styling
- Google Fonts for typography
- Font Awesome for icons
- Chart.js for data visualization

## Design Principles
- Modern, clean interface with a dark/light theme toggle
- Clear visualization of metrics and health status
- Responsive design for all screen sizes
- Real-time data updates

## Project Structure
```
/dashboard
  /assets
    /css
      tailwind.css
      custom.css
    /js
      main.js
      /components
        healthStatus.js
        metricsDisplay.js
        bindingDetails.js
        notificationCenter.js
        systemOverview.js
      /utils
        dataFetcher.js
        formatters.js
  index.html
  README.md
```

## Component Architecture

### 1. Main Dashboard Container
- Header with system name and theme toggle
- Sidebar navigation (if needed for future expansion)
- Main content area with grid layout of components
- Footer with relevant info

### 2. System Overview Component
- High-level metrics summary
- Total bindings count
- Overall system health status
- Last activity timestamps

### 3. Binding Cards Component
- Card for each binding (kubemq_to_ibm, ibm_to_kubemq)
- Health status indicator (green/red)
- Basic metrics (messages sent/received)
- Expandable for detailed view

### 4. Metrics Visualization Component
- Charts for message volumes
- Counters for total messages
- Error rate displays
- Time-series data where applicable

### 5. Health Status Component
- Connection status indicators
- Latency displays
- Error notifications
- Component health details

### 6. Activity Timeline Component
- Recent events (message sends/receives, errors, reconnections)
- Timestamp formatting
- Activity type filtering

## Detailed Implementation Guidelines

### HTML Structure (index.html)

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Messaging Bridge Dashboard</title>
  
  <!-- Tailwind CSS -->
  <script src="https://cdn.tailwindcss.com"></script>
  
  <!-- Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Roboto+Mono:wght@400;500&display=swap" rel="stylesheet">
  
  <!-- Font Awesome -->
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  
  <!-- Chart.js -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  
  <!-- Custom CSS -->
  <link rel="stylesheet" href="assets/css/custom.css">
</head>
<body class="bg-gray-100 dark:bg-gray-900 text-gray-800 dark:text-gray-200 font-inter transition-colors duration-200">
  <!-- Dashboard container will be mounted here -->
  <div id="dashboard-app"></div>
  
  <!-- Main JavaScript -->
  <script type="module" src="assets/js/main.js"></script>
</body>
</html>
```

### Styling with Tailwind and Custom CSS

Define a tailwind.config.js with custom colors and themes:

```javascript
// tailwind.config.js
module.exports = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          // ... other shades
          600: '#0284c7',
          700: '#0369a1',
        },
        secondary: {
          // Custom secondary color palette
        },
        success: '#10b981',
        warning: '#f59e0b',
        danger: '#ef4444',
        info: '#3b82f6',
      },
      fontFamily: {
        inter: ['Inter', 'sans-serif'],
        mono: ['Roboto Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
```

### Main JavaScript (main.js)

```javascript
// main.js
import { DataFetcher } from './utils/dataFetcher.js';
import { SystemOverview } from './components/systemOverview.js';
import { HealthStatus } from './components/healthStatus.js';
import { MetricsDisplay } from './components/metricsDisplay.js';
import { BindingDetails } from './components/bindingDetails.js';
import { NotificationCenter } from './components/notificationCenter.js';

class Dashboard {
  constructor() {
    this.dataFetcher = new DataFetcher();
    this.components = {};
    this.data = {
      metrics: null,
      health: null,
      lastUpdated: null
    };
    
    this.init();
  }
  
  async init() {
    // Create the dashboard layout
    this.createLayout();
    
    // Initialize components
    this.initComponents();
    
    // Fetch initial data
    await this.fetchData();
    
    // Set up refresh interval (every 10 seconds)
    this.setupRefreshInterval();
    
    // Set up theme toggling
    this.setupThemeToggle();
  }
  
  createLayout() {
    const dashboardApp = document.getElementById('dashboard-app');
    
    // Create dashboard structure with header, main content area, etc.
    dashboardApp.innerHTML = `
      <div class="min-h-screen flex flex-col">
        <!-- Header -->
        <header class="bg-white dark:bg-gray-800 shadow-sm">
          <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
            <div class="flex items-center">
              <i class="fas fa-exchange-alt text-primary-600 text-2xl mr-3"></i>
              <h1 class="text-xl font-semibold">Messaging Bridge Dashboard</h1>
            </div>
            <div class="flex items-center">
              <span id="last-updated" class="text-sm text-gray-500 dark:text-gray-400 mr-4"></span>
              <button id="theme-toggle" class="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700">
                <i class="fas fa-moon dark:hidden"></i>
                <i class="fas fa-sun hidden dark:block"></i>
              </button>
            </div>
          </div>
        </header>
        
        <!-- Main Content -->
        <main class="flex-grow p-4 sm:p-6 lg:p-8">
          <div class="max-w-7xl mx-auto">
            <!-- System Overview -->
            <div id="system-overview" class="mb-6"></div>
            
            <!-- Bindings Grid -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              <div id="binding-kubemq-to-ibm" class="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4"></div>
              <div id="binding-ibm-to-kubemq" class="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4"></div>
            </div>
            
            <!-- Metrics and Health -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div id="metrics-display" class="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4"></div>
              <div id="health-status" class="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4"></div>
            </div>
          </div>
        </main>
        
        <!-- Footer -->
        <footer class="bg-white dark:bg-gray-800 py-4 border-t border-gray-200 dark:border-gray-700">
          <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm text-gray-500 dark:text-gray-400">
            Messaging Bridge Dashboard © 2025
          </div>
        </footer>
        
        <!-- Notification Center -->
        <div id="notification-center" class="fixed bottom-4 right-4"></div>
      </div>
    `;
  }
  
  initComponents() {
    // Initialize all the components
    this.components.systemOverview = new SystemOverview(document.getElementById('system-overview'));
    this.components.healthStatus = new HealthStatus(document.getElementById('health-status'));
    this.components.metricsDisplay = new MetricsDisplay(document.getElementById('metrics-display'));
    
    this.components.bindingDetails = {
      kubemqToIbm: new BindingDetails(
        document.getElementById('binding-kubemq-to-ibm'),
        'kubemq_to_ibm'
      ),
      ibmToKubemq: new BindingDetails(
        document.getElementById('binding-ibm-to-kubemq'),
        'ibm_to_kubemq'
      )
    };
    
    this.components.notificationCenter = new NotificationCenter(
      document.getElementById('notification-center')
    );
  }
  
  async fetchData() {
    try {
      // Fetch metrics and health data in parallel
      const [metrics, health] = await Promise.all([
        this.dataFetcher.fetchMetrics(),
        this.dataFetcher.fetchHealth()
      ]);
      
      this.data.metrics = metrics;
      this.data.health = health;
      this.data.lastUpdated = new Date();
      
      // Update the last updated timestamp
      document.getElementById('last-updated').textContent = 
        `Last updated: ${this.data.lastUpdated.toLocaleTimeString()}`;
      
      // Update all components with new data
      this.updateComponents();
      
      // Show success notification
      this.components.notificationCenter.showNotification(
        'Data refreshed successfully', 
        'success'
      );
    } catch (error) {
      console.error('Failed to fetch data:', error);
      this.components.notificationCenter.showNotification(
        'Failed to fetch data. Retrying...', 
        'error'
      );
    }
  }
  
  updateComponents() {
    // Update each component with the relevant data
    this.components.systemOverview.update(this.data);
    this.components.healthStatus.update(this.data.health);
    this.components.metricsDisplay.update(this.data.metrics);
    
    this.components.bindingDetails.kubemqToIbm.update(
      this.data.metrics.data.bindings.kubemq_to_ibm,
      this.data.health.data.bindings.kubemq_to_ibm
    );
    
    this.components.bindingDetails.ibmToKubemq.update(
      this.data.metrics.data.bindings.ibm_to_kubemq,
      this.data.health.data.bindings.ibm_to_kubemq
    );
  }
  
  setupRefreshInterval() {
    // Refresh data every 10 seconds
    setInterval(() => this.fetchData(), 10000);
  }
  
  setupThemeToggle() {
    const themeToggleBtn = document.getElementById('theme-toggle');
    
    // Check user preference or system preference
    if (
      localStorage.getItem('theme') === 'dark' || 
      (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)
    ) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    
    // Toggle theme on button click
    themeToggleBtn.addEventListener('click', () => {
      document.documentElement.classList.toggle('dark');
      
      if (document.documentElement.classList.contains('dark')) {
        localStorage.setItem('theme', 'dark');
      } else {
        localStorage.setItem('theme', 'light');
      }
    });
  }
}

// Initialize the dashboard when the DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const dashboard = new Dashboard();
});
```

### Component Implementation Examples

#### SystemOverview Component (systemOverview.js)
```javascript
// components/systemOverview.js
export class SystemOverview {
  constructor(container) {
    this.container = container;
    this.render();
  }
  
  render() {
    this.container.innerHTML = `
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4">
        <h2 class="text-lg font-semibold mb-4">System Overview</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
            <div class="text-sm text-gray-500 dark:text-gray-400">Total Bindings</div>
            <div class="text-2xl font-semibold mt-1" id="total-bindings">-</div>
          </div>
          <div class="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
            <div class="text-sm text-gray-500 dark:text-gray-400">System Health</div>
            <div class="text-2xl font-semibold mt-1" id="overall-status">-</div>
          </div>
          <div class="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
            <div class="text-sm text-gray-500 dark:text-gray-400">Total Messages</div>
            <div class="text-2xl font-semibold mt-1" id="total-messages">-</div>
          </div>
          <div class="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
            <div class="text-sm text-gray-500 dark:text-gray-400">Total Errors</div>
            <div class="text-2xl font-semibold mt-1" id="total-errors">-</div>
          </div>
        </div>
      </div>
    `;
  }
  
  update(data) {
    if (!data.metrics || !data.health) return;
    
    // Update bindings count
    document.getElementById('total-bindings').textContent = 
      data.health.data.bindings_count;
    
    // Update overall status with appropriate color
    const statusEl = document.getElementById('overall-status');
    statusEl.textContent = data.health.data.overall_status;
    
    if (data.health.data.overall_status === 'healthy') {
      statusEl.classList.add('text-success');
      statusEl.classList.remove('text-danger');
    } else {
      statusEl.classList.add('text-danger');
      statusEl.classList.remove('text-success');
    }
    
    // Calculate and update total messages
    const metricsData = data.metrics.data;
    const totalMessagesReceived = metricsData.system.messages_received_total;
    const totalMessagesSent = metricsData.system.messages_sent_total;
    
    document.getElementById('total-messages').textContent = 
      (totalMessagesReceived + totalMessagesSent).toLocaleString();
    
    // Calculate and update total errors
    const totalErrorsReceived = metricsData.system.errors_received_total;
    const totalErrorsSent = metricsData.system.errors_sent_total;
    
    document.getElementById('total-errors').textContent = 
      (totalErrorsReceived + totalErrorsSent).toLocaleString();
  }
}
```

#### BindingDetails Component (bindingDetails.js)
```javascript
// components/bindingDetails.js
export class BindingDetails {
  constructor(container, bindingName) {
    this.container = container;
    this.bindingName = bindingName;
    this.expanded = false;
    this.render();
  }
  
  render() {
    this.container.innerHTML = `
      <div class="binding-card">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center">
            <div id="${this.bindingName}-status-indicator" class="w-3 h-3 rounded-full bg-gray-300"></div>
            <h3 class="font-semibold ml-2">${this.formatBindingName(this.bindingName)}</h3>
          </div>
          <button id="${this.bindingName}-expand-btn" class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
            <i class="fas fa-chevron-down"></i>
          </button>
        </div>
        
        <div class="grid grid-cols-2 gap-3 mb-3">
          <div class="bg-gray-50 dark:bg-gray-700 p-2 rounded">
            <div class="text-xs text-gray-500 dark:text-gray-400">Messages</div>
            <div class="text-xl font-medium" id="${this.bindingName}-messages">-</div>
          </div>
          <div class="bg-gray-50 dark:bg-gray-700 p-2 rounded">
            <div class="text-xs text-gray-500 dark:text-gray-400">Errors</div>
            <div class="text-xl font-medium" id="${this.bindingName}-errors">-</div>
          </div>
        </div>
        
        <div id="${this.bindingName}-details" class="hidden mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 class="font-medium mb-2">Source</h4>
              <div class="text-sm" id="${this.bindingName}-source-details"></div>
            </div>
            <div>
              <h4 class="font-medium mb-2">Target</h4>
              <div class="text-sm" id="${this.bindingName}-target-details"></div>
            </div>
          </div>
        </div>
      </div>
    `;
    
    // Add event listener for expand/collapse
    document.getElementById(`${this.bindingName}-expand-btn`).addEventListener('click', () => {
      this.toggleExpand();
    });
  }
  
  formatBindingName(name) {
    return name.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
  }
  
  toggleExpand() {
    this.expanded = !this.expanded;
    const detailsEl = document.getElementById(`${this.bindingName}-details`);
    const expandBtn = document.getElementById(`${this.bindingName}-expand-btn`);
    
    if (this.expanded) {
      detailsEl.classList.remove('hidden');
      expandBtn.innerHTML = '<i class="fas fa-chevron-up"></i>';
    } else {
      detailsEl.classList.add('hidden');
      expandBtn.innerHTML = '<i class="fas fa-chevron-down"></i>';
    }
  }
  
  update(metricsData, healthData) {
    if (!metricsData || !healthData) return;
    
    // Update status indicator
    const statusIndicator = document.getElementById(`${this.bindingName}-status-indicator`);
    if (healthData.status === 'healthy') {
      statusIndicator.classList.remove('bg-gray-300', 'bg-danger');
      statusIndicator.classList.add('bg-success');
    } else {
      statusIndicator.classList.remove('bg-gray-300', 'bg-success');
      statusIndicator.classList.add('bg-danger');
    }
    
    // Update messages count
    const messagesReceived = metricsData.messages_received_total || 0;
    const messagesSent = metricsData.messages_sent_total || 0;
    document.getElementById(`${this.bindingName}-messages`).textContent = 
      (messagesReceived + messagesSent).toLocaleString();
    
    // Update errors count
    const errorsReceived = metricsData.errors_received_total || 0;
    const errorsSent = metricsData.errors_sent_total || 0;
    document.getElementById(`${this.bindingName}-errors`).textContent = 
      (errorsReceived + errorsSent).toLocaleString();
    
    // Update source and target details
    this.updateComponentDetails(
      `${this.bindingName}-source-details`, 
      healthData.source.details,
      healthData.source.status
    );
    
    this.updateComponentDetails(
      `${this.bindingName}-target-details`, 
      healthData.target.details,
      healthData.target.status
    );
  }
  
  updateComponentDetails(elementId, details, status) {
    const el = document.getElementById(elementId);
    if (!el) return;
    
    // Create a status badge
    const statusBadge = `
      <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
        status === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
      }">
        ${status}
      </span>
    `;
    
    // Build details HTML
    let detailsHtml = `${statusBadge}<dl class="mt-2">`;
    
    for (const [key, value] of Object.entries(details)) {
      // Format the key name
      const formattedKey = key.split('_').map(word => 
        word.charAt(0).toUpperCase() + word.slice(1)
      ).join(' ');
      
      detailsHtml += `
        <div class="grid grid-cols-2 gap-1 py-1 border-b border-gray-100 dark:border-gray-700">
          <dt class="text-gray-500 dark:text-gray-400">${formattedKey}:</dt>
          <dd class="font-medium">${value !== null ? value : '-'}</dd>
        </div>
      `;
    }
    
    detailsHtml += '</dl>';
    el.innerHTML = detailsHtml;
  }
}
```

### Utility Scripts

#### Data Fetcher (dataFetcher.js)
```javascript
// utils/dataFetcher.js
export class DataFetcher {
  constructor() {
    this.baseUrl = 'http://localhost:9000';
  }
  
  async fetchMetrics() {
    const response = await fetch(`${this.baseUrl}/metrics/`);
    if (!response.ok) {
      throw new Error(`Failed to fetch metrics: ${response.status}`);
    }
    return response.json();
  }
  
  async fetchHealth() {
    const response = await fetch(`${this.baseUrl}/health/`);
    if (!response.ok) {
      throw new Error(`Failed to fetch health: ${response.status}`);
    }
    return response.json();
  }
}
```

#### Formatters (formatters.js)
```javascript
// utils/formatters.js
export const formatBytes = (bytes, decimals = 2) => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

export const formatTimestamp = (timestamp) => {
  if (!timestamp) return '-';
  
  const date = new Date(timestamp);
  return date.toLocaleString();
};

export const formatDuration = (milliseconds) => {
  if (!milliseconds) return '-';
  
  const seconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  
  return hours > 0
    ? `${hours}h ${minutes % 60}m`
    : minutes > 0
      ? `${minutes}m ${seconds % 60}s`
      : `${seconds}s`;
};
```

## Visualization Implementation

Include chart configurations for the metrics visualization component:

```javascript
// Example chart configuration for metrics visualization
const createMessageVolumeTrendChart = (canvasId, data) => {
  const ctx = document.getElementById(canvasId).getContext('2d');
  
  // Process data for chart
  const labels = [...Array(7).keys()].map(i => {
    const date = new Date();
    date.setDate(date.getDate() - i);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }).reverse();
  
  // Create dummy data for demonstration
  // In real app, this would use actual historical data
  const received = Array(7).fill(0).map(() => Math.floor(Math.random() * 100));
  const sent = Array(7).fill(0).map(() => Math.floor(Math.random() * 100));
  
  return new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Messages Received',
          data: received,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          tension: 0.3,
          fill: true
        },
        {
          label: 'Messages Sent',
          data: sent,
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          tension: 0.3,
          fill: true
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
        },
        title: {
          display: true,
          text: 'Message Volume Trend'
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: 'Message Count'
          }
        }
      }
    }
  });
};
```

## Additional Features to Consider

### 1. Real-time Updates with WebSockets
If your API supports WebSockets, implement real-time updates instead of polling:

```javascript
// Example WebSocket connection
const setupWebSocket = () => {
  const ws = new WebSocket('ws://localhost:9000/live-updates');
  
  ws.onopen = () => {
    console.log('WebSocket connection established');
  };
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Update dashboard with new data
    updateDashboardWithData(data);
  };
  
  ws.onclose = () => {
    console.log('WebSocket connection closed. Reconnecting...');
    // Attempt to reconnect after a delay
    setTimeout(setupWebSocket, 3000);
  };
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };
};
```

### 2. Data Export Functionality
Add the ability to export metrics data to CSV or JSON:

```javascript
const exportData = (format = 'json') => {
  const data = {
    metrics: this.data.metrics,
    health: this.data.health,
    exportedAt: new Date().toISOString()
  };
  
  let exportContent, filename, mimeType;
  
  if (format === 'json') {
    exportContent = JSON.stringify(data, null, 2);
    filename = `messaging-bridge-data-${new Date().toISOString()}.json`;
    mimeType = 'application/json';
  } else if (format === 'csv') {
    // Convert data to CSV format
    // This would need a more complex implementation
    exportContent = convertToCSV(data);
    filename = `messaging-bridge-data-${new Date().toISOString()}.csv`;
    mimeType = 'text/csv';
  }
  
  // Create download link
  const blob = new Blob([exportContent], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};
```

### 3. Alert Configurations
Allow users to set thresholds for alerts:

```javascript
const alertConfig = {
  errorThreshold: 5,
  reconnectionThreshold: 3,
  latencyThreshold: 1000, // ms
  checkAlerts: function(data) {
    const alerts = [];
    
    // Check for high error count
    if (data.metrics.data.system.errors_sent_total > this.errorThreshold ||
        data.metrics.data.system.errors_received_total > this.errorThreshold) {
      alerts.push({
        type: 'error',
        message: 'High error count detected',
        details: `Error count exceeds threshold of ${this.errorThreshold}`
      });
    }
    
    // Check for reconnection attempts
    if (data.metrics.data.system.reconnection_attempts_total > this.reconnectionThreshold) {
      alerts.push({
        type: 'warning',
        message: 'High reconnection count detected',
        details: `Reconnection count exceeds threshold of ${this.reconnectionThreshold}`
      });
    }
    
    return alerts;
  }
};
```

## Deployment and Testing

### Serving the Dashboard
Ensure the API server at http://localhost:9000 is configured to serve the dashboard files at the /dashboard endpoint.

### Build Process
1. Structure your project according to the folder structure provided above
2. Install development dependencies if needed:
   ```bash
   npm init -y
   npm install -D tailwindcss postcss autoprefixer
   npx tailwindcss init
   ```
3. Build the tailwind CSS:
   ```bash
   npx tailwindcss -i ./assets/css/tailwind.css -o ./assets/css/tailwind.output.css --minify
   ```
4. Bundle the JavaScript files if needed (optional):
   ```bash
   # Using esbuild for a simple bundle
   npm install -D esbuild
   npx esbuild ./assets/js/main.js --bundle --outfile=./assets/js/bundle.js
   ```

### Cross-Browser Testing
Test the dashboard on multiple browsers:
- Chrome
- Firefox
- Safari
- Edge

### Responsive Testing
Test on different screen sizes:
- Desktop (1920x1080, 1366x768)
- Tablet (1024x768, 768x1024)
- Mobile (375x667, 414x896)

### Performance Testing
- Test initial load time (should be under 2 seconds)
- Test data refresh performance (should be seamless)
- Check memory usage over extended periods

## Additional Implementation Details

### Metrics Visualization Component (metricsDisplay.js)

```javascript
// components/metricsDisplay.js
export class MetricsDisplay {
  constructor(container) {
    this.container = container;
    this.charts = {};
    this.render();
  }
  
  render() {
    this.container.innerHTML = `
      <div>
        <h2 class="text-lg font-semibold mb-4">Metrics Overview</h2>
        
        <div class="mb-6">
          <div class="flex justify-between items-center mb-2">
            <h3 class="font-medium">Message Activity</h3>
            <div class="text-sm text-gray-500 dark:text-gray-400">
              <select id="time-range" class="bg-transparent border-gray-300 dark:border-gray-600 rounded-md text-xs">
                <option value="day">Last 24 Hours</option>
                <option value="week" selected>Last 7 Days</option>
                <option value="month">Last 30 Days</option>
              </select>
            </div>
          </div>
          <div class="h-64">
            <canvas id="message-volume-chart"></canvas>
          </div>
        </div>
        
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
            <h4 class="text-sm font-medium mb-2">Message Distribution</h4>
            <div class="h-40">
              <canvas id="message-distribution-chart"></canvas>
            </div>
          </div>
          <div class="bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
            <h4 class="text-sm font-medium mb-2">Error Rate</h4>
            <div class="h-40">
              <canvas id="error-rate-chart"></canvas>
            </div>
          </div>
        </div>
      </div>
    `;
    
    // Initialize charts once DOM is ready
    setTimeout(() => {
      this.initializeCharts();
    }, 0);
    
    // Add event listener for time range selector
    document.getElementById('time-range').addEventListener('change', (e) => {
      // In a real app, this would fetch data for the selected time range
      // For demo, we'll just regenerate random data
      this.updateChartsForTimeRange(e.target.value);
    });
  }
  
  initializeCharts() {
    // Message volume trend chart
    this.charts.messageVolume = this.createMessageVolumeTrendChart('message-volume-chart');
    
    // Message distribution chart
    this.charts.messageDistribution = this.createMessageDistributionChart('message-distribution-chart');
    
    // Error rate chart
    this.charts.errorRate = this.createErrorRateChart('error-rate-chart');
  }
  
  createMessageVolumeTrendChart(canvasId) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // Get last 7 days for labels
    const labels = [...Array(7).keys()].map(i => {
      const date = new Date();
      date.setDate(date.getDate() - (6 - i));
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    
    // Sample data for demonstration
    const received = Array(7).fill(0).map(() => Math.floor(Math.random() * 100));
    const sent = Array(7).fill(0).map(() => Math.floor(Math.random() * 100));
    
    return new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Messages Received',
            data: received,
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            tension: 0.3,
            fill: true
          },
          {
            label: 'Messages Sent',
            data: sent,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            tension: 0.3,
            fill: true
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'Message Count'
            }
          }
        }
      }
    });
  }
  
  createMessageDistributionChart(canvasId) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    return new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['KubeMQ to IBM', 'IBM to KubeMQ'],
        datasets: [
          {
            data: [60, 40],
            backgroundColor: ['#3b82f6', '#10b981'],
            hoverOffset: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom'
          }
        }
      }
    });
  }
  
  createErrorRateChart(canvasId) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['KubeMQ to IBM', 'IBM to KubeMQ'],
        datasets: [
          {
            label: 'Error Rate (%)',
            data: [2.1, 1.8],
            backgroundColor: ['rgba(239, 68, 68, 0.7)', 'rgba(239, 68, 68, 0.7)']
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            suggestedMax: 5,
            title: {
              display: true,
              text: 'Error Rate (%)'
            }
          }
        }
      }
    });
  }
  
  updateChartsForTimeRange(timeRange) {
    // In a real app, this would fetch new data based on the time range
    // For demo purposes, we'll just update with new random data
    
    // Update message volume chart with new random data
    const datasetLength = timeRange === 'day' ? 24 : 
                          timeRange === 'week' ? 7 : 30;
    
    const labels = [...Array(datasetLength).keys()].map(i => {
      const date = new Date();
      date.setDate(date.getDate() - (datasetLength - 1 - i));
      return timeRange === 'day' 
        ? date.toLocaleTimeString('en-US', { hour: '2-digit' })
        : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    
    // Generate new random data
    const received = Array(datasetLength).fill(0).map(() => Math.floor(Math.random() * 100));
    const sent = Array(datasetLength).fill(0).map(() => Math.floor(Math.random() * 100));
    
    // Update chart data
    this.charts.messageVolume.data.labels = labels;
    this.charts.messageVolume.data.datasets[0].data = received;
    this.charts.messageVolume.data.datasets[1].data = sent;
    this.charts.messageVolume.update();
  }
  
  update(metricsData) {
    if (!metricsData) return;
    
    // In a real implementation, you would use the actual metrics data
    // to update charts. For now, we'll just simulate with random updates
    
    // Update message distribution chart based on current data
    const kubemqToIbmMessages = metricsData.data.bindings.kubemq_to_ibm.messages_sent_total || 0;
    const ibmToKubemqMessages = metricsData.data.bindings.ibm_to_kubemq.messages_sent_total || 0;
    
    // If both are 0, use dummy data for visualization purposes
    const distributionData = [kubemqToIbmMessages || 60, ibmToKubemqMessages || 40];
    this.charts.messageDistribution.data.datasets[0].data = distributionData;
    this.charts.messageDistribution.update();
    
    // Calculate error rates (errors / total messages * 100)
    // Use small error rates if real data isn't available
    const calculateErrorRate = (binding) => {
      const totalMessages = binding.messages_sent_total + binding.messages_received_total;
      const totalErrors = binding.errors_sent_total + binding.errors_received_total;
      
      if (totalMessages === 0) return Math.random() * 3; // Random value for demo
      return (totalErrors / totalMessages * 100).toFixed(1);
    };
    
    const kubemqToIbmErrorRate = calculateErrorRate(metricsData.data.bindings.kubemq_to_ibm);
    const ibmToKubemqErrorRate = calculateErrorRate(metricsData.data.bindings.ibm_to_kubemq);
    
    this.charts.errorRate.data.datasets[0].data = [kubemqToIbmErrorRate, ibmToKubemqErrorRate];
    this.charts.errorRate.update();
  }
}
```

### Health Status Component (healthStatus.js)

```javascript
// components/healthStatus.js
export class HealthStatus {
  constructor(container) {
    this.container = container;
    this.render();
  }
  
  render() {
    this.container.innerHTML = `
      <div>
        <h2 class="text-lg font-semibold mb-4">Health Status</h2>
        
        <div class="mb-6">
          <div id="overall-health-indicator" class="flex items-center justify-center p-4 rounded-lg">
            <div class="text-center">
              <div class="text-6xl mb-2">
                <i class="fas fa-check-circle"></i>
              </div>
              <div class="text-lg font-medium" id="health-status-text">System Healthy</div>
            </div>
          </div>
        </div>
        
        <div class="border-t border-gray-200 dark:border-gray-700 pt-4">
          <h3 class="text-md font-medium mb-3">Component Health</h3>
          <div id="component-health-list">
            <!-- Component health items will be inserted here -->
          </div>
        </div>
      </div>
    `;
  }
  
  update(healthData) {
    if (!healthData) return;
    
    // Update overall health status
    const overallStatus = healthData.data.overall_status;
    const healthIndicator = document.getElementById('overall-health-indicator');
    const healthText = document.getElementById('health-status-text');
    
    if (overallStatus === 'healthy') {
      healthIndicator.className = 'flex items-center justify-center p-4 rounded-lg bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400';
      healthText.textContent = 'System Healthy';
      healthIndicator.querySelector('i').className = 'fas fa-check-circle';
    } else {
      healthIndicator.className = 'flex items-center justify-center p-4 rounded-lg bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400';
      healthText.textContent = 'System Unhealthy';
      healthIndicator.querySelector('i').className = 'fas fa-exclamation-circle';
    }
    
    // Update component health list
    const componentList = document.getElementById('component-health-list');
    let componentsHtml = '';
    
    // Loop through bindings
    for (const [bindingName, binding] of Object.entries(healthData.data.bindings)) {
      componentsHtml += this.createComponentHealthItem(bindingName, binding);
    }
    
    componentList.innerHTML = componentsHtml;
  }
  
  createComponentHealthItem(bindingName, binding) {
    const formattedName = bindingName.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
    
    const sourceStatus = binding.source.status;
    const targetStatus = binding.target.status;
    
    const getStatusIcon = (status) => {
      return status === 'healthy' 
        ? '<i class="fas fa-check-circle text-success"></i>' 
        : '<i class="fas fa-exclamation-circle text-danger"></i>';
    };
    
    return `
      <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 mb-3">
        <div class="font-medium mb-2">${formattedName}</div>
        <div class="grid grid-cols-2 gap-2 text-sm">
          <div class="flex items-center">
            ${getStatusIcon(sourceStatus)}
            <span class="ml-2">Source: ${binding.source.details.connection_status || 'N/A'}</span>
          </div>
          <div class="flex items-center">
            ${getStatusIcon(targetStatus)}
            <span class="ml-2">Target: ${binding.target.details.connection_status || 'N/A'}</span>
          </div>
        </div>
      </div>
    `;
  }
}
```

### Notification Center Component (notificationCenter.js)

```javascript
// components/notificationCenter.js
export class NotificationCenter {
  constructor(container) {
    this.container = container;
    this.notifications = [];
    this.render();
  }
  
  render() {
    this.container.innerHTML = `
      <div class="notification-container flex flex-col space-y-2"></div>
    `;
  }
  
  showNotification(message, type = 'info', duration = 5000) {
    const id = 'notification-' + Date.now();
    const notificationContainer = this.container.querySelector('.notification-container');
    
    const getTypeClasses = (type) => {
      switch (type) {
        case 'success':
          return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 border-green-300 dark:border-green-700';
        case 'error':
          return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300 border-red-300 dark:border-red-700';
        case 'warning':
          return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300 border-yellow-300 dark:border-yellow-700';
        default:
          return 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 border-blue-300 dark:border-blue-700';
      }
    };
    
    const getTypeIcon = (type) => {
      switch (type) {
        case 'success':
          return '<i class="fas fa-check-circle"></i>';
        case 'error':
          return '<i class="fas fa-exclamation-circle"></i>';
        case 'warning':
          return '<i class="fas fa-exclamation-triangle"></i>';
        default:
          return '<i class="fas fa-info-circle"></i>';
      }
    };
    
    const notificationHtml = `
      <div id="${id}" class="notification-item flex items-center p-3 border rounded-lg shadow-sm transform translate-x-full transition-transform duration-300 ${getTypeClasses(type)}">
        <div class="mr-3">${getTypeIcon(type)}</div>
        <div class="flex-grow">${message}</div>
        <button class="ml-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
          <i class="fas fa-times"></i>
        </button>
      </div>
    `;
    
    notificationContainer.insertAdjacentHTML('afterbegin', notificationHtml);
    const notificationElement = document.getElementById(id);
    
    // Animate in
    setTimeout(() => {
      notificationElement.classList.remove('translate-x-full');
    }, 10);
    
    // Set up dismiss button
    notificationElement.querySelector('button').addEventListener('click', () => {
      this.dismissNotification(id);
    });
    
    // Auto dismiss after duration
    setTimeout(() => {
      this.dismissNotification(id);
    }, duration);
    
    // Add to notifications array
    this.notifications.push({
      id,
      element: notificationElement,
      timeout: setTimeout(() => {
        this.dismissNotification(id);
      }, duration)
    });
  }
  
  dismissNotification(id) {
    const notification = this.notifications.find(n => n.id === id);
    if (!notification) return;
    
    // Clear the timeout to prevent double-dismissal
    clearTimeout(notification.timeout);
    
    // Animate out
    notification.element.classList.add('translate-x-full');
    
    // Remove after animation
    setTimeout(() => {
      notification.element.remove();
      this.notifications = this.notifications.filter(n => n.id !== id);
    }, 300);
  }
}
```

## Custom Styles (custom.css)

```css
/* assets/css/custom.css */

/* Custom font settings */
body {
  font-family: 'Inter', sans-serif;
}

code, .monospace {
  font-family: 'Roboto Mono', monospace;
}

/* Custom colors */
.text-success {
  color: #10b981;
}

.text-danger {
  color: #ef4444;
}

.text-warning {
  color: #f59e0b;
}

.text-info {
  color: #3b82f6;
}

.bg-success {
  background-color: #10b981;
}

.bg-danger {
  background-color: #ef4444;
}

.bg-warning {
  background-color: #f59e0b;
}

.bg-info {
  background-color: #3b82f6;
}

/* Animations */
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* Dashboard-specific styles */
.card {
  transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

/* Dark mode specific adjustments */
.dark .card {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
}

.dark .card:hover {
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2);
}

/* Status indicators */
.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.status-healthy {
  background-color: #10b981;
}

.status-unhealthy {
  background-color: #ef4444;
}

.status-warning {
  background-color: #f59e0b;
}

/* Chart customizations */
canvas {
  max-width: 100%;
}
```

## Dashboard REST API Endpoint

To serve the dashboard at `http://localhost:9000/dashboard`, your server needs to implement a handler for this endpoint. Here's a simple example using Express:

```javascript
// server.js example using Express
const express = require('express');
const path = require('path');
const app = express();
const port = 9000;

// Your existing metrics and health API endpoints
app.get('/metrics/', (req, res) => {
  // Return metrics data
  res.json({ success: true, data: { /* your metrics data */ } });
});

app.get('/health/', (req, res) => {
  // Return health data
  res.json({ success: true, data: { /* your health data */ } });
});

// Serve static dashboard files
app.use('/dashboard', express.static(path.join(__dirname, 'dashboard')));

// Start the server
app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});
```

## Final Notes

1. **Error Handling**: Ensure robust error handling for API calls and unexpected data formats.
2. **Accessibility**: Add proper ARIA attributes to make the dashboard accessible.
3. **Security**: Implement proper security measures if the dashboard is exposed outside a secure network.
4. **Documentation**: Include clear documentation for future developers who may need to maintain the dashboard.
5. **Backup Plan**: Implement a graceful fallback if the API is unavailable or returns unexpected data.

IMPORTANT:
1. All Code will be at src/api/static folder
2. use Browser extenstion and tools to test the visual and the functionalites that are working
