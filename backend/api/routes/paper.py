"""
Paper trading endpoints — exposes polymarket-paper-trader state to the dashboard.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/paper", tags=["paper"])


def _engine():
    from integrations.paper_polymarket import get_engine
    return get_engine()


@router.get("/balance")
async def paper_balance():
    return _engine().get_balance()


@router.get("/portfolio")
async def paper_portfolio():
    return _engine().get_portfolio()


@router.get("/history")
async def paper_history(limit: int = 50):
    trades = _engine().get_history(limit=limit)
    return [
        {
            "id": t.id,
            "market_slug": t.market_slug,
            "market_question": t.market_question,
            "outcome": t.outcome,
            "side": t.side,
            "avg_price": t.avg_price,
            "amount_usd": t.amount_usd,
            "shares": t.shares,
            "slippage_bps": round(t.slippage, 1),
            "levels_filled": t.levels_filled,
            "fee": t.fee,
            "created_at": t.created_at,
        }
        for t in trades
    ]


@router.post("/reset")
async def paper_reset():
    from integrations.paper_polymarket import reset_engine
    acc = reset_engine()
    return {"status": "reset", "balance": 10_000.0}
