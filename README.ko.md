# Casca

*이 언어로 읽기: [English](README.md) | [العربية](README.ar.md) | [বাংলা](README.bn.md) | [Deutsch](README.de.md) | [Español](README.es.md) | [Français](README.fr.md) | [हिन्दी](README.hi.md) | [Bahasa Indonesia](README.id.md) | [Italiano](README.it.md) | [日本語](README.ja.md) | **한국어** | [Nederlands](README.nl.md) | [Polski](README.pl.md) | [Português (Brasil)](README.pt-BR.md) | [Русский](README.ru.md) | [ไทย](README.th.md) | [Türkçe](README.tr.md) | [Українська](README.uk.md) | [Tiếng Việt](README.vi.md) | [简体中文](README.zh-Hans.md)*

모든 웹사이트를 네이티브 GNOME 앱으로 만듭니다: 메뉴에 아이콘이 생기고, 자체 창을 가지며, 브라우저 바가 남지 않습니다.

## 설치

### Flatpak (권장)

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

`flatpak-builder`와 `org.gnome.Platform`/`Sdk` 런타임(매니페스트에 명시된 버전)이 필요합니다. 아직 Flathub이 설정되어 있지 않다면:

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### 프로젝트 폴더에서 직접 실행 (Flatpak 없이)

```bash
./install.sh
```

이 스크립트는 Casca를 GNOME 애플리케이션 메뉴에 등록합니다. 프로젝트 폴더를 이동한 경우, 스크립트를 다시 실행하세요.

## 설치 없이 실행하기

```bash
python3 run.py
```

## 사용자 매뉴얼

전체 매뉴얼(모든 옵션 다룸: 프리셋, 아이콘, 단축키, 사용자 지정 브라우저, 모바일 모드, 해상도)은 앱 자체에 내장되어 있습니다 — Casca를 열고 홈 화면 우측 상단의 도움말 버튼("?" 아이콘)을 누르세요.

## 요구 사항

- Python 3.11+
- GTK4 및 libadwaita 1.5+ (`python3-gi`, `gir1.2-adw-1`)
- WebKitGTK 6.0 (`gir1.2-webkit-6.0`) — 각 앱의 자체 창과 내장 매뉴얼에 사용됩니다.
  이것이 없어도 Casca는 정상적으로 작동하며, 앱을 외부 브라우저(Chrome, Chromium,
  GNOME Web, Firefox 등)에서 엽니다. 다만 색상이 적용된 자체 창 옵션을 사용할 수 없게 됩니다.
- Python 의존성(`PyGObject`, `requests`, `Pillow`)은 `pyproject.toml`에 명시되어 있으며,
  격리된 환경(예: venv)을 사용하고 싶다면 `pip install -e .`로 설치하세요.

## 프로젝트 구조

- `casca/window.py` — UI (GTK4 + libadwaita)
- `casca/browsers.py` — 설치된 브라우저 감지 및 각 앱의 실행 명령 구성
- `casca/webview_app.py` — 자체 창 엔진(WebKitGTK), `run_webview.py`를 통해 실행됨
- `casca/entries.py` — 앱 생성/수정/삭제 (레지스트리 및 `.desktop` 파일)
- `casca/presets.py` — 미리 준비된 사이트 카탈로그
- `casca/icons.py` — 아이콘 가져오기, 다운로드 및 처리
- `casca/data/help_template.html` / `casca/help_content.py` — 내장 사용자 매뉴얼
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` — Flatpak 매니페스트

## 브랜드 아이콘

`casca/data/social_icons/`의 아이콘 갤러리는 [Simple Icons](https://simpleicons.org) 프로젝트의 파일을 사용합니다(CC0 라이선스 — 같은 폴더의 `LICENSE.txt` 참고). 법적 이유로 Simple Icons에서 제외를 요청한 브랜드(Microsoft 및 그 제품들, Amazon, LinkedIn, Yahoo)는 번들 아이콘이 없습니다 — 이 경우 Casca는 사이트의 파비콘을 자동으로 가져오거나 이니셜 아바타를 표시합니다.

## 샌드박싱 (Flatpak)

Flatpak으로 실행될 때, Casca는 의도적으로 `flatpak-spawn` 권한(`--talk-name=org.freedesktop.Flatpak`)을 요청하지 않습니다 — 이 권한은 호스트에서 임의의 명령을 실행할 수 있는 접근을 부여하며 Flathub 리뷰에서 엄격하게 검토됩니다. 샌드박스 안에서 Casca는 "자체 창"(WebKitGTK)만 제공하며, 외부 브라우저를 감지하거나 제공하지 않습니다(이는 Flatpak 외부에서 `install.sh`를 통한 로컬 설치에서는 정상적으로 계속 작동합니다). Casca가 각 웹 앱을 위해 생성하는 `.desktop` 파일은 샌드박스 밖에서 GNOME Shell(호스트)에 의해 실행됩니다 — 선택된 엔진이 "자체 창"인 경우, 해당 `.desktop`은 `flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca`를 통해 Casca 자체를 다시 엽니다.
