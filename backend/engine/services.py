import asyncio
from typing import Optional, List, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from ..core.config_models import GridConfig
from ..core.state import state_manager
from ..core.db import save_action_log, get_db
from ..core.logging import logger
from .grid_engine import GridEngine


class BotService:
    """High-level bot service orchestrating the grid engine."""

    def __init__(self):
        self.engine = GridEngine()
        self.config: Optional[GridConfig] = None
        self.ws_clients: List = []

    async def initialize(self, config: GridConfig):
        """Initialize the bot service."""
        self.config = config
        await self.engine.initialize(config)

        # Subscribe to state changes for WebSocket broadcast
        state_manager.subscribe(self.broadcast_state_update)

    async def start_bot(self, confirm: bool = False) -> Dict:
        """Start the trading bot."""
        if not confirm:
            return {"success": False, "message": "Confirmation required"}

        if not self.config:
            return {"success": False, "message": "No configuration loaded"}

        if not self.config.enabled:
            # Enable the bot
            self.config.enabled = True
            state_manager.set_config(self.config)

        try:
            await self.engine.start()

            # Log action
            db = next(get_db())
            save_action_log(
                db,
                action="START",
                params={"mode": self.config.mode, "exchange": self.config.exchange},
                result="success",
                mode=self.config.mode,
                exchange=self.config.exchange
            )

            return {"success": True, "message": "Bot started successfully"}

        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            return {"success": False, "message": str(e)}

    async def stop_bot(self, confirm: bool = False) -> Dict:
        """Stop the trading bot."""
        if not confirm:
            return {"success": False, "message": "Confirmation required"}

        try:
            await self.engine.stop()

            # Disable the bot
            if self.config:
                self.config.enabled = False
                state_manager.set_config(self.config)

            # Log action
            db = next(get_db())
            save_action_log(
                db,
                action="STOP",
                params={},
                result="success",
                mode=self.config.mode if self.config else "",
                exchange=self.config.exchange if self.config else ""
            )

            return {"success": True, "message": "Bot stopped successfully"}

        except Exception as e:
            logger.error(f"Failed to stop bot: {e}")
            return {"success": False, "message": str(e)}

    async def reset_bot(self, confirm: bool = False, clear_positions: bool = False, cancel_only: bool = False) -> Dict:
        """Reset the bot (clear and reinitialize)."""
        if not confirm:
            return {"success": False, "message": "Confirmation required"}

        try:
            await self.engine.reset(clear_positions=clear_positions, cancel_only=cancel_only)

            # Log action
            db = next(get_db())
            save_action_log(
                db,
                action="RESET",
                params={"clear_positions": clear_positions},
                result="success",
                mode=self.config.mode if self.config else "",
                exchange=self.config.exchange if self.config else ""
            )

            return {"success": True, "message": "Bot reset successfully"}

        except Exception as e:
            logger.error(f"Failed to reset bot: {e}")
            return {"success": False, "message": str(e)}

    async def update_config(self, new_config: GridConfig) -> Dict:
        """Update bot configuration."""
        old_config = self.config
        self.config = new_config
        state_manager.set_config(new_config)

        # Log config change
        db = next(get_db())
        save_action_log(
            db,
            action="CONFIG_CHANGED",
            params=new_config.model_dump(),
            result="success",
            mode=new_config.mode,
            exchange=new_config.exchange
        )

        # If bot is running and critical params changed, require restart
        state = await state_manager.get_state()
        if state.state in ["RUNNING", "SIM_RUNNING"]:
            critical_changed = (
                old_config.upper_bound != new_config.upper_bound or
                old_config.lower_bound != new_config.lower_bound or
                old_config.total_levels != new_config.total_levels or
                old_config.mode != new_config.mode or
                old_config.exchange != new_config.exchange
            )

            if critical_changed:
                return {
                    "success": True,
                    "message": "Configuration updated. Restart required for changes to take effect.",
                    "restart_required": True
                }

        # Reinitialize if not running
        if state.state == "STOPPED":
            await self.engine.initialize(new_config)

        return {"success": True, "message": "Configuration updated"}

    async def toggle_zone(self, zone_id: int, enabled: bool) -> Dict:
        """Enable or disable a zone."""
        try:
            await self.engine.toggle_zone(zone_id, enabled)

            # Log action
            db = next(get_db())
            save_action_log(
                db,
                action="ZONE_TOGGLED",
                params={"zone_id": zone_id, "enabled": enabled},
                result="success",
                mode=self.config.mode if self.config else "",
                exchange=self.config.exchange if self.config else ""
            )

            return {"success": True, "message": f"Zone {zone_id} {'enabled' if enabled else 'disabled'}"}

        except Exception as e:
            logger.error(f"Failed to toggle zone: {e}")
            return {"success": False, "message": str(e)}

    async def get_status(self) -> Dict:
        """Get current bot status."""
        state = await state_manager.get_state()
        config = state_manager.get_config()

        return {
            "state": state.state,
            "enabled": config.enabled if config else False,
            "mode": config.mode if config else "sim",
            "exchange": config.exchange if config else "okx",
            "network": config.network if config else "live",
            "symbol": config.symbol if config else "BTC/USDT",
            "active_zones": self._get_active_zones(),
            "active_levels": state.active_levels,
            "pnl": {
                "realized": state.pnl_realized,
                "unrealized": state.pnl_unrealized
            },
            "inventory": state.inventory,
            "last_error": state.last_error
        }

    async def get_grid_levels(self) -> List[Dict]:
        """Get all grid levels with their status."""
        if not self.engine.levels:
            return []

        # Check which levels have active orders
        active_level_indices = set()
        for order_info in self.engine.active_orders.values():
            if order_info['status'] == 'open':
                active_level_indices.add(order_info['level_index'])

        levels = []
        for i, price in enumerate(self.engine.levels):
            zone_info = self.engine.zone_map.get(i, {})
            # Level is active if there's an active order at this level
            # If no zones configured, consider all zones as enabled
            zone_enabled = zone_info.get('enabled', True) if zone_info else True
            is_active = zone_enabled and i in active_level_indices
            levels.append({
                "index": i,
                "price": price,
                "zone_id": zone_info.get('zone_id', 0),
                "active": is_active,
                "side": self._determine_side_for_level(price)
            })

        return levels

    def _get_active_zones(self) -> List[int]:
        """Get list of active zone IDs."""
        if not self.config or not self.config.zones:
            return []
        return [z.id for z in self.config.zones if z.enabled]

    def _determine_side_for_level(self, price: float) -> str:
        """Determine order side for a price level."""
        if not self.config:
            return "unknown"

        # For grid bot, use actual level positions to determine side
        # Check if there are active orders at this level
        for order_info in self.engine.active_orders.values():
            if abs(self.engine.levels[order_info['level_index']] - price) < 0.01:
                return order_info['side']

        # Fallback to mid-price calculation
        mid_price = (self.config.upper_bound + self.config.lower_bound) / 2
        tolerance = 1.0  # Small tolerance for mid price

        if price < mid_price - tolerance:
            return "buy"
        elif price > mid_price + tolerance:
            return "sell"
        return "mid"

    def add_ws_client(self, client):
        """Add WebSocket client for broadcasting."""
        self.ws_clients.append(client)

    def remove_ws_client(self, client):
        """Remove WebSocket client."""
        if client in self.ws_clients:
            self.ws_clients.remove(client)

    async def broadcast_state_update(self, event: Dict):
        """Broadcast state update to all WebSocket clients."""
        message = {
            "type": "state_update",
            "timestamp": datetime.utcnow().isoformat(),
            "data": event
        }

        # Send to all connected clients
        for client in self.ws_clients:
            try:
                await client.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")

    async def cancel_order_at_level(self, level_index: int) -> Dict:
        """Cancel order at specific grid level."""
        try:
            result = await self.engine.cancel_order_at_level(level_index)

            # Log action
            db = next(get_db())
            save_action_log(
                db,
                action="CANCEL_ORDER",
                params={"level_index": level_index},
                result="success",
                mode=self.config.mode if self.config else "",
                exchange=self.config.exchange if self.config else ""
            )

            return {"success": True, "message": f"Order at level {level_index} cancelled"}
        except Exception as e:
            logger.error(f"Failed to cancel order at level {level_index}: {e}")
            return {"success": False, "message": str(e)}

    async def enable_order_at_level(self, level_index: int) -> Dict:
        """Enable (place) order at specific grid level."""
        try:
            result = await self.engine.enable_order_at_level(level_index)

            # Log action
            db = next(get_db())
            save_action_log(
                db,
                action="ENABLE_ORDER",
                params={"level_index": level_index},
                result="success",
                mode=self.config.mode if self.config else "",
                exchange=self.config.exchange if self.config else ""
            )

            return {"success": True, "message": f"Order at level {level_index} enabled"}
        except Exception as e:
            logger.error(f"Failed to enable order at level {level_index}: {e}")
            return {"success": False, "message": str(e)}

    async def close(self):
        """Clean up resources."""
        await self.engine.close()


# Global service instance
bot_service = BotService()