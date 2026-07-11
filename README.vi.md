# Casca

*Đọc bằng: [English](README.md) | [العربية](README.ar.md) | [বাংলা](README.bn.md) | [Deutsch](README.de.md) | [Español](README.es.md) | [Français](README.fr.md) | [हिन्दी](README.hi.md) | [Bahasa Indonesia](README.id.md) | [Italiano](README.it.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Nederlands](README.nl.md) | [Polski](README.pl.md) | [Português (Brasil)](README.pt-BR.md) | [Русский](README.ru.md) | [ไทย](README.th.md) | [Türkçe](README.tr.md) | [Українська](README.uk.md) | **Tiếng Việt** | [简体中文](README.zh-Hans.md)*

Biến bất kỳ trang web nào thành một ứng dụng GNOME gốc: biểu tượng trong menu, cửa sổ riêng, không còn thanh trình duyệt thừa.

## Cài đặt

### Flatpak (khuyến nghị)

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

Cần có `flatpak-builder` và runtime `org.gnome.Platform`/`Sdk` (phiên bản được khai báo trong
manifest). Nếu bạn chưa thiết lập Flathub:

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### Trực tiếp từ thư mục dự án (không cần Flatpak)

```bash
./install.sh
```

Thao tác này đăng ký Casca vào menu ứng dụng của GNOME. Nếu bạn di chuyển thư mục dự án, hãy chạy
lại script này.

## Chạy mà không cần cài đặt

```bash
python3 run.py
```

## Hướng dẫn sử dụng

Hướng dẫn đầy đủ (bao gồm mọi tùy chọn: mẫu có sẵn, biểu tượng, phím tắt, trình duyệt tùy chỉnh, chế độ
di động, độ phân giải) đã được tích hợp sẵn trong ứng dụng — mở Casca và nhấn nút trợ giúp (biểu tượng "?")
ở góc trên bên phải màn hình chính.

## Yêu cầu

- Python 3.11+
- GTK4 và libadwaita 1.5+ (`python3-gi`, `gir1.2-adw-1`)
- WebKitGTK 6.0 (`gir1.2-webkit-6.0`) — được sử dụng bởi cửa sổ riêng của mỗi ứng dụng và hướng dẫn
  sử dụng tích hợp sẵn. Nếu không có, Casca vẫn hoạt động bình thường, mở các ứng dụng trong trình duyệt
  bên ngoài (Chrome, Chromium, GNOME Web, Firefox…), chỉ mất đi tùy chọn cửa sổ riêng có màu.
- Các phụ thuộc Python (`PyGObject`, `requests`, `Pillow`) được khai báo trong `pyproject.toml`;
  cài đặt bằng `pip install -e .` nếu bạn muốn sử dụng một môi trường cách ly (ví dụ: venv).

## Cấu trúc dự án

- `casca/window.py` — giao diện người dùng (GTK4 + libadwaita)
- `casca/browsers.py` — phát hiện các trình duyệt đã cài đặt và xây dựng lệnh khởi chạy của mỗi ứng dụng
- `casca/webview_app.py` — bộ máy cửa sổ riêng (WebKitGTK), chạy thông qua `run_webview.py`
- `casca/entries.py` — tạo/chỉnh sửa/xóa ứng dụng (registry và các tệp `.desktop`)
- `casca/presets.py` — danh mục các trang web dựng sẵn
- `casca/icons.py` — lấy, tải xuống và xử lý biểu tượng
- `casca/data/help_template.html` / `casca/help_content.py` — hướng dẫn sử dụng tích hợp sẵn
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` — manifest của Flatpak

## Biểu tượng thương hiệu

Bộ sưu tập biểu tượng trong `casca/data/social_icons/` sử dụng các tệp từ dự án
[Simple Icons](https://simpleicons.org) (giấy phép CC0 — xem `LICENSE.txt` trong cùng thư mục đó).
Các thương hiệu đã yêu cầu gỡ bỏ khỏi Simple Icons vì lý do pháp lý (Microsoft và các sản phẩm của
hãng, Amazon, LinkedIn, Yahoo) không có biểu tượng đi kèm — trong những trường hợp đó, Casca sẽ tự
động lấy favicon của trang web hoặc hiển thị một avatar chữ cái đầu.

## Sandbox (Flatpak)

Khi chạy dưới dạng Flatpak, Casca cố tình không yêu cầu quyền `flatpak-spawn`
(`--talk-name=org.freedesktop.Flatpak`) — quyền này cho phép truy cập để chạy các lệnh tùy ý trên
máy chủ và bị xem xét rất kỹ trong quá trình duyệt của Flathub. Khi chạy trong sandbox, Casca chỉ
cung cấp "cửa sổ riêng" của nó (WebKitGTK); nó không phát hiện hoặc cung cấp các trình duyệt bên ngoài
(điều đó vẫn hoạt động bình thường trong bản cài đặt cục bộ thông qua `install.sh`, bên ngoài Flatpak).
Các tệp `.desktop` mà Casca tạo ra cho mỗi ứng dụng web được chạy bởi GNOME Shell (máy chủ), bên ngoài
sandbox — khi engine được chọn là "cửa sổ riêng", tệp `.desktop` đó sẽ mở lại chính Casca thông qua
`flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca`.
