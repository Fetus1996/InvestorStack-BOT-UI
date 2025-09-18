from typing import Protocol, Dict, List, Literal, Optional
from abc import abstractmethod


class BaseExchange(Protocol):
    """Base exchange protocol for all exchange implementations."""

    @abstractmethod
    async def load_markets(self) -> Dict:
        """Load market information."""
        ...

    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> Dict:
        """Fetch current ticker data for a symbol."""
        ...

    @abstractmethod
    async def place_limit_order(self, symbol: str, side: Literal["buy", "sell"], price: float, amount: float) -> Dict:
        """Place a limit order."""
        ...

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> Dict:
        """Cancel an order."""
        ...

    @abstractmethod
    async def fetch_open_orders(self, symbol: str) -> List[Dict]:
        """Fetch all open orders for a symbol."""
        ...

    @abstractmethod
    async def fetch_balance(self) -> Dict:
        """Fetch account balance."""
        ...

    @abstractmethod
    async def fetch_order(self, order_id: str, symbol: str) -> Dict:
        """Fetch a specific order by ID."""
        ...

    @abstractmethod
    async def close(self):
        """Close exchange connection."""
        ...