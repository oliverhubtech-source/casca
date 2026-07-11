# Casca

*Read this in: **English** | [العربية](README.ar.md) | [বাংলা](README.bn.md) | [Deutsch](README.de.md) | [Español](README.es.md) | [Français](README.fr.md) | [हिन्दी](README.hi.md) | [Bahasa Indonesia](README.id.md) | [Italiano](README.it.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Nederlands](README.nl.md) | [Polski](README.pl.md) | [Português (Brasil)](README.pt-BR.md) | [Русский](README.ru.md) | [ไทย](README.th.md) | [Türkçe](README.tr.md) | [Українська](README.uk.md) | [Tiếng Việt](README.vi.md) | [简体中文](README.zh-Hans.md)*

Turns any website into a native GNOME app: icon in the menu, its own window, no leftover browser bar.

## Installation

### Flatpak (recommended)

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

Needs `flatpak-builder` and the `org.gnome.Platform`/`Sdk` runtime (version declared in the
manifest). If you don't have Flathub set up yet:

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### Straight from the project folder (no Flatpak)

```bash
./install.sh
```

This registers Casca in the GNOME applications menu. If you move the project folder, run the
script again.

## Running without installing

```bash
python3 run.py
```

## User manual

The full manual (covering every option: presets, icon, shortcut, custom browser, mobile mode,
resolution) is built into the app itself — open Casca and tap the help button ("?" icon) in the
top-right corner of the home screen.

## Requirements

- Python 3.11+
- GTK4 and libadwaita 1.5+ (`python3-gi`, `gir1.2-adw-1`)
- WebKitGTK 6.0 (`gir1.2-webkit-6.0`) — used by each app's own window and the built-in manual.
  Without it, Casca still works normally, opening apps in an external browser (Chrome, Chromium,
  GNOME Web, Firefox…), it just loses the colored own-window option.
- Python dependencies (`PyGObject`, `requests`, `Pillow`) are declared in `pyproject.toml`;
  install with `pip install -e .` if you'd rather use an isolated environment (e.g. a venv).

## Project structure

- `casca/window.py` — the UI (GTK4 + libadwaita)
- `casca/browsers.py` — detection of installed browsers and building each app's launch command
- `casca/webview_app.py` — the own-window engine (WebKitGTK), run via `run_webview.py`
- `casca/entries.py` — creating/editing/removing apps (registry + `.desktop` files)
- `casca/presets.py` — the catalog of ready-made sites
- `casca/icons.py` — fetching, downloading and processing icons
- `casca/data/help_template.html` / `casca/help_content.py` — the built-in user manual
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` — the Flatpak manifest

## Brand icons

The icon gallery in `casca/data/social_icons/` uses files from the
[Simple Icons](https://simpleicons.org) project (CC0 license — see `LICENSE.txt` in that same
folder). Brands that asked to be removed from Simple Icons for legal reasons (Microsoft and its
products, Amazon, LinkedIn, Yahoo) don't have a bundled icon — Casca fetches the site's favicon
automatically or shows an initials avatar in those cases.

## Sandboxing (Flatpak)

Running as a Flatpak, Casca deliberately doesn't request the `flatpak-spawn` permission
(`--talk-name=org.freedesktop.Flatpak`) — that permission grants access to running arbitrary
commands on the host and is heavily scrutinized in Flathub review. Sandboxed, Casca only offers
its "own window" (WebKitGTK); it doesn't detect or offer external browsers (that keeps working
normally in the local install via `install.sh`, outside the Flatpak). The `.desktop` files Casca
creates for each web app are run by GNOME Shell (the host), outside the sandbox — when the chosen
engine is the "own window", that `.desktop` reopens Casca itself via
`flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca`.
