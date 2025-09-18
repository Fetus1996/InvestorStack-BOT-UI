import ccxt
import os
from typing import Dict, List, Literal, Optional
from dotenv import load_dotenv
from ..core.logging import logger

load_dotenv()


class OKXExchange:
    """OKX exchange connector using CCXT."""

    def __init__(self):
        api_key = os.getenv("OKX_API_KEY", "")
        api_secret = os.getenv("OKX_API_SECRET", "")
        passphrase = os.getenv("OKX_PASSPHRASE", "")
        network = os.getenv("NETWORK", "live")

        if not all([api_key, api_secret, passphrase]):
            raise ValueError("OKX API credentials not configured")

        self.exchange = ccxt.okx({
            'apiKey': api_key,
            'secret': api_secret,
            'password': passphrase,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
            }
        })

        # Set demo header if needed
        if network == "demo":
            self.exchange.headers = {'x-simulated-trading': '1'}
            logger.info("OKX initialized in DEMO mode")
        else:
            self.exchange.headers = {'x-simulated-trading': '0'}
            logger.info("OKX initialized in LIVE mode")

    async def load_markets(self) -> Dict:
        """Load market information."""
        try:
            markets = self.exchange.load_markets()
            return markets
        except Exception as e:
            logger.error(f"Failed to load markets: {e}")
            raise

    async def fetch_ticker(self, symbol: str) -> Dict:
        """Fetch current ticker data for a symbol."""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'last': ticker['last'],
                'volume': ticker['baseVolume'],
                'timestamp': ticker['timestamp']
            }
        except Exception as e:
            logger.error(f"Failed to fetch ticker for {symbol}: {e}")
            raise

    async def place_limit_order(self, symbol: str, side: Literal["buy", "sell"], price: float, amount: float) -> Dict:
        """Place a limit order."""
        try:
            order = self.exchange.create_limit_order(symbol, side, amount, price)
            logger.info(f"Placed {side} order: {amount} @ {price} for {symbol}")
            return {
                'id': order['id'],
                'symbol': symbol,
                'side': side,
                'price': price,
                'amount': amount,
                'status': order['status'],
                'timestamp': order['timestamp']
            }
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise

    async def cancel_order(self, order_id: str, symbol: str) -> Dict:
        """Cancel an order."""
        try:
            result = self.exchange.cancel_order(order_id, symbol)
            logger.info(f"Cancelled order {order_id}")
            return {'id': order_id, 'status': 'cancelled'}
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise

    async def fetch_open_orders(self, symbol: str) -> List[Dict]:
        """Fetch all open orders for a symbol."""
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            return [{
                'id': o['id'],
                'symbol': o['symbol'],
                'side': o['side'],
                'price': o['price'],
                'amount': o['amount'],
                'remaining': o['remaining'],
                'status': o['status'],
                'timestamp': o['timestamp']
            } for o in orders]
        except Exception as e:
            logger.error(f"Failed to fetch open orders: {e}")
            raise

    async def fetch_balance(self) -> Dict:
        """Fetch account balance."""
        try:
            balance = self.exchange.fetch_balance()
            return {
                'free': balance['free'],
                'used': balance['used'],
                'total': balance['total']
            }
        except Exception as e:
            logger.error(f"Failed to fetch balance: {e}")
            raise

    async def fetch_order(self, order_id: str, symbol: str) -> Dict:
        """Fetch a specific order by ID."""
        try:
            order = self.exchange.fetch_order(order_id, symbol)
            return {
                'id': order['id'],
                'symbol': order['symbol'],
                'side': order['side'],
                'price': order['price'],
                'amount': order['amount'],
                'filled': order['filled'],
                'remaining': order['remaining'],
                'status': order['status'],
                'timestamp': order['timestamp']
            }
        except Exception as e:
            logger.error(f"Failed to fetch order {order_id}: {e}")
            raise

    async def close(self):
        """Close exchange connection."""
        if hasattr(self.exchange, 'close'):
            self.exchange.close()
        logger.info("OKX exchange connection closed")