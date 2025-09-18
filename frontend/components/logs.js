// Logs component
async function loadLogs(filter = '') {
    try {
        const params = new URLSearchParams();
        if (filter) params.append('action', filter);
        params.append('limit', '100');

        const result = await apiCall(`/api/logs?${params}`);
        if (result.success) {
            displayLogs(result.data.logs);
        }
    } catch (error) {
        console.error('Failed to load logs:', error);
    }
}

// Display logs
function displayLogs(logs) {
    const tbody = document.getElementById('logs-body');
    tbody.innerHTML = '';

    if (logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No logs available</td></tr>';
        return;
    }

    logs.forEach(log => {
        const row = document.createElement('tr');
        const timestamp = new Date(log.timestamp).toLocaleString();
        const details = JSON.stringify(log.params, null, 2);

        row.innerHTML = `
            <td>${timestamp}</td>
            <td>${log.action}</td>
            <td>${log.user}</td>
            <td>${log.mode}</td>
            <td><pre style="margin: 0; font-size: 12px;">${details}</pre></td>
            <td>${log.result}</td>
        `;
        tbody.appendChild(row);
    });
}

// Initialize log controls
document.getElementById('refresh-logs').addEventListener('click', () => {
    const filter = document.getElementById('log-filter').value;
    loadLogs(filter);
});

document.getElementById('log-filter').addEventListener('change', (e) => {
    loadLogs(e.target.value);
});

// Auto-refresh logs via WebSocket
if (typeof handleStateUpdate !== 'undefined') {
    const originalHandler = handleStateUpdate;
    window.handleStateUpdate = function(update) {
        originalHandler(update);

        // Refresh logs on relevant updates
        if (update.type === 'state_change' || update.type === 'zone_toggle') {
            const activeTab = document.querySelector('.tab-content.active');
            if (activeTab && activeTab.id === 'logs-tab') {
                const filter = document.getElementById('log-filter').value;
                loadLogs(filter);
            }
        }
    };
}