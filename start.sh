#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

# ── Backend ────────────────────────────────────────────────────────────────
cd "$ROOT/backend"

if [ ! -d ".venv" ]; then
  echo "Creating Python venv..."
  python3 -m venv .venv
fi

source .venv/bin/activate

if ! python -c "import fastapi" 2>/dev/null; then
  echo "Installing backend dependencies..."
  pip install -r requirements.txt -q
fi

echo "Starting backend on port 8000..."
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# ── Frontend ───────────────────────────────────────────────────────────────
cd "$ROOT/frontend"

if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install -q
fi

if [ ! -f ".env.local" ]; then
  cp .env.local.example .env.local
fi

echo "Starting frontend on port 3001..."
npm run dev -- --port 3001 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

# ── Done ───────────────────────────────────────────────────────────────────
echo ""
echo "✅ MoneyClaw running!"
echo "   Dashboard → http://localhost:3001"
echo "   API       → http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop both services."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'" INT TERM
wait
