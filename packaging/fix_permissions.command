#!/bin/bash
# Fix macOS "no permission to read" after AirDrop / email / USB transfer.
set -e
echo "Zamira Health — исправление прав доступа..."
echo ""

fix_path() {
  if [ -e "$1" ]; then
    xattr -cr "$1" 2>/dev/null || true
    chmod -R u+rwX "$1" 2>/dev/null || true
    echo "  OK: $1"
  fi
}

for dir in "$HOME/Downloads" "$HOME/Desktop" "$HOME/Documents"; do
  fix_path "$dir/ZamiraHealth.dmg"
  fix_path "$dir/ZamiraHealth.zip"
done

# If this script lives on a mounted DMG, fix the whole volume.
VOL="$(cd "$(dirname "$0")" && pwd -P)"
if [[ "$VOL" == /Volumes/* ]]; then
  fix_path "$VOL"
fi

echo ""
echo "Готово. Теперь:"
echo "  1. Дважды нажмите ZamiraHealth.dmg (в Загрузках)"
echo "  2. Если macOS спросит — нажмите «Открыть»"
echo ""
read -r -p "Нажмите Enter для закрытия..."
