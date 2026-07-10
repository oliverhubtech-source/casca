# Casca

*Leia em: [English](README.md) | **Português (Brasil)***

Transforma qualquer site num app do GNOME: ícone no menu, janela própria, sem barra de navegação sobrando.

## Instalação

### Flatpak (recomendado)

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

Precisa do `flatpak-builder` e do runtime `org.gnome.Platform`/`Sdk` (versão declarada no
manifest). Se ainda não tiver o Flathub configurado:

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### Direto da pasta do projeto (sem Flatpak)

```bash
./install.sh
```

Isso registra o Casca no menu de aplicativos do GNOME. Se você mover a pasta do projeto, rode o script de novo.

## Rodar sem instalar

```bash
python3 run.py
```

## Manual de uso

O manual completo (com todas as opções: predefinidos, ícone, atalho, navegador personalizado, modo mobile,
resolução) está embutido no próprio app — abra o Casca e toque no botão de ajuda (ícone de "?") no canto
superior direito da tela inicial.

## Requisitos

- Python 3.11+
- GTK4 e libadwaita 1.5+ (`python3-gi`, `gir1.2-adw-1`)
- WebKitGTK 6.0 (`gir1.2-webkit-6.0`) — usado pela janela própria de cada app e pelo manual embutido.
  Sem ele, o Casca ainda funciona normalmente abrindo apps num navegador externo (Chrome, Chromium,
  GNOME Web, Firefox…), só perde a opção de janela própria colorida.
- Dependências Python (`PyGObject`, `requests`, `Pillow`) estão declaradas em `pyproject.toml`;
  instale com `pip install -e .` se preferir um ambiente isolado (ex.: venv).

## Estrutura do projeto

- `casca/window.py` — interface (GTK4 + libadwaita)
- `casca/browsers.py` — detecção de navegadores instalados e montagem do comando de cada app
- `casca/webview_app.py` — motor de janela própria (WebKitGTK), executado via `run_webview.py`
- `casca/entries.py` — criação/edição/remoção dos apps (registro + arquivos `.desktop`)
- `casca/presets.py` — catálogo de sites pré-definidos
- `casca/icons.py` — busca, download e processamento de ícones
- `casca/data/help_template.html` / `casca/help_content.py` — manual de uso embutido
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` — manifest do Flatpak

## Ícones de marca

A galeria de ícones em `casca/data/social_icons/` usa arquivos do projeto
[Simple Icons](https://simpleicons.org) (licença CC0 — ver `LICENSE.txt` na própria pasta).
Marcas que pediram remoção do Simple Icons por motivos legais (Microsoft e seus produtos,
Amazon, LinkedIn, Yahoo) não têm ícone embutido — o Casca busca o favicon do site
automaticamente ou mostra um avatar com iniciais nesses casos.

## Sandboxing (Flatpak)

Rodando como Flatpak, o Casca deliberadamente não pede a permissão `flatpak-spawn`
(`--talk-name=org.freedesktop.Flatpak`) — essa permissão dá acesso a rodar comandos
arbitrários no host e é fortemente escrutinada no review do Flathub. Sandboxado, o Casca só
oferece sua "janela própria" (WebKitGTK); ele não detecta nem oferece navegadores externos
(isso continua funcionando normalmente na instalação local via `install.sh`, fora do Flatpak).
Os arquivos `.desktop` que o Casca cria pra cada web app são executados pelo GNOME Shell (host),
fora do sandbox — quando o motor escolhido é a "janela própria", esse `.desktop` reabre o
próprio Casca via `flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca`.
