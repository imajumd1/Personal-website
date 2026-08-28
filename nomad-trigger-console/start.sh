#!/usr/bin/env bash
# Start both backend and frontend for local development
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "Starting NOMAD Trigger Console..."

# Backend
cd "$ROOT/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
.venv/bin/python run.py &
BACKEND_PID=$!

# Frontend
cd "$ROOT/frontend"
if [ ! -d node_modules ]; then
  npm install
fi
npm run dev &
FRONTEND_PID=$!

echo ""
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo "  Press Ctrl+C to stop"
echo ""

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
