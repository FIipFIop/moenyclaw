from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from models.portfolio import PortfolioSnapshot, SystemConfig

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/current")
async def current_portfolio(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PortfolioSnapshot).order_by(PortfolioSnapshot.snapshot_at.desc()).limit(1)
    )
    snap = result.scalar_one_or_none()
    if not snap:
        return {"total_usd": 0.0, "hyperliquid_balance": 0.0, "polymarket_balance": 0.0,
                "unrealized_pnl": 0.0, "realized_pnl_today": 0.0, "snapshot_at": None}
    return {
        "total_usd": snap.total_usd,
        "hyperliquid_balance": snap.hyperliquid_balance,
        "polymarket_balance": snap.polymarket_balance,
        "unrealized_pnl": snap.unrealized_pnl,
        "realized_pnl_today": snap.realized_pnl_today,
        "snapshot_at": snap.snapshot_at,
    }


@router.get("/history")
async def portfolio_history(days: int = 7, db: AsyncSession = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.snapshot_at >= since)
        .order_by(PortfolioSnapshot.snapshot_at.asc())
    )
    snaps = result.scalars().all()
    return [
        {
            "total_usd": s.total_usd,
            "unrealized_pnl": s.unrealized_pnl,
            "realized_pnl_today": s.realized_pnl_today,
            "snapshot_at": s.snapshot_at,
        }
        for s in snaps
    ]
