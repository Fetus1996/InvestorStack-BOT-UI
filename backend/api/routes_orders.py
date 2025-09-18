from fastapi import APIRouter
from ..core.config_models import APIResponse
from ..engine.services import bot_service
from ..core.logging import logger

router = APIRouter(prefix="/api", tags=["orders"])


@router.get("/orders/active")
async def get_active_orders():
    """Get all active orders with their details."""
    try:
        engine = bot_service.engine

        if not engine or not engine.active_orders:
            return APIResponse(success=True, data={"orders": [], "count": 0})

        # Get all active orders
        orders = []
        for order_id, order_info in engine.active_orders.items():
            if order_info['status'] == 'open':
                # Get the level price
                level_price = engine.levels[order_info['level_index']] if order_info['level_index'] < len(engine.levels) else order_info['price']

                orders.append({
                    'id': order_id,
                    'level_index': order_info['level_index'],
                    'price': order_info['price'],
                    'side': order_info['side'],
                    'amount': order_info['size'],
                    'zone_id': order_info.get('zone_id', 0),
                    'status': order_info['status']
                })

        # Sort by price
        orders.sort(key=lambda x: x['price'], reverse=True)

        return APIResponse(
            success=True,
            data={
                "orders": orders,
                "count": len(orders),
                "buy_count": len([o for o in orders if o['side'] == 'buy']),
                "sell_count": len([o for o in orders if o['side'] == 'sell'])
            }
        )

    except Exception as e:
        logger.error(f"Failed to get active orders: {e}")
        return APIResponse(success=False, error=str(e))


@router.post("/orders/{order_id}/cancel")
async def cancel_specific_order(order_id: str):
    """Cancel a specific order by ID."""
    try:
        engine = bot_service.engine

        if not engine:
            return APIResponse(success=False, error="Engine not initialized")

        # Find the order
        if order_id not in engine.active_orders:
            return APIResponse(success=False, error=f"Order {order_id} not found")

        order_info = engine.active_orders[order_id]

        # Only cancel if it's a real order (not manual sync)
        if not order_id.startswith("manual_"):
            await engine.exchange.cancel_order(order_id, engine.config.symbol)

        # Remove from active orders
        del engine.active_orders[order_id]

        logger.info(f"Cancelled order {order_id}")

        return APIResponse(
            success=True,
            message=f"Order {order_id} cancelled successfully"
        )

    except Exception as e:
        logger.error(f"Failed to cancel order {order_id}: {e}")
        return APIResponse(success=False, error=str(e))