from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime, timedelta
import json
from ..core.config_models import APIResponse
from ..core.db import get_db, ActionLogDB

router = APIRouter(prefix="/api", tags=["logs"])


@router.get("/logs")
async def get_logs(
    action: Optional[str] = Query(None, description="Filter by action type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs"),
    since: Optional[str] = Query(None, description="ISO timestamp to filter logs since"),
    db: Session = Depends(get_db)
):
    """Get action logs."""
    try:
        query = db.query(ActionLogDB)

        # Apply filters
        if action:
            query = query.filter(ActionLogDB.action == action)

        if since:
            since_time = datetime.fromisoformat(since.replace('Z', '+00:00'))
            query = query.filter(ActionLogDB.ts >= since_time)

        # Order by timestamp descending and limit
        logs = query.order_by(desc(ActionLogDB.ts)).limit(limit).all()

        # Format logs for response
        log_data = []
        for log in logs:
            log_data.append({
                "id": log.id,
                "timestamp": log.ts.isoformat() if log.ts else "",
                "user": log.user,
                "action": log.action,
                "params": json.loads(log.params) if log.params else {},
                "result": log.result,
                "mode": log.mode,
                "exchange": log.exchange
            })

        return APIResponse(success=True, data={"logs": log_data})

    except Exception as e:
        return APIResponse(success=False, error=str(e))