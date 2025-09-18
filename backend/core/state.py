from typing import Dict, List, Optional
import asyncio
import json
from .config_models import RuntimeState, GridConfig
from .logging import logger


class StateManager:
    """Manages bot runtime state."""

    def __init__(self):
        self._state = RuntimeState()
        self._config: Optional[GridConfig] = None
        self._lock = asyncio.Lock()
        self._subscribers = []

    async def get_state(self) -> RuntimeState:
        """Get current state."""
        async with self._lock:
            return self._state.model_copy()

    async def set_state(self, state: str):
        """Set bot state."""
        async with self._lock:
            old_state = self._state.state
            self._state.state = state
            logger.info(f"State transition: {old_state} -> {state}")
            await self._notify_subscribers({"type": "state_change", "old": old_state, "new": state})

    async def update_pnl(self, realized: float = None, unrealized: float = None):
        """Update PnL values."""
        async with self._lock:
            if realized is not None:
                self._state.pnl_realized = realized
            if unrealized is not None:
                self._state.pnl_unrealized = unrealized
            await self._notify_subscribers({"type": "pnl_update", "realized": self._state.pnl_realized, "unrealized": self._state.pnl_unrealized})

    async def update_inventory(self, inventory: dict):
        """Update inventory."""
        async with self._lock:
            self._state.inventory = inventory
            await self._notify_subscribers({"type": "inventory_update", "inventory": inventory})

    async def set_active_levels(self, levels: List[int]):
        """Set active grid levels."""
        async with self._lock:
            self._state.active_levels = levels
            await self._notify_subscribers({"type": "levels_update", "levels": levels})

    async def set_error(self, error: str):
        """Set error state."""
        async with self._lock:
            self._state.state = "ERROR"
            self._state.last_error = error
            logger.error(f"Bot error: {error}")
            await self._notify_subscribers({"type": "error", "message": error})

    async def clear_error(self):
        """Clear error state."""
        async with self._lock:
            self._state.last_error = None

    def subscribe(self, callback):
        """Subscribe to state changes."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback):
        """Unsubscribe from state changes."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def _notify_subscribers(self, event: dict):
        """Notify all subscribers of state changes."""
        for callback in self._subscribers:
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}")

    def set_config(self, config: GridConfig):
        """Set grid configuration."""
        self._config = config

    def get_config(self) -> Optional[GridConfig]:
        """Get grid configuration."""
        return self._config

    async def reset(self):
        """Reset state to initial values."""
        async with self._lock:
            self._state = RuntimeState()
            await self._notify_subscribers({"type": "reset"})


state_manager = StateManager()