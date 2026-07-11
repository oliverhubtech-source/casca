# Casca

*Lire ceci en : [English](README.md) | [العربية](README.ar.md) | [বাংলা](README.bn.md) | [Deutsch](README.de.md) | [Español](README.es.md) | **Français** | [हिन्दी](README.hi.md) | [Bahasa Indonesia](README.id.md) | [Italiano](README.it.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Nederlands](README.nl.md) | [Polski](README.pl.md) | [Português (Brasil)](README.pt-BR.md) | [Русский](README.ru.md) | [ไทย](README.th.md) | [Türkçe](README.tr.md) | [Українська](README.uk.md) | [Tiếng Việt](README.vi.md) | [简体中文](README.zh-Hans.md)*

Transforme n'importe quel site web en une application GNOME native : icône dans le menu, sa propre fenêtre, sans barre de navigateur qui traîne.

## Installation

### Flatpak (recommandé)

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

Nécessite `flatpak-builder` et le runtime `org.gnome.Platform`/`Sdk` (version déclarée dans le
manifest). Si vous n'avez pas encore configuré Flathub :

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### Directement depuis le dossier du projet (sans Flatpak)

```bash
./install.sh
```

Cela enregistre Casca dans le menu des applications GNOME. Si vous déplacez le dossier du projet,
relancez le script.

## Exécution sans installation

```bash
python3 run.py
```

## Manuel utilisateur

Le manuel complet (couvrant toutes les options : préréglages, icône, raccourci, navigateur
personnalisé, mode mobile, résolution) est intégré directement dans l'application — ouvrez Casca
et appuyez sur le bouton d'aide (icône « ? ») dans le coin supérieur droit de l'écran d'accueil.

## Prérequis

- Python 3.11+
- GTK4 et libadwaita 1.5+ (`python3-gi`, `gir1.2-adw-1`)
- WebKitGTK 6.0 (`gir1.2-webkit-6.0`) — utilisé par la fenêtre propre de chaque application et le
  manuel intégré. Sans cela, Casca fonctionne quand même normalement, en ouvrant les applications
  dans un navigateur externe (Chrome, Chromium, GNOME Web, Firefox…), il perd simplement l'option
  de fenêtre propre colorée.
- Les dépendances Python (`PyGObject`, `requests`, `Pillow`) sont déclarées dans `pyproject.toml` ;
  installez-les avec `pip install -e .` si vous préférez utiliser un environnement isolé (par
  exemple un venv).

## Structure du projet

- `casca/window.py` — l'interface utilisateur (GTK4 + libadwaita)
- `casca/browsers.py` — détection des navigateurs installés et construction de la commande de
  lancement de chaque application
- `casca/webview_app.py` — le moteur de fenêtre propre (WebKitGTK), exécuté via `run_webview.py`
- `casca/entries.py` — création/modification/suppression des applications (registre et fichiers
  `.desktop`)
- `casca/presets.py` — le catalogue des sites prêts à l'emploi
- `casca/icons.py` — récupération, téléchargement et traitement des icônes
- `casca/data/help_template.html` / `casca/help_content.py` — le manuel utilisateur intégré
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` — le manifest Flatpak

## Icônes de marques

La galerie d'icônes dans `casca/data/social_icons/` utilise des fichiers du projet
[Simple Icons](https://simpleicons.org) (licence CC0 — voir `LICENSE.txt` dans ce même dossier).
Les marques qui ont demandé à être retirées de Simple Icons pour des raisons légales (Microsoft et
ses produits, Amazon, LinkedIn, Yahoo) n'ont pas d'icône fournie — Casca récupère automatiquement
le favicon du site ou affiche un avatar avec initiales dans ces cas-là.

## Isolation (Flatpak)

En tant que Flatpak, Casca ne demande volontairement pas la permission `flatpak-spawn`
(`--talk-name=org.freedesktop.Flatpak`) — cette permission accorde l'accès à l'exécution de
commandes arbitraires sur l'hôte et est fortement scrutée lors de la revue Flathub. En mode
sandboxé, Casca propose uniquement sa « fenêtre propre » (WebKitGTK) ; il ne détecte ni ne propose
de navigateurs externes (cela continue de fonctionner normalement dans l'installation locale via
`install.sh`, en dehors du Flatpak). Les fichiers `.desktop` que Casca crée pour chaque application
web sont exécutés par GNOME Shell (l'hôte), en dehors du sandbox — lorsque le moteur choisi est la
« fenêtre propre », ce fichier `.desktop` rouvre Casca lui-même via
`flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca`.
