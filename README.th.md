# Casca

*อ่านเวอร์ชันภาษา: [English](README.md) | [العربية](README.ar.md) | [বাংলা](README.bn.md) | [Deutsch](README.de.md) | [Español](README.es.md) | [Français](README.fr.md) | [हिन्दी](README.hi.md) | [Bahasa Indonesia](README.id.md) | [Italiano](README.it.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Nederlands](README.nl.md) | [Polski](README.pl.md) | [Português (Brasil)](README.pt-BR.md) | [Русский](README.ru.md) | **ไทย** | [Türkçe](README.tr.md) | [Українська](README.uk.md) | [Tiếng Việt](README.vi.md) | [简体中文](README.zh-Hans.md)*

เปลี่ยนเว็บไซต์ใดก็ได้ให้เป็นแอป GNOME แบบเนทีฟ: มีไอคอนในเมนู มีหน้าต่างของตัวเอง ไม่มีแถบเบราว์เซอร์เหลือค้างอยู่

## การติดตั้ง

### Flatpak (แนะนำ)

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

ต้องมี `flatpak-builder` และรันไทม์ `org.gnome.Platform`/`Sdk` (เวอร์ชันที่ระบุไว้ใน
manifest) หากยังไม่ได้ตั้งค่า Flathub ไว้:

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### รันตรงจากโฟลเดอร์โปรเจกต์ (ไม่ใช้ Flatpak)

```bash
./install.sh
```

การทำเช่นนี้จะลงทะเบียน Casca ไว้ในเมนูแอปพลิเคชันของ GNOME หากคุณย้ายโฟลเดอร์โปรเจกต์ ให้รันสคริปต์
นี้อีกครั้ง

## การรันโดยไม่ต้องติดตั้ง

```bash
python3 run.py
```

## คู่มือผู้ใช้

คู่มือฉบับเต็ม (ครอบคลุมทุกตัวเลือก: พรีเซ็ต, ไอคอน, ทางลัด, เบราว์เซอร์ที่กำหนดเอง, โหมดมือถือ,
ความละเอียด) ถูกฝังไว้ในแอปเอง — เปิด Casca แล้วแตะปุ่มช่วยเหลือ (ไอคอน "?") ที่มุมขวาบนของ
หน้าจอหลัก

## ข้อกำหนดของระบบ

- Python 3.11+
- GTK4 และ libadwaita 1.5+ (`python3-gi`, `gir1.2-adw-1`)
- WebKitGTK 6.0 (`gir1.2-webkit-6.0`) — ใช้โดยหน้าต่างเฉพาะของแต่ละแอปและคู่มือในตัว
  หากไม่มี Casca ก็ยังทำงานได้ตามปกติ โดยจะเปิดแอปในเบราว์เซอร์ภายนอก (Chrome, Chromium,
  GNOME Web, Firefox…) เพียงแต่จะสูญเสียตัวเลือกหน้าต่างเฉพาะที่มีสีสัน
- ไลบรารีที่ Python ต้องพึ่งพา (`PyGObject`, `requests`, `Pillow`) ถูกประกาศไว้ใน `pyproject.toml`
  ติดตั้งด้วย `pip install -e .` หากต้องการใช้สภาพแวดล้อมแยกต่างหาก (เช่น venv)

## โครงสร้างโปรเจกต์

- `casca/window.py` — ส่วนติดต่อผู้ใช้ (GTK4 + libadwaita)
- `casca/browsers.py` — การตรวจจับเบราว์เซอร์ที่ติดตั้งไว้และการสร้างคำสั่งเปิดของแต่ละแอป
- `casca/webview_app.py` — เอนจินหน้าต่างเฉพาะ (WebKitGTK) ที่รันผ่าน `run_webview.py`
- `casca/entries.py` — การสร้าง/แก้ไข/ลบแอป (registry และไฟล์ `.desktop`)
- `casca/presets.py` — แคตตาล็อกไซต์สำเร็จรูป
- `casca/icons.py` — การดึง ดาวน์โหลด และประมวลผลไอคอน
- `casca/data/help_template.html` / `casca/help_content.py` — คู่มือผู้ใช้ในตัว
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` — manifest ของ Flatpak

## ไอคอนแบรนด์

แกลเลอรีไอคอนใน `casca/data/social_icons/` ใช้ไฟล์จากโปรเจกต์
[Simple Icons](https://simpleicons.org) (สัญญาอนุญาต CC0 — ดู `LICENSE.txt` ในโฟลเดอร์
เดียวกันนั้น) แบรนด์ที่ขอให้ลบออกจาก Simple Icons ด้วยเหตุผลทางกฎหมาย (Microsoft และผลิตภัณฑ์
ของบริษัท, Amazon, LinkedIn, Yahoo) จะไม่มีไอคอนแนบมาให้ — Casca จะดึง favicon ของไซต์
โดยอัตโนมัติ หรือแสดงอวาตาร์ตัวอักษรย่อในกรณีเหล่านั้น

## การแซนด์บ็อกซ์ (Flatpak)

เมื่อรันเป็น Flatpak Casca จงใจไม่ขอสิทธิ์ `flatpak-spawn`
(`--talk-name=org.freedesktop.Flatpak`) — สิทธิ์นั้นเปิดทางให้รันคำสั่งใดๆ ก็ได้บนโฮสต์
และถูกตรวจสอบอย่างเข้มงวดในกระบวนการรีวิวของ Flathub เมื่ออยู่ในแซนด์บ็อกซ์ Casca จะเสนอ
"หน้าต่างเฉพาะ" (WebKitGTK) ให้ใช้ได้เท่านั้น โดยจะไม่ตรวจจับหรือเสนอเบราว์เซอร์ภายนอก
(ซึ่งยังคงทำงานได้ตามปกติในกรณีที่ติดตั้งแบบโลคัลผ่าน `install.sh` นอกเหนือจาก Flatpak)
ไฟล์ `.desktop` ที่ Casca สร้างให้กับแต่ละเว็บแอปจะถูกรันโดย GNOME Shell (โฮสต์)
นอกแซนด์บ็อกซ์ — เมื่อเอนจินที่เลือกไว้คือ "หน้าต่างเฉพาะ" ไฟล์ `.desktop` นั้นจะเปิด Casca
เองใหม่อีกครั้งผ่านคำสั่ง
`flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca`
