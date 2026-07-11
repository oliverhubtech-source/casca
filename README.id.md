# Casca

*Baca ini dalam: [English](README.md) | [العربية](README.ar.md) | [বাংলা](README.bn.md) | [Deutsch](README.de.md) | [Español](README.es.md) | [Français](README.fr.md) | [हिन्दी](README.hi.md) | **Bahasa Indonesia** | [Italiano](README.it.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Nederlands](README.nl.md) | [Polski](README.pl.md) | [Português (Brasil)](README.pt-BR.md) | [Русский](README.ru.md) | [ไทย](README.th.md) | [Türkçe](README.tr.md) | [Українська](README.uk.md) | [Tiếng Việt](README.vi.md) | [简体中文](README.zh-Hans.md)*

Mengubah situs web apa pun menjadi aplikasi GNOME native: ikon di menu, jendela sendiri, tanpa sisa bilah browser.

## Instalasi

### Flatpak (direkomendasikan)

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

Membutuhkan `flatpak-builder` dan runtime `org.gnome.Platform`/`Sdk` (versi yang dideklarasikan di
manifest). Jika Anda belum mengatur Flathub:

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### Langsung dari folder proyek (tanpa Flatpak)

```bash
./install.sh
```

Ini mendaftarkan Casca di menu aplikasi GNOME. Jika Anda memindahkan folder proyek, jalankan
skrip ini lagi.

## Menjalankan tanpa instalasi

```bash
python3 run.py
```

## Manual pengguna

Manual lengkap (mencakup semua opsi: preset, ikon, pintasan, browser kustom, mode mobile,
resolusi) sudah terpasang di dalam aplikasi itu sendiri — buka Casca dan ketuk tombol bantuan (ikon "?") di
pojok kanan atas layar utama.

## Persyaratan

- Python 3.11+
- GTK4 dan libadwaita 1.5+ (`python3-gi`, `gir1.2-adw-1`)
- WebKitGTK 6.0 (`gir1.2-webkit-6.0`) — digunakan oleh jendela sendiri milik setiap aplikasi dan manual bawaan.
  Tanpa ini, Casca tetap berfungsi normal, membuka aplikasi di browser eksternal (Chrome, Chromium,
  GNOME Web, Firefox…), hanya saja kehilangan opsi jendela sendiri berwarna.
- Dependensi Python (`PyGObject`, `requests`, `Pillow`) dideklarasikan di `pyproject.toml`;
  instal dengan `pip install -e .` jika Anda lebih suka menggunakan lingkungan terisolasi (misalnya, venv).

## Struktur proyek

- `casca/window.py` — antarmuka pengguna (GTK4 + libadwaita)
- `casca/browsers.py` — deteksi browser yang terpasang dan pembuatan perintah peluncuran setiap aplikasi
- `casca/webview_app.py` — mesin jendela sendiri (WebKitGTK), dijalankan melalui `run_webview.py`
- `casca/entries.py` — membuat/mengedit/menghapus aplikasi (registry + berkas `.desktop`)
- `casca/presets.py` — katalog situs yang sudah jadi
- `casca/icons.py` — mengambil, mengunduh, dan memproses ikon
- `casca/data/help_template.html` / `casca/help_content.py` — manual pengguna bawaan
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` — manifest Flatpak

## Ikon merek

Galeri ikon di `casca/data/social_icons/` menggunakan berkas dari proyek
[Simple Icons](https://simpleicons.org) (lisensi CC0 — lihat `LICENSE.txt` di folder yang
sama). Merek yang meminta untuk dihapus dari Simple Icons karena alasan hukum (Microsoft dan produknya, Amazon, LinkedIn, Yahoo) tidak memiliki ikon bawaan — Casca akan mengambil favicon situs
secara otomatis atau menampilkan avatar inisial dalam kasus-kasus tersebut.

## Sandboxing (Flatpak)

Saat berjalan sebagai Flatpak, Casca dengan sengaja tidak meminta izin `flatpak-spawn`
(`--talk-name=org.freedesktop.Flatpak`) — izin tersebut memberikan akses untuk menjalankan perintah sembarangan
di host dan sangat diteliti dalam peninjauan Flathub. Dalam sandbox, Casca hanya menawarkan
"jendela sendiri"-nya (WebKitGTK); Casca tidak mendeteksi atau menawarkan browser eksternal (hal itu tetap berfungsi
normal pada instalasi lokal melalui `install.sh`, di luar Flatpak). Berkas `.desktop` yang dibuat Casca
untuk setiap aplikasi web dijalankan oleh GNOME Shell (host), di luar sandbox — ketika
mesin yang dipilih adalah "jendela sendiri", berkas `.desktop` tersebut membuka kembali Casca itu sendiri melalui
`flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca`.
