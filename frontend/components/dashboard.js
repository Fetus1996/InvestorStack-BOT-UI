// Dashboard component
async function loadDashboard() {
    loadGridLevels();
    initializeControlButtons();
    await loadAPIStatus();
    await loadPortfolioValue();
}

// Load API status for dashboard
async function loadAPIStatus() {
    try {
        const result = await apiCall('/api/keys');
        if (result.success) {
            const exchangeElement = document.getElementById('dashboard-exchange');
            const statusBadge = document.getElementById('dashboard-api-status');

            exchangeElement.textContent = result.data.exchange.toUpperCase();

            if (result.data.has_keys) {
                statusBadge.textContent = 'CONFIGURED';
                statusBadge.className = 'api-badge configured';
            } else {
                statusBadge.textContent = 'NOT CONFIGURED';
                statusBadge.className = 'api-badge not-configured';
            }
        }
    } catch (error) {
        console.error('Failed to load API status:', error);
    }
}

// Load portfolio value in THB
async function loadPortfolioValue() {
    try {
        const result = await apiCall('/api/keys/test', {
            method: 'POST'
        });

        const portfolioElement = document.getElementById('portfolio-value-thb');

        if (result.success && result.data.total_value_thb) {
            const thbValue = result.data.total_value_thb.toLocaleString('th-TH', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
            portfolioElement.textContent = `${thbValue} THB`;
        } else {
            portfolioElement.textContent = '-';
        }
    } catch (error) {
        console.error('Failed to load portfolio value:', error);
        document.getElementById('portfolio-value-thb').textContent = '-';
    }
}

// Initialize control buttons
function initializeControlButtons() {
    // Start button
    document.getElementById('start-btn').addEventListener('click', () => {
        modal.confirm(
            'Start Bot',
            'Are you sure you want to start the trading bot?',
            async () => {
                try {
                    const result = await apiCall('/api/start', {
                        method: 'POST',
                        body: JSON.stringify({ confirm: true })
                    });
                    if (result.success) {
                        showNotification('Bot started successfully', 'success');
                        fetchStatus();
                    }
                } catch (error) {
                    showNotification('Failed to start bot', 'error');
                }
            }
        );
    });

    // Stop button
    document.getElementById('stop-btn').addEventListener('click', () => {
        modal.confirm(
            'Stop Bot',
            'Are you sure you want to stop the trading bot?',
            async () => {
                try {
                    const result = await apiCall('/api/stop', {
                        method: 'POST',
                        body: JSON.stringify({ confirm: true })
                    });
                    if (result.success) {
                        showNotification('Bot stopped successfully', 'success');
                        fetchStatus();
                    }
                } catch (error) {
                    showNotification('Failed to stop bot', 'error');
                }
            }
        );
    });

    // Reset button
    document.getElementById('reset-btn').addEventListener('click', () => {
        modal.resetOptions(async (clearPositions) => {
            try {
                const result = await apiCall('/api/reset', {
                    method: 'POST',
                    body: JSON.stringify({
                        confirm: true,
                        clear_positions: clearPositions,
                        cancel_only: !clearPositions
                    })
                });
                if (result.success) {
                    showNotification('Grid reset successfully', 'success');
                    fetchStatus();
                    loadGridLevels();
                }
            } catch (error) {
                showNotification('Failed to reset grid', 'error');
            }
        });
    });

    // Clear button
    document.getElementById('clear-btn').addEventListener('click', () => {
        modal.confirm(
            'Clear Orders',
            'Are you sure you want to cancel all open orders?',
            async () => {
                try {
                    const result = await apiCall('/api/reset', {
                        method: 'POST',
                        body: JSON.stringify({
                            confirm: true,
                            clear_positions: false,
                            cancel_only: true
                        })
                    });
                    if (result.success) {
                        showNotification('Orders cleared successfully', 'success');
                        fetchStatus();
                        // Add small delay to ensure backend has completed cancellation
                        setTimeout(() => {
                            loadGridLevels(); // Refresh grid display
                        }, 1000);
                    }
                } catch (error) {
                    showNotification('Failed to clear orders', 'error');
                }
            }
        );
    });
}

// Load grid levels and active orders
async function loadGridLevels() {
    try {
        // Load both levels and actual orders
        const [levelsResult, ordersResult] = await Promise.all([
            apiCall('/api/levels'),
            apiCall('/api/orders/active')
        ]);

        if (ordersResult.success) {
            // Display actual orders instead of just levels
            displayActiveOrders(ordersResult.data);
        } else if (levelsResult.success) {
            // Fallback to levels if orders endpoint fails
            displayGridLevels(levelsResult.data.levels);
            displayZoneControls(levelsResult.data.levels);
        }
    } catch (error) {
        console.error('Failed to load grid levels:', error);
    }
}

// Display active orders (all individual orders from exchange)
function displayActiveOrders(ordersData) {
    const tbody = document.getElementById('grid-levels-body');
    tbody.innerHTML = '';

    // Sort orders by price descending (highest price first)
    const sortedOrders = [...ordersData.orders].sort((a, b) => b.price - a.price);

    sortedOrders.forEach((order, idx) => {
        const row = document.createElement('tr');
        const sideClass = order.side === 'buy' ? 'row-buy' : 'row-sell';
        row.className = sideClass;

        row.innerHTML = `
            <td>${sortedOrders.length - idx}</td>
            <td>$${order.price.toFixed(2)}</td>
            <td style="font-weight: 600;">${order.side.toUpperCase()}</td>
            <td>Zone ${order.zone_id || 0}</td>
            <td>Active</td>
            <td><button class="btn-cancel-order" data-level="${idx}" data-order-id="${order.id}">Cancel</button></td>
        `;
        tbody.appendChild(row);
    });

    // Update open orders count with actual count
    document.getElementById('open-orders-count').textContent = ordersData.count;
}

// Display grid levels
function displayGridLevels(levels) {
    const tbody = document.getElementById('grid-levels-body');
    tbody.innerHTML = '';

    // Sort levels by price descending (highest price first)
    const sortedLevels = [...levels].sort((a, b) => b.price - a.price);

    sortedLevels.forEach(level => {
        const row = document.createElement('tr');
        const sideClass = level.side === 'buy' ? 'row-buy' : level.side === 'sell' ? 'row-sell' : 'row-mid';
        row.className = `${sideClass} ${level.active ? '' : 'row-inactive'}`;

        console.log(`Creating button for level: ${level.index}, active: ${level.active}`);

        // Create all cells manually instead of using innerHTML
        const levelCell = document.createElement('td');
        levelCell.textContent = level.index;

        const priceCell = document.createElement('td');
        priceCell.textContent = `$${level.price.toFixed(2)}`;

        const sideCell = document.createElement('td');
        sideCell.style.fontWeight = '600';
        sideCell.textContent = level.side.toUpperCase();

        const zoneCell = document.createElement('td');
        zoneCell.textContent = `Zone ${level.zone_id}`;

        const statusCell = document.createElement('td');
        statusCell.textContent = level.active ? 'Active' : 'Inactive';

        const actionCell = document.createElement('td');
        const actionButton = document.createElement('button');

        if (level.active) {
            actionButton.className = 'btn-cancel-order';
            actionButton.textContent = 'Cancel';
            actionButton.setAttribute('data-level', level.index.toString());
            console.log(`Set data-level to: ${level.index.toString()}`);
        } else {
            actionButton.className = 'btn-enable-order';
            actionButton.textContent = 'Enable';
            actionButton.setAttribute('data-level', level.index.toString());
            console.log(`Set data-level to: ${level.index.toString()}`);
        }

        actionCell.appendChild(actionButton);

        // Append all cells to row
        row.appendChild(levelCell);
        row.appendChild(priceCell);
        row.appendChild(sideCell);
        row.appendChild(zoneCell);
        row.appendChild(statusCell);
        row.appendChild(actionCell);
        tbody.appendChild(row);
    });

    // Update open orders count
    const activeCount = levels.filter(l => l.active).length;
    document.getElementById('open-orders-count').textContent = activeCount;
}

// Display zone controls
function displayZoneControls(levels) {
    const container = document.getElementById('zone-toggles');
    container.innerHTML = '';

    // Get unique zones
    const zones = new Map();
    levels.forEach(level => {
        if (!zones.has(level.zone_id)) {
            zones.set(level.zone_id, level.active);
        }
    });

    // Create toggle buttons for each zone
    zones.forEach((isActive, zoneId) => {
        const button = document.createElement('button');
        button.className = `zone-toggle ${isActive ? 'enabled' : ''}`;
        button.textContent = `Zone ${zoneId}`;
        button.dataset.zoneId = zoneId;
        button.dataset.enabled = isActive;

        button.addEventListener('click', async () => {
            const currentlyEnabled = button.dataset.enabled === 'true';
            const newState = !currentlyEnabled;

            try {
                const endpoint = newState ?
                    `/api/zones/${zoneId}/enable` :
                    `/api/zones/${zoneId}/disable`;

                const result = await apiCall(endpoint, { method: 'POST' });

                if (result.success) {
                    button.dataset.enabled = newState;
                    button.className = `zone-toggle ${newState ? 'enabled' : ''}`;
                    showNotification(`Zone ${zoneId} ${newState ? 'enabled' : 'disabled'}`, 'success');
                    loadGridLevels(); // Refresh grid levels
                }
            } catch (error) {
                showNotification(`Failed to toggle zone ${zoneId}`, 'error');
            }
        });

        container.appendChild(button);
    });
}

// Global click listener for cancel buttons
document.addEventListener('click', function(e) {
    console.log('Click on element:', e.target.tagName, e.target.className, 'data-level:', e.target.getAttribute('data-level'));

    if (e.target.classList.contains('btn-cancel-order')) {
        e.preventDefault();
        e.stopPropagation();

        const levelIndex = e.target.getAttribute('data-level');
        const orderId = e.target.getAttribute('data-order-id');

        console.log('Cancel button clicked - level:', levelIndex, 'orderId:', orderId);

        if (orderId) {
            // Cancel by order ID
            cancelOrderById(orderId);
        } else if (levelIndex !== null && levelIndex !== undefined) {
            // Cancel by level
            cancelOrder(parseInt(levelIndex));
        }
    }

    if (e.target.classList.contains('btn-enable-order')) {
        e.preventDefault();
        e.stopPropagation();

        const levelIndex = e.target.getAttribute('data-level');
        console.log('Enable button clicked for level:', levelIndex, 'type:', typeof levelIndex);

        if (levelIndex !== null && levelIndex !== undefined) {
            enableOrder(parseInt(levelIndex));
        } else {
            console.error('data-level attribute is null or undefined');
            alert('Error: Could not find level index');
        }
    }
});

// Cancel specific order
async function cancelOrder(levelIndex) {
    try {
        const result = await apiCall(`/api/orders/level/${levelIndex}/cancel`, {
            method: 'POST'
        });

        if (result.success) {
            showNotification(`Order at level ${levelIndex} cancelled`, 'success');
            loadGridLevels(); // Refresh grid
            await loadPortfolioValue(); // Refresh portfolio value
        } else {
            showNotification(result.message || `Failed to cancel order at level ${levelIndex}`, 'error');
        }
    } catch (error) {
        console.error('Cancel error:', error);
        showNotification(`Failed to cancel order at level ${levelIndex}`, 'error');
    }
}

// Enable specific order (re-place order at level)
async function enableOrder(levelIndex) {
    try {
        const result = await apiCall(`/api/orders/level/${levelIndex}/enable`, {
            method: 'POST'
        });
        if (result.success) {
            showNotification(`Order at level ${levelIndex} enabled`, 'success');
            loadGridLevels(); // Refresh grid
            await loadPortfolioValue(); // Refresh portfolio value
        } else {
            showNotification(result.message || `Failed to enable order at level ${levelIndex}`, 'error');
        }
    } catch (error) {
        console.error('Enable error:', error);
        showNotification(`Failed to enable order at level ${levelIndex}`, 'error');
    }
}

// Cancel order by ID
async function cancelOrderById(orderId) {
    try {
        const result = await apiCall(`/api/orders/${orderId}/cancel`, { method: 'POST' });
        if (result.success) {
            showNotification('Order cancelled', 'success');
            loadGridLevels();
            await loadPortfolioValue();
        } else {
            showNotification(result.message || 'Failed to cancel order', 'error');
        }
    } catch (error) {
        console.error('Cancel error:', error);
        showNotification('Failed to cancel order', 'error');
    }
}

// Make functions globally available
window.cancelOrder = cancelOrder;
window.enableOrder = enableOrder;
window.cancelOrderById = cancelOrderById;