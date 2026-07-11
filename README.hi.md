# Casca

*इसे इस भाषा में पढ़ें: [English](README.md) | [العربية](README.ar.md) | [বাংলা](README.bn.md) | [Deutsch](README.de.md) | [Español](README.es.md) | [Français](README.fr.md) | **हिन्दी** | [Bahasa Indonesia](README.id.md) | [Italiano](README.it.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Nederlands](README.nl.md) | [Polski](README.pl.md) | [Português (Brasil)](README.pt-BR.md) | [Русский](README.ru.md) | [ไทย](README.th.md) | [Türkçe](README.tr.md) | [Українська](README.uk.md) | [Tiếng Việt](README.vi.md) | [简体中文](README.zh-Hans.md)*

किसी भी वेबसाइट को नेटिव GNOME ऐप में बदल देता है: मेनू में आइकन, अपनी खुद की विंडो, बिना किसी बचे-खुचे ब्राउज़र बार के।

## इंस्टॉलेशन

### Flatpak (अनुशंसित)

```bash
flatpak-builder --user --install --force-clean build-dir io.github.oliverhubtech_source.Casca.yml
flatpak run io.github.oliverhubtech_source.Casca
```

इसके लिए `flatpak-builder` और `org.gnome.Platform`/`Sdk` रनटाइम (मैनिफेस्ट में घोषित संस्करण) चाहिए। यदि आपने अभी तक Flathub सेट अप नहीं किया है:

```bash
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

### सीधे प्रोजेक्ट फ़ोल्डर से (बिना Flatpak के)

```bash
./install.sh
```

यह Casca को GNOME एप्लिकेशन मेनू में रजिस्टर करता है। यदि आप प्रोजेक्ट फ़ोल्डर को स्थानांतरित करते हैं, तो स्क्रिप्ट को फिर से चलाएं।

## बिना इंस्टॉल किए चलाना

```bash
python3 run.py
```

## उपयोगकर्ता मैनुअल

पूरा मैनुअल (हर विकल्प को कवर करते हुए: प्रीसेट, आइकन, शॉर्टकट, कस्टम ब्राउज़र, मोबाइल मोड, रिज़ॉल्यूशन) ऐप में ही अंतर्निहित है — Casca खोलें और होम स्क्रीन के ऊपरी-दाएं कोने में सहायता बटन ("?" आइकन) पर टैप करें।

## आवश्यकताएं

- Python 3.11+
- GTK4 और libadwaita 1.5+ (`python3-gi`, `gir1.2-adw-1`)
- WebKitGTK 6.0 (`gir1.2-webkit-6.0`) — इसका उपयोग हर ऐप की अपनी विंडो और अंतर्निहित मैनुअल द्वारा किया जाता है।
  इसके बिना भी, Casca सामान्य रूप से काम करता है, ऐप्स को बाहरी ब्राउज़र (Chrome, Chromium,
  GNOME Web, Firefox…) में खोलते हुए, बस यह रंगीन खुद-की-विंडो विकल्प खो देता है।
- Python डिपेंडेंसीज़ (`PyGObject`, `requests`, `Pillow`) `pyproject.toml` में घोषित हैं;
  यदि आप एक आइसोलेटेड एनवायरनमेंट (जैसे एक venv) का उपयोग करना पसंद करते हैं तो `pip install -e .` से इंस्टॉल करें।

## प्रोजेक्ट संरचना

- `casca/window.py` — UI (GTK4 + libadwaita)
- `casca/browsers.py` — इंस्टॉल किए गए ब्राउज़रों का पता लगाना और हर ऐप का लॉन्च कमांड बनाना
- `casca/webview_app.py` — खुद-की-विंडो इंजन (WebKitGTK), `run_webview.py` के ज़रिए चलाया जाता है
- `casca/entries.py` — ऐप्स बनाना/संपादित करना/हटाना (रजिस्ट्री + `.desktop` फ़ाइलें)
- `casca/presets.py` — तैयार साइटों की सूची
- `casca/icons.py` — आइकनों को प्राप्त करना, डाउनलोड करना और प्रोसेस करना
- `casca/data/help_template.html` / `casca/help_content.py` — अंतर्निहित उपयोगकर्ता मैनुअल
- `io.github.oliverhubtech_source.Casca.yml` / `python3-requirements.yaml` — Flatpak मैनिफेस्ट

## ब्रांड आइकन

`casca/data/social_icons/` में आइकन गैलरी [Simple Icons](https://simpleicons.org) प्रोजेक्ट की फ़ाइलों का उपयोग करती है (CC0 लाइसेंस — उसी फ़ोल्डर में `LICENSE.txt` देखें)। जिन ब्रांड्स ने कानूनी कारणों से Simple Icons से हटाए जाने का अनुरोध किया (Microsoft और इसके उत्पाद, Amazon, LinkedIn, Yahoo) उनके पास बंडल किया गया आइकन नहीं है — इन मामलों में Casca स्वचालित रूप से साइट का फ़ेविकॉन प्राप्त करता है या एक इनिशियल्स अवतार दिखाता है।

## सैंडबॉक्सिंग (Flatpak)

Flatpak के रूप में चलते समय, Casca जानबूझकर `flatpak-spawn` अनुमति
(`--talk-name=org.freedesktop.Flatpak`) का अनुरोध नहीं करता — यह अनुमति होस्ट पर मनमाने कमांड चलाने की पहुंच देती है और Flathub समीक्षा में इसकी गहन जांच की जाती है। सैंडबॉक्स्ड होने पर, Casca केवल अपनी "खुद की विंडो" (WebKitGTK) प्रदान करता है; यह बाहरी ब्राउज़रों का पता नहीं लगाता या उन्हें प्रस्तुत नहीं करता (यह स्थानीय इंस्टॉल में `install.sh` के ज़रिए, Flatpak के बाहर, सामान्य रूप से काम करता रहता है)। हर वेब ऐप के लिए Casca द्वारा बनाई गई `.desktop` फ़ाइलें GNOME Shell (होस्ट) द्वारा, सैंडबॉक्स के बाहर चलाई जाती हैं — जब चुना गया इंजन "खुद की विंडो" होता है, तो वह `.desktop` फ़ाइल
`flatpak run --command=casca-webview io.github.oliverhubtech_source.Casca` के ज़रिए Casca को खुद फिर से खोलती है।
