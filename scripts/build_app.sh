#!/bin/bash
# Assemble Wellnest.app into build/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/build"
APP="$BUILD/Wellnest.app"
PAYLOAD="$APP/Contents/Resources/wellnest"

bash "$ROOT/scripts/build_icon.sh"

# Clinical reference DB (RxNorm + openFDA + curated guidelines)
if [[ -f "$ROOT/data/reference/reference.db" ]]; then
  echo "Reference DB present: $(du -h "$ROOT/data/reference/reference.db" | cut -f1)"
else
  echo "Building reference DB..."
  if command -v python3 >/dev/null 2>&1; then
    python3 "$ROOT/scripts/download_reference_db.py" || python3 "$ROOT/scripts/download_reference_db.py" --offline
  fi
fi

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources" "$PAYLOAD"

cp "$ROOT/packaging/app/Info.plist" "$APP/Contents/Info.plist"
cp "$ROOT/build/AppIcon.icns" "$APP/Contents/Resources/AppIcon.icns"
cp "$ROOT/packaging/app/launcher.sh" "$APP/Contents/MacOS/wellnest"
chmod +x "$APP/Contents/MacOS/wellnest"

# Build the React dashboard if sources are present (frontend/dist ships in the app).
if [ -d "$ROOT/frontend" ] && command -v npm >/dev/null 2>&1; then
  if [ ! -f "$ROOT/frontend/dist/index.html" ] || [ -n "$(find "$ROOT/frontend/src" -newer "$ROOT/frontend/dist/index.html" -print -quit 2>/dev/null)" ]; then
    echo "Building frontend…"
    (cd "$ROOT/frontend" && npm install --no-audit --no-fund && npm run build) || echo "WARN: frontend build failed; app falls back to legacy dashboard"
  fi
fi

rsync -a \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude 'build' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.DS_Store' \
  --exclude 'node_modules' \
  --exclude '/dist' \
  --exclude 'frontend/src' \
  --exclude 'frontend/public' \
  --exclude 'profiles/zamira' \
  --exclude 'profiles/aziz' \
  --exclude '_petvita' \
  --exclude '_archive' \
  "$ROOT/" "$PAYLOAD/"

# Ad-hoc sign (does not remove Gatekeeper prompt without Apple Developer ID, but marks bundle consistently)
if command -v codesign >/dev/null 2>&1; then
  codesign --force --deep --sign - "$APP" 2>/dev/null || true
fi

echo "App bundle: $APP"
du -sh "$APP"
