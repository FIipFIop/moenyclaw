from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from models.portfolio import SystemConfig

router = APIRouter(prefix="/api/system", tags=["system"])


async def _get_config(key: str, db: AsyncSession, default: str = "") -> str:
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else default


async def _set_config(key: str, value: str, db: AsyncSession) -> None:
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = value
        row.updated_at = datetime.utcnow()
    else:
        db.add(SystemConfig(key=key, value=value))
    await db.commit()


@router.get("/config")
async def get_system_config(db: AsyncSession = Depends(get_db)):
    trading = await _get_config("trading_enabled", db, "false")
    return {"trading_enabled": trading == "true"}


@router.post("/toggle-trading")
async def toggle_trading(db: AsyncSession = Depends(get_db)):
    current = await _get_config("trading_enabled", db, "false")
    new_val = "false" if current == "true" else "true"
    await _set_config("trading_enabled", new_val, db)

    # Broadcast to WS clients
    from core.websocket_manager import ws_manager
    await ws_manager.broadcast({"event": "trading_toggled", "data": {"trading_enabled": new_val == "true"}})

    return {"trading_enabled": new_val == "true"}
