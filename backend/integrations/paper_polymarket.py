"""
Paper Polymarket engine — wraps polymarket-paper-trader for realistic simulation.
Uses real Polymarket order books for level-by-level execution and slippage tracking.
Starting balance: $10,000 paper money.
Data persisted in backend/data/paper_polymarket/.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "data" / "paper_polymarket"
_engine: "Engine | None" = None  # noqa: F821


def get_engine():
    """Return the singleton paper trading engine, initializing on first call."""
    global _engine
    if _engine is not None:
        return _engine

    from pm_trader.engine import Engine

    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _engine = Engine(_DATA_DIR)

    # Create account if it doesn't exist yet
    try:
        acc = _engine.get_account()
        logger.info("Paper Polymarket account loaded: $%.2f cash", _engine.get_balance()["cash"])
    except Exception:
        acc = _engine.init_account(balance=10_000.0)
        logger.info("Paper Polymarket account created: $10,000 starting balance")

    return _engine


def reset_engine():
    """Wipe paper account and restart with $10k."""
    global _engine
    engine = get_engine()
    engine.reset()
    acc = engine.init_account(balance=10_000.0)
    logger.info("Paper Polymarket account reset: $10,000")
    return acc
