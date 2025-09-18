# Grid Trading Bot

A comprehensive Static Grid trading system with support for OKX and Bitkub exchanges, featuring both Real and Simulation modes, complete with a web UI for monitoring and control.

## ⚠️ Important Setup Notes

**Before using this bot, please ensure:**

1. **Position Size Minimums:**
   - Bitkub: Minimum 0.0001 BTC per order
   - OKX: Minimum 0.00001 BTC per order

2. **Balance Requirements:**
   - Have sufficient balance for buy orders (THB for Bitkub, USDT for OKX)
   - Consider having some base currency (BTC/ETH) for sell orders

3. **API Permissions:**
   - Enable trading permissions on your exchange account
   - Use IP restrictions for security

4. **Grid Configuration:**
   - Ensure grid range covers current market price
   - Test with simulation mode first

## Features

- **Static Grid Trading**: Automatically places buy/sell orders at predetermined price levels
- **Multi-Exchange Support**: OKX (with Demo mode) and Bitkub
- **Portfolio Value Tracking**: Real-time portfolio value calculation in THB
- **Dual Modes**: Real trading and Simulation for strategy testing
- **Zone Management**: Enable/disable groups of grid levels
- **Web Interface**: Modern dashboard with real-time updates via WebSocket
- **Live Balance Display**: Real-time account balance with total portfolio value
- **Comprehensive Logging**: Track all actions and trades
- **Security**: API keys stored securely in .env file
- **Testing**: Pytest suite for core functionality

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, CCXT
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Database**: SQLite
- **Real-time**: WebSockets

## Installation

### Prerequisites

- Python 3.11 or higher
- pip package manager

### Setup

1. Clone the repository:
```bash
cd grid-bot
```

2. Install dependencies:
```bash
make install
# or
pip install -r backend/requirements.txt
```

3. Set up configuration:
```bash
make setup
# or manually:
cp .env.example .env
cp config.example.json config.json
```

4. Configure API keys in `.env`:
```bash
# Edit .env file with your credentials
nano .env
```

## Configuration

### Environment Variables (.env)

```bash
MODE=sim                 # sim or real
EXCHANGE=okx             # okx or bitkub
NETWORK=live             # live or demo (OKX only)
SYMBOL=BTC/USDT          # Trading pair

# OKX Credentials
OKX_API_KEY=your_api_key
OKX_API_SECRET=your_secret
OKX_PASSPHRASE=your_passphrase

# Bitkub Credentials
BITKUB_API_KEY=your_api_key
BITKUB_API_SECRET=your_secret

DB_URL=sqlite:///./grid.db
```

### Grid Configuration (config.json)

```json
{
  "upper_bound": 65000,      // Upper price boundary
  "lower_bound": 60000,      // Lower price boundary
  "total_levels": 11,        // Number of grid levels
  "spacing_type": "fixed",   // fixed or percent
  "position_size": 0.001,    // Size per order (BTC)
  "max_exposure": 0.05,      // Maximum total exposure
  "enabled": false,          // Bot enabled status
  "mode": "sim",            // sim or real
  "exchange": "okx",        // okx or bitkub
  "symbol": "BTC/USDT"      // Trading symbol
}
```

## Running the Application

