from fastapi import APIRouter, HTTPException
from ..core.config_models import APIResponse
from ..engine.services import bot_service

router = APIRouter(prefix="/api/zones", tags=["zones"])


@router.post("/{zone_id}/enable")
async def enable_zone(zone_id: int):
    """Enable a zone."""
    try:
        result = await bot_service.toggle_zone(zone_id, enabled=True)
        return APIResponse(
            success=result["success"],
            message=result["message"]
        )
    except Exception as e:
        return APIResponse(success=False, error=str(e))


@router.post("/{zone_id}/disable")
async def disable_zone(zone_id: int):
    """Disable a zone."""
    try:
        result = await bot_service.toggle_zone(zone_id, enabled=False)
        return APIResponse(
            success=result["success"],
            message=result["message"]
        )
    except Exception as e:
        return APIResponse(success=False, error=str(e))