# Casca

*اقرأ هذا بلغة: [English](README.md) | **العربية** | [বাংলা](README.bn.md) | [Deutsch](README.de.md) | [Español](README.es.md) | [Français](README.fr.md) | [हिन्दी](README.hi.md) | [Bahasa Indonesia](README.id.md) | [Italiano](README.it.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Nederlands](README.nl.md) | [Polski](README.pl.md) | [Português (Brasil)](README.pt-BR.md) | [Русский](README.ru.md) | [ไทย](README.th.md) | [Türkçe](README.tr.md) | [Українська](README.uk.md) | [Tiếng Việt](README.vi.md) | [简体中文](README.zh-Hans.md)*

يحوّل أي موقع ويب إلى تطبيق GNOME أصلي: أيقونة في القائمة، نافذة خاصة به، بدون شريط متصفح متبقٍّ.

## التثبيت

### Flatpak (موصى به)

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

يحتاج إلى `flatpak-builder` وبيئة تشغيل `org.gnome.Platform`/`Sdk` (الإصدار المُعلن في
manifest). إذا لم يكن Flathub مُعدًّا لديك بعد:

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### مباشرة من مجلد المشروع (بدون Flatpak)

```bash
./install.sh
```

هذا يسجّل Casca في قائمة تطبيقات GNOME. إذا نقلت مجلد المشروع، شغّل
السكربت مرة أخرى.

## التشغيل بدون تثبيت

```bash
python3 run.py
```

## دليل المستخدم

الدليل الكامل (الذي يغطي كل خيار: الإعدادات المسبقة presets، الأيقونة، الاختصار، المتصفح المخصص، وضع الجوال،
الدقة) مدمج داخل التطبيق نفسه — افتح Casca واضغط على زر المساعدة (أيقونة "؟") في
الزاوية العلوية اليمنى من الشاشة الرئيسية.

## المتطلبات

- Python 3.11+
- GTK4 و libadwaita 1.5+ (`python3-gi`، `gir1.2-adw-1`)
- WebKitGTK 6.0 (`gir1.2-webkit-6.0`) — يُستخدم من قِبل النافذة الخاصة بكل تطبيق والدليل المدمج.
  بدونه، يستمر Casca في العمل بشكل طبيعي، حيث يفتح التطبيقات في متصفح خارجي (Chrome، Chromium،
  GNOME Web، Firefox…)، لكنه يفقد فقط خيار النافذة الخاصة الملوّنة.
- تبعيات Python (`PyGObject`، `requests`، `Pillow`) معلنة في `pyproject.toml`؛
  ثبّتها باستخدام `pip install -e .` إذا كنت تفضّل استخدام بيئة معزولة (مثل venv).

## بنية المشروع

- `casca/window.py` — واجهة المستخدم (GTK4 + libadwaita)
- `casca/browsers.py` — كشف المتصفحات المثبتة وبناء أمر التشغيل لكل تطبيق
- `casca/webview_app.py` — محرّك النافذة الخاصة (WebKitGTK)، يُشغَّل عبر `run_webview.py`
- `casca/entries.py` — إنشاء/تعديل/حذف التطبيقات (السجل وملفات `.desktop`)
- `casca/presets.py` — كتالوج المواقع الجاهزة
- `casca/icons.py` — جلب الأيقونات وتنزيلها ومعالجتها
- `casca/data/help_template.html` / `casca/help_content.py` — دليل المستخدم المدمج
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` — manifest الخاص بـ Flatpak

## أيقونات العلامات التجارية

معرض الأيقونات في `casca/data/social_icons/` يستخدم ملفات من
مشروع [Simple Icons](https://simpleicons.org) (رخصة CC0 — راجع `LICENSE.txt` في نفس
المجلد). العلامات التجارية التي طلبت إزالتها من Simple Icons لأسباب قانونية (Microsoft ومنتجاتها،
Amazon، LinkedIn، Yahoo) ليس لديها أيقونة مضمّنة — يقوم Casca بجلب أيقونة الموقع (favicon)
تلقائيًا أو يعرض صورة رمزية بالأحرف الأولى في تلك الحالات.

## العزل (Sandboxing) (Flatpak)

عند التشغيل كـ Flatpak، لا يطلب Casca عمدًا إذن `flatpak-spawn`
(`--talk-name=org.freedesktop.Flatpak`) — هذا الإذن يمنح صلاحية تشغيل أوامر عشوائية
على المضيف ويخضع لتدقيق صارم في مراجعة Flathub. عند العزل، لا يقدّم Casca سوى
"النافذة الخاصة" (WebKitGTK)؛ فهو لا يكتشف أو يقدّم متصفحات خارجية (يستمر ذلك في العمل
بشكل طبيعي في التثبيت المحلي عبر `install.sh`، خارج Flatpak). ملفات `.desktop` التي ينشئها Casca
لكل تطبيق ويب يتم تشغيلها بواسطة GNOME Shell (المضيف)، خارج العزل — عندما يكون
المحرّك المختار هو "النافذة الخاصة"، يعيد ملف `.desktop` هذا فتح Casca نفسه عبر
`flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca`.
