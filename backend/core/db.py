from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from datetime import datetime
import json
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DB_URL", "sqlite:///./grid.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ActionLogDB(Base):
    __tablename__ = "action_logs"

    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime(timezone=True), server_default=func.now())
    user = Column(String, default="local")
    action = Column(String, nullable=False)
    params = Column(Text, default="{}")
    result = Column(Text, default="")
    mode = Column(String, default="")
    exchange = Column(String, default="")


class OrderDB(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    level_index = Column(Integer, nullable=False)
    zone_id = Column(Integer, nullable=False)
    side = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    size = Column(Float, nullable=False)
    status = Column(String, default="open")
    exchange_order_id = Column(String, nullable=True)
    ts_open = Column(DateTime(timezone=True), server_default=func.now())
    ts_update = Column(DateTime(timezone=True), onupdate=func.now())


class TradeDB(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, nullable=False)
    side = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    size = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)
    ts = Column(DateTime(timezone=True), server_default=func.now())


class ConfigHistoryDB(Base):
    __tablename__ = "config_history"

    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime(timezone=True), server_default=func.now())
    config = Column(Text, nullable=False)
    user = Column(String, default="local")


class StateSnapshotDB(Base):
    __tablename__ = "state_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime(timezone=True), server_default=func.now())
    state = Column(String, nullable=False)
    active_levels = Column(Text, default="[]")
    pnl_realized = Column(Float, default=0.0)
    pnl_unrealized = Column(Float, default=0.0)
    inventory = Column(Text, default="{}")


Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_action_log(db: Session, action: str, params: dict = None, result: str = "", mode: str = "", exchange: str = "", user: str = "local"):
    """Save an action log entry."""
    log = ActionLogDB(
        action=action,
        params=json.dumps(params or {}),
        result=result,
        mode=mode,
        exchange=exchange,
        user=user
    )
    db.add(log)
    db.commit()
    return log


def save_order(db: Session, level_index: int, zone_id: int, side: str, price: float, size: float, exchange_order_id: str = None):
    """Save an order."""
    order = OrderDB(
        level_index=level_index,
        zone_id=zone_id,
        side=side,
        price=price,
        size=size,
        exchange_order_id=exchange_order_id
    )
    db.add(order)
    db.commit()
    return order


def save_trade(db: Session, order_id: int, side: str, price: float, size: float, fee: float = 0.0):
    """Save a trade."""
    trade = TradeDB(
        order_id=order_id,
        side=side,
        price=price,
        size=size,
        fee=fee
    )
    db.add(trade)
    db.commit()
    return trade


def save_config_history(db: Session, config: dict, user: str = "local"):
    """Save config history."""
    history = ConfigHistoryDB(
        config=json.dumps(config),
        user=user
    )
    db.add(history)
    db.commit()
    return history


def save_state_snapshot(db: Session, state: str, active_levels: list, pnl_realized: float, pnl_unrealized: float, inventory: dict):
    """Save state snapshot."""
    snapshot = StateSnapshotDB(
        state=state,
        active_levels=json.dumps(active_levels),
        pnl_realized=pnl_realized,
        pnl_unrealized=pnl_unrealized,
        inventory=json.dumps(inventory)
    )
    db.add(snapshot)
    db.commit()
    return snapshot