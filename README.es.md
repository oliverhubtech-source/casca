# Casca

*Leer esto en: [English](README.md) | [العربية](README.ar.md) | [বাংলা](README.bn.md) | [Deutsch](README.de.md) | **Español** | [Français](README.fr.md) | [हिन्दी](README.hi.md) | [Bahasa Indonesia](README.id.md) | [Italiano](README.it.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Nederlands](README.nl.md) | [Polski](README.pl.md) | [Português (Brasil)](README.pt-BR.md) | [Русский](README.ru.md) | [ไทย](README.th.md) | [Türkçe](README.tr.md) | [Українська](README.uk.md) | [Tiếng Việt](README.vi.md) | [简体中文](README.zh-Hans.md)*

Convierte cualquier sitio web en una aplicación nativa de GNOME: icono en el menú, ventana propia, sin barra de navegador residual.

## Instalación

### Flatpak (recomendado)

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

Necesita `flatpak-builder` y el runtime `org.gnome.Platform`/`Sdk` (versión declarada en el
manifiesto). Si aún no tienes Flathub configurado:

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### Directamente desde la carpeta del proyecto (sin Flatpak)

```bash
./install.sh
```

Esto registra Casca en el menú de aplicaciones de GNOME. Si mueves la carpeta del proyecto, ejecuta
el script de nuevo.

## Ejecutar sin instalar

```bash
python3 run.py
```

## Manual de usuario

El manual completo (que cubre todas las opciones: preajustes, icono, atajo, navegador
personalizado, modo móvil, resolución) está integrado en la propia app — abre Casca y toca el
botón de ayuda (icono "?") en la esquina superior derecha de la pantalla de inicio.

## Requisitos

- Python 3.11+
- GTK4 y libadwaita 1.5+ (`python3-gi`, `gir1.2-adw-1`)
- WebKitGTK 6.0 (`gir1.2-webkit-6.0`) — usado por la ventana propia de cada app y por el manual
  integrado. Sin él, Casca sigue funcionando con normalidad, abriendo las apps en un navegador
  externo (Chrome, Chromium, GNOME Web, Firefox…), solo pierde la opción de ventana propia con
  color.
- Las dependencias de Python (`PyGObject`, `requests`, `Pillow`) están declaradas en
  `pyproject.toml`; instálalas con `pip install -e .` si prefieres usar un entorno aislado (por
  ejemplo, un venv).

## Estructura del proyecto

- `casca/window.py` — la interfaz de usuario (GTK4 + libadwaita)
- `casca/browsers.py` — detección de los navegadores instalados y construcción del comando de
  lanzamiento de cada app
- `casca/webview_app.py` — el motor de ventana propia (WebKitGTK), ejecutado mediante `run_webview.py`
- `casca/entries.py` — creación/edición/eliminación de apps (registro y archivos `.desktop`)
- `casca/presets.py` — el catálogo de sitios ya preparados
- `casca/icons.py` — obtención, descarga y procesamiento de iconos
- `casca/data/help_template.html` / `casca/help_content.py` — el manual de usuario integrado
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` — el manifiesto de Flatpak

## Iconos de marcas

La galería de iconos en `casca/data/social_icons/` usa archivos del proyecto
[Simple Icons](https://simpleicons.org) (licencia CC0 — ver `LICENSE.txt` en esa misma carpeta).
Las marcas que pidieron ser eliminadas de Simple Icons por motivos legales (Microsoft y sus
productos, Amazon, LinkedIn, Yahoo) no tienen un icono incluido — en esos casos Casca obtiene
automáticamente el favicon del sitio o muestra un avatar con iniciales.

## Aislamiento (sandboxing) (Flatpak)

Al ejecutarse como Flatpak, Casca deliberadamente no solicita el permiso `flatpak-spawn`
(`--talk-name=org.freedesktop.Flatpak`) — ese permiso otorga acceso para ejecutar comandos
arbitrarios en el host y es objeto de un escrutinio intenso en la revisión de Flathub. En modo
aislado (sandboxed), Casca solo ofrece su "ventana propia" (WebKitGTK); no detecta ni ofrece
navegadores externos (eso sigue funcionando con normalidad en la instalación local mediante
`install.sh`, fuera del Flatpak). Los archivos `.desktop` que Casca crea para cada app web son
ejecutados por GNOME Shell (el host), fuera del sandbox — cuando el motor elegido es la "ventana
propia", ese `.desktop` reabre el propio Casca mediante
`flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca`.
