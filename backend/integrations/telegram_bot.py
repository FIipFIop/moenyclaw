"""
Telegram bot for MoneyClaw.
Commands: /balance /web /status /start_trading /stop_trading
Also sends hourly portfolio reports automatically.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from core.config import settings

logger = logging.getLogger(__name__)


def _auth(func):
    """Decorator: only respond to the authorized user."""
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user:
            return
        allowed = settings.telegram_allowed_user_id
        if allowed is not None and update.effective_user.id != allowed:
            await update.message.reply_text("Unauthorized.")
            return
        return await func(self, update, context)
    return wrapper


class TelegramBot:
    def __init__(self, agents: dict[str, Any]) -> None:
        self._agents = agents
        self._app: Application | None = None

    def _build_app(self) -> Application:
        app = Application.builder().token(settings.telegram_bot_token).build()
        app.add_handler(CommandHandler("balance", self._cmd_balance))
        app.add_handler(CommandHandler("web", self._cmd_web))
        app.add_handler(CommandHandler("status", self._cmd_status))
        app.add_handler(CommandHandler("start_trading", self._cmd_start_trading))
        app.add_handler(CommandHandler("stop_trading", self._cmd_stop_trading))
        app.add_handler(CommandHandler("help", self._cmd_help))
        return app

    async def run(self) -> None:
        self._app = self._build_app()
        logger.info("Starting Telegram bot polling")
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(drop_pending_updates=True)
        # Keep running until cancelled
        import asyncio
        while True:
            await asyncio.sleep(3600)

    async def send_message(self, text: str) -> None:
        """Send a message to the authorized user."""
        if not self._app or not settings.telegram_allowed_user_id:
            return
        try:
            await self._app.bot.send_message(
                chat_id=settings.telegram_allowed_user_id,
                text=text,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error("Telegram send_message error: %s", e)

    async def send_hourly_report(
        self,
        total: float,
        hl: float,
        pm: float,
        unrealized: float,
    ) -> None:
        """Send the hourly portfolio summary."""
        pnl_emoji = "📈" if unrealized >= 0 else "📉"
        msg = (
            f"*⏰ Hourly Report — {datetime.utcnow().strftime('%H:%M UTC')}*\n\n"
            f"💰 *Total Portfolio:* ${total:,.2f}\n"
            f"├ Hyperliquid: ${hl:,.2f}\n"
            f"└ Polymarket:  ${pm:,.2f}\n\n"
            f"{pnl_emoji} *Unrealized PnL:* ${unrealized:+,.2f}\n\n"
            f"Trading: {'🟢 LIVE' if settings.trading_enabled else '🔴 Paper'}"
        )
        await self.send_message(msg)

    # ── Command handlers ────────────────────────────────────────────────────

    @_auth
    async def _cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Fetching balances… ⏳")
        try:
            from integrations.hyperliquid import hyperliquid_client
            from integrations.polymarket import polymarket_client

            hl = await hyperliquid_client.get_balance()
            pm = await polymarket_client.get_balance()

            hl_equity = hl.get("equity", 0.0)
            pm_equity = pm if isinstance(pm, float) else 0.0
            total = hl_equity + pm_equity
            unrealized = hl.get("unrealized_pnl", 0.0)
            pnl_emoji = "📈" if unrealized >= 0 else "📉"

            # Also get realized PnL today from latest snapshot
            from core.database import AsyncSessionLocal
            from models.portfolio import PortfolioSnapshot
            from sqlalchemy import select

            realized = 0.0
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(PortfolioSnapshot).order_by(PortfolioSnapshot.snapshot_at.desc()).limit(1)
                )
                snap = result.scalar_one_or_none()
                if snap:
                    realized = snap.realized_pnl_today

            msg = (
                f"*💼 Portfolio Balance*\n\n"
                f"💰 *Total:* ${total:,.2f}\n"
                f"├ Hyperliquid: ${hl_equity:,.2f}\n"
                f"└ Polymarket:  ${pm_equity:,.2f}\n\n"
                f"{pnl_emoji} *Unrealized PnL:* ${unrealized:+,.2f}\n"
                f"✅ *Realized Today:* ${realized:+,.2f}\n\n"
                f"Mode: {'🟢 LIVE' if settings.trading_enabled else '🔴 Paper (dry-run)'}"
            )
            await update.message.reply_text(msg, parse_mode="Markdown")

        except Exception as e:
            await update.message.reply_text(f"Error fetching balance: {e}")

    @_auth
    async def _cmd_web(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Generating dashboard link… 🔗")
        try:
            from core.database import AsyncSessionLocal
            from api.routes.tokens import TOKEN_TTL_HOURS
            from models.token import DashboardToken
            import uuid
            from datetime import timedelta

            token = str(uuid.uuid4())
            expires_at = datetime.utcnow() + timedelta(hours=TOKEN_TTL_HOURS)

            async with AsyncSessionLocal() as session:
                session.add(DashboardToken(token=token, expires_at=expires_at))
                await session.commit()

            url = f"{settings.dashboard_url}/access/{token}"
            msg = (
                f"*🔐 Dashboard Access Link*\n\n"
                f"[Open Dashboard]({url})\n\n"
                f"⏳ Valid for *{TOKEN_TTL_HOURS} hour* — single use.\n"
                f"After it expires, use /web again."
            )
            await update.message.reply_text(msg, parse_mode="Markdown")

        except Exception as e:
            await update.message.reply_text(f"Error generating link: {e}")

    @_auth
    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            from core.database import AsyncSessionLocal
            from models.agent import Agent
            from sqlalchemy import select

            async with AsyncSessionLocal() as session:
                result = await session.execute(select(Agent).order_by(Agent.name))
                agents = result.scalars().all()

            status_map = {
                "idle": "⚪",
                "thinking": "🟡",
                "waiting": "🔵",
                "error": "🔴",
            }

            lines = ["*🤖 Agent Status*\n"]
            for a in agents:
                emoji = status_map.get(a.status, "⚫")
                last = a.last_message[:50] if a.last_message else "—"
                lines.append(f"{emoji} *{a.name}* — {a.status}\n   _{last}_")

            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

        except Exception as e:
            await update.message.reply_text(f"Error fetching status: {e}")

    @_auth
    async def _cmd_start_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        from core.config import settings as cfg
        cfg.trading_enabled = True
        await update.message.reply_text(
            "🟢 *Trading ENABLED* — agents will now execute real orders.\n⚠️ Use /stop\\_trading to disable.",
            parse_mode="Markdown",
        )

    @_auth
    async def _cmd_stop_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        from core.config import settings as cfg
        cfg.trading_enabled = False
        await update.message.reply_text(
            "🔴 *Trading DISABLED* — agents running in paper/dry-run mode.",
            parse_mode="Markdown",
        )

    @_auth
    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = (
            "*🐾 MoneyClaw Commands*\n\n"
            "/balance — Portfolio balance & PnL\n"
            "/web — Get time-limited dashboard link\n"
            "/status — All agent statuses\n"
            "/start\\_trading — Enable live trading\n"
            "/stop\\_trading — Disable trading (paper mode)\n"
            "/help — This message"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
