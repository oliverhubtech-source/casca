# Casca

*Bunu şu dilde oku: [English](README.md) | [العربية](README.ar.md) | [বাংলা](README.bn.md) | [Deutsch](README.de.md) | [Español](README.es.md) | [Français](README.fr.md) | [हिन्दी](README.hi.md) | [Bahasa Indonesia](README.id.md) | [Italiano](README.it.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Nederlands](README.nl.md) | [Polski](README.pl.md) | [Português (Brasil)](README.pt-BR.md) | [Русский](README.ru.md) | [ไทย](README.th.md) | **Türkçe** | [Українська](README.uk.md) | [Tiếng Việt](README.vi.md) | [简体中文](README.zh-Hans.md)*

Herhangi bir web sitesini yerel bir GNOME uygulamasına dönüştürür: menüde simge, kendi penceresi, arkada tarayıcı çubuğu bırakmaz.

## Kurulum

### Flatpak (önerilen)

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

`flatpak-builder` ve `org.gnome.Platform`/`Sdk` çalışma zamanı (manifestoda belirtilen sürüm) gereklidir. Henüz Flathub kurulu değilse:

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### Doğrudan proje klasöründen (Flatpak olmadan)

```bash
./install.sh
```

Bu, Casca'yı GNOME uygulamalar menüsüne kaydeder. Proje klasörünü taşırsanız, betiği tekrar çalıştırın.

## Kurulum yapmadan çalıştırma

```bash
python3 run.py
```

## Kullanıcı kılavuzu

Tam kılavuz (her seçeneği kapsar: hazır ayarlar, simge, kısayol, özel tarayıcı, mobil mod, çözünürlük) uygulamanın kendi içine gömülüdür — Casca'yı açın ve ana ekranın sağ üst köşesindeki yardım düğmesine ("?" simgesi) dokunun.

## Gereksinimler

- Python 3.11+
- GTK4 ve libadwaita 1.5+ (`python3-gi`, `gir1.2-adw-1`)
- WebKitGTK 6.0 (`gir1.2-webkit-6.0`) — her uygulamanın kendi penceresi ve gömülü kılavuz tarafından kullanılır. Bu olmadan da Casca normal şekilde çalışmaya devam eder, uygulamaları harici bir tarayıcıda açar (Chrome, Chromium, GNOME Web, Firefox…), sadece renkli kendi-pencere seçeneğini kaybeder.
- Python bağımlılıkları (`PyGObject`, `requests`, `Pillow`) `pyproject.toml` içinde belirtilmiştir; izole bir ortam kullanmayı tercih ederseniz (örn. bir venv) `pip install -e .` ile kurun.

## Proje yapısı

- `casca/window.py` — kullanıcı arayüzü (GTK4 + libadwaita)
- `casca/browsers.py` — kurulu tarayıcıların tespiti ve her uygulamanın başlatma komutunun oluşturulması
- `casca/webview_app.py` — kendi-pencere motoru (WebKitGTK), `run_webview.py` üzerinden çalıştırılır
- `casca/entries.py` — uygulamaları oluşturma/düzenleme/kaldırma (kayıt defteri + `.desktop` dosyaları)
- `casca/presets.py` — hazır sitelerin kataloğu
- `casca/icons.py` — simgelerin alınması, indirilmesi ve işlenmesi
- `casca/data/help_template.html` / `casca/help_content.py` — gömülü kullanıcı kılavuzu
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` — Flatpak manifestosu

## Marka simgeleri

`casca/data/social_icons/` içindeki simge galerisi, [Simple Icons](https://simpleicons.org) projesinden dosyaları kullanır (CC0 lisansı — aynı klasördeki `LICENSE.txt` dosyasına bakın). Yasal nedenlerle Simple Icons'tan çıkarılmasını isteyen markaların (Microsoft ve ürünleri, Amazon, LinkedIn, Yahoo) paket içinde simgesi yoktur — Casca bu durumlarda sitenin favicon'unu otomatik olarak alır veya bir baş harf avatarı gösterir.

## Kum havuzu (Flatpak)

Casca, bir Flatpak olarak çalışırken kasıtlı olarak `flatpak-spawn` iznini (`--talk-name=org.freedesktop.Flatpak`) istemez — bu izin, ana makinede rastgele komutlar çalıştırma erişimi sağlar ve Flathub incelemesinde ciddi şekilde denetlenir. Kum havuzuna alınmış haldeyken Casca yalnızca "kendi penceresini" (WebKitGTK) sunar; harici tarayıcıları tespit etmez veya sunmaz (bu, Flatpak dışında `install.sh` ile yapılan yerel kurulumda normal şekilde çalışmaya devam eder). Casca'nın her web uygulaması için oluşturduğu `.desktop` dosyaları, kum havuzunun dışında GNOME Shell (ana makine) tarafından çalıştırılır — seçilen motor "kendi pencere" olduğunda, bu `.desktop` dosyası `flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca` aracılığıyla Casca'nın kendisini yeniden açar.
