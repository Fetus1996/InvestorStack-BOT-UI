import hashlib
import hmac
import json
import time
from typing import Dict, List, Literal, Optional
import httpx
import os
from dotenv import load_dotenv
from ..core.logging import logger

load_dotenv()


class BitkubExchange:
    """Bitkub exchange connector using REST API."""

    BASE_URL = "https://api.bitkub.com"

    def __init__(self):
        self.api_key = os.getenv("BITKUB_API_KEY", "")
        self.api_secret = os.getenv("BITKUB_API_SECRET", "")

        if not all([self.api_key, self.api_secret]):
            raise ValueError("Bitkub API credentials not configured")

        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info("Bitkub exchange initialized")

    def _sign_request(self, timestamp: int, method: str, path: str, body: str = "") -> str:
        """Generate HMAC-SHA256 signature for Bitkub API."""
        payload = f"{timestamp}{method}{path}{body}"
        signature = hmac.new(
            self.api_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    async def _get_server_time(self) -> int:
        """Get server timestamp from Bitkub API."""
        try:
            response = await self.client.get(f"{self.BASE_URL}/api/servertime")
            # Server returns timestamp in seconds, API expects milliseconds
            server_ts = int(response.json())
            return server_ts * 1000
        except Exception as e:
            logger.warning(f"Failed to get server time: {e}, using local time")
            # Fallback to local time if server time fails
            return int(time.time() * 1000)

    async def _request(self, method: str, endpoint: str, params: Dict = None, signed: bool = False) -> Dict:
        """Make HTTP request to Bitkub API."""
        url = f"{self.BASE_URL}{endpoint}"
        headers = {"Content-Type": "application/json"}

        if signed:
            # Use server timestamp for signed requests
            timestamp = await self._get_server_time()
            # For POST requests with params, create JSON body
            if method.upper() == "POST" and params:
                body = json.dumps(params, separators=(',', ':'))
            else:
                body = ""

            signature = self._sign_request(timestamp, method.upper(), endpoint, body)
            headers.update({
                "X-BTK-APIKEY": self.api_key,
                "X-BTK-TIMESTAMP": str(timestamp),
                "X-BTK-SIGN": signature
            })

            logger.info(f"Signed Request: method={method}, endpoint={endpoint}, timestamp={timestamp}, body={body[:100] if body else 'empty'}, sig={signature[:20]}...")

            if method.upper() == "POST":
                # Send params as JSON body for POST
                if body:
                    response = await self.client.post(url, content=body, headers=headers)
                else:
                    response = await self.client.post(url, headers=headers)
            else:
                # For GET requests, send params as query parameters
                response = await self.client.request(method, url, headers=headers, params=params)
        else:
            response = await self.client.request(method, url, params=params, headers=headers)

        # Handle empty response
        if not response.text:
            logger.warning(f"Empty response from {endpoint}")
            return {'error': 0, 'result': []}

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {endpoint}: {response.text[:200]}")
            raise Exception(f"Invalid JSON response: {e}")

        if response.status_code != 200:
            raise Exception(f"Bitkub API error: {response.status_code} - {data}")

        # Check if response is just an error code or has error field
        if isinstance(data, dict):
            if 'error' in data and data['error'] != 0:
                error_code = data['error']
                error_messages = {
                    1: "Invalid JSON payload",
                    2: "Missing required parameter",
                    3: "Invalid parameter",
                    4: "Invalid timestamp",
                    5: "Invalid signature",
                    6: "Invalid API key or secret",
                    7: "API key not found",
                    8: "API is not activated",
                    9: "IP not allowed",
                    10: "Invalid IP address",
                    11: "Private API only",
                    15: "Insufficient balance",
                    18: "Order amount too small or invalid",
                    20: "Rate limit exceeded"
                }
                error_msg = error_messages.get(error_code, f"Unknown error code: {error_code}")
                raise Exception(f"Bitkub API error {error_code}: {error_msg}")
        elif isinstance(data, int):
            # Response is just an error code
            raise Exception(f"Bitkub API error code: {data}")

        return data

    async def load_markets(self) -> Dict:
        """Load market information."""
        try:
            response = await self._request("GET", "/api/v3/market/symbols")
            markets = {}
            for symbol_data in response.get('result', []):
                # Build symbol from base and quote assets
                base = symbol_data['base_asset']
                quote = symbol_data['quote_asset']
                symbol = f"{quote}_{base}"  # Format: THB_BTC

                markets[symbol] = {
                    'id': symbol_data.get('pairing_id', 0),
                    'symbol': symbol,
                    'base': base,
                    'quote': quote,
                    'active': not (symbol_data.get('freeze_buy', False) or symbol_data.get('freeze_sell', False)),
                    'min_size': float(symbol_data.get('min_quote_size', 10)),
                    'price_step': float(symbol_data.get('price_step', '0.01'))
                }
            return markets
        except Exception as e:
            logger.error(f"Failed to load markets: {e}")
            raise

    async def fetch_ticker(self, symbol: str) -> Dict:
        """Fetch current ticker data for a symbol."""
        try:
            # Use public API v1 for ticker (doesn't require auth)
            url = f"https://api.bitkub.com/api/market/ticker"
            response = await self.client.get(url)
            data = response.json()

            if symbol not in data:
                raise Exception(f"Symbol {symbol} not found in ticker data")

            ticker = data[symbol]
            return {
                'symbol': symbol,
                'bid': float(ticker['highestBid']),
                'ask': float(ticker['lowestAsk']),
                'last': float(ticker['last']),
                'volume': float(ticker['baseVolume']),
                'timestamp': int(time.time() * 1000)
            }
        except Exception as e:
            logger.error(f"Failed to fetch ticker for {symbol}: {e}")
            raise

    async def place_limit_order(self, symbol: str, side: Literal["buy", "sell"], price: float, amount: float) -> Dict:
        """Place a limit order."""
        try:
            # Use v3 endpoints
            endpoint = "/api/v3/market/place-bid" if side == "buy" else "/api/v3/market/place-ask"

            # Convert symbol format from THB_BTC to BTC_THB for API
            if symbol == "THB_BTC":
                api_symbol = "BTC_THB"
            else:
                # Handle other symbols if needed
                api_symbol = symbol

            # For buy orders, amount is in THB (quote currency)
            # For sell orders, amount is in BTC (base currency)
            if side == "buy":
                # Use fixed 100 THB for buy orders
                order_amount = 100  # THB amount
            else:
                # Calculate BTC amount from 100 THB worth
                order_amount = 100 / price  # BTC amount (100 THB worth)

            params = {
                'sym': api_symbol,
                'amt': order_amount,  # Amount in THB for buy, BTC for sell
                'rat': price,         # Rate in THB per BTC
                'typ': 'limit'
            }

            logger.info(f"Placing {side} order: endpoint={endpoint}, params={params}")

            response = await self._request("POST", endpoint, params, signed=True)

            # Log the full response for debugging
            logger.info(f"Order response: {response}")

            order_id = response.get('result', {}).get('id', '')
            if order_id:
                logger.info(f"✅ Successfully placed {side} order: {order_amount} @ {price} for {symbol}, ID: {order_id}")
            else:
                logger.warning(f"Order may have failed, no ID returned: {response}")

            return {
                'id': order_id,
                'symbol': symbol,
                'side': side,
                'price': price,
                'amount': amount,
                'status': 'open',
                'timestamp': response.get('result', {}).get('ts', int(time.time() * 1000))
            }
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise

    async def cancel_order(self, order_id: str, symbol: str) -> Dict:
        """Cancel an order."""
        try:
            # Convert symbol format
            api_symbol = "BTC_THB" if symbol == "THB_BTC" else symbol

            # *** IMPORTANT FIX: Get correct order side for cancellation ***
            # Bitkub API error 21 occurs when wrong side is specified for SELL orders
            # Query open orders to find the correct side
            logger.info(f"Attempting to cancel order {order_id}")
            open_orders = await self.fetch_open_orders(symbol)
            logger.info(f"Found {len(open_orders)} open orders")

            order_side = 'buy'  # default fallback
            found_order = False

            for order in open_orders:
                logger.info(f"Checking order {order['id']} (side: {order['side']}) vs target {order_id}")
                if str(order['id']) == str(order_id):
                    order_side = order['side']
                    found_order = True
                    logger.info(f"FOUND! Order {order_id} has side: {order_side}")
                    break

            if not found_order:
                logger.warning(f"Order {order_id} not found in open orders, using default side: {order_side}")
                # Try both sides if order not found
                for side_to_try in ['sell', 'buy']:
                    logger.info(f"Trying to cancel with side: {side_to_try}")
                    params = {
                        'sym': api_symbol,
                        'id': order_id,
                        'sd': side_to_try,
                        'hash': order_id
                    }
                    try:
                        response = await self._request("POST", "/api/v3/market/cancel-order", params, signed=True)
                        logger.info(f"Cancel attempt with side {side_to_try}: {response}")
                        if response.get('error', 0) == 0:
                            logger.info(f"Successfully cancelled order {order_id} with side {side_to_try}")
                            return {'id': order_id, 'status': 'cancelled'}
                    except Exception as e:
                        logger.warning(f"Failed to cancel with side {side_to_try}: {e}")
                        continue
                raise Exception(f"Failed to cancel order {order_id} with any side")

            # If order was found, use the correct side
            if found_order:
                params = {
                    'sym': api_symbol,
                    'id': order_id,
                    'sd': order_side,
                    'hash': order_id
                }

                response = await self._request("POST", "/api/v3/market/cancel-order", params, signed=True)
                logger.info(f"Cancelled {order_side} order {order_id}")
                return {'id': order_id, 'status': 'cancelled'}
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise

    async def fetch_open_orders(self, symbol: str) -> List[Dict]:
        """Fetch all open orders for a symbol."""
        try:
            # Convert symbol format
            api_symbol = "BTC_THB" if symbol == "THB_BTC" else symbol
            params = {'sym': api_symbol}
            logger.info(f"Fetching open orders for {api_symbol}")
            response = await self._request("POST", "/api/v3/market/my-open-orders", params, signed=True)
            logger.info(f"Open orders response: {response}")

            # Check if response is valid
            if not isinstance(response, dict):
                logger.warning(f"Invalid open orders response: {response}")
                return []

            # Check if result exists and is valid
            result = response.get('result')
            if result is None:
                logger.info("No open orders found")
                return []

            # Handle both list and dict formats
            if isinstance(result, list):
                orders_data = result
            elif isinstance(result, dict):
                # Some APIs return a dict with orders as values
                orders_data = list(result.values()) if result else []
            else:
                logger.warning(f"Unexpected result format: {type(result)}")
                return []

            orders = []
            for order in orders_data:
                orders.append({
                    'id': order['id'],
                    'symbol': symbol,
                    'side': order['side'],
                    'price': float(order['rate']),
                    'amount': float(order['amount']),
                    'remaining': float(order['amount']) - float(order.get('filled', 0)),
                    'status': 'open',
                    'timestamp': order['ts']
                })

            return orders
        except Exception as e:
            logger.error(f"Failed to fetch open orders: {e}")
            raise

    async def fetch_balance(self) -> Dict:
        """Fetch account balance."""
        try:
            response = await self._request("POST", "/api/v3/market/wallet", None, signed=True)

            logger.info(f"Wallet API raw response: {response}")

            # Check if response has the expected structure
            if not isinstance(response, dict) or 'result' not in response:
                logger.error(f"Unexpected wallet response format: {response}")
                raise Exception(f"Unexpected wallet response format")

            balance = {'free': {}, 'used': {}, 'total': {}}
            result = response.get('result', {})

            logger.info(f"Wallet result: {result}")

            if isinstance(result, dict):
                for currency, value in result.items():
                    # Bitkub API returns simple numbers, not objects
                    if isinstance(value, (int, float)):
                        total = float(value)
                        # Assume all balance is available (not in orders)
                        balance['free'][currency] = total
                        balance['used'][currency] = 0
                        balance['total'][currency] = total

                        if total > 0:
                            logger.info(f"Found balance for {currency}: total={total}")
                    elif isinstance(value, dict):
                        # In case API changes to return objects
                        available = float(value.get('available', 0))
                        reserved = float(value.get('reserved', 0))
                        total = available + reserved

                        balance['free'][currency] = available
                        balance['used'][currency] = reserved
                        balance['total'][currency] = total

                        if total > 0:
                            logger.info(f"Found balance for {currency}: available={available}, reserved={reserved}, total={total}")

            logger.info(f"Final balance dict: {balance}")
            return balance
        except Exception as e:
            logger.error(f"Failed to fetch balance: {e}")
            raise

    async def fetch_order(self, order_id: str, symbol: str) -> Dict:
        """Fetch a specific order by ID."""
        try:
            # Convert symbol format
            api_symbol = "BTC_THB" if symbol == "THB_BTC" else symbol
            params = {
                'sym': api_symbol,
                'id': order_id
            }
            response = await self._request("POST", "/api/v3/market/order-info", params, signed=True)

            order = response.get('result', {})
            return {
                'id': order['id'],
                'symbol': symbol,
                'side': order['side'],
                'price': float(order['rate']),
                'amount': float(order['amount']),
                'filled': float(order.get('filled', 0)),
                'remaining': float(order['amount']) - float(order.get('filled', 0)),
                'status': order['status'],
                'timestamp': order['ts']
            }
        except Exception as e:
            logger.error(f"Failed to fetch order {order_id}: {e}")
            raise

    async def close(self):
        """Close exchange connection."""
        await self.client.aclose()
        logger.info("Bitkub exchange connection closed")