# Casca

*এই ভাষায় পড়ুন: [English](README.md) | [العربية](README.ar.md) | **বাংলা** | [Deutsch](README.de.md) | [Español](README.es.md) | [Français](README.fr.md) | [हिन्दी](README.hi.md) | [Bahasa Indonesia](README.id.md) | [Italiano](README.it.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Nederlands](README.nl.md) | [Polski](README.pl.md) | [Português (Brasil)](README.pt-BR.md) | [Русский](README.ru.md) | [ไทย](README.th.md) | [Türkçe](README.tr.md) | [Українська](README.uk.md) | [Tiếng Việt](README.vi.md) | [简体中文](README.zh-Hans.md)*

যেকোনো ওয়েবসাইটকে একটি নেটিভ GNOME অ্যাপে রূপান্তরিত করে: মেনুতে আইকন, নিজস্ব উইন্ডো, ব্রাউজার বার-এর কোনো অবশিষ্টাংশ ছাড়াই।

## ইনস্টলেশন

### Flatpak (প্রস্তাবিত)

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

এর জন্য `flatpak-builder` এবং `org.gnome.Platform`/`Sdk` রানটাইম প্রয়োজন (সংস্করণ ম্যানিফেস্টে
উল্লেখ করা আছে)। যদি আপনার এখনও Flathub সেটআপ করা না থাকে:

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### সরাসরি প্রোজেক্ট ফোল্ডার থেকে (Flatpak ছাড়াই)

```bash
./install.sh
```

এটি Casca-কে GNOME অ্যাপ্লিকেশন মেনুতে নিবন্ধিত করে। যদি আপনি প্রোজেক্ট ফোল্ডারটি স্থানান্তর করেন,
তাহলে স্ক্রিপ্টটি আবার চালান।

## ইনস্টল না করে চালানো

```bash
python3 run.py
```

## ব্যবহারকারী ম্যানুয়াল

সম্পূর্ণ ম্যানুয়াল (প্রতিটি অপশন সম্পর্কে বিস্তারিত: প্রিসেট, আইকন, শর্টকাট, কাস্টম ব্রাউজার, মোবাইল
মোড, রেজোলিউশন) অ্যাপের মধ্যেই তৈরি করা আছে — Casca খুলুন এবং হোম স্ক্রিনের উপরের-ডান কোণায়
সাহায্য বাটনে ("?" আইকন) ট্যাপ করুন।

## প্রয়োজনীয়তা

- Python 3.11+
- GTK4 এবং libadwaita 1.5+ (`python3-gi`, `gir1.2-adw-1`)
- WebKitGTK 6.0 (`gir1.2-webkit-6.0`) — প্রতিটি অ্যাপের নিজস্ব উইন্ডো এবং বিল্ট-ইন ম্যানুয়াল দ্বারা
  ব্যবহৃত হয়। এটি ছাড়া, Casca তবুও স্বাভাবিকভাবে কাজ করে, অ্যাপগুলো একটি বাহ্যিক ব্রাউজারে
  (Chrome, Chromium, GNOME Web, Firefox…) খুলে, এটি শুধু রঙিন নিজস্ব-উইন্ডো অপশনটি হারায়।
- Python নির্ভরতাগুলো (`PyGObject`, `requests`, `Pillow`) `pyproject.toml`-এ ঘোষিত আছে;
  যদি আপনি একটি আইসোলেটেড এনভায়রনমেন্ট (যেমন একটি venv) ব্যবহার করতে চান তাহলে
  `pip install -e .` দিয়ে ইনস্টল করুন।

## প্রোজেক্ট কাঠামো

- `casca/window.py` — ইউআই (GTK4 + libadwaita)
- `casca/browsers.py` — ইনস্টল করা ব্রাউজারগুলো শনাক্তকরণ এবং প্রতিটি অ্যাপের লঞ্চ কমান্ড তৈরি করা
- `casca/webview_app.py` — নিজস্ব-উইন্ডো ইঞ্জিন (WebKitGTK), `run_webview.py` এর মাধ্যমে চালানো হয়
- `casca/entries.py` — অ্যাপ তৈরি/সম্পাদনা/অপসারণ (রেজিস্ট্রি + `.desktop` ফাইল)
- `casca/presets.py` — তৈরি করা সাইটগুলোর ক্যাটালগ
- `casca/icons.py` — আইকন সংগ্রহ, ডাউনলোড এবং প্রক্রিয়াকরণ
- `casca/data/help_template.html` / `casca/help_content.py` — বিল্ট-ইন ব্যবহারকারী ম্যানুয়াল
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` — Flatpak ম্যানিফেস্ট

## ব্র্যান্ড আইকন

`casca/data/social_icons/`-এর আইকন গ্যালারিতে [Simple Icons](https://simpleicons.org) প্রোজেক্টের
ফাইল ব্যবহার করা হয় (CC0 লাইসেন্স — একই ফোল্ডারে `LICENSE.txt` দেখুন)। যেসব ব্র্যান্ড আইনি কারণে
Simple Icons থেকে সরিয়ে ফেলার অনুরোধ করেছে (Microsoft এবং এর পণ্যসমূহ, Amazon, LinkedIn, Yahoo)
তাদের কোনো বান্ডিল করা আইকন নেই — সেসব ক্ষেত্রে Casca স্বয়ংক্রিয়ভাবে সাইটের ফেভিকন সংগ্রহ করে
অথবা একটি ইনিশিয়াল অ্যাভাটার দেখায়।

## স্যান্ডবক্সিং (Flatpak)

Flatpak হিসেবে চলার সময়, Casca ইচ্ছাকৃতভাবে `flatpak-spawn` অনুমতি
(`--talk-name=org.freedesktop.Flatpak`) অনুরোধ করে না — এই অনুমতি হোস্টে যেকোনো কমান্ড চালানোর
অ্যাক্সেস প্রদান করে এবং Flathub পর্যালোচনায় এটি ব্যাপকভাবে যাচাই করা হয়। স্যান্ডবক্সড অবস্থায়,
Casca শুধুমাত্র তার "নিজস্ব উইন্ডো" (WebKitGTK) অফার করে; এটি বাহ্যিক ব্রাউজার শনাক্ত বা অফার করে
না (এটি `install.sh` এর মাধ্যমে স্থানীয় ইনস্টলে, Flatpak-এর বাইরে, স্বাভাবিকভাবে কাজ করতে থাকে)।
Casca প্রতিটি ওয়েব অ্যাপের জন্য যে `.desktop` ফাইল তৈরি করে তা GNOME Shell (হোস্ট) দ্বারা,
স্যান্ডবক্সের বাইরে চালানো হয় — যখন নির্বাচিত ইঞ্জিন "নিজস্ব উইন্ডো" হয়, সেই `.desktop` ফাইলটি
`flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca` এর মাধ্যমে Casca-কে
পুনরায় খোলে।
