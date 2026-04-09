# 🐾 MoneyClaw — Financial AI Agent Network

A multi-agent AI system for crypto trading on Polymarket and Hyperliquid. Agents debate trade ideas, challenge each other, and execute when they reach consensus. Controlled via Telegram. Dashboard via Vercel.

## Architecture

```
Master Agent (nvidia/nemotron-3-super) ← orchestrates all
├── Research Agent (minimax/m2.5) ← scans markets
├── Analysis Agent (google/gemma-4-31b) ← builds theses
├── Debate Agent (google/gemma-4-26b) ← challenges theses
├── Risk Agent (nvidia/nemotron-3-super) ← approves/rejects
└── Execution Agent (google/gemma-4-26b) ← places orders
```

## Quick Start

### 1. Clone & configure

```bash
git clone https://github.com/FIipFIop/moenyclaw.git
cd moenyclaw

cp .env.example backend/.env
# Fill in all values in backend/.env
```

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`. Telegram bot starts automatically.

### 3. Frontend (local)

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev  # http://localhost:3000
```

### 4. Get dashboard access

Send `/web` to your Telegram bot → click the link (valid 1 hour).

---

## Environment Variables

Copy `.env.example` to `backend/.env` and fill in:

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | Get at openrouter.ai |
| `POLYMARKET_API_KEY` | Polymarket CLOB API key |
| `POLYMARKET_PRIVATE_KEY` | Wallet private key (Polygon) |
| `HYPERLIQUID_PRIVATE_KEY` | Hyperliquid account key |
| `HYPERLIQUID_ADDRESS` | Your HL wallet address |
| `TELEGRAM_BOT_TOKEN` | From @BotFather |
| `TELEGRAM_ALLOWED_USER_ID` | Your Telegram user ID (from @userinfobot) |
| `TELEGRAM_VERCEL_URL` | Your Vercel frontend URL |
| `TRADING_ENABLED` | `false` = paper mode, `true` = live |

---

## Telegram Commands

| Command | Description |
|---|---|
| `/balance` | Portfolio balance on both exchanges |
| `/web` | Generate time-limited dashboard link (1hr) |
| `/status` | All 6 agents current status |
| `/start_trading` | Enable live trading |
| `/stop_trading` | Switch to paper/dry-run mode |
| `/help` | Command list |

---

## Deploying to Vercel

The **frontend** (Next.js) deploys to Vercel. The **backend** needs a persistent server (VPS, Fly.io, Railway).

```bash
# Install Vercel CLI
npm i -g vercel

cd frontend
vercel --prod
```

Set in Vercel environment variables:
```
NEXT_PUBLIC_BACKEND_API_URL=https://your-backend.fly.dev
NEXT_PUBLIC_BACKEND_WS_URL=wss://your-backend.fly.dev/ws
```

---

## Docker (backend)

```bash
docker build -t moneyclaw .
docker run -p 8000:8000 \
  -v $(pwd)/data:/data \
  --env-file backend/.env \
  moneyclaw
```

---

## Safety

- `TRADING_ENABLED=false` by default — agents analyze but don't place real orders
- Use `/start_trading` Telegram command (or set env var) to enable live trading
- Dashboard access tokens expire after 1 hour and are single-use
- All secrets stay in `backend/.env` which is git-ignored

---

## Agent Communication Flow

```
Research → [OPPORTUNITY] → All
Master   → [OPPORTUNITY] → Analysis (tasks it)
Analysis → [ANALYSIS]    → All
Debate   → [CHALLENGE]   → Analysis (pushes back)
Analysis → [REVISED]     → Risk
Risk     → [RISK_REVIEW] → Master
Master   → [DECISION]    → Execution
Execution→ [REPORT]      → All
(fail)   → [CORRECTION]  → All (self-learn)
```
