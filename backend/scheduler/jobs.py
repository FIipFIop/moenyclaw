"""
APScheduler jobs:
- Hourly portfolio snapshot + Telegram report
- Hourly research scan trigger
"""
from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def take_portfolio_snapshot(
    hyperliquid_client,
    polymarket_client,
    telegram_bot,
) -> None:
    """Fetch balances from both exchanges and save a snapshot."""
    from core.database import AsyncSessionLocal
    from models.portfolio import PortfolioSnapshot

    try:
        hl_bal = await hyperliquid_client.get_balance()
        pm_bal = await polymarket_client.get_balance()

        hl_equity = hl_bal.get("equity", 0.0)
        pm_equity = pm_bal if isinstance(pm_bal, float) else 0.0
        total = hl_equity + pm_equity
        unrealized = hl_bal.get("unrealized_pnl", 0.0)

        async with AsyncSessionLocal() as session:
            snap = PortfolioSnapshot(
                hyperliquid_balance=hl_equity,
                polymarket_balance=pm_equity,
                total_usd=total,
                unrealized_pnl=unrealized,
                realized_pnl_today=0.0,  # updated when trades close
                snapshot_at=datetime.utcnow(),
            )
            session.add(snap)
            await session.commit()

        logger.info("Portfolio snapshot saved: $%.2f total", total)

        # Send hourly Telegram report
        if telegram_bot:
            await telegram_bot.send_hourly_report(
                total=total,
                hl=hl_equity,
                pm=pm_equity,
                unrealized=unrealized,
            )

    except Exception as e:
        logger.error("Portfolio snapshot error: %s", e)


async def trigger_research_scan(research_agent) -> None:
    """Tell research agent to scan markets."""
    try:
        import uuid
        await research_agent.scan(round_id=str(uuid.uuid4()))
    except Exception as e:
        logger.error("Research scan trigger error: %s", e)
