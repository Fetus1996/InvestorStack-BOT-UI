from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict
from ..core.config_models import APIResponse
from ..engine.services import bot_service
from ..core.logging import logger

router = APIRouter(prefix="/api", tags=["sync"])


class ManualOrder(BaseModel):
    id: str  # Order ID from exchange
    price: float
    side: str  # "buy" or "sell"
    amount: float


class ManualSyncRequest(BaseModel):
    orders: List[ManualOrder]


@router.post("/sync/manual")
async def manual_sync_orders(request: ManualSyncRequest):
    """Manually sync orders from user input when API returns empty."""
    try:
        # Get the engine
        engine = bot_service.engine

        if not engine.levels:
            return APIResponse(success=False, error="Grid engine not initialized")

        # Clear existing orders
        engine.active_orders.clear()

        # Map manual orders to grid levels - keep each order separate
        synced_count = 0
        for idx, order in enumerate(request.orders):
            # Find closest grid level
            closest_level = None
            min_diff = float('inf')
            for i, level_price in enumerate(engine.levels):
                diff = abs(order.price - level_price)
                if diff < min_diff:
                    min_diff = diff
                    closest_level = i

            if closest_level is not None:
                # Use the actual order ID from exchange
                order_id = order.id
                engine.active_orders[order_id] = {
                    'id': order_id,
                    'level_index': closest_level,
                    'zone_id': engine.zone_map.get(closest_level, {}).get('zone_id', 0),
                    'side': order.side,
                    'price': order.price,
                    'size': order.amount,
                    'status': 'open'
                }
                synced_count += 1
                logger.info(f"Manually synced order {order_id} at price {order.price} to level {closest_level}")

        # Update active levels
        active_levels = list(set(order_info['level_index'] for order_info in engine.active_orders.values()))
        from ..core.state import state_manager
        await state_manager.set_active_levels(active_levels)

        # Save synced orders to file for persistence
        import json
        import os
        sync_file = "manual_sync_orders.json"
        sync_data = {
            "orders": [
                {
                    "id": order_info['id'],
                    "level_index": order_info['level_index'],
                    "price": order_info['price'],
                    "side": order_info['side'],
                    "size": order_info['size'],
                    "zone_id": order_info['zone_id']
                }
                for order_info in engine.active_orders.values()
            ]
        }
        with open(sync_file, 'w') as f:
            json.dump(sync_data, f)

        logger.info(f"Manually synced {synced_count} orders and saved to {sync_file}")

        return APIResponse(
            success=True,
            message=f"Successfully synced {synced_count} orders",
            data={"synced_count": synced_count, "active_levels": active_levels}
        )

    except Exception as e:
        logger.error(f"Failed to manually sync orders: {e}")
        return APIResponse(success=False, error=str(e))


@router.delete("/sync/manual")
async def clear_manual_sync():
    """Clear manually synced orders."""
    try:
        # Clear from engine
        engine = bot_service.engine
        if engine:
            engine.active_orders.clear()
            logger.info("Cleared active orders from engine")

        # Delete saved file
        import os
        sync_file = "manual_sync_orders.json"
        if os.path.exists(sync_file):
            os.remove(sync_file)
            logger.info(f"Deleted {sync_file}")

        return APIResponse(
            success=True,
            message="Successfully cleared manual sync"
        )

    except Exception as e:
        logger.error(f"Failed to clear manual sync: {e}")
        return APIResponse(success=False, error=str(e))