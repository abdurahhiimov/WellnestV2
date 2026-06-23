#!/bin/bash
# Zip delivery — sometimes works when DMG has permission issues over AirDrop.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
bash "$ROOT/scripts/build_dmg.sh"
STAGING="$ROOT/build/dmg-staging"
ZIP="$ROOT/build/Wellnest.zip"
rm -f "$ZIP"
ditto -c -k --sequesterRsrc --keepParent "$STAGING" "$ZIP"
echo "Zip: $ZIP ($(du -h "$ZIP" | cut -f1))"
echo "Send this if the DMG won't open."
