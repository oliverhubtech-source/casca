#!/usr/bin/env bash
# Installs Casca into the GNOME applications menu, running straight from this folder.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPLICATIONS_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$APPLICATIONS_DIR/io.github.oliverhubtech_source.Casca.desktop"
ICON_THEME_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

mkdir -p "$APPLICATIONS_DIR" "$ICON_THEME_DIR"
chmod +x "$PROJECT_DIR/run.py"

sed "s|__PROJECT_DIR__|$PROJECT_DIR|g" "$PROJECT_DIR/casca/data/io.github.oliverhubtech_source.Casca.desktop.in" > "$DESKTOP_FILE"
chmod +x "$DESKTOP_FILE"

# Installs the icon into the system theme, so it also works in the "About Casca" screen and alt-tab.
cp "$PROJECT_DIR/casca/data/icons/io.github.oliverhubtech_source.Casca.png" "$ICON_THEME_DIR/io.github.oliverhubtech_source.Casca.png"
HICOLOR_DIR="$HOME/.local/share/icons/hicolor"
# Removes a .svg from a previous install (the icon is now a 256x256 PNG).
rm -f "$HICOLOR_DIR/scalable/apps/io.github.oliverhubtech_source.Casca.svg"
if [ -f "$HICOLOR_DIR/icon-theme.cache" ] && [ ! -f "$HICOLOR_DIR/index.theme" ]; then
    # Stale binary cache with no matching index.theme: blocks discovery of new icons
    # (GTK trusts it instead of scanning the folder). Without this file, GTK scans
    # the folder directly — works the same, just loses the cache's performance shortcut.
    rm -f "$HICOLOR_DIR/icon-theme.cache"
fi
gtk-update-icon-cache "$HICOLOR_DIR" >/dev/null 2>&1 || true

update-desktop-database "$APPLICATIONS_DIR" >/dev/null 2>&1 || true

echo "Casca installed! It should now appear in the GNOME applications menu."
echo "File created at: $DESKTOP_FILE"