### Standard Mode
```bash
make run
# or
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

### Development Mode (with debug logging)
```bash
make dev
```

### Docker
```bash
docker-compose up
```

Access the web interface at: http://localhost:8000

## Usage Guide

### 1. Initial Setup

1. Open http://localhost:8000 in your browser
2. Go to **API Keys** tab
3. Select your exchange (OKX or Bitkub)
4. Enter your API credentials
5. Save the keys

### 2. Configure Grid

1. Go to **Config** tab
2. Set your grid parameters:
   - Upper/Lower bounds
   - Number of levels
   - Position sizing
   - Select mode (Sim/Real)
3. Save configuration

### 3. Start Trading

1. Go to **Dashboard** tab
2. Click **Start Bot** (confirmation required)
3. Monitor grid levels and zones
4. View real-time portfolio value in THB

### 4. Monitor Portfolio Value

- **Portfolio Value**: View total portfolio value in THB on dashboard
- Real-time calculation using current market prices
- Supports multiple currencies (BTC, DOGE, THB, USDT)
- Automatic updates when trades execute

### 5. Zone Management

- Enable/disable zones to control which price levels are active
- Each zone represents a group of grid levels
- Useful for adapting to market conditions

## Portfolio Value Calculation

The system now provides real-time portfolio value calculation in Thai Baht (THB):

### Dashboard Metrics

The dashboard displays three key metrics:
- **Open Orders**: Number of active orders
- **Active Levels**: Number of active grid levels
- **Portfolio Value**: Total portfolio value in THB

### How Portfolio Value is Calculated

**For Bitkub Exchange:**
- THB balances are added directly
- BTC balances are converted using current THB_BTC market price
- DOGE balances are converted using current THB_DOGE market price
- Other cryptocurrencies can be easily added

**For OKX Exchange:**
- USDT balances are converted to THB using market rates (or ~36 THB fallback)
- BTC balances are converted via BTC/USDT × USDT/THB rates
- Automatic fallback rates prevent calculation failures

### Real-time Updates

Portfolio values automatically refresh:
- When orders are placed or cancelled
- During API connection tests
- When balances change due to trading

## Exchange-Specific Notes

### OKX

- Supports both Live and Demo networks
- Demo mode requires demo account API keys
- Symbol format: `BTC/USDT`, `ETH/USDT`
- When using Demo:
  - Set `NETWORK=demo` in .env
  - Use demo account credentials
  - All requests include `x-simulated-trading: 1` header

### Bitkub

- Live trading only (no demo)
- Symbol format: `THB_BTC`, `THB_ETH`
- Custom REST implementation with HMAC-SHA256 signing
- Quote currency comes first in symbol notation

## Testing

Run all tests:
```bash
make test
```

Run specific test suites:
```bash
make test-grid    # Grid calculator tests
make test-config  # Configuration validation
make test-flow    # Start/stop flow tests
```

## API Endpoints

### Status & Control
- `GET /api/status` - Get bot status
- `POST /api/start` - Start bot (requires confirmation)
- `POST /api/stop` - Stop bot (requires confirmation)
- `POST /api/reset` - Reset grid

### Configuration
- `GET /api/config` - Get configuration
- `PUT /api/config` - Update configuration
- `GET /api/levels` - Get grid levels

### Zones
- `POST /api/zones/{id}/enable` - Enable zone
- `POST /api/zones/{id}/disable` - Disable zone

### Keys & Logs
- `POST /api/keys` - Save API keys
- `GET /api/keys` - Get keys status
- `POST /api/keys/test` - Test API connection and get balance with portfolio value
- `DELETE /api/keys` - Delete API keys
- `GET /api/logs` - Get action logs

### Orders & Trades
- `GET /api/orders` - Get orders
- `GET /api/trades` - Get trades

### WebSocket
- `WS /api/ws` - Real-time updates

## Project Structure

```
grid-bot/
├── backend/
│   ├── api/              # API routes
│   ├── core/             # Core models and database
│   ├── engine/           # Trading engine and exchanges
│   ├── tests/            # Test suites
│   └── app.py            # Main application
├── frontend/
│   ├── index.html        # Main UI
│   ├── styles.css        # Styling
│   ├── app.js            # Main JavaScript
│   └── components/       # UI components
├── .env.example          # Environment template
├── config.example.json   # Config template
├── requirements.txt      # Python dependencies
├── Makefile             # Build commands
└── README.md            # This file
```

## Troubleshooting

### Orders Not Being Created

1. **Check Position Size**:
   - Bitkub: Must be ≥ 0.0001 BTC
   - OKX: Must be ≥ 0.00001 BTC

2. **Check Balance**:
   - Insufficient THB/USDT for buy orders
   - Insufficient BTC/ETH for sell orders

3. **Check Grid Configuration**:
   - Grid range must cover current market price
   - Price levels must match exchange tick sizes

4. **Check Bot Status**:
   - Bot must be RUNNING (not STOPPED)
   - Check logs for error messages

5. **Config Not Updating**:
   - Restart the bot server after major config changes
   - Check if API returns validation errors

### API Connection Issues

1. **Check API Keys**:
   - Correct API key and secret
   - Trading permissions enabled
   - IP restrictions configured properly

2. **Exchange Specific**:
   - Bitkub: Use Thai IP or VPN
   - OKX: Check if demo/live network matches

## Safety Features

1. **Confirmation Modals**: All critical actions require confirmation
2. **Zone Control**: Disable grid sections without stopping the bot
3. **Simulation Mode**: Test strategies without real money
4. **Action Logging**: Complete audit trail of all operations
5. **Error Handling**: Graceful error recovery and state management

## Troubleshooting

### Bot won't start
- Check API keys are correctly configured
- Verify exchange and network settings match your account
- Ensure upper bound > lower bound
- Check logs for specific error messages

### WebSocket disconnected
- Automatic reconnection after 3 seconds
- Check network connectivity
- Verify backend is running

### Orders not placing
- Verify API key permissions (trading enabled)
- Check account balance
- Ensure symbol format matches exchange requirements
- Review position size vs. account balance

## Security Notes

- Never share your API keys
- API keys are stored in .env with restricted permissions (0600)
- Keys are never displayed in full in the UI
- Use read-only keys for monitoring if possible
- Regularly rotate your API keys

## Support

For issues or questions:
1. Check the Logs tab for error details
2. Review this README for configuration
3. Ensure all dependencies are installed
4. Verify exchange API is accessible

## License

This is a proof-of-concept implementation. Use at your own risk in production environments.