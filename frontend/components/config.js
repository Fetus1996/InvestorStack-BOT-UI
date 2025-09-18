// Config component
async function loadConfig() {
    try {
        const result = await apiCall('/api/config');
        if (result.success) {
            displayConfig(result.data);
        }
    } catch (error) {
        console.error('Failed to load config:', error);
    }
}

// Display configuration
function displayConfig(config) {
    document.getElementById('upper-bound').value = config.upper_bound;
    document.getElementById('lower-bound').value = config.lower_bound;
    document.getElementById('total-levels').value = config.total_levels;
    document.getElementById('spacing-type').value = config.spacing_type;
    // Format with full precision for small numbers
    document.getElementById('position-size').value = config.position_size.toFixed(8).replace(/\.?0+$/, '');
    document.getElementById('max-exposure').value = config.max_exposure.toFixed(8).replace(/\.?0+$/, '');
    document.getElementById('mode').value = config.mode;
    document.getElementById('exchange').value = config.exchange;
    document.getElementById('network').value = config.network || 'live';
    document.getElementById('symbol').value = config.symbol;
    document.getElementById('enabled').checked = config.enabled;

    // Update network visibility
    updateNetworkVisibility(config.exchange);

    // Update symbol hint
    updateSymbolHint(config.exchange);
}

// Initialize config form
document.getElementById('config-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData(e.target);
    // Parse numbers with full precision
    const positionSize = formData.get('position_size');
    const maxExposure = formData.get('max_exposure');

    const config = {
        upper_bound: parseFloat(formData.get('upper_bound')),
        lower_bound: parseFloat(formData.get('lower_bound')),
        total_levels: parseInt(formData.get('total_levels')),
        spacing_type: formData.get('spacing_type'),
        spacing_value: 0, // Auto-calculated
        position_size: parseFloat(positionSize),
        max_exposure: parseFloat(maxExposure),
        mode: formData.get('mode'),
        exchange: formData.get('exchange'),
        network: formData.get('network'),
        symbol: formData.get('symbol'),
        enabled: formData.get('enabled') === 'on',
        zones: [] // Will be managed separately
    };

    // Validate
    if (config.upper_bound <= config.lower_bound) {
        showNotification('Upper bound must be greater than lower bound', 'error');
        return;
    }

    if (config.total_levels < 2) {
        showNotification('Total levels must be at least 2', 'error');
        return;
    }

    // Confirm if enabling
    if (config.enabled && !document.getElementById('enabled').checked) {
        modal.confirm(
            'Enable Bot',
            'Are you sure you want to enable the bot?',
            async () => {
                await saveConfig(config);
            }
        );
    } else {
        await saveConfig(config);
    }
});

// Save configuration
async function saveConfig(config) {
    try {
        const result = await apiCall('/api/config', {
            method: 'PUT',
            body: JSON.stringify(config)
        });

        if (result.success) {
            showNotification('Configuration saved successfully', 'success');

            if (result.data && result.data.restart_required) {
                modal.show(
                    'Restart Required',
                    'Configuration changes require a bot restart to take effect. Please restart the bot when ready.'
                );
            }

            fetchStatus();
        }
    } catch (error) {
        showNotification('Failed to save configuration', 'error');
    }
}

// Exchange change handler
document.getElementById('exchange').addEventListener('change', (e) => {
    updateNetworkVisibility(e.target.value);
    updateSymbolHint(e.target.value);
});

// Update network visibility
function updateNetworkVisibility(exchange) {
    const networkGroup = document.getElementById('network-group');
    if (exchange === 'okx') {
        networkGroup.style.display = 'flex';
    } else {
        networkGroup.style.display = 'none';
    }
}

// Update symbol hint
function updateSymbolHint(exchange) {
    const hint = document.getElementById('symbol-hint');
    if (exchange === 'okx') {
        hint.textContent = 'OKX: BTC/USDT | ETH/USDT';
    } else {
        hint.textContent = 'Bitkub: THB_BTC | THB_ETH';
    }
}