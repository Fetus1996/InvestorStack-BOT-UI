from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..engine.services import bot_service
from ..core.config_models import APIResponse
import os
from dotenv import load_dotenv

router = APIRouter(prefix="/api", tags=["status"])


class StartRequest(BaseModel):
    confirm: bool


class StopRequest(BaseModel):
    confirm: bool


class ResetRequest(BaseModel):
    confirm: bool
    clear_positions: bool = False
    cancel_only: bool = True


@router.get("/status")
async def get_status():
    """Get current bot status."""
    try:
        status = await bot_service.get_status()
        return APIResponse(success=True, data=status)
    except Exception as e:
        return APIResponse(success=False, error=str(e))


@router.post("/start")
async def start_bot(request: StartRequest):
    """Start the trading bot."""
    if not request.confirm:
        return APIResponse(success=False, message="Confirmation required")

    result = await bot_service.start_bot(confirm=True)

    # Return current orders immediately
    if result["success"]:
        from ..engine.services import bot_service as service
        orders_data = {
            "orders": [],
            "count": 0
        }

        if service.engine and service.engine.active_orders:
            for order_id, order_info in service.engine.active_orders.items():
                if order_info.get('status') == 'open':
                    orders_data["orders"].append({
                        'id': order_id,
                        'level_index': order_info['level_index'],
                        'price': order_info['price'],
                        'side': order_info['side'],
                        'amount': order_info['size'],
                        'zone_id': order_info.get('zone_id', 0),
                        'status': order_info['status']
                    })
            orders_data["count"] = len(orders_data["orders"])

        result["orders"] = orders_data

    return APIResponse(
        success=result["success"],
        message=result["message"],
        data=result.get("orders")
    )


@router.post("/stop")
async def stop_bot(request: StopRequest):
    """Stop the trading bot."""
    if not request.confirm:
        return APIResponse(success=False, message="Confirmation required")

    result = await bot_service.stop_bot(confirm=True)
    return APIResponse(
        success=result["success"],
        message=result["message"]
    )


@router.post("/reset")
async def reset_bot(request: ResetRequest):
    """Reset the bot (clear and reinitialize)."""
    if not request.confirm:
        return APIResponse(success=False, message="Confirmation required")

    result = await bot_service.reset_bot(
        confirm=True,
        clear_positions=request.clear_positions and not request.cancel_only,
        cancel_only=request.cancel_only
    )
    return APIResponse(
        success=result["success"],
        message=result["message"]
    )


@router.get("/balance")
async def get_balance():
    """Get account balance from exchange."""
    try:
        load_dotenv()
        exchange = os.getenv("EXCHANGE", "okx")

        if exchange == "okx":
            from ..engine.exchange_okx_ccxt import OKXExchange
            exchange_client = OKXExchange()
        elif exchange == "bitkub":
            from ..engine.exchange_bitkub import BitkubExchange
            exchange_client = BitkubExchange()
        else:
            return APIResponse(success=False, error="Unknown exchange")

        balance = await exchange_client.fetch_balance()
        await exchange_client.close()

        # Return only non-zero balances
        non_zero_balance = {}
        for currency, amount in balance.get('total', {}).items():
            if amount > 0:
                non_zero_balance[currency] = amount

        return APIResponse(success=True, data=non_zero_balance)

    except Exception as e:
        return APIResponse(success=False, error=str(e))