#!/usr/bin/env bash
# Compiles every po/<lang>.po into casca/data/locale/<lang>/LC_MESSAGES/casca.mo.
# Run this after editing any .po file — the compiled .mo files are what gettext
# actually reads at runtime (and what's shipped/committed to the repo), not the .po sources.
set -euo pipefail

PO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCALE_DIR="$PO_DIR/../casca/data/locale"

for po_file in "$PO_DIR"/*.po; do
    lang="$(basename "$po_file" .po)"
    dest_dir="$LOCALE_DIR/$lang/LC_MESSAGES"
    mkdir -p "$dest_dir"
    msgfmt --check -o "$dest_dir/casca.mo" "$po_file"
    echo "compiled $lang"
done
