"""Builds the help.html shown in HelpWindow, with text translated via gettext.

The page's HTML/CSS/JS structure is a static template (kept in
``data/help_template.html``, with ``{...}`` placeholders); only the visible
text is filled in here at render time, in whatever language is active.
"""

import os
from pathlib import Path

from .i18n import _

_TEMPLATE_PATH = Path(__file__).parent / "data" / "help_template.html"


def _active_lang() -> str:
    raw = os.environ.get("LANGUAGE", "").split(":")[0] or os.environ.get("LANG", "en")
    return raw.split(".")[0].replace("_", "-") or "en"


def render_help_html() -> str:
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")

    user_guide = _("User Guide")

    return template.format(
        lang=_active_lang(),
        title=_("Casca — User Guide"),
        casca_icon_alt=_("Casca icon"),
        eyebrow=user_guide,
        hero_title=_("Websites, turned into apps. No fuss."),
        intro=_(
            "Casca turns any address into a GNOME app: icon in the menu, its own window, "
            "no leftover browser bar. This guide covers every option on the creation screen."
        ),
        nav_first_app=_("First app"),
        nav_presets=_("Presets"),
        nav_icon=_("Icon"),
        nav_shortcut=_("Shortcut"),
        nav_browser=_("Browser"),
        nav_mobile=_("Mobile mode"),
        nav_resolution=_("Resolution"),
        nav_edit=_("Edit"),
        first_app_title=_("Creating your first app"),
        first_app_subtitle=_("Two buttons on the home screen, two paths."),
        first_app_li_preset=_(
            "<strong>Create from preset</strong> — pick an already-cataloged site (Gmail, "
            "WhatsApp, Netflix, ChatGPT…), with name, address and icon ready to go."
        ),
        first_app_li_new=_(
            "<strong>Create new web app</strong> — start from scratch: you type in the name and address."
        ),
        first_app_note=_(
            "Everything below the name and address is <strong>optional</strong>. Without touching "
            "anything, Casca figures it out on its own: fetches the icon, doesn't create a Desktop "
            "shortcut, opens in its own window at normal size."
        ),
        presets_title=_("Preset sites"),
        presets_intro=_(
            'A search field at the top filters by site name (<code class="eyebrow text-[13px] '
            'bg-shell-mist dark:bg-[#2a2836] px-1.5 py-0.5 rounded">gmail</code>) or by category '
            '(<code class="eyebrow text-[13px] bg-shell-mist dark:bg-[#2a2836] px-1.5 py-0.5 '
            'rounded">microsoft</code>). Categories start collapsed — tap one to expand it.'
        ),
        cat_google=_("Google Products"),
        cat_microsoft=_("Microsoft Products"),
        cat_ai=_("Artificial Intelligence"),
        cat_search=_("Search Engines"),
        cat_messengers=_("Messengers"),
        cat_social=_("Social Networks"),
        cat_streaming=_("Streaming"),
        cat_music=_("Music"),
        cat_productivity=_("Productivity & Organization"),
        cat_pdf=_("PDF Tools"),
        cat_finance=_("Calculations & Finance"),
        cat_utilities=_("Generators & Utilities"),
        cat_conversion=_("Conversion & Sharing"),
        cat_security=_("Security & Diagnostics"),
        cat_creativity=_("Creativity & Content"),
        icon_title=_("Icon"),
        icon_intro=_("Check <strong>Customize icon and shortcut</strong> to choose manually."),
        icon_card_search_title=_("Search online"),
        icon_card_search_desc=_(
            "Checks several sources — Google, DuckDuckGo, apple-touch-icon, PWA manifest — "
            "and shows the results in a grid."
        ),
        icon_card_computer_title=_("From computer"),
        icon_card_computer_desc=_("Picks a PNG, JPG or SVG file already saved on your computer."),
        icon_card_gallery_title=_("From gallery"),
        icon_card_gallery_desc=_("Over 160 brand icons already included, no internet needed."),
        icon_outro=_(
            "Without checking anything, Casca fetches an icon automatically on save — or uses "
            "the icon that's already set, if the app came from a preset."
        ),
        shortcut_title=_("Desktop Shortcut"),
        shortcut_body=_(
            "Every app already shows up in the GNOME applications menu. To also get an icon on "
            "the Desktop, check <strong>Customize icon and shortcut</strong> and turn on "
            "<strong>Also create on the Desktop</strong>."
        ),
        browser_title=_("Custom browser"),
        browser_intro=_(
            "By default, every app opens in <strong>Casca's own window</strong>: lighter, top bar "
            "automatically colored to match the icon, isolated session per app."
        ),
        browser_warning=_(
            "<strong>Heads up:</strong> sites with Google login (Gmail, Drive, Calendar, Meet…) "
            "tend to refuse login in the built-in window — a Google restriction against "
            "unrecognized browsers, with no workaround. Check <strong>Use a custom browser</strong> "
            "and pick Chrome, Helium, GNOME Web or another installed browser."
        ),
        browser_outro=_(
            "With a Chromium-based browser (Chrome, Chromium, Brave, Edge, Vivaldi, Helium…) and "
            "more than one account configured in it, <strong>Browser account</strong> also shows up "
            "— choose which already-logged-in account opens the app, instead of a new profile with "
            "no login."
        ),
        mobile_title=_("Mobile mode"),
        mobile_body=_(
            "Check <strong>Open in mobile mode</strong> and pick a device — Google Pixel, iPhone, "
            "Galaxy, iPad. The app identifies itself to the site as that device, unlocking the "
            "mobile layout (usually simpler and faster)."
        ),
        resolution_title=_("Window resolution"),
        resolution_intro=_(
            "Check <strong>Customize window resolution</strong> — three ways to set the size, "
            "works with or without mobile mode enabled."
        ),
        resolution_li_device=_(
            "<strong>By device</strong> — uses the screen size of the device chosen in mobile mode."
        ),
        resolution_li_default=_("<strong>Default size</strong> — common resolutions (laptop, Full HD…)."),
        resolution_li_custom=_("<strong>Custom</strong> — you type in width and height in pixels."),
        edit_title=_("Edit and delete"),
        edit_body=_(
            "On the home screen, every app has a pencil to <strong>edit</strong> (changes any "
            "setting, including ones that were disabled at creation) and a trash icon to "
            "<strong>delete</strong> (removes the shortcut from the menu, the Desktop, and the "
            "saved icon)."
        ),
        footer=_("Casca — built to turn websites into GNOME apps."),
    )
