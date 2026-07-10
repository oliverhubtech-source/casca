"""Catalog of popular sites with no native Linux app, grouped by category."""

from dataclasses import dataclass

from .i18n import _


@dataclass(frozen=True)
class Preset:
    name: str
    url: str
    icon_key: str | None = None  # filename in casca/data/social_icons, without extension


@dataclass(frozen=True)
class PresetCategory:
    title: str
    presets: tuple[Preset, ...]


PRESET_CATEGORIES: tuple[PresetCategory, ...] = (
    PresetCategory(
        _("Google Products"),
        (
            Preset("Gmail", "https://mail.google.com/", icon_key="mail"),
            Preset("Google Agenda", "https://calendar.google.com/", icon_key="google-agenda"),
            Preset("Google Drive", "https://drive.google.com/", icon_key="drive"),
            Preset("Google Docs", "https://docs.google.com/document/u/0/", icon_key="google-docs"),
            Preset("Google Planilhas", "https://docs.google.com/spreadsheets/u/0/", icon_key="google-planilhas"),
            Preset("Google Apresentações", "https://docs.google.com/presentation/u/0/", icon_key="google-apresentacoes"),
            Preset("Google Meet", "https://meet.google.com/", icon_key="google-meet"),
            Preset("Google Fotos", "https://photos.google.com/", icon_key="google-fotos"),
            Preset("Google Keep", "https://keep.google.com/", icon_key="google-keep"),
            Preset("YouTube", "https://youtube.com/", icon_key="youtube2"),
            Preset("YouTube Music", "https://music.youtube.com/", icon_key="youtube2"),
        ),
    ),
    PresetCategory(
        _("Microsoft Products"),
        (
            Preset("Outlook", "https://outlook.office.com/mail/", icon_key="outlook"),
            Preset("Microsoft Teams", "https://teams.microsoft.com/", icon_key="microsoft-teams"),
            Preset("OneDrive", "https://onedrive.live.com/", icon_key="microsoft-office"),
            Preset("Word Online", "https://www.office.com/launch/word", icon_key="microsoft-office"),
            Preset("Excel Online", "https://www.office.com/launch/excel", icon_key="microsoft-office"),
            Preset("PowerPoint Online", "https://www.office.com/launch/powerpoint", icon_key="microsoft-office"),
            Preset("Microsoft To Do", "https://to-do.office.com/", icon_key="microsoft-to-do"),
        ),
    ),
    PresetCategory(
        _("Artificial Intelligence"),
        (
            Preset("ChatGPT", "https://chat.openai.com/", icon_key="chatgpt"),
            Preset("Claude", "https://claude.ai/", icon_key="claude"),
            Preset("Google Gemini", "https://gemini.google.com/", icon_key="gemini"),
            Preset("Microsoft Copilot", "https://copilot.microsoft.com/", icon_key="copilot"),
            Preset("Perplexity", "https://www.perplexity.ai/", icon_key="perplexity"),
            Preset("Grok", "https://grok.com/", icon_key="grok"),
            Preset("DeepSeek", "https://chat.deepseek.com/", icon_key="deepseek"),
            Preset("Meta AI", "https://www.meta.ai/", icon_key="meta-ai"),
            Preset("Poe", "https://poe.com/", icon_key="poe"),
            Preset("Mistral (Le Chat)", "https://chat.mistral.ai/", icon_key="mistral"),
        ),
    ),
    PresetCategory(
        _("Search Engines"),
        (
            Preset("Google", "https://www.google.com/", icon_key="google"),
            Preset("Bing", "https://www.bing.com/", icon_key="bing"),
            Preset("DuckDuckGo", "https://duckduckgo.com/", icon_key="duckduckgo"),
            Preset("Yahoo", "https://search.yahoo.com/", icon_key="yahoo"),
            Preset("Ecosia", "https://www.ecosia.org/", icon_key="ecosia"),
            Preset("Brave Search", "https://search.brave.com/", icon_key="brave-search"),
            Preset("Startpage", "https://www.startpage.com/", icon_key="startpage"),
        ),
    ),
    PresetCategory(
        _("Messengers"),
        (
            Preset("WhatsApp Web", "https://web.whatsapp.com/", icon_key="whatsapp"),
            Preset("Telegram Web", "https://web.telegram.org/", icon_key="telegram-web"),
            Preset("Discord", "https://discord.com/app", icon_key="discord"),
            Preset("Messenger", "https://www.messenger.com/", icon_key="messenger"),
            Preset("Slack", "https://slack.com/", icon_key="slack"),
        ),
    ),
    PresetCategory(
        _("Social Networks"),
        (
            Preset("Instagram", "https://www.instagram.com/", icon_key="instagram"),
            Preset("Facebook", "https://www.facebook.com/", icon_key="facebook"),
            Preset("X (Twitter)", "https://x.com/", icon_key="twitter"),
            Preset("LinkedIn", "https://www.linkedin.com/", icon_key="linkedin"),
            Preset("Reddit", "https://www.reddit.com/", icon_key="reddit"),
            Preset("TikTok", "https://www.tiktok.com/", icon_key="tiktok"),
        ),
    ),
    PresetCategory(
        _("Streaming"),
        (
            Preset("Netflix", "https://www.netflix.com/", icon_key="netflix"),
            Preset("Disney+", "https://www.disneyplus.com/", icon_key="disney-plus"),
            Preset("Prime Video", "https://www.primevideo.com/", icon_key="prime-video"),
            Preset("Max", "https://www.max.com/", icon_key="max"),
            Preset("Globoplay", "https://globoplay.globo.com/", icon_key="globoplay"),
            Preset("Twitch", "https://www.twitch.tv/", icon_key="twitch"),
            Preset("Paramount+", "https://www.paramountplus.com/", icon_key="paramount-plus"),
        ),
    ),
    PresetCategory(
        _("Music"),
        (
            Preset("Spotify", "https://open.spotify.com/", icon_key="spotify"),
            Preset("YouTube Music", "https://music.youtube.com/", icon_key="youtube2"),
            Preset("Deezer", "https://www.deezer.com/", icon_key="deezer"),
            Preset("Tidal", "https://tidal.com/", icon_key="tidal"),
            Preset("SoundCloud", "https://soundcloud.com/", icon_key="soundcloud"),
            Preset("Amazon Music", "https://music.amazon.com/", icon_key="amazon-music"),
            Preset("Apple Music", "https://music.apple.com/", icon_key="apple-music"),
        ),
    ),
    PresetCategory(
        _("Productivity & Organization"),
        (
            Preset("Notion", "https://www.notion.so/", icon_key="notion"),
            Preset("Trello", "https://trello.com/", icon_key="trello"),
            Preset("Figma", "https://www.figma.com/", icon_key="figma"),
            Preset("Canva", "https://www.canva.com/", icon_key="canva"),
            Preset("LanguageTool", "https://languagetool.org/", icon_key="languagetool"),
            Preset("Focusmate", "https://www.focusmate.com/", icon_key="focusmate"),
            Preset("Google Keep", "https://keep.google.com/", icon_key="google-keep"),
            Preset("Evernote", "https://evernote.com/", icon_key="evernote"),
        ),
    ),
    PresetCategory(
        _("PDF Tools"),
        (
            Preset("PDF24 Tools", "https://tools.pdf24.org/en/", icon_key="pdf24-tools"),
            Preset("iLovePDF", "https://www.ilovepdf.com/pt", icon_key="ilovepdf"),
            Preset("TinyWow PDF", "https://tinywow.com/tools/pdf", icon_key="tinywow-pdf"),
            Preset("pdfFiller", "https://edit-pdf.pdffiller.com/", icon_key="pdffiller"),
        ),
    ),
    PresetCategory(
        _("Calculations & Finance"),
        (
            Preset("Omni Calculator", "https://www.omnicalculator.com/pt", icon_key="omni-calculator"),
            Preset("Calculadora do Cidadão (BCB)", "https://www3.bcb.gov.br/CALCIDADAO", icon_key="calculadora-cidadao"),
            Preset(
                "Correção de Valores (BCB)",
                "https://www3.bcb.gov.br/CALCIDADAO/publico/exibirFormCorrecaoValores.do?method=exibirFormCorrecaoValores",
                icon_key="correcao-valores-bcb",
            ),
        ),
    ),
    PresetCategory(
        _("Generators & Utilities"),
        (
            Preset("QRCode Monkey", "https://www.qrcode-monkey.com/", icon_key="qrcode-monkey"),
            Preset("ME-QR", "https://me-qr.com/", icon_key="me-qr"),
            Preset("ThisPersonDoesNotExist", "https://thispersondoesnotexist.com/", icon_key="thispersondoesnotexist"),
            Preset("Whip Contagem", "https://www.whip.com.br/contagem-caracteres"),
        ),
    ),
    PresetCategory(
        _("Conversion & Sharing"),
        (
            Preset("CloudConvert", "https://cloudconvert.com/", icon_key="cloudconvert"),
            Preset("Photopea", "https://www.photopea.com/", icon_key="photopea"),
            Preset("Wormhole", "https://wormhole.app/", icon_key="wormhole"),
            Preset("ProtectedText", "https://www.protectedtext.com/", icon_key="protectedtext"),
            Preset("Wheel of Names", "https://wheelofnames.com/", icon_key="wheel-of-names"),
        ),
    ),
    PresetCategory(
        _("Security & Diagnostics"),
        (
            Preset("UnshortLink", "https://unshortlink.com/", icon_key="unshortlink"),
            Preset("Unshorten.it", "https://unshorten.it/"),
            Preset("GetLinkInfo", "https://getlinkinfo.com/", icon_key="getlinkinfo"),
            Preset("Down For Everyone", "https://downforeveryoneorjustme.com/", icon_key="down-for-everyone"),
            Preset("Have I Been Pwned", "https://haveibeenpwned.com/", icon_key="have-i-been-pwned"),
        ),
    ),
    PresetCategory(
        _("Creativity & Content"),
        (
            Preset("Zest", "https://zest.is/", icon_key="zest"),
            Preset("Google Trends", "https://trends.google.com/trends/", icon_key="google-trends"),
            Preset("Answer the Public", "https://answerthepublic.com/", icon_key="answer-the-public"),
            Preset("Dicionário Criativo", "https://dicionariocriativo.com.br/", icon_key="dicionario-criativo"),
            Preset("Swipefile", "https://swipefile.com/", icon_key="swipefile"),
        ),
    ),
)
