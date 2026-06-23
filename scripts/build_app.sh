#!/bin/bash
# Assemble Wellnest.app into build/
# Bundles a standalone Python runtime — no system Python required by end user.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/build"
APP="$BUILD/Wellnest.app"
PAYLOAD="$APP/Contents/Resources/wellnest"

bash "$ROOT/scripts/build_icon.sh"

# ── Standalone Python binaries ───────────────────────────────────────────────
# Two separate tarballs: ARM64 (Apple Silicon) + x86_64 (Intel).
# The launcher picks the right one at runtime via `uname -m`.
PY_DATE="20260602"
PY_ARM_VER="3.13.13"
PY_X86_VER="3.12.13"
PY_ARM_ASSET="cpython-${PY_ARM_VER}+${PY_DATE}-aarch64-apple-darwin-install_only_stripped.tar.gz"
PY_X86_ASSET="cpython-${PY_X86_VER}+${PY_DATE}-x86_64-apple-darwin-install_only.tar.gz"
PY_BASE="https://github.com/astral-sh/python-build-standalone/releases/download/${PY_DATE}"

mkdir -p "$BUILD"

download_python() {
  local asset="$1" cache="$BUILD/$1"
  if [ ! -f "$cache" ] || [ "$(wc -c < "$cache")" -lt 1000000 ]; then
    echo "Downloading $asset..."
    curl -L --progress-bar -o "$cache" "$PY_BASE/$asset" || {
      echo "ERROR: Could not download $asset"
      exit 1
    }
  fi
}

download_python "$PY_ARM_ASSET"
download_python "$PY_X86_ASSET"

echo "Bundling Python runtimes..."
PY_ARM_DIR="$APP/Contents/MacOS/python_arm64"
PY_X86_DIR="$APP/Contents/MacOS/python_x86_64"
rm -rf "$PY_ARM_DIR" "$PY_X86_DIR"
mkdir -p "$PY_ARM_DIR" "$PY_X86_DIR"
tar -xzf "$BUILD/$PY_ARM_ASSET" -C "$PY_ARM_DIR" --strip-components=1
tar -xzf "$BUILD/$PY_X86_ASSET" -C "$PY_X86_DIR" --strip-components=1
echo "  ARM64:  $(du -sh "$PY_ARM_DIR" | cut -f1)"
echo "  x86_64: $(du -sh "$PY_X86_DIR" | cut -f1)"

# ── Clinical reference DB ────────────────────────────────────────────────────
if [[ -f "$ROOT/data/reference/reference.db" ]]; then
  echo "Reference DB present: $(du -h "$ROOT/data/reference/reference.db" | cut -f1)"
else
  echo "Building reference DB..."
  PYTHON_BIN="$PY_ARM_DIR/bin/python3"
  [ -x "$PYTHON_BIN" ] || PYTHON_BIN="$PY_X86_DIR/bin/python3"
  "$PYTHON_BIN" "$ROOT/scripts/download_reference_db.py" --offline || true
fi

# ── Assemble .app bundle ─────────────────────────────────────────────────────
rm -f "$APP/Contents/MacOS/wellnest" "$APP/Contents/Info.plist" \
      "$APP/Contents/Resources/AppIcon.icns"
rm -rf "$PAYLOAD"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources" "$PAYLOAD"

cp "$ROOT/packaging/app/Info.plist"  "$APP/Contents/Info.plist"
cp "$ROOT/build/AppIcon.icns"        "$APP/Contents/Resources/AppIcon.icns"
cp "$ROOT/packaging/app/launcher.sh" "$APP/Contents/MacOS/wellnest"
chmod +x "$APP/Contents/MacOS/wellnest"

# Build the React dashboard
if [ -d "$ROOT/frontend" ] && command -v npm >/dev/null 2>&1; then
  if [ ! -f "$ROOT/frontend/dist/index.html" ] || \
     [ -n "$(find "$ROOT/frontend/src" -newer "$ROOT/frontend/dist/index.html" -print -quit 2>/dev/null)" ]; then
    echo "Building frontend..."
    (cd "$ROOT/frontend" && npm install --no-audit --no-fund && npm run build) \
      || echo "WARN: frontend build failed"
  fi
fi

rsync -a \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude 'venv' \
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

# Shallow ad-hoc sign only the main executable — deep signing bundled Python
# binaries causes Gatekeeper "damaged" errors on macOS 13+ without a paid
# Apple Developer ID. Users run "Open Wellnest.command" from the DMG instead.
if command -v codesign >/dev/null 2>&1; then
  codesign --force --sign - "$APP/Contents/MacOS/wellnest" 2>/dev/null || true
fi

echo ""
echo "App bundle: $APP"
du -sh "$APP"
