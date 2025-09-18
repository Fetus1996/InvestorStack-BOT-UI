// API Keys component
async function loadKeys() {
    try {
        const result = await apiCall('/api/keys');
        if (result.success) {
            displayKeysStatus(result.data);
        }

        // Also load config to show current symbol
        const configResult = await apiCall('/api/config');
        if (configResult.success) {
            updateActiveAPIDisplay(result.data, configResult.data);
        }
    } catch (error) {
        console.error('Failed to load keys status:', error);
    }
}

// Display keys status
function displayKeysStatus(status) {
    const exchange = status.exchange;
    document.getElementById('keys-exchange').value = exchange;
    updateKeysFields(exchange);

    if (exchange === 'okx') {
        document.getElementById('okx-network').value = status.network || 'live';
    }
}

// Update active API display
function updateActiveAPIDisplay(keysStatus, config) {
    const activeApiStatusDiv = document.querySelector('.active-api-status');
    const managementButtons = document.getElementById('api-management-buttons');

    if (!keysStatus.has_keys) {
        // Hide the "Currently Active API" section and management buttons
        activeApiStatusDiv.style.display = 'none';
        managementButtons.style.display = 'none';
        return;
    }

    // Show both the section and management buttons if keys are configured
    activeApiStatusDiv.style.display = 'block';
    managementButtons.style.display = 'block';

    // Update active exchange
    const exchangeText = keysStatus.exchange ? keysStatus.exchange.toUpperCase() : '-';
    document.getElementById('active-exchange').textContent = exchangeText;

    // Update API status
    const statusElement = document.getElementById('active-api-status');
    statusElement.textContent = 'Configured';
    statusElement.className = 'status-configured';

    // Update symbol (keep this as it's useful)
    document.getElementById('active-symbol').textContent = config ? config.symbol || '-' : '-';
}

// Initialize keys form
document.getElementById('keys-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const exchange = document.getElementById('keys-exchange').value;
    const keysData = {
        exchange: exchange
    };

    if (exchange === 'okx') {
        keysData.okx_api_key = document.getElementById('okx-api-key').value;
        keysData.okx_api_secret = document.getElementById('okx-api-secret').value;
        keysData.okx_passphrase = document.getElementById('okx-passphrase').value;
        keysData.network = document.getElementById('okx-network').value;
    } else {
        keysData.bitkub_api_key = document.getElementById('bitkub-api-key').value;
        keysData.bitkub_api_secret = document.getElementById('bitkub-api-secret').value;
    }

    // Validate
    if (exchange === 'okx') {
        if (!keysData.okx_api_key || !keysData.okx_api_secret || !keysData.okx_passphrase) {
            showNotification('Please fill in all OKX API fields', 'error');
            return;
        }
    } else {
        if (!keysData.bitkub_api_key || !keysData.bitkub_api_secret) {
            showNotification('Please fill in all Bitkub API fields', 'error');
            return;
        }
    }

    try {
        const result = await apiCall('/api/keys', {
            method: 'POST',
            body: JSON.stringify(keysData)
        });

        if (result.success) {
            showNotification('API keys saved successfully', 'success');

            // Clear form fields for security
            if (exchange === 'okx') {
                document.getElementById('okx-api-key').value = '';
                document.getElementById('okx-api-secret').value = '';
                document.getElementById('okx-passphrase').value = '';
            } else {
                document.getElementById('bitkub-api-key').value = '';
                document.getElementById('bitkub-api-secret').value = '';
            }

            // Display masked keys
            if (result.data) {
                displayMaskedKeys(result.data);
            }

            // Reload keys status to update active API display
            await loadKeys();
        }
    } catch (error) {
        showNotification('Failed to save API keys', 'error');
    }
});

// Exchange selector change handler
document.getElementById('keys-exchange').addEventListener('change', (e) => {
    updateKeysFields(e.target.value);
});

// Update keys fields based on exchange
function updateKeysFields(exchange) {
    const okxFields = document.getElementById('okx-fields');
    const bitkubFields = document.getElementById('bitkub-fields');

    if (exchange === 'okx') {
        okxFields.style.display = 'grid';
        bitkubFields.style.display = 'none';
    } else {
        okxFields.style.display = 'none';
        bitkubFields.style.display = 'grid';
    }
}

// Display masked keys
function displayMaskedKeys(data) {
    let message = 'Keys saved:\n';

    if (data.exchange === 'okx') {
        if (data.okx_api_key) message += `API Key: ${data.okx_api_key}\n`;
        if (data.okx_api_secret) message += `Secret: ${data.okx_api_secret}\n`;
        if (data.okx_passphrase) message += `Passphrase: ${data.okx_passphrase}\n`;
    } else {
        if (data.bitkub_api_key) message += `API Key: ${data.bitkub_api_key}\n`;
        if (data.bitkub_api_secret) message += `Secret: ${data.bitkub_api_secret}\n`;
    }

    modal.show('API Keys Saved', `<pre>${message}</pre>`);
}

