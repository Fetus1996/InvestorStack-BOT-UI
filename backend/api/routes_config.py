from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import json
import os
from ..core.config_models import GridConfig, APIResponse
from ..core.db import get_db, save_config_history
from ..engine.services import bot_service
from ..engine.exchange_validator import ExchangeValidator

router = APIRouter(prefix="/api", tags=["config"])

CONFIG_FILE = "config.json"


@router.get("/config")
async def get_config():
    """Get current grid configuration."""
    try:
        config = bot_service.config
        if not config:
            # Load from file if not in memory
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config_data = json.load(f)
                    config = GridConfig(**config_data)
            else:
                # Return default config
                config = GridConfig(
                    upper_bound=65000,
                    lower_bound=60000,
                    total_levels=11,
                    spacing_type="fixed",
                    spacing_value=0,
                    position_size=0.001,
                    max_exposure=0.05,
                    zones=[],
                    enabled=False,
                    mode="sim",
                    exchange="okx",
                    network="live",
                    symbol="BTC/USDT"
                )

        return APIResponse(success=True, data=config.model_dump())
    except Exception as e:
        return APIResponse(success=False, error=str(e))


@router.put("/config")
async def update_config(config: GridConfig, db: Session = Depends(get_db)):
    """Update grid configuration."""
    try:
        # Validate config
        config_dict = config.model_dump()

        # Save to file
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_dict, f, indent=2)

        # Save to .env (some settings)
        env_file = ".env"
        env_lines = []

        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                env_lines = f.readlines()

        # Update relevant .env values
        env_updates = {
            'MODE': config.mode,
            'EXCHANGE': config.exchange,
            'NETWORK': config.network or 'live',
            'SYMBOL': config.symbol
        }

        updated_lines = []
        for line in env_lines:
            key = line.split('=')[0].strip() if '=' in line else ''
            if key in env_updates:
                updated_lines.append(f"{key}={env_updates[key]}\n")
                del env_updates[key]
            else:
                updated_lines.append(line)

        # Add any missing keys
        for key, value in env_updates.items():
            updated_lines.append(f"{key}={value}\n")

        with open(env_file, 'w') as f:
            f.writelines(updated_lines)

        # Save to history
        save_config_history(db, config_dict)

        # Update bot service
        result = await bot_service.update_config(config)

        return APIResponse(
            success=True,
            message=result["message"],
            data={"restart_required": result.get("restart_required", False)}
        )
    except Exception as e:
        return APIResponse(success=False, error=str(e))


@router.get("/levels")
async def get_levels():
    """Get calculated grid levels."""
    try:
        levels = await bot_service.get_grid_levels()
        return APIResponse(success=True, data={"levels": levels})
    except Exception as e:
        return APIResponse(success=False, error=str(e))


@router.get("/minimum-requirements/{exchange}/{symbol}")
async def get_minimum_requirements(exchange: str, symbol: str):
    """Get minimum order requirements for a symbol."""
    try:
        # Convert symbol format if needed
        if exchange == "bitkub" and "/" in symbol:
            # Convert BTC/THB to THB_BTC
            parts = symbol.split("/")
            symbol = f"{parts[1]}_{parts[0]}"

        requirements = ExchangeValidator.get_minimum_order_info(exchange, symbol)

        if not requirements:
            return APIResponse(
                success=False,
                message=f"No requirements found for {symbol} on {exchange}"
            )

        return APIResponse(success=True, data=requirements)
    except Exception as e:
        return APIResponse(success=False, error=str(e))