from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import json
from pathlib import Path

# Import API routes
from backend.api.routes_status import router as status_router
from backend.api.routes_config import router as config_router
from backend.api.routes_zones import router as zones_router
from backend.api.routes_keys import router as keys_router
from backend.api.routes_logs import router as logs_router
from backend.api.routes_orders_trades import router as orders_trades_router
from backend.api.routes_orders import router as orders_router
from backend.api.routes_sync import router as sync_router
from backend.api.ws import handle_websocket

# Import services
from backend.engine.services import bot_service
from backend.core.config_models import GridConfig
from backend.core.logging import logger

# Create FastAPI app
app = FastAPI(
    title="Grid Trading Bot",
    version="1.0.0",
    description="Static Grid Trading System with OKX and Bitkub support"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:9000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(status_router)
app.include_router(config_router)
app.include_router(zones_router)
app.include_router(keys_router)
app.include_router(logs_router)
app.include_router(orders_trades_router)
app.include_router(orders_router)
app.include_router(sync_router)

# WebSocket endpoint
@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await handle_websocket(websocket)

# Serve frontend files
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    # Mount CSS and JS files
    @app.get("/styles.css")
    async def serve_css():
        return FileResponse(str(frontend_path / "styles.css"), media_type="text/css")

    @app.get("/app.js")
    async def serve_app_js():
        return FileResponse(str(frontend_path / "app.js"), media_type="application/javascript")

    # Serve component files
    @app.get("/components/{filename}")
    async def serve_component(filename: str):
        return FileResponse(str(frontend_path / "components" / filename), media_type="application/javascript")

    # Serve index.html
    @app.get("/")
    async def serve_frontend():
        """Serve frontend index.html."""
        return FileResponse(str(frontend_path / "index.html"))

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize bot on startup."""
    logger.info("Starting Grid Trading Bot API...")

    # Load config from file if exists
    config_file = "config.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
                config = GridConfig(**config_data)
                await bot_service.initialize(config)
                logger.info("Bot initialized with saved configuration")

                # Load manually synced orders if exists
                sync_file = "manual_sync_orders.json"
                if os.path.exists(sync_file):
                    try:
                        with open(sync_file, 'r') as f:
                            sync_data = json.load(f)
                            for order in sync_data.get('orders', []):
                                bot_service.engine.active_orders[order['id']] = {
                                    'id': order['id'],
                                    'level_index': order['level_index'],
                                    'price': order['price'],
                                    'side': order['side'],
                                    'size': order['size'],
                                    'zone_id': order['zone_id'],
                                    'status': 'open'
                                }
                            logger.info(f"Loaded {len(sync_data.get('orders', []))} manually synced orders")
                    except Exception as e:
                        logger.error(f"Failed to load manual sync orders: {e}")

        except Exception as e:
            logger.error(f"Failed to load config: {e}")
    else:
        # Initialize with default config
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
        await bot_service.initialize(config)
        logger.info("Bot initialized with default configuration")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info("Shutting down Grid Trading Bot API...")
    await bot_service.close()

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Grid Trading Bot"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000, reload=True)