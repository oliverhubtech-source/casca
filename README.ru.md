# Casca

*Читать это на: [English](README.md) | [العربية](README.ar.md) | [বাংলা](README.bn.md) | [Deutsch](README.de.md) | [Español](README.es.md) | [Français](README.fr.md) | [हिन्दी](README.hi.md) | [Bahasa Indonesia](README.id.md) | [Italiano](README.it.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Nederlands](README.nl.md) | [Polski](README.pl.md) | [Português (Brasil)](README.pt-BR.md) | **Русский** | [ไทย](README.th.md) | [Türkçe](README.tr.md) | [Українська](README.uk.md) | [Tiếng Việt](README.vi.md) | [简体中文](README.zh-Hans.md)*

Превращает любой сайт в нативное приложение GNOME: значок в меню, собственное окно, никакой лишней панели браузера.

## Установка

### Flatpak (рекомендуется)

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

Требуется `flatpak-builder` и runtime `org.gnome.Platform`/`Sdk` (версия указана в
манифесте). Если у вас ещё не настроен Flathub:

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### Прямо из папки проекта (без Flatpak)

```bash
./install.sh
```

Это регистрирует Casca в меню приложений GNOME. Если вы переместите папку проекта, запустите
скрипт снова.

## Запуск без установки

```bash
python3 run.py
```

## Руководство пользователя

Полное руководство (охватывающее все опции: пресеты, значок, ярлык, пользовательский браузер,
мобильный режим, разрешение) встроено прямо в приложение — откройте Casca и нажмите кнопку
справки (значок "?") в правом верхнем углу главного экрана.

## Требования

- Python 3.11+
- GTK4 и libadwaita 1.5+ (`python3-gi`, `gir1.2-adw-1`)
- WebKitGTK 6.0 (`gir1.2-webkit-6.0`) — используется собственным окном каждого приложения и
  встроенным руководством. Без него Casca по-прежнему работает нормально, открывая приложения во
  внешнем браузере (Chrome, Chromium, GNOME Web, Firefox…), просто теряется опция цветного
  собственного окна.
- Зависимости Python (`PyGObject`, `requests`, `Pillow`) указаны в `pyproject.toml`;
  устанавливайте через `pip install -e .`, если предпочитаете изолированное окружение
  (например, venv).

## Структура проекта

- `casca/window.py` — интерфейс (GTK4 + libadwaita)
- `casca/browsers.py` — обнаружение установленных браузеров и формирование команды запуска
  для каждого приложения
- `casca/webview_app.py` — движок собственного окна (WebKitGTK), запускается через
  `run_webview.py`
- `casca/entries.py` — создание/редактирование/удаление приложений (реестр и файлы `.desktop`)
- `casca/presets.py` — каталог готовых сайтов
- `casca/icons.py` — получение, загрузка и обработка значков
- `casca/data/help_template.html` / `casca/help_content.py` — встроенное руководство пользователя
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` — манифест Flatpak

## Значки брендов

Галерея значков в `casca/data/social_icons/` использует файлы из проекта
[Simple Icons](https://simpleicons.org) (лицензия CC0 — см. `LICENSE.txt` в той же папке).
Бренды, которые попросили удалить их из Simple Icons по юридическим причинам (Microsoft и её
продукты, Amazon, LinkedIn, Yahoo), не имеют встроенного значка — в этих случаях Casca
автоматически получает favicon сайта или показывает аватар с инициалами.

## Песочница (Flatpak)

Работая как Flatpak, Casca намеренно не запрашивает разрешение `flatpak-spawn`
(`--talk-name=org.freedesktop.Flatpak`) — это разрешение даёт доступ к запуску произвольных
команд на хосте и тщательно проверяется при рецензировании Flathub. В песочнице Casca предлагает
только "собственное окно" (WebKitGTK); она не обнаруживает и не предлагает внешние браузеры (это
по-прежнему работает нормально при локальной установке через `install.sh`, вне Flatpak). Файлы
`.desktop`, которые Casca создаёт для каждого веб-приложения, запускаются GNOME Shell (хостом),
вне песочницы — когда выбранный движок это "собственное окно", этот `.desktop` заново открывает
саму Casca через `flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca`.
