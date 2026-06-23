#!/bin/bash
# Build AppIcon.icns from branding/logo.png
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/branding/logo-1024.png"
if [ ! -f "$SRC" ]; then
  SRC="$ROOT/branding/logo.png"
  if [ -f "$SRC" ]; then
    sips -s format png "$SRC" --out "$ROOT/branding/logo-1024.png" >/dev/null
    SRC="$ROOT/branding/logo-1024.png"
  fi
fi
OUT="$ROOT/build/AppIcon.icns"
ICONSET="$ROOT/build/AppIcon.iconset"

if [ ! -f "$SRC" ]; then
  echo "ERROR: Missing $SRC"
  exit 1
fi

rm -rf "$ICONSET"
mkdir -p "$ICONSET" "$(dirname "$OUT")"

make_icon() {
  local size=$1 name=$2
  sips -z "$size" "$size" "$SRC" --out "$ICONSET/$name" >/dev/null
}

make_icon 16  icon_16x16.png
make_icon 32  icon_16x16@2x.png
make_icon 32  icon_32x32.png
make_icon 64  icon_32x32@2x.png
make_icon 128 icon_128x128.png
make_icon 256 icon_128x128@2x.png
make_icon 256 icon_256x256.png
make_icon 512 icon_256x256@2x.png
make_icon 512 icon_512x512.png
make_icon 1024 icon_512x512@2x.png

iconutil -c icns "$ICONSET" -o "$OUT"
echo "Icon: $OUT"