// Test API Connection
document.getElementById('test-connection').addEventListener('click', async () => {
    const statusDiv = document.getElementById('connection-status');
    const resultDiv = document.getElementById('connection-result');

    // Show loading
    statusDiv.style.display = 'block';
    resultDiv.innerHTML = '<div class="loading">Testing connection...</div>';
    resultDiv.className = '';

    try {
        const result = await apiCall('/api/keys/test', {
            method: 'POST'
        });

        if (result.success) {
            resultDiv.innerHTML = `
                <div class="success">
                    ✅ ${result.message}
                    <br>Exchange: ${result.data.exchange.toUpperCase()}
                    ${result.data.network ? `<br>Network: ${result.data.network.toUpperCase()}` : ''}
                </div>
            `;
            resultDiv.className = 'success-message';

            // Display balance from test result
            if (result.data.balance && Object.keys(result.data.balance).length > 0) {
                let balanceHtml = '<h4>Account Balance:</h4>';

                // Display total portfolio value first if available
                if (result.data.total_value_thb) {
                    balanceHtml += `<div style="background: #e8f5e8; padding: 10px; margin-bottom: 15px; border-radius: 5px; border: 1px solid #4caf50;">
                        <strong style="color: #2e7d32; font-size: 16px;">Total Portfolio Value: ${result.data.total_value_thb.toLocaleString('th-TH', {minimumFractionDigits: 2, maximumFractionDigits: 2})} THB</strong>
                    </div>`;
                }

                balanceHtml += '<ul style="list-style: none; padding-left: 0;">';
                for (const [currency, balanceInfo] of Object.entries(result.data.balance)) {
                    balanceHtml += `<li style="margin-bottom: 10px;">
                        <strong>${currency}:</strong><br>
                        <div style="padding-left: 20px;">
                            Total: ${balanceInfo.total.toFixed(8)}<br>
                            Available: ${balanceInfo.free.toFixed(8)}<br>
                            In Orders: ${balanceInfo.used.toFixed(8)}
                        </div>
                    </li>`;
                }
                balanceHtml += '</ul>';
                resultDiv.innerHTML += balanceHtml;
            } else {
                resultDiv.innerHTML += '<h4>Account Balance:</h4><p>No balance found or all balances are zero.</p>';
            }
        } else {
            resultDiv.innerHTML = `
                <div class="error">
                    ❌ ${result.message}
                    <br><small>${result.error || ''}</small>
                </div>
            `;
            resultDiv.className = 'error-message';
        }
    } catch (error) {
        resultDiv.innerHTML = `
            <div class="error">
                ❌ Connection test failed
                <br><small>${error.message}</small>
            </div>
        `;
        resultDiv.className = 'error-message';
    }
});

// Edit API button handler
document.getElementById('edit-api-btn').addEventListener('click', async () => {
    const editSection = document.getElementById('edit-api-section');

    if (editSection.style.display === 'none') {
        // Load current exchange from config
        try {
            const result = await apiCall('/api/keys');
            if (result.success) {
                const exchange = result.data.exchange;
                document.getElementById('edit-exchange').value = exchange;
                updateEditFields(exchange);
            }
        } catch (error) {
            console.error('Failed to load current exchange:', error);
        }
        editSection.style.display = 'block';
    } else {
        editSection.style.display = 'none';
    }
});

// Cancel edit button handler
document.getElementById('cancel-edit').addEventListener('click', () => {
    document.getElementById('edit-api-section').style.display = 'none';
    // Clear form fields
    document.getElementById('edit-api-form').reset();
});

// Exchange selector for edit form
document.getElementById('edit-exchange').addEventListener('change', (e) => {
    updateEditFields(e.target.value);
});

// Update edit fields based on exchange
function updateEditFields(exchange) {
    const okxFields = document.getElementById('edit-okx-fields');
    const bitkubFields = document.getElementById('edit-bitkub-fields');

    if (exchange === 'okx') {
        okxFields.style.display = 'grid';
        bitkubFields.style.display = 'none';
    } else {
        okxFields.style.display = 'none';
        bitkubFields.style.display = 'grid';
    }
}

