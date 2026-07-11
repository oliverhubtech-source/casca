# Casca

*言語を選択: [English](README.md) | [العربية](README.ar.md) | [বাংলা](README.bn.md) | [Deutsch](README.de.md) | [Español](README.es.md) | [Français](README.fr.md) | [हिन्दी](README.hi.md) | [Bahasa Indonesia](README.id.md) | [Italiano](README.it.md) | **日本語** | [한국어](README.ko.md) | [Nederlands](README.nl.md) | [Polski](README.pl.md) | [Português (Brasil)](README.pt-BR.md) | [Русский](README.ru.md) | [ไทย](README.th.md) | [Türkçe](README.tr.md) | [Українська](README.uk.md) | [Tiếng Việt](README.vi.md) | [简体中文](README.zh-Hans.md)*

どんなウェブサイトもネイティブのGNOMEアプリに変えます:メニューにアイコン、専用のウィンドウ、余計なブラウザバーもありません。

## インストール

### Flatpak（推奨）

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

`flatpak-builder`と`org.gnome.Platform`/`Sdk`ランタイム（マニフェストに記載されているバージョン）が必要です。まだFlathubを設定していない場合は次を実行してください。

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### プロジェクトフォルダから直接（Flatpakなし）

```bash
./install.sh
```

これによりCascaがGNOMEのアプリケーションメニューに登録されます。プロジェクトフォルダを移動した場合は、このスクリプトをもう一度実行してください。

## インストールせずに実行する

```bash
python3 run.py
```

## ユーザーマニュアル

すべてのオプション（プリセット、アイコン、ショートカット、カスタムブラウザ、モバイルモード、解像度）を網羅した完全なマニュアルはアプリ自体に組み込まれています。Cascaを開き、ホーム画面右上のヘルプボタン(「？」アイコン)をタップしてください。

## 必要要件

- Python 3.11以上
- GTK4およびlibadwaita 1.5以上(`python3-gi`、`gir1.2-adw-1`)
- WebKitGTK 6.0(`gir1.2-webkit-6.0`)— 各アプリ専用ウィンドウと組み込みマニュアルで使用されます。これがなくてもCascaは通常どおり動作し、アプリを外部ブラウザ(Chrome、Chromium、GNOME Web、Firefoxなど)で開きますが、専用ウィンドウのカラーオプションは利用できなくなります。
- Pythonの依存関係(`PyGObject`、`requests`、`Pillow`)は`pyproject.toml`に記載されています。分離された環境(venvなど)を使いたい場合は`pip install -e .`でインストールしてください。

## プロジェクト構成

- `casca/window.py` — UI(GTK4 + libadwaita)
- `casca/browsers.py` — インストール済みブラウザの検出と各アプリの起動コマンドの構築
- `casca/webview_app.py` — 専用ウィンドウエンジン(WebKitGTK)、`run_webview.py`経由で実行
- `casca/entries.py` — アプリの作成・編集・削除(レジストリと`.desktop`ファイル)
- `casca/presets.py` — 既製サイトのカタログ
- `casca/icons.py` — アイコンの取得、ダウンロード、加工
- `casca/data/help_template.html` / `casca/help_content.py` — 組み込みユーザーマニュアル
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` — Flatpakマニフェスト

## ブランドアイコン

`casca/data/social_icons/`にあるアイコンギャラリーは、[Simple Icons](https://simpleicons.org)プロジェクト(CC0ライセンス — 同フォルダ内の`LICENSE.txt`を参照)のファイルを使用しています。法的理由によりSimple Iconsからの削除を要請したブランド(Microsoftおよびその製品、Amazon、LinkedIn、Yahoo)にはバンドルされたアイコンがありません — この場合Cascaはサイトのファビコンを自動取得するか、イニシャルアバターを表示します。

## サンドボックス化(Flatpak)

Flatpakとして実行する場合、Cascaは意図的に`flatpak-spawn`権限(`--talk-name=org.freedesktop.Flatpak`)を要求しません — この権限はホスト上で任意のコマンドを実行するアクセスを許可するものであり、Flathubのレビューで厳しく審査されるためです。サンドボックス化された状態では、Cascaは「専用ウィンドウ」(WebKitGTK)のみを提供し、外部ブラウザの検出や提供は行いません(これはFlatpakの外部で、`install.sh`によるローカルインストールでは引き続き通常どおり機能します)。Cascaが各ウェブアプリ用に作成する`.desktop`ファイルは、サンドボックスの外側にあるGNOME Shell(ホスト)によって実行されます — 選択されたエンジンが「専用ウィンドウ」の場合、その`.desktop`は`flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca`経由でCasca自体を再度開きます。
