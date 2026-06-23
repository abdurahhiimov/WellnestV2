#!/bin/bash
# "Open Wellnest" — clears macOS quarantine, then launches the app.
# Double-click this file the FIRST time instead of the app icon.
set -e

APP_NAME="Wellnest.app"
APP_PATH="/Applications/$APP_NAME"

echo "========================================"
echo "  Wellnest — first-launch helper"
echo "========================================"
echo ""

# Step 1: Clear quarantine flag that causes "damaged" error
if [ -d "$APP_PATH" ]; then
  echo "Removing macOS quarantine from $APP_PATH ..."
  xattr -cr "$APP_PATH" 2>/dev/null && echo "  Done." || echo "  (skipped)"
else
  # App not yet in /Applications — try to find it near this script
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
  NEARBY="$SCRIPT_DIR/$APP_NAME"
  if [ -d "$NEARBY" ]; then
    echo "Removing macOS quarantine from $NEARBY ..."
    xattr -cr "$NEARBY" 2>/dev/null && echo "  Done." || echo "  (skipped)"
    echo ""
    echo "NOTE: Please drag Wellnest.app to your Applications folder first,"
    echo "then double-click this script again."
    echo ""
    read -r -p "Press Enter to close..."
    exit 0
  else
    echo "Wellnest.app not found in /Applications."
    echo ""
    echo "Please:"
    echo "  1. Open this DMG"
    echo "  2. Drag Wellnest.app to Applications"
    echo "  3. Double-click 'Open Wellnest' again"
    echo ""
    read -r -p "Press Enter to close..."
    exit 1
  fi
fi

# Step 2: Open the app
echo ""
echo "Opening Wellnest..."
open "$APP_PATH"

echo ""
echo "Wellnest is starting. It may take 1-2 minutes on first launch"
echo "while it finishes setting up. Your browser will open automatically."
echo ""
read -r -p "Press Enter to close this window..."
