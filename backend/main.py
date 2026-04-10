"""
MoneyClaw — Financial AI Agent Network
FastAPI application entrypoint.

Startup sequence:
1. Initialize database (create tables)
2. Initialize agents + message bus
3. Start Telegram bot as background task
4. Start APScheduler (hourly jobs)
5. Register all API routes
"""
from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import AsyncSessionLocal, init_db
from core.message_bus import bus
from core.websocket_manager import ws_manager

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup → yield → shutdown."""
    logger.info("=== MoneyClaw starting up ===")

    # 1. Database
    await init_db()
    logger.info("Database ready")

    # 2. Seed agent rows in DB
    await _seed_agents()

    # 3. Wire message bus
    bus.set_ws_manager(ws_manager)
    bus.set_session_factory(AsyncSessionLocal)

    # 4. Instantiate agents
    from agents.analysis_agent import AnalysisAgent
    from agents.debate_agent import DebateAgent
    from agents.execution_agent import ExecutionAgent
    from agents.master_agent import MasterAgent
    from agents.research_agent import ResearchAgent
    from agents.risk_agent import RiskAgent

    agents = {
        "master": MasterAgent(bus),
        "research": ResearchAgent(bus),
        "analysis": AnalysisAgent(bus),
        "risk": RiskAgent(bus),
        "debate": DebateAgent(bus),
        "execution": ExecutionAgent(bus),
    }
    app.state.agents = agents

    # Run startup hooks
    for agent in agents.values():
        await agent.startup()
    logger.info("All agents initialized")

    # 5. Start message bus dispatcher
    bus_task = asyncio.create_task(bus.run())

    # 6. Telegram bot (optional — skipped if no token)
    telegram_task = None
    tg_bot = None
    if settings.telegram_bot_token:
        try:
            from integrations.telegram_bot import TelegramBot
            tg_bot = TelegramBot(agents=agents)
            telegram_task = asyncio.create_task(tg_bot.run())
            logger.info("Telegram bot started")
        except Exception as e:
            logger.warning("Telegram bot failed to start: %s", e)
    else:
        logger.info("TELEGRAM_BOT_TOKEN not set — Telegram bot disabled")
    app.state.telegram_bot = tg_bot

    # 7. APScheduler
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from integrations.hyperliquid import hyperliquid_client
    from integrations.polymarket import polymarket_client
    from scheduler.jobs import take_portfolio_snapshot, trigger_research_scan

    scheduler = AsyncIOScheduler()

    async def _snapshot_job():
        await take_portfolio_snapshot(
            hyperliquid_client,
            polymarket_client,
            app.state.telegram_bot,
        )

    async def _research_job():
        await trigger_research_scan(agents["research"])

    scheduler.add_job(_snapshot_job, "interval", hours=1, id="portfolio_snapshot")
    scheduler.add_job(_research_job, "interval", minutes=20, id="research_scan")
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("Scheduler started")

    # Take initial portfolio snapshot (non-blocking)
    asyncio.create_task(_snapshot_job())

    logger.info("=== MoneyClaw ready ===")
    yield

    # Shutdown
    logger.info("=== MoneyClaw shutting down ===")
    scheduler.shutdown(wait=False)
    bus.stop()
    bus_task.cancel()
    if telegram_task:
        telegram_task.cancel()
    for agent in agents.values():
        await agent.teardown()
    from integrations.openrouter import openrouter
    await openrouter.close()
    from integrations.polymarket import polymarket_client as pm
    await pm.close()
    logger.info("Shutdown complete")


async def _seed_agents() -> None:
    """Ensure all 6 agent rows exist in the DB."""
    from models.agent import Agent
    from sqlalchemy import select

    agent_definitions = [
        ("master", settings.model_master),
        ("research", settings.model_research),
        ("analysis", settings.model_analysis),
        ("risk", settings.model_risk),
        ("debate", settings.model_debate),
        ("execution", settings.model_execution),
    ]

    async with AsyncSessionLocal() as session:
        for name, model in agent_definitions:
            result = await session.execute(select(Agent).where(Agent.name == name))
            if not result.scalar_one_or_none():
                session.add(Agent(name=name, model=model, status="idle"))
        await session.commit()


# ── App factory ────────────────────────────────────────────────────────────

app = FastAPI(
    title="MoneyClaw Agent Network",
    version="1.0.0",
    description="Multi-agent crypto trading system",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local network — all origins allowed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ──────────────────────────────────────────────────────────────────
from api.routes import agents, paper, portfolio, prompt, system, tokens, trades, ws

app.include_router(agents.router)
app.include_router(paper.router)
app.include_router(trades.router)
app.include_router(portfolio.router)
app.include_router(tokens.router)
app.include_router(system.router)
app.include_router(prompt.router)
app.include_router(ws.router)


@app.get("/health")
async def health():
    return {"status": "ok", "agents": list(app.state.agents.keys()) if hasattr(app.state, "agents") else []}
