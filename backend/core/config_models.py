from typing import Literal, List, Optional
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal


class ZoneDef(BaseModel):
    """Zone definition for grid levels."""
    id: int
    level_start: int
    level_end: int
    enabled: bool = True

    @field_validator('level_end')
    def validate_level_range(cls, v, values):
        if 'level_start' in values.data and v < values.data['level_start']:
            raise ValueError('level_end must be >= level_start')
        return v


class GridConfig(BaseModel):
    """Grid trading configuration."""
    upper_bound: float = Field(gt=0, description="Upper price boundary")
    lower_bound: float = Field(gt=0, description="Lower price boundary")
    total_levels: int = Field(ge=2, description="Total number of grid levels")
    spacing_type: Literal["fixed", "percent"] = "fixed"
    spacing_value: float = Field(ge=0, description="Spacing value (0 for auto-calculated)")
    position_size: float = Field(gt=0, description="Position size per level")
    max_exposure: float = Field(gt=0, description="Maximum notional exposure")
    zones: List[ZoneDef] = []
    enabled: bool = False
    mode: Literal["real", "sim"] = "sim"
    exchange: Literal["okx", "bitkub"] = "okx"
    network: Optional[Literal["live", "demo"]] = "live"
    symbol: str = "BTC/USDT"

    @field_validator('upper_bound')
    def validate_bounds(cls, v, values):
        if 'lower_bound' in values.data and v <= values.data['lower_bound']:
            raise ValueError('upper_bound must be > lower_bound')
        return v

    @field_validator('network')
    def validate_network(cls, v, values):
        if 'exchange' in values.data and values.data['exchange'] == 'bitkub' and v == 'demo':
            raise ValueError('Bitkub does not support demo network')
        return v


class RuntimeState(BaseModel):
    """Runtime state of the bot."""
    state: Literal["STOPPED", "STARTING", "RUNNING", "STOPPING", "ERROR", "SIM_RUNNING"] = "STOPPED"
    active_levels: List[int] = []
    pnl_realized: float = 0.0
    pnl_unrealized: float = 0.0
    inventory: dict = {}
    last_error: Optional[str] = None


class ActionLog(BaseModel):
    """Action log entry."""
    id: Optional[int] = None
    ts: str
    user: str = "local"
    action: str
    params: dict = {}
    result: str = ""
    mode: str = ""
    exchange: str = ""


class OrderModel(BaseModel):
    """Order data model."""
    id: Optional[int] = None
    level_index: int
    zone_id: int
    side: Literal["buy", "sell"]
    price: float
    size: float
    status: str = "open"
    exchange_order_id: Optional[str] = None
    ts_open: str
    ts_update: Optional[str] = None


class TradeModel(BaseModel):
    """Trade data model."""
    id: Optional[int] = None
    order_id: int
    side: Literal["buy", "sell"]
    price: float
    size: float
    fee: float = 0.0
    ts: str


class APIResponse(BaseModel):
    """Standard API response."""
    success: bool = True
    message: str = ""
    data: Optional[dict] = None
    error: Optional[str] = None