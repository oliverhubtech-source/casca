# Casca

*Leggi questo in: [English](README.md) | [العربية](README.ar.md) | [বাংলা](README.bn.md) | [Deutsch](README.de.md) | [Español](README.es.md) | [Français](README.fr.md) | [हिन्दी](README.hi.md) | [Bahasa Indonesia](README.id.md) | **Italiano** | [日本語](README.ja.md) | [한국어](README.ko.md) | [Nederlands](README.nl.md) | [Polski](README.pl.md) | [Português (Brasil)](README.pt-BR.md) | [Русский](README.ru.md) | [ไทย](README.th.md) | [Türkçe](README.tr.md) | [Українська](README.uk.md) | [Tiếng Việt](README.vi.md) | [简体中文](README.zh-Hans.md)*

Trasforma qualsiasi sito web in un'app nativa GNOME: icona nel menu, finestra propria, nessuna barra del browser residua.

## Installazione

### Flatpak (consigliato)

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

Serve `flatpak-builder` e il runtime `org.gnome.Platform`/`Sdk` (versione dichiarata nel
manifest). Se non hai ancora configurato Flathub:

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### Direttamente dalla cartella del progetto (senza Flatpak)

```bash
./install.sh
```

Questo registra Casca nel menu delle applicazioni GNOME. Se sposti la cartella del progetto, esegui
di nuovo lo script.

## Eseguire senza installare

```bash
python3 run.py
```

## Manuale utente

Il manuale completo (che copre ogni opzione: preset, icona, scorciatoia, browser personalizzato, modalità
mobile, risoluzione) è integrato nell'app stessa — apri Casca e tocca il pulsante di aiuto (icona "?") nell'angolo
in alto a destra della schermata principale.

## Requisiti

- Python 3.11+
- GTK4 e libadwaita 1.5+ (`python3-gi`, `gir1.2-adw-1`)
- WebKitGTK 6.0 (`gir1.2-webkit-6.0`) — usato dalla finestra propria di ogni app e dal manuale
  integrato. Senza di esso, Casca funziona comunque normalmente, aprendo le app in un browser esterno
  (Chrome, Chromium, GNOME Web, Firefox…), perde solo l'opzione della finestra propria colorata.
- Le dipendenze Python (`PyGObject`, `requests`, `Pillow`) sono dichiarate in `pyproject.toml`;
  installale con `pip install -e .` se preferisci usare un ambiente isolato (ad esempio un venv).

## Struttura del progetto

- `casca/window.py` — l'interfaccia utente (GTK4 + libadwaita)
- `casca/browsers.py` — rilevamento dei browser installati e costruzione del comando di avvio di ogni app
- `casca/webview_app.py` — il motore della finestra propria (WebKitGTK), eseguito tramite `run_webview.py`
- `casca/entries.py` — creazione/modifica/rimozione delle app (registro e file `.desktop`)
- `casca/presets.py` — il catalogo dei siti già pronti
- `casca/icons.py` — recupero, download ed elaborazione delle icone
- `casca/data/help_template.html` / `casca/help_content.py` — il manuale utente integrato
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` — il manifest Flatpak

## Icone dei brand

La galleria di icone in `casca/data/social_icons/` usa file del progetto
[Simple Icons](https://simpleicons.org) (licenza CC0 — vedi `LICENSE.txt` nella stessa
cartella). I brand che hanno chiesto di essere rimossi da Simple Icons per motivi legali (Microsoft e i suoi
prodotti, Amazon, LinkedIn, Yahoo) non hanno un'icona inclusa — Casca recupera automaticamente la favicon
del sito o mostra un avatar con le iniziali in questi casi.

## Sandboxing (Flatpak)

Eseguito come Flatpak, Casca deliberatamente non richiede il permesso `flatpak-spawn`
(`--talk-name=org.freedesktop.Flatpak`) — questo permesso concede l'accesso all'esecuzione di comandi
arbitrari sull'host ed è pesantemente controllato nella revisione di Flathub. In sandbox, Casca offre solo
la "finestra propria" (WebKitGTK); non rileva né offre browser esterni (questo continua a funzionare
normalmente nell'installazione locale tramite `install.sh`, al di fuori del Flatpak). I file `.desktop` che Casca
crea per ogni web app vengono eseguiti da GNOME Shell (l'host), al di fuori della sandbox — quando il motore
scelto è la "finestra propria", quel `.desktop` riapre Casca stesso tramite
`flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca`.
