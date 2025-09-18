import asyncio
from typing import Dict, List, Optional, Literal
from datetime import datetime
from ..core.config_models import GridConfig, RuntimeState
from ..core.state import state_manager
from ..core.logging import logger
from ..core.db import get_db, save_order, save_trade, save_action_log
from .grid_calculator import GridCalculator
from .exchange_base import BaseExchange
from .exchange_sim import SimulatedExchange
from .exchange_okx_ccxt import OKXExchange
from .exchange_bitkub import BitkubExchange
from .exchange_validator import ExchangeValidator


class GridEngine:
    """Main grid trading engine."""

    def __init__(self):
        self.config: Optional[GridConfig] = None
        self.exchange: Optional[BaseExchange] = None
        self.levels: List[float] = []
        self.active_orders: Dict[str, dict] = {}
        self.zone_map: dict = {}
        self.running = False
        self.monitor_task = None
        self.db = None

    async def initialize(self, config: GridConfig):
        """Initialize the grid engine with configuration."""
        self.config = config
        state_manager.set_config(config)

        # Calculate grid levels
        self.levels = GridCalculator.calculate_grid(
            config.lower_bound,
            config.upper_bound,
            config.total_levels,
            config.spacing_type
        )

        # Map levels to zones
        if config.zones:
            self.zone_map = GridCalculator.get_zone_levels(self.levels,
                [z.model_dump() for z in config.zones])
        else:
            # Create default zones
            self.zone_map = {i: {'zone_id': 0, 'enabled': True, 'price': self.levels[i]}
                            for i in range(len(self.levels))}

        # Initialize exchange
        await self._init_exchange()

        logger.info(f"Grid engine initialized with {len(self.levels)} levels")

    async def _init_exchange(self):
        """Initialize the appropriate exchange connector."""
        if self.exchange:
            await self.exchange.close()

        if self.config.mode == "sim":
            mid_price = (self.config.upper_bound + self.config.lower_bound) / 2
            self.exchange = SimulatedExchange(initial_price=mid_price)
            await state_manager.set_state("SIM_RUNNING")
        else:
            if self.config.exchange == "okx":
                self.exchange = OKXExchange()
            elif self.config.exchange == "bitkub":
                self.exchange = BitkubExchange()
            else:
                raise ValueError(f"Unsupported exchange: {self.config.exchange}")

        # Load markets
        await self.exchange.load_markets()

    async def start(self):
        """Start the grid trading bot."""
        if self.running:
            logger.warning("Grid engine already running")
            return

        await state_manager.set_state("STARTING")
        self.running = True

        try:
            # Place initial grid orders
            await self._place_grid_orders()

            # Start monitoring task
            self.monitor_task = asyncio.create_task(self._monitor_orders())

            state = "SIM_RUNNING" if self.config.mode == "sim" else "RUNNING"
            await state_manager.set_state(state)

            logger.info("Grid engine started successfully")

        except Exception as e:
            logger.error(f"Failed to start grid engine: {e}")
            await state_manager.set_error(str(e))
            self.running = False
            raise

    async def stop(self):
        """Stop the grid trading bot."""
        if not self.running:
            logger.warning("Grid engine not running")
            return

        await state_manager.set_state("STOPPING")
        self.running = False

        # Cancel monitoring task
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        # Cancel all open orders
        await self._cancel_all_orders()

        await state_manager.set_state("STOPPED")
        logger.info("Grid engine stopped")

    async def reset(self, clear_positions: bool = False, cancel_only: bool = False):
        """Reset the grid (clear and reinitialize).

        Args:
            clear_positions: Whether to close all positions
            cancel_only: If True, only cancel orders without restarting
        """
        logger.info(f"Resetting grid engine (cancel_only={cancel_only})")

        # Stop if running
        if self.running:
            await self.stop()

        # Clear all orders
        await self._cancel_all_orders()

        # Clear positions if requested
        if clear_positions:
            await self._close_all_positions()

        # Only restart if not cancel_only mode
        if not cancel_only and self.config:
            await self.initialize(self.config)
            await self.start()

    async def _sync_with_exchange_orders(self):
        """Sync grid engine with existing orders on exchange."""
        try:
            # Fetch all open orders from exchange
            open_orders = await self.exchange.fetch_open_orders(self.config.symbol)
            logger.info(f"Found {len(open_orders)} existing orders on exchange")

            # If we already have manually synced orders and exchange returns empty, keep them
            if len(open_orders) == 0 and len(self.active_orders) > 0:
                logger.info(f"Exchange returned empty but we have {len(self.active_orders)} manually synced orders, keeping them")
                return True

            # Clear local tracking only if we got real orders from exchange
            self.active_orders.clear()

            # Map exchange orders to grid levels
            for order in open_orders:
                order_price = order['price']

                # Find closest grid level
                closest_level = None
                min_diff = float('inf')
                for i, level_price in enumerate(self.levels):
                    diff = abs(order_price - level_price)
                    if diff < min_diff:
                        min_diff = diff
                        closest_level = i

                # Add to active orders tracking
                if closest_level is not None:
                    self.active_orders[order['id']] = {
                        'level_index': closest_level,
                        'zone_id': self.zone_map.get(closest_level, {}).get('zone_id', 0),
                        'side': order['side'],
                        'price': order_price,
                        'size': order.get('amount', self.config.position_size),
                        'status': 'open'
                    }
                    logger.info(f"Synced order {order['id']} at price {order_price} to level {closest_level}")

            # Update active levels based on synced orders
            active_levels = list(set(order_info['level_index'] for order_info in self.active_orders.values()))
            await state_manager.set_active_levels(active_levels)

            logger.info(f"Synced {len(self.active_orders)} orders with grid engine")
            return True
        except Exception as e:
            logger.warning(f"Could not sync with exchange orders: {e}")
            return False

    async def _place_grid_orders(self):
        """Place initial grid orders."""
        # First try to sync with existing orders from exchange
        sync_success = await self._sync_with_exchange_orders()

        # If we have active orders (either from exchange or manual sync), use them
        if len(self.active_orders) > 0:
            logger.info(f"Using {len(self.active_orders)} existing orders, skipping new order placement")
            return

        # If no orders at all, place new grid orders
        logger.info("No existing orders found, placing new grid orders")

        # Check for existing orders at each level to prevent duplicates
        existing_levels = set()
        for order_info in self.active_orders.values():
            if order_info['status'] == 'open':
                existing_levels.add(order_info['level_index'])

        # Get current market price
        ticker = await self.exchange.fetch_ticker(self.config.symbol)
        mid_price = ticker['last']

        placed_count = 0
        for i, level_price in enumerate(self.levels):
            # Skip if order already exists at this level
            if i in existing_levels:
                logger.info(f"Order already exists at level {i}, skipping")
                continue

            # Check if zone is enabled
            if i in self.zone_map and not self.zone_map[i]['enabled']:
                continue

            # Determine order side
            side = GridCalculator.determine_side(level_price, mid_price)
            if side == "skip":
                continue

            try:
                # Validate order before placing
                is_valid, error_msg = ExchangeValidator.validate_order(
                    self.config.exchange,
                    self.config.symbol,
                    self.config.position_size,
                    level_price
                )

                if not is_valid:
                    logger.warning(f"Order validation failed at level {i}: {error_msg}")
                    continue

                # Round values to match exchange requirements
                rounded_price = ExchangeValidator.round_price(
                    self.config.exchange,
                    self.config.symbol,
                    level_price
                )
                rounded_size = ExchangeValidator.round_size(
                    self.config.exchange,
                    self.config.symbol,
                    self.config.position_size
                )

                # Place order
                order = await self.exchange.place_limit_order(
                    self.config.symbol,
                    side,
                    rounded_price,
                    rounded_size
                )

                self.active_orders[order['id']] = {
                    'level_index': i,
                    'zone_id': self.zone_map.get(i, {}).get('zone_id', 0),
                    'side': side,
                    'price': level_price,
                    'size': self.config.position_size,
                    'status': 'open'
                }

                placed_count += 1

            except Exception as e:
                logger.error(f"Failed to place order at level {i}: {e}")

        logger.info(f"Placed {placed_count} initial grid orders")
        await state_manager.set_active_levels([i for i in range(len(self.levels))
                                               if i in self.zone_map and self.zone_map[i]['enabled']])

    async def _monitor_orders(self):
        """Monitor orders for fills and replace as needed."""
        last_valid_order_count = 0

        while self.running:
            try:
                # Fetch open orders
                open_orders = await self.exchange.fetch_open_orders(self.config.symbol)

                # If API returns empty but we have orders, likely API issue - skip this cycle
                if len(open_orders) == 0 and len(self.active_orders) > 0:
                    logger.warning(f"API returned 0 orders but we track {len(self.active_orders)} orders - likely API issue, skipping")
                    await asyncio.sleep(5)
                    continue

                open_order_ids = {o['id'] for o in open_orders}

                # Only process if we got valid data from API
                if len(open_orders) > 0:
                    last_valid_order_count = len(open_orders)

                    # Check for filled orders
                    for order_id, order_info in list(self.active_orders.items()):
                        if order_id not in open_order_ids and order_info['status'] == 'open':
                            # Order was filled
                            logger.info(f"Order {order_id} filled at level {order_info['level_index']}")

                            # Update order status
                            self.active_orders[order_id]['status'] = 'filled'

                            # Replace order at same level (static grid)
                            await self._replace_order(order_info['level_index'])

                            # Update PnL
                            await self._update_pnl()

                await asyncio.sleep(5)  # Check every 5 seconds

            except Exception as e:
                logger.error(f"Error in order monitoring: {e}")
                await asyncio.sleep(10)

    async def _replace_order(self, level_index: int):
        """Replace a filled order at the same grid level."""
        if not self.running:
            return

        # Check if zone is still enabled
        if level_index in self.zone_map and not self.zone_map[level_index]['enabled']:
            return

        try:
            # Get current market price to determine side
            ticker = await self.exchange.fetch_ticker(self.config.symbol)
            mid_price = ticker['last']
            level_price = self.levels[level_index]

            side = GridCalculator.determine_side(level_price, mid_price)
            if side == "skip":
                return

            # Place new order at same level
            order = await self.exchange.place_limit_order(
                self.config.symbol,
                side,
                level_price,
                self.config.position_size
            )

            self.active_orders[order['id']] = {
                'level_index': level_index,
                'zone_id': self.zone_map.get(level_index, {}).get('zone_id', 0),
                'side': side,
                'price': level_price,
                'size': self.config.position_size,
                'status': 'open'
            }

            logger.info(f"Replaced order at level {level_index}: {side} @ {level_price}")

        except Exception as e:
            logger.error(f"Failed to replace order at level {level_index}: {e}")

    async def _cancel_all_orders(self):
        """Cancel all open orders."""
        cancelled_count = 0
        open_orders = []

        # First, fetch all open orders from the exchange
        try:
            open_orders = await self.exchange.fetch_open_orders(self.config.symbol)
            logger.info(f"Found {len(open_orders)} open orders on exchange")

            # Cancel each order from the exchange
            for order in open_orders:
                try:
                    await self.exchange.cancel_order(order['id'], self.config.symbol)
                    cancelled_count += 1
                    logger.info(f"Cancelled order {order['id']}")

                    # Update local tracking if exists
                    if order['id'] in self.active_orders:
                        self.active_orders[order['id']]['status'] = 'cancelled'
                except Exception as e:
                    logger.error(f"Failed to cancel order {order['id']}: {e}")
        except Exception as e:
            logger.error(f"Failed to fetch open orders: {e}")

        # Also cancel any locally tracked orders that might not be on exchange
        open_order_ids = [o['id'] for o in open_orders]
        for order_id in list(self.active_orders.keys()):
            if self.active_orders[order_id]['status'] == 'open':
                if order_id not in open_order_ids:
                    try:
                        await self.exchange.cancel_order(order_id, self.config.symbol)
                        self.active_orders[order_id]['status'] = 'cancelled'
                        cancelled_count += 1
                    except Exception as e:
                        # Order might already be cancelled or filled
                        self.active_orders[order_id]['status'] = 'unknown'
                        logger.debug(f"Could not cancel order {order_id}: {e}")

        # Clear all active orders tracking
        self.active_orders.clear()

        # Update state to reflect no active levels
        await state_manager.set_active_levels([])

        logger.info(f"Cancelled {cancelled_count} orders, cleared all order tracking")

    async def _close_all_positions(self):
        """Close all open positions."""
        try:
            balance = await self.exchange.fetch_balance()
            # Implementation depends on specific exchange requirements
            logger.info("Closed all positions")
        except Exception as e:
            logger.error(f"Failed to close positions: {e}")

    async def _update_pnl(self):
        """Update PnL calculations."""
        try:
            # Simple PnL calculation (can be enhanced)
            balance = await self.exchange.fetch_balance()
            ticker = await self.exchange.fetch_ticker(self.config.symbol)

            # Calculate unrealized PnL based on current positions
            base_currency = self.config.symbol.split('/')[0]
            quote_currency = self.config.symbol.split('/')[1]

            base_value = balance['total'].get(base_currency, 0) * ticker['last']
            quote_value = balance['total'].get(quote_currency, 0)
            total_value = base_value + quote_value

            # Update state
            await state_manager.update_pnl(unrealized=base_value)
            await state_manager.update_inventory(balance['total'])

        except Exception as e:
            logger.error(f"Failed to update PnL: {e}")

    async def toggle_zone(self, zone_id: int, enabled: bool):
        """Enable or disable a zone."""
        zones_updated = 0
        for level_index, zone_info in self.zone_map.items():
            if zone_info['zone_id'] == zone_id:
                self.zone_map[level_index]['enabled'] = enabled
                zones_updated += 1

                # Cancel orders in disabled zone
                if not enabled:
                    for order_id, order_info in list(self.active_orders.items()):
                        if order_info['level_index'] == level_index and order_info['status'] == 'open':
                            try:
                                await self.exchange.cancel_order(order_id, self.config.symbol)
                                self.active_orders[order_id]['status'] = 'cancelled'
                            except Exception as e:
                                logger.error(f"Failed to cancel order {order_id}: {e}")

        logger.info(f"Zone {zone_id} {'enabled' if enabled else 'disabled'}, {zones_updated} levels affected")

        # Update active levels
        await state_manager.set_active_levels([i for i in range(len(self.levels))
                                               if i in self.zone_map and self.zone_map[i]['enabled']])

    async def cancel_order_at_level(self, level_index: int):
        """Cancel order at specific grid level."""
        if level_index < 0 or level_index >= len(self.levels):
            raise ValueError(f"Invalid level index: {level_index}")

        # Find and cancel order at this level
        for order_id, order_info in list(self.active_orders.items()):
            if order_info['level_index'] == level_index and order_info['status'] == 'open':
                try:
                    await self.exchange.cancel_order(order_id, self.config.symbol)
                    self.active_orders[order_id]['status'] = 'cancelled'
                    logger.info(f"Cancelled order at level {level_index}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to cancel order {order_id}: {e}")
                    raise

        logger.warning(f"No active order found at level {level_index}")
        return False

    async def enable_order_at_level(self, level_index: int):
        """Enable (place) order at specific grid level."""
        if level_index < 0 or level_index >= len(self.levels):
            raise ValueError(f"Invalid level index: {level_index}")

        # Check if zone is enabled
        if level_index in self.zone_map and not self.zone_map[level_index]['enabled']:
            raise ValueError(f"Zone for level {level_index} is disabled")

        # Check if order already exists at this level
        for order_id, order_info in self.active_orders.items():
            if order_info['level_index'] == level_index and order_info['status'] == 'open':
                logger.warning(f"Order already exists at level {level_index}")
                return False

        try:
            # Get current market price to determine side
            ticker = await self.exchange.fetch_ticker(self.config.symbol)
            mid_price = ticker['last']
            level_price = self.levels[level_index]

            side = GridCalculator.determine_side(level_price, mid_price)
            if side == "skip":
                raise ValueError(f"Cannot place order at mid price level {level_index}")

            # Place new order at level
            order = await self.exchange.place_limit_order(
                self.config.symbol,
                side,
                level_price,
                self.config.position_size
            )

            self.active_orders[order['id']] = {
                'level_index': level_index,
                'zone_id': self.zone_map.get(level_index, {}).get('zone_id', 0),
                'side': side,
                'price': level_price,
                'size': self.config.position_size,
                'status': 'open'
            }

            logger.info(f"Placed order at level {level_index}: {side} @ {level_price}")
            return True

        except Exception as e:
            logger.error(f"Failed to place order at level {level_index}: {e}")
            raise

    async def close(self):
        """Clean up resources."""
        if self.running:
            await self.stop()
        if self.exchange:
            await self.exchange.close()