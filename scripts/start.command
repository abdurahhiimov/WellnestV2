#!/bin/bash
# Start Wellnest local server and open the dashboard in the browser.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

URL="http://127.0.0.1:8787/app/"
HEALTH="http://127.0.0.1:8787/health"

if lsof -ti :8787 >/dev/null 2>&1; then
  echo "Restarting server (loads latest code)..."
  lsof -ti :8787 | xargs kill 2>/dev/null || true
  sleep 1
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip -q
pip install -r requirements-app.txt -q
python scripts/init_db.py >/dev/null 2>&1 || true

echo "Starting Wellnest server..."
python scripts/start_server.py &
SERVER_PID=$!

for _ in $(seq 1 50); do
  if curl -sf "$HEALTH" >/dev/null 2>&1; then
    echo "Ready: $URL"
    open "$URL" 2>/dev/null || true
    wait "$SERVER_PID"
    exit 0
  fi
  sleep 0.2
done

echo ""
echo "ERROR: Dashboard server did not start on port 8787."
echo "  1. Close this window and double-click start.command again"
echo "  2. Or run manually:"
echo "       cd $ROOT && source .venv/bin/activate && python scripts/start_server.py"
echo "  3. Then open: $URL"
echo ""
osascript -e 'display alert "Wellnest" message "Server did not start. Double-click start.command again, or open Terminal and run the command shown there."' 2>/dev/null || true
kill "$SERVER_PID" 2>/dev/null || true
exit 1