// Edit API form submission
document.getElementById('edit-api-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const exchange = document.getElementById('edit-exchange').value;
    const keysData = {
        exchange: exchange
    };

    if (exchange === 'okx') {
        keysData.okx_api_key = document.getElementById('edit-okx-api-key').value;
        keysData.okx_api_secret = document.getElementById('edit-okx-api-secret').value;
        keysData.okx_passphrase = document.getElementById('edit-okx-passphrase').value;
        keysData.network = document.getElementById('edit-okx-network').value;

        // Validate OKX fields
        if (!keysData.okx_api_key || !keysData.okx_api_secret || !keysData.okx_passphrase) {
            showNotification('Please fill in all OKX API fields', 'error');
            return;
        }
    } else {
        keysData.bitkub_api_key = document.getElementById('edit-bitkub-api-key').value;
        keysData.bitkub_api_secret = document.getElementById('edit-bitkub-api-secret').value;

        // Validate Bitkub fields
        if (!keysData.bitkub_api_key || !keysData.bitkub_api_secret) {
            showNotification('Please fill in all Bitkub API fields', 'error');
            return;
        }
    }

    try {
        // Update API keys
        const result = await apiCall('/api/keys', {
            method: 'POST',
            body: JSON.stringify(keysData)
        });

        if (result.success) {
            // Update config to match exchange
            const configResult = await apiCall('/api/config');
            if (configResult.success) {
                const config = configResult.data;
                config.exchange = exchange;

                // Update symbol based on exchange
                if (exchange === 'okx') {
                    config.symbol = 'BTC/USDT';
                    config.network = keysData.network;
                } else if (exchange === 'bitkub') {
                    config.symbol = 'THB_BTC';
                }

                // Save updated config
                await apiCall('/api/config', {
                    method: 'POST',
                    body: JSON.stringify(config)
                });
            }

            showNotification('API credentials updated successfully', 'success');

            // Clear form fields
            document.getElementById('edit-api-form').reset();

            // Hide edit section
            document.getElementById('edit-api-section').style.display = 'none';

            // Reload keys page to update display
            await loadKeys();

            // Also update dashboard API indicator
            await loadAPIStatus();
        }
    } catch (error) {
        showNotification('Failed to update API credentials', 'error');
    }
});

// Delete API button handler - test which button works
document.addEventListener('click', async (e) => {
    // Test ANY click on buttons with delete-related classes or IDs
    if (e.target.tagName === 'BUTTON' &&
        (e.target.textContent.includes('Delete') ||
         e.target.className.includes('delete') ||
         e.target.id.includes('delete'))) {

        alert(`Button clicked: ID="${e.target.id}", Class="${e.target.className}", Text="${e.target.textContent}"`);

        e.preventDefault();
        e.stopPropagation();

        // Direct delete for now
        try {
            const result = await apiCall('/api/keys', {
                method: 'DELETE'
            });

            if (result.success) {
                showNotification('API keys deleted successfully', 'success');
                await loadKeys();
            } else {
                showNotification(result.message || 'Failed to delete API keys', 'error');
            }
        } catch (error) {
            console.error('Delete error:', error);
            showNotification('Failed to delete API keys: ' + error.message, 'error');
        }
    }
});

// Test connection from edit form
document.getElementById('test-edit-connection').addEventListener('click', async () => {
    const exchange = document.getElementById('edit-exchange').value;
    const keysData = {
        exchange: exchange
    };

    if (exchange === 'okx') {
        keysData.okx_api_key = document.getElementById('edit-okx-api-key').value;
        keysData.okx_api_secret = document.getElementById('edit-okx-api-secret').value;
        keysData.okx_passphrase = document.getElementById('edit-okx-passphrase').value;
        keysData.network = document.getElementById('edit-okx-network').value;

        if (!keysData.okx_api_key || !keysData.okx_api_secret || !keysData.okx_passphrase) {
            showNotification('Please fill in all OKX API fields before testing', 'error');
            return;
        }
    } else {
        keysData.bitkub_api_key = document.getElementById('edit-bitkub-api-key').value;
        keysData.bitkub_api_secret = document.getElementById('edit-bitkub-api-secret').value;

        if (!keysData.bitkub_api_key || !keysData.bitkub_api_secret) {
            showNotification('Please fill in all Bitkub API fields before testing', 'error');
            return;
        }
    }

    showNotification('Testing connection...', 'info');

    try {
        // First save the temporary keys
        const saveResult = await apiCall('/api/keys', {
            method: 'POST',
            body: JSON.stringify(keysData)
        });

        if (saveResult.success) {
            // Then test the connection
            const testResult = await apiCall('/api/keys/test', {
                method: 'POST'
            });

            if (testResult.success) {
                showNotification('✅ Connection successful!', 'success');
            } else {
                showNotification(`❌ Connection failed: ${testResult.message}`, 'error');
            }
        }
    } catch (error) {
        showNotification(`Connection test failed: ${error.message}`, 'error');
    }
});