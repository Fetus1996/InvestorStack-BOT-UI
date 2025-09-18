from typing import Dict, Tuple
from ..core.logging import logger


class ExchangeValidator:
    """Validate orders against exchange requirements."""

    # Minimum requirements per exchange
    REQUIREMENTS = {
        "okx": {
            "BTC/USDT": {
                "min_size": 0.00001,
                "min_value": 5.0,
                "size_step": 0.00000001,  # Allow smaller steps for testing
                "price_tick": 0.1
            },
            "ETH/USDT": {
                "min_size": 0.001,
                "min_value": 5.0,
                "size_step": 0.0001,
                "price_tick": 0.01
            },
            "SOL/USDT": {
                "min_size": 0.01,
                "min_value": 5.0,
                "size_step": 0.01,
                "price_tick": 0.001
            }
        },
        "bitkub": {
            "THB_BTC": {
                "min_size": 0.000003,  # ~0.000003 BTC (10 THB) for Bitkub
                "min_value": 10.0,
                "size_step": 0.00000001,
                "price_tick": 0.01
            },
            "THB_ETH": {
                "min_size": 0.005,
                "min_value": 10.0,
                "size_step": 0.00000001,
                "price_tick": 0.01
            }
        }
    }

    @staticmethod
    def validate_order(exchange: str, symbol: str, size: float, price: float) -> Tuple[bool, str]:
        """
        Validate if order meets exchange requirements.
        Returns (is_valid, error_message).
        """
        # Get requirements
        if exchange not in ExchangeValidator.REQUIREMENTS:
            return True, ""  # Unknown exchange, skip validation

        exchange_reqs = ExchangeValidator.REQUIREMENTS[exchange]
        if symbol not in exchange_reqs:
            logger.warning(f"No requirements found for {symbol} on {exchange}")
            return True, ""  # Unknown symbol, skip validation

        reqs = exchange_reqs[symbol]

        # Check minimum size
        if size < reqs["min_size"]:
            return False, f"Order size {size} is below minimum {reqs['min_size']} for {symbol}"

        # Check minimum value
        order_value = size * price
        if order_value < reqs["min_value"]:
            return False, f"Order value {order_value:.2f} is below minimum {reqs['min_value']} for {symbol}"

        # Check size step
        if reqs["size_step"] > 0:
            # Use proper floating point comparison
            steps = round(size / reqs["size_step"])
            expected_size = steps * reqs["size_step"]
            tolerance = reqs["size_step"] * 0.001  # 0.1% tolerance
            if abs(size - expected_size) > tolerance:
                return False, f"Order size {size} doesn't match step size {reqs['size_step']} (expected: {expected_size})"

        # Check price tick
        if reqs["price_tick"] > 0:
            # Use proper floating point comparison
            ticks = round(price / reqs["price_tick"])
            expected_price = ticks * reqs["price_tick"]
            tolerance = reqs["price_tick"] * 0.001  # 0.1% tolerance
            if abs(price - expected_price) > tolerance:
                return False, f"Price {price} doesn't match tick size {reqs['price_tick']} (expected: {expected_price})"

        return True, ""

    @staticmethod
    def round_size(exchange: str, symbol: str, size: float) -> float:
        """Round size to match exchange requirements."""
        if exchange not in ExchangeValidator.REQUIREMENTS:
            return size

        exchange_reqs = ExchangeValidator.REQUIREMENTS[exchange]
        if symbol not in exchange_reqs:
            return size

        step = exchange_reqs[symbol]["size_step"]
        if step > 0:
            return round(size / step) * step
        return size

    @staticmethod
    def round_price(exchange: str, symbol: str, price: float) -> float:
        """Round price to match exchange requirements."""
        if exchange not in ExchangeValidator.REQUIREMENTS:
            return price

        exchange_reqs = ExchangeValidator.REQUIREMENTS[exchange]
        if symbol not in exchange_reqs:
            return price

        tick = exchange_reqs[symbol]["price_tick"]
        if tick > 0:
            return round(price / tick) * tick
        return price

    @staticmethod
    def get_minimum_order_info(exchange: str, symbol: str) -> Dict:
        """Get minimum order requirements for display."""
        if exchange not in ExchangeValidator.REQUIREMENTS:
            return {}

        exchange_reqs = ExchangeValidator.REQUIREMENTS[exchange]
        if symbol not in exchange_reqs:
            return {}

        return exchange_reqs[symbol]