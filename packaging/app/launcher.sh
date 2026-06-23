#!/bin/bash
# Wellnest.app — start local server and open dashboard (no Terminal window).
set -uo pipefail

APP_ROOT="$(cd "$(dirname "$0")/../Resources/wellnest" && pwd)"
export ACTIVE_PROFILE=user
export PYTHONPATH="$APP_ROOT"

URL="http://127.0.0.1:8787/app/"
HEALTH="http://127.0.0.1:8787/health"
LOG_DIR="$HOME/Library/Logs/Wellnest"
SUPPORT_DIR="$HOME/Library/Application Support/Wellnest"
VENV_DIR="$SUPPORT_DIR/venv"
PYTHON="$VENV_DIR/bin/python"
PID_FILE="$SUPPORT_DIR/server.pid"
REQ_FILE="$APP_ROOT/requirements-app.txt"

mkdir -p "$LOG_DIR" "$SUPPORT_DIR"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

alert() {
  osascript -e "display alert \"Wellnest\" message \"$1\"" 2>/dev/null || true
}

notify() {
  osascript -e "display notification \"$1\" with title \"Wellnest\"" 2>/dev/null || true
}

python_major_minor() {
  "$1" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null
}

version_ge_310() {
  local ver="$1"
  local major="${ver%%.*}"
  local minor="${ver#*.}"
  minor="${minor%%.*}"
  if [ "$major" -gt 3 ]; then return 0; fi
  if [ "$major" -eq 3 ] && [ "$minor" -ge 10 ]; then return 0; fi
  return 1
}

find_system_python() {
  local cmd ver
  for cmd in \
    /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 /opt/homebrew/bin/python3.10 \
    /usr/local/bin/python3.12 /usr/local/bin/python3.11 /usr/local/bin/python3.10 \
    /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3 python3; do
    if [ -x "$cmd" ] && "$cmd" -c "import sys; sys.exit(0)" 2>/dev/null; then
      ver="$(python_major_minor "$cmd")" || continue
      if version_ge_310 "$ver"; then
        echo "$cmd"
        return 0
      fi
    fi
  done
  return 1
}

ensure_venv() {
  if [ -x "$PYTHON" ]; then
    return 0
  fi
  notify "First launch — setting up (1–2 min)…"
  local sys_py ver
  sys_py="$(find_system_python)" || {
    alert "Python 3.10 or newer is required. In Terminal, run: brew install python@3.12"
    exit 1
  }
  ver="$(python_major_minor "$sys_py")"
  echo "Using Python $ver ($sys_py)" >>"$LOG_DIR/setup.log"
  if ! "$sys_py" -m venv "$VENV_DIR" >>"$LOG_DIR/setup.log" 2>&1; then
    alert "Could not set up Wellnest. See setup.log for details."
    exit 1
  fi
  "$PYTHON" -m pip install --upgrade pip >>"$LOG_DIR/setup.log" 2>&1 || true
}

server_usable() {
  local body code
  body="$(curl -sf "$HEALTH" 2>/dev/null)" || return 1
  echo "$body" | grep -qE '"version": ?3' || return 1
  code="$(curl -sf -o /dev/null -w "%{http_code}" "$URL" 2>/dev/null || echo 000)"
  [ "$code" = "200" ] || return 1
  return 0
}

if server_usable; then
  open "$URL"
  exit 0
fi

if lsof -ti :8787 >/dev/null 2>&1; then
  lsof -ti :8787 | xargs kill 2>/dev/null || true
  sleep 1
fi

cd "$APP_ROOT" || exit 1

ensure_venv

"$PYTHON" -m pip install -r "$REQ_FILE" -q >>"$LOG_DIR/setup.log" 2>&1 || {
  alert "Install error. Open ~/Library/Logs/Wellnest/setup.log"
  open "$LOG_DIR" 2>/dev/null || true
  exit 1
}
"$PYTHON" scripts/init_db.py --profile user >>"$LOG_DIR/setup.log" 2>&1 || true
"$PYTHON" scripts/refresh_dashboard.py >>"$LOG_DIR/setup.log" 2>&1 || true

nohup "$PYTHON" scripts/start_server.py >>"$LOG_DIR/server.log" 2>&1 &
echo $! >"$PID_FILE"

for _ in $(seq 1 120); do
  if server_usable; then
    open "$URL"
    notify "Dashboard opened in your browser"
    exit 0
  fi
  sleep 0.25
done

alert "The server didn't start. Open ~/Library/Logs/Wellnest/server.log"
open "$LOG_DIR" 2>/dev/null || true
exit 1
