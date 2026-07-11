# Casca

*选择语言: [English](README.md) | [العربية](README.ar.md) | [বাংলা](README.bn.md) | [Deutsch](README.de.md) | [Español](README.es.md) | [Français](README.fr.md) | [हिन्दी](README.hi.md) | [Bahasa Indonesia](README.id.md) | [Italiano](README.it.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Nederlands](README.nl.md) | [Polski](README.pl.md) | [Português (Brasil)](README.pt-BR.md) | [Русский](README.ru.md) | [ไทย](README.th.md) | [Türkçe](README.tr.md) | [Українська](README.uk.md) | [Tiếng Việt](README.vi.md) | **简体中文***

将任何网站变成原生 GNOME 应用：菜单中有图标，拥有独立窗口，不留浏览器地址栏的痕迹。

## 安装

### Flatpak（推荐）

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

需要 `flatpak-builder` 以及 `org.gnome.Platform`/`Sdk` 运行时（版本见清单文件中的声明）。如果你还没有配置 Flathub：

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### 直接从项目文件夹运行（不使用 Flatpak）

```bash
./install.sh
```

这会将 Casca 注册到 GNOME 应用程序菜单中。如果你移动了项目文件夹，请再次运行该脚本。

## 无需安装直接运行

```bash
python3 run.py
```

## 用户手册

完整手册（涵盖所有选项：预设、图标、快捷方式、自定义浏览器、移动模式、分辨率）内置于应用本身——打开 Casca，点击主页右上角的帮助按钮（"?"图标）。

## 系统要求

- Python 3.11+
- GTK4 与 libadwaita 1.5+（`python3-gi`、`gir1.2-adw-1`）
- WebKitGTK 6.0（`gir1.2-webkit-6.0`）——用于每个应用自己的窗口以及内置手册。没有它，Casca 仍能正常工作，会改用外部浏览器（Chrome、Chromium、GNOME Web、Firefox……）打开应用，只是会失去带颜色的独立窗口选项。
- Python 依赖项（`PyGObject`、`requests`、`Pillow`）已在 `pyproject.toml` 中声明；如果你更想使用一个隔离环境（例如 venv），可以用 `pip install -e .` 安装。

## 项目结构

- `casca/window.py` —— 用户界面（GTK4 + libadwaita）
- `casca/browsers.py` —— 检测已安装的浏览器，并为每个应用构建启动命令
- `casca/webview_app.py` —— 独立窗口引擎（WebKitGTK），通过 `run_webview.py` 运行
- `casca/entries.py` —— 应用的创建/编辑/删除（注册表 + `.desktop` 文件）
- `casca/presets.py` —— 现成网站的目录
- `casca/icons.py` —— 图标的获取、下载与处理
- `casca/data/help_template.html` / `casca/help_content.py` —— 内置用户手册
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` —— Flatpak 清单文件

## 品牌图标

`casca/data/social_icons/` 中的图标库使用了来自 [Simple Icons](https://simpleicons.org) 项目的文件（CC0 许可证——详见该文件夹中的 `LICENSE.txt`）。出于法律原因要求从 Simple Icons 中移除的品牌（Microsoft 及其产品、Amazon、LinkedIn、Yahoo）没有内置图标——在这些情况下，Casca 会自动获取网站的 favicon，或显示一个首字母头像。

## 沙盒隔离（Flatpak）

作为 Flatpak 运行时，Casca 有意不请求 `flatpak-spawn` 权限（`--talk-name=org.freedesktop.Flatpak`）——该权限会授予在宿主机上运行任意命令的能力，在 Flathub 审核中会受到严格审查。在沙盒环境中，Casca 只提供"独立窗口"（WebKitGTK）选项；它不会检测或提供外部浏览器（这项功能在通过 `install.sh` 进行的本地安装中——即在 Flatpak 之外——仍能正常使用）。Casca 为每个 Web 应用创建的 `.desktop` 文件由 GNOME Shell（宿主机）在沙盒之外运行——当选择的引擎是"独立窗口"时，该 `.desktop` 文件会通过 `flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca` 重新打开 Casca 本身。
