// Manual Sync functionality
function showManualSyncDialog() {
    // Create modal HTML
    const modalHTML = `
        <div id="manual-sync-modal" class="modal">
            <div class="modal-content">
                <span class="close">&times;</span>
                <h2>Manual Order Sync</h2>
                <p>Enter your open orders from Bitkub (paste from exchange):</p>
                <textarea id="orders-input" placeholder="Example:
436044722,3600000,0.00002770,buy
436044723,3600000,0.00002770,buy
436044724,3650000,0.00002732,buy
355045002,3700000,0.00002702,sell
355045003,3700000,0.00002702,sell
355045001,3750000,0.00002666,sell" rows="10" style="width: 100%; font-family: monospace;"></textarea>
                <div style="margin-top: 10px;">
                    <small>Format: OrderID,Price,Amount,Side (one per line)</small>
                </div>
                <div style="margin-top: 20px;">
                    <button class="btn btn-primary" onclick="executeManualSync()">Sync Orders</button>
                    <button class="btn btn-secondary" onclick="closeManualSyncModal()">Cancel</button>
                </div>
            </div>
        </div>
        <style>
        .modal {
            display: block;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.4);
        }
        .modal-content {
            background-color: #1e1e1e;
            margin: 10% auto;
            padding: 20px;
            border: 1px solid #333;
            width: 600px;
            border-radius: 10px;
        }
        .close {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        .close:hover { color: #fff; }
        #orders-input {
            background: #2a2a2a;
            color: #fff;
            border: 1px solid #444;
            padding: 10px;
            border-radius: 5px;
        }
        </style>
    `;

    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Add close event
    document.querySelector('.close').onclick = closeManualSyncModal;
    document.getElementById('manual-sync-modal').onclick = (e) => {
        if (e.target === document.getElementById('manual-sync-modal')) {
            closeManualSyncModal();
        }
    };
}

function closeManualSyncModal() {
    const modal = document.getElementById('manual-sync-modal');
    if (modal) modal.remove();
}

async function executeManualSync() {
    const input = document.getElementById('orders-input').value.trim();
    if (!input) {
        showNotification('Please enter orders', 'error');
        return;
    }

    try {
        // Parse the input
        const lines = input.split('\n').filter(line => line.trim());
        const orders = lines.map(line => {
            const parts = line.split(',').map(p => p.trim());
            if (parts.length !== 4) {
                throw new Error(`Invalid format in line: ${line}`);
            }
            return {
                id: parts[0],
                price: parseFloat(parts[1]),
                amount: parseFloat(parts[2]),
                side: parts[3].toLowerCase()
            };
        });

        // Send to API
        const result = await apiCall('/api/sync/manual', {
            method: 'POST',
            body: JSON.stringify({ orders })
        });

        if (result.success) {
            showNotification(`Successfully synced ${result.data.synced_count} orders`, 'success');
            closeManualSyncModal();

            // Reload the dashboard
            if (window.loadDashboard) loadDashboard();
            if (window.loadGridLevels) loadGridLevels();
        } else {
            showNotification('Sync failed: ' + result.error, 'error');
        }
    } catch (error) {
        showNotification('Error parsing orders: ' + error.message, 'error');
    }
}

// Attach to button
document.addEventListener('DOMContentLoaded', () => {
    const syncBtn = document.getElementById('manual-sync-btn');
    if (syncBtn) {
        syncBtn.addEventListener('click', showManualSyncDialog);
    }
});

// Make functions globally available
window.showManualSyncDialog = showManualSyncDialog;
window.closeManualSyncModal = closeManualSyncModal;
window.executeManualSync = executeManualSync;