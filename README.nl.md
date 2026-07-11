# Casca

*Lees dit in: [English](README.md) | [العربية](README.ar.md) | [বাংলা](README.bn.md) | [Deutsch](README.de.md) | [Español](README.es.md) | [Français](README.fr.md) | [हिन्दी](README.hi.md) | [Bahasa Indonesia](README.id.md) | [Italiano](README.it.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | **Nederlands** | [Polski](README.pl.md) | [Português (Brasil)](README.pt-BR.md) | [Русский](README.ru.md) | [ไทย](README.th.md) | [Türkçe](README.tr.md) | [Українська](README.uk.md) | [Tiếng Việt](README.vi.md) | [简体中文](README.zh-Hans.md)*

Zet elke website om in een native GNOME-app: pictogram in het menu, eigen venster, geen overgebleven browserbalk.

## Installatie

### Flatpak (aanbevolen)

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

Vereist `flatpak-builder` en de `org.gnome.Platform`/`Sdk`-runtime (versie zoals opgegeven in het
manifest). Als je Flathub nog niet hebt ingesteld:

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### Rechtstreeks vanuit de projectmap (zonder Flatpak)

```bash
./install.sh
```

Dit registreert Casca in het GNOME-toepassingenmenu. Als je de projectmap verplaatst, voer het
script dan opnieuw uit.

## Uitvoeren zonder installatie

```bash
python3 run.py
```

## Gebruikershandleiding

De volledige handleiding (die elke optie behandelt: voorinstellingen, pictogram, sneltoets,
aangepaste browser, mobiele modus, resolutie) is ingebouwd in de app zelf — open Casca en tik op
de help-knop (het "?"-pictogram) in de rechterbovenhoek van het beginscherm.

## Vereisten

- Python 3.11+
- GTK4 en libadwaita 1.5+ (`python3-gi`, `gir1.2-adw-1`)
- WebKitGTK 6.0 (`gir1.2-webkit-6.0`) — gebruikt door het eigen venster van elke app en de
  ingebouwde handleiding. Zonder deze werkt Casca nog steeds normaal en opent apps in een externe
  browser (Chrome, Chromium, GNOME Web, Firefox…), maar verliest dan de gekleurde
  eigen-venster-optie.
- Python-afhankelijkheden (`PyGObject`, `requests`, `Pillow`) zijn gedeclareerd in
  `pyproject.toml`; installeer met `pip install -e .` als je liever een geïsoleerde omgeving
  gebruikt (bijv. een venv).

## Projectstructuur

- `casca/window.py` — de UI (GTK4 + libadwaita)
- `casca/browsers.py` — detectie van geïnstalleerde browsers en het opbouwen van het
  opstartcommando van elke app
- `casca/webview_app.py` — de eigen-venster-engine (WebKitGTK), uitgevoerd via `run_webview.py`
- `casca/entries.py` — apps aanmaken/bewerken/verwijderen (register + `.desktop`-bestanden)
- `casca/presets.py` — de catalogus van kant-en-klare sites
- `casca/icons.py` — pictogrammen ophalen, downloaden en verwerken
- `casca/data/help_template.html` / `casca/help_content.py` — de ingebouwde gebruikershandleiding
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` — het Flatpak-manifest

## Merkpictogrammen

De pictogramgalerij in `casca/data/social_icons/` gebruikt bestanden van het
[Simple Icons](https://simpleicons.org)-project (CC0-licentie — zie `LICENSE.txt` in dezelfde
map). Merken die om juridische redenen hebben gevraagd om verwijdering uit Simple Icons (Microsoft
en zijn producten, Amazon, LinkedIn, Yahoo) hebben geen meegeleverd pictogram — Casca haalt in die
gevallen automatisch het favicon van de site op of toont een avatar met initialen.

## Sandboxing (Flatpak)

Wanneer Casca als Flatpak draait, vraagt het bewust niet om de `flatpak-spawn`-toestemming
(`--talk-name=org.freedesktop.Flatpak`) — die toestemming geeft toegang tot het uitvoeren van
willekeurige commando's op de host en wordt streng gecontroleerd bij Flathub-review. Binnen de
sandbox biedt Casca alleen zijn "eigen venster" (WebKitGTK) aan; het detecteert of biedt geen
externe browsers aan (dat blijft normaal werken bij de lokale installatie via `install.sh`, buiten
de Flatpak). De `.desktop`-bestanden die Casca voor elke webapp aanmaakt, worden uitgevoerd door
GNOME Shell (de host), buiten de sandbox — wanneer de gekozen engine het "eigen venster" is, opent
dat `.desktop`-bestand Casca zelf opnieuw via
`flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca`.
