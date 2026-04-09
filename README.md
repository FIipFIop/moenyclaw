# 🐾 MoneyClaw — Financial AI Agent Network

A multi-agent AI system for crypto trading on Polymarket and Hyperliquid. Agents debate trade ideas, challenge each other, and execute when they reach consensus. Controlled via Telegram. Dashboard runs locally on your network — no cloud required.

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
# Only OPENROUTER_API_KEY is needed to start — all others are optional
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

Open `http://localhost:3000` directly — or if Telegram is set up, send `/web` to get a time-limited link.

---

## Environment Variables

Copy `.env.example` to `backend/.env`. **All keys except `OPENROUTER_API_KEY` are optional** — the system runs in demo/paper mode without them.

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Recommended | Free at openrouter.ai — agents reason without real keys |
| `POLYMARKET_PRIVATE_KEY` | Optional | Needed for real Polymarket trading |
| `HYPERLIQUID_PRIVATE_KEY` | Optional | Needed for real Hyperliquid trading |
| `HYPERLIQUID_ADDRESS` | Optional | Your HL wallet address |
| `TELEGRAM_BOT_TOKEN` | Optional | From @BotFather — system works fine without it |
| `TELEGRAM_ALLOWED_USER_ID` | Optional | Your Telegram user ID (from @userinfobot) |
| `DASHBOARD_URL` | Optional | Your local network address e.g. `http://192.168.1.10:3000` |
| `TRADING_ENABLED` | No | `false` = paper mode (default), `true` = live execution |

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

## Accessing from other devices on your network

To reach the dashboard from your phone or another PC on the same WiFi:

1. Find your machine's local IP: `ipconfig getifaddr en0` (Mac) or `hostname -I` (Linux)
2. Set in `backend/.env`: `DASHBOARD_URL=http://192.168.1.X:3000`
3. Run the frontend bound to all interfaces: `npm run dev -- -H 0.0.0.0`
4. Access from any device: `http://192.168.1.X:3000`

The `/web` Telegram command will generate a link using `DASHBOARD_URL`, so the link works from your phone.

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
