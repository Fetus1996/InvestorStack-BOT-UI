from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime
import json
from ..core.config_models import APIResponse
from ..core.db import get_db, OrderDB, TradeDB
from ..engine.services import bot_service

router = APIRouter(prefix="/api", tags=["orders", "trades"])


@router.get("/orders")
async def get_orders(
    status: Optional[str] = Query(None, description="Filter by order status (open/closed)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of orders"),
    db: Session = Depends(get_db)
):
    """Get orders."""
    try:
        query = db.query(OrderDB)

        # Apply filters
        if status:
            query = query.filter(OrderDB.status == status)

        # Order by timestamp descending and limit
        orders = query.order_by(desc(OrderDB.ts_open)).limit(limit).all()

        # Format orders for response
        order_data = []
        for order in orders:
            order_data.append({
                "id": order.id,
                "level_index": order.level_index,
                "zone_id": order.zone_id,
                "side": order.side,
                "price": order.price,
                "size": order.size,
                "status": order.status,
                "exchange_order_id": order.exchange_order_id,
                "ts_open": order.ts_open.isoformat() if order.ts_open else "",
                "ts_update": order.ts_update.isoformat() if order.ts_update else ""
            })

        return APIResponse(success=True, data={"orders": order_data})

    except Exception as e:
        return APIResponse(success=False, error=str(e))


@router.get("/trades")
async def get_trades(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of trades"),
    since: Optional[str] = Query(None, description="ISO timestamp to filter trades since"),
    db: Session = Depends(get_db)
):
    """Get trades."""
    try:
        query = db.query(TradeDB)

        # Apply filters
        if since:
            since_time = datetime.fromisoformat(since.replace('Z', '+00:00'))
            query = query.filter(TradeDB.ts >= since_time)

        # Order by timestamp descending and limit
        trades = query.order_by(desc(TradeDB.ts)).limit(limit).all()

        # Format trades for response
        trade_data = []
        for trade in trades:
            trade_data.append({
                "id": trade.id,
                "order_id": trade.order_id,
                "side": trade.side,
                "price": trade.price,
                "size": trade.size,
                "fee": trade.fee,
                "timestamp": trade.ts.isoformat() if trade.ts else ""
            })

        return APIResponse(success=True, data={"trades": trade_data})

    except Exception as e:
        return APIResponse(success=False, error=str(e))


@router.post("/orders/level/{level_index}/cancel")
async def cancel_order_at_level(level_index: int):
    """Cancel order at specific grid level."""
    try:
        result = await bot_service.cancel_order_at_level(level_index)
        return APIResponse(
            success=result["success"],
            message=result["message"]
        )
    except Exception as e:
        return APIResponse(success=False, error=str(e))


@router.post("/orders/level/{level_index}/enable")
async def enable_order_at_level(level_index: int):
    """Enable (place) order at specific grid level."""
    try:
        result = await bot_service.enable_order_at_level(level_index)
        return APIResponse(
            success=result["success"],
            message=result["message"]
        )
    except Exception as e:
        return APIResponse(success=False, error=str(e))