# Casca

*In dieser Sprache lesen: [English](README.md) | [العربية](README.ar.md) | [বাংলা](README.bn.md) | **Deutsch** | [Español](README.es.md) | [Français](README.fr.md) | [हिन्दी](README.hi.md) | [Bahasa Indonesia](README.id.md) | [Italiano](README.it.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Nederlands](README.nl.md) | [Polski](README.pl.md) | [Português (Brasil)](README.pt-BR.md) | [Русский](README.ru.md) | [ไทย](README.th.md) | [Türkçe](README.tr.md) | [Українська](README.uk.md) | [Tiếng Việt](README.vi.md) | [简体中文](README.zh-Hans.md)*

Verwandelt jede Website in eine native GNOME-App: eigenes Icon im Menü, eigenes Fenster, keine übrig gebliebene Browserleiste.

## Installation

### Flatpak (empfohlen)

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

Benötigt `flatpak-builder` und die `org.gnome.Platform`/`Sdk`-Runtime (Version im
Manifest angegeben). Falls Flathub noch nicht eingerichtet ist:

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### Direkt aus dem Projektordner (ohne Flatpak)

```bash
./install.sh
```

Dies registriert Casca im GNOME-Anwendungsmenü. Falls du den Projektordner verschiebst, führe
das Skript erneut aus.

## Ausführen ohne Installation

```bash
python3 run.py
```

## Benutzerhandbuch

Das vollständige Handbuch (das jede Option abdeckt: Presets, Icon, Tastenkürzel, benutzerdefinierter
Browser, Mobilmodus, Auflösung) ist direkt in die App integriert — öffne Casca und tippe auf die
Hilfe-Schaltfläche ("?"-Icon) in der oberen rechten Ecke des Startbildschirms.

## Voraussetzungen

- Python 3.11+
- GTK4 und libadwaita 1.5+ (`python3-gi`, `gir1.2-adw-1`)
- WebKitGTK 6.0 (`gir1.2-webkit-6.0`) — wird vom eigenen Fenster jeder App und dem integrierten
  Handbuch verwendet. Ohne diese Komponente funktioniert Casca weiterhin normal und öffnet Apps
  in einem externen Browser (Chrome, Chromium, GNOME Web, Firefox…), verliert dabei nur die
  farbige Option für ein eigenes Fenster.
- Python-Abhängigkeiten (`PyGObject`, `requests`, `Pillow`) sind in `pyproject.toml` deklariert;
  installiere sie mit `pip install -e .`, falls du lieber eine isolierte Umgebung verwenden
  möchtest (z. B. ein venv).

## Projektstruktur

- `casca/window.py` — die Benutzeroberfläche (GTK4 + libadwaita)
- `casca/browsers.py` — Erkennung installierter Browser und Erstellung des Startbefehls jeder App
- `casca/webview_app.py` — die Engine für das eigene Fenster (WebKitGTK), ausgeführt über `run_webview.py`
- `casca/entries.py` — Erstellen/Bearbeiten/Entfernen von Apps (Registry + `.desktop`-Dateien)
- `casca/presets.py` — der Katalog fertiger Websites
- `casca/icons.py` — Abrufen, Herunterladen und Verarbeiten von Icons
- `casca/data/help_template.html` / `casca/help_content.py` — das integrierte Benutzerhandbuch
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` — das Flatpak-Manifest

## Marken-Icons

Die Icon-Galerie in `casca/data/social_icons/` verwendet Dateien aus dem Projekt
[Simple Icons](https://simpleicons.org) (CC0-Lizenz — siehe `LICENSE.txt` im selben Ordner).
Marken, die aus rechtlichen Gründen ihre Entfernung aus Simple Icons verlangt haben (Microsoft
und seine Produkte, Amazon, LinkedIn, Yahoo) haben kein mitgeliefertes Icon — Casca ruft in
diesen Fällen automatisch das Favicon der Website ab oder zeigt einen Avatar mit Initialen an.

## Sandboxing (Flatpak)

Als Flatpak ausgeführt, fordert Casca bewusst nicht die `flatpak-spawn`-Berechtigung an
(`--talk-name=org.freedesktop.Flatpak`) — diese Berechtigung gewährt Zugriff auf die Ausführung
beliebiger Befehle auf dem Host und wird in der Flathub-Überprüfung streng geprüft. Im Sandbox-
Modus bietet Casca nur sein "eigenes Fenster" (WebKitGTK) an; es erkennt oder bietet keine
externen Browser an (das funktioniert weiterhin normal in der lokalen Installation über
`install.sh`, außerhalb des Flatpaks). Die `.desktop`-Dateien, die Casca für jede Web-App
erstellt, werden von GNOME Shell (dem Host) außerhalb der Sandbox ausgeführt — wenn die gewählte
Engine das "eigene Fenster" ist, öffnet diese `.desktop`-Datei Casca selbst erneut über
`flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca`.
