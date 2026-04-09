from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from models.trade import Trade

router = APIRouter(prefix="/api/trades", tags=["trades"])


@router.get("")
async def list_trades(
    limit: int = 50,
    offset: int = 0,
    exchange: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Trade).order_by(Trade.created_at.desc())
    if exchange:
        q = q.where(Trade.exchange == exchange)
    if status:
        q = q.where(Trade.status == status)
    q = q.limit(limit).offset(offset)

    result = await db.execute(q)
    trades = result.scalars().all()
    return [_serialize_trade(t) for t in trades]


@router.get("/{trade_id}")
async def get_trade(trade_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()
    if not trade:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Trade not found")
    return _serialize_trade(trade)


def _serialize_trade(t: Trade) -> dict:
    return {
        "id": t.id,
        "round_id": t.round_id,
        "exchange": t.exchange,
        "market": t.market,
        "direction": t.direction,
        "size": t.size,
        "entry_price": t.entry_price,
        "exit_price": t.exit_price,
        "pnl": t.pnl,
        "status": t.status,
        "rejection_reason": t.rejection_reason,
        "order_id": t.order_id,
        "opened_at": t.opened_at,
        "closed_at": t.closed_at,
        "created_at": t.created_at,
    }
