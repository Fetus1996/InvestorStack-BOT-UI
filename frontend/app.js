// Main application script
let ws = null;
let currentStatus = null;

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    initializeTabs();
    initializeWebSocket();
    loadInitialData();
});

// Tab switching
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.dataset.tab;

            // Update active states
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            button.classList.add('active');
            document.getElementById(`${targetTab}-tab`).classList.add('active');

            // Load tab-specific data
            switch(targetTab) {
                case 'dashboard':
                    loadDashboard();
                    break;
                case 'config':
                    loadConfig();
                    break;
                case 'keys':
                    loadKeys();
                    break;
                case 'logs':
                    loadLogs();
                    break;
            }
        });
    });
}

// WebSocket connection
function initializeWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
        document.getElementById('ws-status').className = 'ws-status connected';
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        document.getElementById('ws-status').className = 'ws-status disconnected';
        // Reconnect after 3 seconds
        setTimeout(initializeWebSocket, 3000);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    // Keep alive
    setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
        }
    }, 30000);
}

// Handle WebSocket messages
function handleWebSocketMessage(data) {
    switch(data.type) {
        case 'initial_status':
            updateStatus(data.data);
            break;
        case 'state_update':
            handleStateUpdate(data.data);
            break;
        default:
            console.log('Unknown WebSocket message:', data);
    }
}

// Handle state updates
function handleStateUpdate(update) {
    switch(update.type) {
        case 'state_change':
            fetchStatus();
            break;
        case 'pnl_update':
            updatePnL(update.realized, update.unrealized);
            break;
        case 'inventory_update':
            updateInventory(update.inventory);
            break;
        case 'levels_update':
            updateActiveLevels(update.levels);
            break;
        case 'error':
            showNotification('Error: ' + update.message, 'error');
            break;
    }
}

// Load initial data
async function loadInitialData() {
    await fetchStatus();
    loadDashboard();
}

// Fetch bot status
async function fetchStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        if (data.success) {
            updateStatus(data.data);
        }
    } catch (error) {
        console.error('Failed to fetch status:', error);
    }
}

// Update status display
function updateStatus(status) {
    currentStatus = status;

    // Update status indicators
    const statusEl = document.getElementById('bot-status');
    statusEl.textContent = status.state;
    statusEl.className = 'status-indicator';

    if (status.state === 'RUNNING' || status.state === 'SIM_RUNNING') {
        statusEl.classList.add('running');
    } else if (status.state === 'STARTING' || status.state === 'STOPPING') {
        statusEl.classList.add('starting');
    }

    document.getElementById('bot-mode').textContent = status.mode.toUpperCase();
    document.getElementById('exchange-name').textContent = status.exchange.toUpperCase();
    document.getElementById('network-type').textContent = (status.network || 'LIVE').toUpperCase();

    // Update PnL
    updatePnL(status.pnl.realized, status.pnl.unrealized);

    // Update inventory
    updateInventory(status.inventory);

    // Update active levels
    document.getElementById('active-levels-count').textContent = status.active_levels.length;

    // Update control buttons
    updateControlButtons(status.state);
}

// Update PnL display
function updatePnL(realized, unrealized) {
    document.getElementById('pnl-realized').textContent = realized.toFixed(2);
    document.getElementById('pnl-unrealized').textContent = unrealized.toFixed(2);
}

// Update inventory display
function updateInventory(inventory) {
    const display = document.getElementById('inventory-display');
    if (!inventory || Object.keys(inventory).length === 0) {
        display.textContent = '-';
        return;
    }

    const items = [];
    for (const [currency, amount] of Object.entries(inventory)) {
        if (amount > 0) {
            items.push(`${amount.toFixed(4)} ${currency}`);
        }
    }
    display.textContent = items.join(', ') || '-';
}

// Update active levels count
function updateActiveLevels(levels) {
    document.getElementById('active-levels-count').textContent = levels.length;
}

// Update control buttons based on state
function updateControlButtons(state) {
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');

    if (state === 'RUNNING' || state === 'SIM_RUNNING') {
        startBtn.disabled = true;
        stopBtn.disabled = false;
    } else if (state === 'STOPPED') {
        startBtn.disabled = false;
        stopBtn.disabled = true;
    } else {
        startBtn.disabled = true;
        stopBtn.disabled = true;
    }
}

// Show notification
function showNotification(message, type = 'info') {
    // Simple notification (can be enhanced with a toast library)
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#17a2b8'};
        color: white;
        border-radius: 5px;
        z-index: 2000;
        animation: slideIn 0.3s;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// API helper function
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        const data = await response.json();
        if (!data.success && data.error) {
            throw new Error(data.error);
        }

        return data;
    } catch (error) {
        console.error('API call failed:', error);
        showNotification(error.message, 'error');
        throw error;
    }
}