#!/bin/bash
# Build Wellnest.dmg for delivery
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/build"
APP="$BUILD/Wellnest.app"
DMG_STAGING="$BUILD/dmg-staging"
DMG_OUT="$BUILD/Wellnest.dmg"
VOLUME_NAME="Wellnest"

bash "$ROOT/scripts/build_app.sh"

rm -rf "$DMG_STAGING"
mkdir -p "$DMG_STAGING"
cp -R "$APP" "$DMG_STAGING/"
if [ -f "$ROOT/packaging/fix_permissions.command" ]; then
  cp "$ROOT/packaging/fix_permissions.command" "$DMG_STAGING/fix_permissions.command"
  chmod +x "$DMG_STAGING/fix_permissions.command"
fi
chmod -R u+rwX,a+rX "$DMG_STAGING"
xattr -cr "$DMG_STAGING" 2>/dev/null || true
ln -s /Applications "$DMG_STAGING/Applications"

rm -f "$DMG_OUT"
hdiutil create \
  -volname "$VOLUME_NAME" \
  -srcfolder "$DMG_STAGING" \
  -ov \
  -format UDZO \
  "$DMG_OUT"

echo ""
echo "Done: $DMG_OUT"
echo "Size: $(du -h "$DMG_OUT" | cut -f1)"
echo ""
echo "Test: open \"$DMG_OUT\""
