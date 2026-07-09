#!/usr/bin/env bash
# Instala o Casca no menu de aplicativos do GNOME, rodando direto desta pasta.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPLICATIONS_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$APPLICATIONS_DIR/io.github.oliverhubtech_source.Casca.desktop"
ICON_THEME_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

mkdir -p "$APPLICATIONS_DIR" "$ICON_THEME_DIR"
chmod +x "$PROJECT_DIR/run.py"

sed "s|__PROJECT_DIR__|$PROJECT_DIR|g" "$PROJECT_DIR/casca/data/io.github.oliverhubtech_source.Casca.desktop.in" > "$DESKTOP_FILE"
chmod +x "$DESKTOP_FILE"

# Instala o ícone no tema do sistema, pra funcionar também na tela "Sobre o Casca" e no alt-tab.
cp "$PROJECT_DIR/casca/data/icons/io.github.oliverhubtech_source.Casca.png" "$ICON_THEME_DIR/io.github.oliverhubtech_source.Casca.png"
HICOLOR_DIR="$HOME/.local/share/icons/hicolor"
# Remove um .svg de uma instalação anterior (o ícone agora é PNG 256x256).
rm -f "$HICOLOR_DIR/scalable/apps/io.github.oliverhubtech_source.Casca.svg"
if [ -f "$HICOLOR_DIR/icon-theme.cache" ] && [ ! -f "$HICOLOR_DIR/index.theme" ]; then
    # Cache binário desatualizado sem index.theme correspondente: bloqueia a busca de ícones
    # novos (o GTK confia nele em vez de escanear a pasta). Sem esse arquivo, o GTK escaneia
    # a pasta diretamente — funciona igual, só perde o atalho de performance do cache.
    rm -f "$HICOLOR_DIR/icon-theme.cache"
fi
gtk-update-icon-cache "$HICOLOR_DIR" >/dev/null 2>&1 || true

update-desktop-database "$APPLICATIONS_DIR" >/dev/null 2>&1 || true

echo "Casca instalado! Ele já deve aparecer no menu de aplicativos do GNOME."
echo "Arquivo criado em: $DESKTOP_FILE"
