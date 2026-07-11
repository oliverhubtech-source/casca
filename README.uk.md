# Casca

*Читати це мовою: [English](README.md) | [العربية](README.ar.md) | [বাংলা](README.bn.md) | [Deutsch](README.de.md) | [Español](README.es.md) | [Français](README.fr.md) | [हिन्दी](README.hi.md) | [Bahasa Indonesia](README.id.md) | [Italiano](README.it.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Nederlands](README.nl.md) | [Polski](README.pl.md) | [Português (Brasil)](README.pt-BR.md) | [Русский](README.ru.md) | [ไทย](README.th.md) | [Türkçe](README.tr.md) | **Українська** | [Tiếng Việt](README.vi.md) | [简体中文](README.zh-Hans.md)*

Перетворює будь-який вебсайт на нативний застосунок GNOME: піктограма в меню, власне вікно, без зайвої панелі браузера.

## Встановлення

### Flatpak (рекомендовано)

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

Потрібні `flatpak-builder` та середовище виконання `org.gnome.Platform`/`Sdk` (версія вказана в
маніфесті). Якщо у вас ще не налаштований Flathub:

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### Прямо з папки проєкту (без Flatpak)

```bash
./install.sh
```

Це реєструє Casca в меню застосунків GNOME. Якщо ви перемістите папку проєкту, запустіть
скрипт знову.

## Запуск без встановлення

```bash
python3 run.py
```

## Посібник користувача

Повний посібник (охоплює кожну опцію: пресети, іконку, ярлик, власний браузер, мобільний режим,
роздільну здатність) вбудований прямо в застосунок — відкрийте Casca й натисніть кнопку допомоги
(іконка "?") у верхньому правому куті головного екрана.

## Вимоги

- Python 3.11+
- GTK4 та libadwaita 1.5+ (`python3-gi`, `gir1.2-adw-1`)
- WebKitGTK 6.0 (`gir1.2-webkit-6.0`) — використовується власним вікном кожного застосунку та
  вбудованим посібником. Без нього Casca все одно працює нормально, відкриваючи застосунки у
  зовнішньому браузері (Chrome, Chromium, GNOME Web, Firefox…), просто втрачає опцію кольорового
  власного вікна.
- Залежності Python (`PyGObject`, `requests`, `Pillow`) вказані в `pyproject.toml`;
  встановлюйте командою `pip install -e .`, якщо волієте використовувати ізольоване середовище
  (наприклад, venv).

## Структура проєкту

- `casca/window.py` — інтерфейс користувача (GTK4 + libadwaita)
- `casca/browsers.py` — виявлення встановлених браузерів і побудова команди запуску для кожного застосунку
- `casca/webview_app.py` — рушій власного вікна (WebKitGTK), що запускається через `run_webview.py`
- `casca/entries.py` — створення/редагування/видалення застосунків (реєстр і файли `.desktop`)
- `casca/presets.py` — каталог готових сайтів
- `casca/icons.py` — отримання, завантаження та обробка іконок
- `casca/data/help_template.html` / `casca/help_content.py` — вбудований посібник користувача
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` — маніфест Flatpak

## Іконки брендів

Галерея іконок у `casca/data/social_icons/` використовує файли з проєкту
[Simple Icons](https://simpleicons.org) (ліцензія CC0 — див. `LICENSE.txt` у тій самій
папці). Бренди, які попросили видалити їх із Simple Icons з юридичних причин (Microsoft та його
продукти, Amazon, LinkedIn, Yahoo), не мають вбудованої іконки — у таких випадках Casca
автоматично отримує фавікон сайту або показує аватар з ініціалами.

## Пісочниця (Flatpak)

Працюючи як Flatpak, Casca свідомо не запитує дозвіл `flatpak-spawn`
(`--talk-name=org.freedesktop.Flatpak`) — цей дозвіл надає доступ до виконання довільних
команд на хості й ретельно перевіряється під час рецензування Flathub. У пісочниці Casca
пропонує лише "власне вікно" (WebKitGTK); вона не виявляє й не пропонує зовнішні браузери (це
продовжує нормально працювати в локальному встановленні через `install.sh`, поза Flatpak).
Файли `.desktop`, які Casca створює для кожного веб-застосунку, запускаються GNOME Shell
(хостом), поза пісочницею — коли обраний рушій це "власне вікно", цей `.desktop` знову
відкриває саму Casca через
`flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca`.
