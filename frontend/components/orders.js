// Orders display component
async function loadActiveOrders() {
    try {
        const result = await apiCall('/api/orders/active');
        if (result.success) {
            displayActiveOrders(result.data);
        }
    } catch (error) {
        console.error('Failed to load active orders:', error);
    }
}

// Display active orders in a table
function displayActiveOrders(data) {
    const container = document.getElementById('active-orders-container');
    if (!container) return;

    // Update count
    const countElement = document.getElementById('open-orders-count');
    if (countElement) {
        countElement.textContent = data.count;
    }

    // Create table
    const table = document.createElement('table');
    table.className = 'orders-table';

    const thead = `
        <thead>
            <tr>
                <th>Price</th>
                <th>Side</th>
                <th>Amount</th>
                <th>Action</th>
            </tr>
        </thead>
    `;

    const tbody = document.createElement('tbody');

    data.orders.forEach(order => {
        const row = document.createElement('tr');
        const sideClass = order.side === 'buy' ? 'order-buy' : 'order-sell';
        row.className = sideClass;

        row.innerHTML = `
            <td>$${order.price.toFixed(2)}</td>
            <td style="font-weight: 600;">${order.side.toUpperCase()}</td>
            <td>${order.amount.toFixed(8)} BTC</td>
            <td>
                <button class="btn-cancel-order" onclick="cancelSingleOrder('${order.id}')">
                    Cancel
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });

    table.innerHTML = thead;
    table.appendChild(tbody);

    container.innerHTML = '';
    container.appendChild(table);

    // Add summary
    const summary = document.createElement('div');
    summary.className = 'orders-summary';
    summary.innerHTML = `
        <div>Total: ${data.count} orders</div>
        <div>Buy: ${data.buy_count} | Sell: ${data.sell_count}</div>
    `;
    container.appendChild(summary);
}

// Cancel single order
async function cancelSingleOrder(orderId) {
    if (!confirm(`Cancel order ${orderId}?`)) return;

    try {
        const result = await apiCall(`/api/orders/${orderId}/cancel`, { method: 'POST' });
        if (result.success) {
            showNotification('Order cancelled', 'success');
            loadActiveOrders();
            loadGridLevels();
        }
    } catch (error) {
        showNotification('Failed to cancel order', 'error');
    }
}

// Make functions globally available
window.loadActiveOrders = loadActiveOrders;
window.cancelSingleOrder = cancelSingleOrder;