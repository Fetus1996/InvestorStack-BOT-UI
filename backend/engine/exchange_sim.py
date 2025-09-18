import asyncio
import random
import time
from typing import Dict, List, Literal, Optional
from collections import defaultdict
from ..core.logging import logger


class SimulatedExchange:
    """Simulated exchange for testing strategies."""

    def __init__(self, initial_price: float = 62000.0, volatility: float = 0.001, seed: int = None):
        self.current_price = initial_price
        self.volatility = volatility
        self.orders = {}
        self.order_counter = 1000
        self.balances = defaultdict(float)
        self.balances['USDT'] = 10000.0
        self.balances['BTC'] = 0.1
        self.trades = []
        self.price_history = [initial_price]
        self.last_update = time.time()

        if seed is not None:
            random.seed(seed)

        # Start price update task
        self._running = True
        asyncio.create_task(self._price_updater())
        logger.info(f"Simulated exchange initialized with price {initial_price}")

    async def _price_updater(self):
        """Update price with random walk."""
        while self._running:
            await asyncio.sleep(1)
            change = random.gauss(0, self.volatility)
            self.current_price *= (1 + change)
            self.current_price = max(1, self.current_price)
            self.price_history.append(self.current_price)

            # Check for order matches
            await self._match_orders()

    async def _match_orders(self):
        """Match orders against current price."""
        for order_id, order in list(self.orders.items()):
            if order['status'] != 'open':
                continue

            matched = False
            if order['side'] == 'buy' and self.current_price <= order['price']:
                matched = True
            elif order['side'] == 'sell' and self.current_price >= order['price']:
                matched = True

            if matched:
                # Execute trade
                base_currency = order['symbol'].split('/')[0]
                quote_currency = order['symbol'].split('/')[1]

                if order['side'] == 'buy':
                    cost = order['amount'] * order['price']
                    if self.balances[quote_currency] >= cost:
                        self.balances[quote_currency] -= cost
                        self.balances[base_currency] += order['amount']
                        order['status'] = 'filled'
                        order['filled'] = order['amount']
                        order['remaining'] = 0

                        self.trades.append({
                            'id': f"trade_{len(self.trades) + 1}",
                            'order_id': order_id,
                            'symbol': order['symbol'],
                            'side': order['side'],
                            'price': order['price'],
                            'amount': order['amount'],
                            'timestamp': int(time.time() * 1000)
                        })
                        logger.info(f"Simulated fill: {order['side']} {order['amount']} @ {order['price']}")
                else:  # sell
                    if self.balances[base_currency] >= order['amount']:
                        self.balances[base_currency] -= order['amount']
                        self.balances[quote_currency] += order['amount'] * order['price']
                        order['status'] = 'filled'
                        order['filled'] = order['amount']
                        order['remaining'] = 0

                        self.trades.append({
                            'id': f"trade_{len(self.trades) + 1}",
                            'order_id': order_id,
                            'symbol': order['symbol'],
                            'side': order['side'],
                            'price': order['price'],
                            'amount': order['amount'],
                            'timestamp': int(time.time() * 1000)
                        })
                        logger.info(f"Simulated fill: {order['side']} {order['amount']} @ {order['price']}")

    async def load_markets(self) -> Dict:
        """Load market information."""
        return {
            'BTC/USDT': {
                'id': 'BTC/USDT',
                'symbol': 'BTC/USDT',
                'base': 'BTC',
                'quote': 'USDT',
                'active': True,
                'maker': 0.001,
                'taker': 0.001
            }
        }

    async def fetch_ticker(self, symbol: str) -> Dict:
        """Fetch current ticker data for a symbol."""
        spread = self.current_price * 0.001
        return {
            'symbol': symbol,
            'bid': self.current_price - spread,
            'ask': self.current_price + spread,
            'last': self.current_price,
            'volume': random.uniform(100, 1000),
            'timestamp': int(time.time() * 1000)
        }

    async def place_limit_order(self, symbol: str, side: Literal["buy", "sell"], price: float, amount: float) -> Dict:
        """Place a limit order."""
        order_id = f"sim_{self.order_counter}"
        self.order_counter += 1

        order = {
            'id': order_id,
            'symbol': symbol,
            'side': side,
            'price': price,
            'amount': amount,
            'filled': 0,
            'remaining': amount,
            'status': 'open',
            'timestamp': int(time.time() * 1000)
        }

        self.orders[order_id] = order
        logger.info(f"Simulated order placed: {side} {amount} @ {price}")
        return order

    async def cancel_order(self, order_id: str, symbol: str) -> Dict:
        """Cancel an order."""
        if order_id in self.orders:
            self.orders[order_id]['status'] = 'cancelled'
            logger.info(f"Simulated order cancelled: {order_id}")
            return {'id': order_id, 'status': 'cancelled'}
        raise Exception(f"Order {order_id} not found")

    async def fetch_open_orders(self, symbol: str) -> List[Dict]:
        """Fetch all open orders for a symbol."""
        return [
            order for order in self.orders.values()
            if order['symbol'] == symbol and order['status'] == 'open'
        ]

    async def fetch_balance(self) -> Dict:
        """Fetch account balance."""
        return {
            'free': dict(self.balances),
            'used': {},
            'total': dict(self.balances)
        }

    async def fetch_order(self, order_id: str, symbol: str) -> Dict:
        """Fetch a specific order by ID."""
        if order_id in self.orders:
            return self.orders[order_id]
        raise Exception(f"Order {order_id} not found")

    async def close(self):
        """Close exchange connection."""
        self._running = False
        logger.info("Simulated exchange closed")