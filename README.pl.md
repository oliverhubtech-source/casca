# Casca

*Czytaj to w: [English](README.md) | [العربية](README.ar.md) | [বাংলা](README.bn.md) | [Deutsch](README.de.md) | [Español](README.es.md) | [Français](README.fr.md) | [हिन्दी](README.hi.md) | [Bahasa Indonesia](README.id.md) | [Italiano](README.it.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Nederlands](README.nl.md) | **Polski** | [Português (Brasil)](README.pt-BR.md) | [Русский](README.ru.md) | [ไทย](README.th.md) | [Türkçe](README.tr.md) | [Українська](README.uk.md) | [Tiếng Việt](README.vi.md) | [简体中文](README.zh-Hans.md)*

Zamienia dowolną stronę internetową w natywną aplikację GNOME: ikona w menu, własne okno, bez pozostałości paska przeglądarki.

## Instalacja

### Flatpak (zalecane)

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

Wymaga `flatpak-builder` oraz środowiska uruchomieniowego `org.gnome.Platform`/`Sdk` (wersja podana w
manifeście). Jeśli nie masz jeszcze skonfigurowanego Flathub:

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### Bezpośrednio z folderu projektu (bez Flatpak)

```bash
./install.sh
```

To rejestruje Casca w menu aplikacji GNOME. Jeśli przeniesiesz folder projektu, uruchom skrypt
ponownie.

## Uruchamianie bez instalacji

```bash
python3 run.py
```

## Podręcznik użytkownika

Pełny podręcznik (obejmujący każdą opcję: presety, ikonę, skrót, niestandardową przeglądarkę, tryb
mobilny, rozdzielczość) jest wbudowany w samą aplikację — otwórz Casca i dotknij przycisku pomocy
(ikona „?") w prawym górnym rogu ekranu głównego.

## Wymagania

- Python 3.11+
- GTK4 i libadwaita 1.5+ (`python3-gi`, `gir1.2-adw-1`)
- WebKitGTK 6.0 (`gir1.2-webkit-6.0`) — używane przez własne okno każdej aplikacji oraz wbudowany
  podręcznik. Bez niego Casca nadal działa normalnie, otwierając aplikacje w zewnętrznej
  przeglądarce (Chrome, Chromium, GNOME Web, Firefox…), traci jedynie opcję kolorowego własnego
  okna.
- Zależności Python (`PyGObject`, `requests`, `Pillow`) są zadeklarowane w `pyproject.toml`;
  zainstaluj za pomocą `pip install -e .`, jeśli wolisz używać izolowanego środowiska (np. venv).

## Struktura projektu

- `casca/window.py` — interfejs użytkownika (GTK4 + libadwaita)
- `casca/browsers.py` — wykrywanie zainstalowanych przeglądarek i budowanie polecenia uruchamiania
  każdej aplikacji
- `casca/webview_app.py` — silnik własnego okna (WebKitGTK), uruchamiany przez `run_webview.py`
- `casca/entries.py` — tworzenie/edycja/usuwanie aplikacji (rejestr i pliki `.desktop`)
- `casca/presets.py` — katalog gotowych stron
- `casca/icons.py` — pobieranie, ściąganie i przetwarzanie ikon
- `casca/data/help_template.html` / `casca/help_content.py` — wbudowany podręcznik użytkownika
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` — manifest Flatpak

## Ikony marek

Galeria ikon w `casca/data/social_icons/` wykorzystuje pliki z projektu
[Simple Icons](https://simpleicons.org) (licencja CC0 — zobacz `LICENSE.txt` w tym samym
folderze). Marki, które poprosiły o usunięcie z Simple Icons z powodów prawnych (Microsoft i jego
produkty, Amazon, LinkedIn, Yahoo) nie mają dołączonej ikony — w takich przypadkach Casca
automatycznie pobiera favicon strony lub wyświetla awatar z inicjałami.

## Piaskownica (Flatpak)

Działając jako Flatpak, Casca celowo nie żąda uprawnienia `flatpak-spawn`
(`--talk-name=org.freedesktop.Flatpak`) — to uprawnienie daje dostęp do uruchamiania dowolnych
poleceń na hoście i jest szczegółowo kontrolowane podczas przeglądu Flathub. W piaskownicy Casca
oferuje jedynie „własne okno" (WebKitGTK); nie wykrywa ani nie oferuje zewnętrznych przeglądarek
(to nadal działa normalnie w lokalnej instalacji przez `install.sh`, poza Flatpak). Pliki
`.desktop` tworzone przez Casca dla każdej aplikacji webowej są uruchamiane przez GNOME Shell
(hosta), poza piaskownicą — gdy wybranym silnikiem jest „własne okno", ten plik `.desktop` ponownie
otwiera samą Casca poprzez
`flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca`.
