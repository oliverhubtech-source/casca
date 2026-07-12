"""Store: catalog of ready-made sites to import — local by default, or from a remote URL.

To use a catalog hosted on GitHub, set STORE_URL to the JSON's "raw" URL
(e.g. "https://raw.githubusercontent.com/user/repo/main/store_catalog.json").
While STORE_URL is None, the Store uses the local catalog in data/store_catalog.json.
"""

import base64
import binascii
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import requests

from .fileutils import safe_ext, slugify
from .i18n import _

STORE_URL: str | None = None
LOCAL_CATALOG_PATH = Path(__file__).parent / "data" / "store_catalog.json"
_REQUEST_TIMEOUT = 10


@dataclass(frozen=True)
class StoreItem:
    name: str
    url: str
    company: str
    kind: str
    package: str | None
    country: str | None
    icon_base64: str | None
    icon_ext: str
    tags: tuple[str, ...] = ()


def _load_local() -> dict:
    if not LOCAL_CATALOG_PATH.exists():
        return {"apps": []}
    try:
        return json.loads(LOCAL_CATALOG_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {"apps": []}


_catalog_cache: list[StoreItem] | None = None


def fetch_catalog(force_refresh: bool = False) -> list[StoreItem]:
    """Fetch the Store catalog (remote if STORE_URL is set; local otherwise).

    The local catalog is a few MB (icons embedded as base64), so the result is
    cached in memory — without this, every time the Store window opens it would
    re-read and re-parse the whole JSON file from disk."""
    global _catalog_cache
    if _catalog_cache is not None and not force_refresh:
        return _catalog_cache

    payload = None
    if STORE_URL:
        try:
            response = requests.get(STORE_URL, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            payload = None
    if payload is None:
        payload = _load_local()

    items = []
    for entry in payload.get("apps", []):
        name = entry.get("name")
        url = entry.get("url")
        if not name or not url:
            continue
        items.append(
            StoreItem(
                name=name,
                url=url,
                company=entry.get("company") or _("Independent"),
                kind=entry.get("kind") or _("Other"),
                package=entry.get("package"),
                country=entry.get("country"),
                icon_base64=entry.get("icon_base64"),
                icon_ext=entry.get("icon_ext") or "png",
                tags=tuple(entry.get("tags") or ()),
            )
        )
    _catalog_cache = items
    return items


_FACET_FALLBACK = {"package": _("Independent apps"), "country": _("Global")}


def group_by(items: list[StoreItem], facet: str) -> dict[str, list[StoreItem]]:
    """Group items by one of the facets (company/kind/package/country)."""
    fallback = _FACET_FALLBACK.get(facet, _("Other"))
    groups: dict[str, list[StoreItem]] = {}
    for item in items:
        key = getattr(item, facet) or fallback
        groups.setdefault(key, []).append(item)
    return dict(sorted(groups.items(), key=lambda pair: pair[0]))


GLOBAL_REGION = _("Global")

# Best-effort mapping from a POSIX locale's country code to one of the country
# names actually used in the catalog — good enough to preselect a sensible default
# region; the user can always override it in the Store, or pick "Global".
_LOCALE_COUNTRY_MAP: dict[str, str] = {
    "BR": "Brazil",
    "US": "United States",
    "DE": "Germany",
    "PL": "Poland",
    "NL": "Netherlands",
    "FR": "France",
    "GB": "United Kingdom",
    "AR": "Argentina",
    "UY": "Uruguay",
    "PY": "Paraguay",
    "CO": "Colombia",
    "CL": "Chile",
    "MX": "Mexico",
    "ES": "Spain",
}


def available_regions(items: list[StoreItem]) -> list[str]:
    """Distinct, sorted country values actually present in the catalog."""
    return sorted({item.country for item in items if item.country})


def detect_default_region(regions: list[str]) -> str:
    """Guesses the user's region from the system locale (e.g. LANG=pt_BR.UTF-8 ->
    "Brazil"), falling back to GLOBAL_REGION if it can't be mapped to one of
    `regions` — this only preselects the dropdown, the user can always override it."""
    locale_value = os.environ.get("LC_ALL") or os.environ.get("LC_CTYPE") or os.environ.get("LANG") or ""
    country_code = locale_value.split(".")[0].split("_")[-1].upper()
    region = _LOCALE_COUNTRY_MAP.get(country_code)
    return region if region in regions else GLOBAL_REGION


def region_matches(item: StoreItem, region: str | None) -> bool:
    """Whether `item` should show for the selected region: region-less (global)
    items always match; region-specific items (Marketplace/News) only match their
    own region. No region, or GLOBAL_REGION, means no filtering at all."""
    if not region or region == GLOBAL_REGION:
        return True
    return item.country is None or item.country == region


# Fixed, controlled vocabulary for usage tags/chips shown on the app detail page —
# keeps the chips visually consistent instead of free text per catalog entry.
USAGE_TAG_VOCAB: tuple[str, ...] = (
    _("Communication"),
    _("Social"),
    _("Business"),
    _("Development"),
    _("Office"),
    _("Entertainment"),
    _("Video Streaming"),
    _("Music Streaming"),
    _("Artificial Intelligence"),
    _("Design"),
    _("Finance"),
    _("Security"),
    _("Utilities"),
    _("News"),
    _("Shopping"),
    _("Cloud"),
    _("Search"),
    _("Education"),
)

# Generic fallback tags per `kind`, used when a catalog entry has no curated `tags`.
KIND_FALLBACK_TAGS: dict[str, tuple[str, ...]] = {
    "Messenger": (_("Communication"), _("Social")),
    "PDF": (_("Utilities"), _("Office")),
    "Security": (_("Security"), _("Utilities")),
    "News": (_("News"),),
    "Artificial Intelligence": (_("Artificial Intelligence"),),
    "Finance": (_("Finance"), _("Utilities")),
    "Music Streaming": (_("Music Streaming"), _("Entertainment")),
    "Social Network": (_("Social"), _("Communication")),
    "Utility": (_("Utilities"),),
    "Cloud Computing": (_("Cloud"), _("Office")),
    "Marketplace": (_("Shopping"),),
    "Conversion & Sharing": (_("Utilities"),),
    "Creativity": (_("Design"), _("Utilities")),
    "Video Streaming": (_("Video Streaming"), _("Entertainment")),
    "Productivity": (_("Office"), _("Business")),
    "Search Engine": (_("Search"), _("Utilities")),
}


def usage_tags(item: StoreItem) -> tuple[str, ...]:
    """The item's curated tags if the catalog entry has any, otherwise a generic
    fallback derived from its `kind`."""
    if item.tags:
        return item.tags
    return KIND_FALLBACK_TAGS.get(item.kind, ())


@dataclass(frozen=True)
class KindInfo:
    blurb: str
    space_range_mb: tuple[int, int]
    pc_access: tuple[str, ...]
    speed_tier: int  # 1-3, heuristic baseline used by rank_badge()
    usability_tier: int  # 1-3, heuristic baseline used by rank_badge()


# Per-category copy for the Store's detail page — deliberately generic (by `kind`,
# not per individual app): with 212 catalog entries, per-app editorial descriptions
# aren't realistic to keep accurate, so this is framed to the user as an estimate/
# typical pattern for that category rather than a fact about the specific site.
KIND_INFO: dict[str, KindInfo] = {
    "Messenger": KindInfo(
        _("Messaging app for real-time conversations with people or groups."),
        (150, 300), ("notifications", "camera", "mic"), 2, 3,
    ),
    "PDF": KindInfo(
        _("Tool to create, edit, convert or sign PDF files right from the browser."),
        (80, 150), ("files",), 3, 2,
    ),
    "Security": KindInfo(
        _("Digital security tool: checks links, data breaches or account safety."),
        (60, 120), (), 3, 2,
    ),
    "News": KindInfo(
        _("News portal with up-to-date journalistic content."),
        (100, 200), ("notifications",), 2, 2,
    ),
    "Artificial Intelligence": KindInfo(
        _("AI assistant to chat, or generate text, images or code."),
        (150, 250), ("mic", "files"), 2, 3,
    ),
    "Finance": KindInfo(
        _("Financial tool: calculator, value correction or money management."),
        (60, 120), (), 3, 2,
    ),
    "Music Streaming": KindInfo(
        _("Music and podcast streaming service."),
        (150, 300), ("notifications",), 2, 3,
    ),
    "Social Network": KindInfo(
        _("Social network to post, follow people and interact with content."),
        (150, 350), ("camera", "mic", "notifications", "location"), 2, 3,
    ),
    "Utility": KindInfo(
        _("Everyday utility for a specific task, right in the browser."),
        (60, 120), (), 3, 2,
    ),
    "Cloud Computing": KindInfo(
        _("Cloud storage and services to keep and reach files from anywhere."),
        (120, 250), ("files",), 2, 2,
    ),
    "Marketplace": KindInfo(
        _("Online marketplace to buy and sell products."),
        (120, 250), ("notifications", "location"), 2, 2,
    ),
    "Conversion & Sharing": KindInfo(
        _("File conversion tool or quick content sharing."),
        (60, 120), ("files",), 3, 2,
    ),
    "Creativity": KindInfo(
        _("Creative tool for images, text or ideas."),
        (100, 200), ("files",), 2, 3,
    ),
    "Video Streaming": KindInfo(
        _("Video, movie and TV show streaming service."),
        (200, 400), ("notifications",), 2, 3,
    ),
    "Productivity": KindInfo(
        _("Productivity tool to organize tasks, documents or meetings."),
        (120, 250), ("notifications", "files", "camera", "mic"), 2, 3,
    ),
    "Search Engine": KindInfo(
        _("Search engine to find information on the internet."),
        (60, 120), ("location",), 3, 2,
    ),
}

_DEFAULT_KIND_INFO = KindInfo(
    _("Site added to Casca as a web app."),
    (80, 200), ("notifications",), 2, 2,
)


def kind_info(kind: str) -> KindInfo:
    return KIND_INFO.get(kind, _DEFAULT_KIND_INFO)


# (icon name, label) for each possible "PC access" a site's category typically asks
# for — shown on the detail page so the user knows what to expect before adding it.
PC_ACCESS_LABELS: dict[str, tuple[str, str]] = {
    "camera": ("camera-web-symbolic", _("Camera")),
    "mic": ("audio-input-microphone-symbolic", _("Microphone")),
    "notifications": ("preferences-system-notifications-symbolic", _("Notifications")),
    "files": ("folder-symbolic", _("Files")),
    "location": ("find-location-symbolic", _("Location")),
}

# Deliberately smaller/more selective than window.py's _COMPANY_ICON_KEYS (which also
# maps small independent tools to an icon file) — this is only the subset that counts
# as a globally recognized brand for the "verified company" badge.
VERIFIED_COMPANIES: frozenset[str] = frozenset(
    {
        "Google",
        "Microsoft",
        "Apple",
        "Amazon",
        "Meta",
        "Netflix",
        "Spotify",
        "Discord",
        "Slack",
        "Notion",
        "Figma",
        "Canva",
        "OpenAI",
        "Anthropic",
        "xAI",
        "Mistral AI",
        "Reddit",
        "Telegram",
        "Twitch",
        "Yahoo",
        "DuckDuckGo",
        "ByteDance",
        "Atlassian",
        "Warner Bros. Discovery",
        "Paramount",
        "Disney",
        "Cloudflare",
        "IBM",
    }
)

# Kinds where the site is typically a single-purpose tool run by a small/independent
# team rather than a continuously-maintained product — used as a heuristic penalty
# for the "updates" sub-score in rank_badge().
_SPARSE_UPDATE_KINDS = {"Utility", "Conversion & Sharing"}


@dataclass(frozen=True)
class BadgeInfo:
    tier: str  # "Bronze" / "Silver" / "Gold"
    scores: dict[str, int]  # updates/usability/speed/community, each 1-3
    total: int  # 4-12


def rank_badge(item: StoreItem) -> BadgeInfo:
    """Heuristic Bronze/Silver/Gold "Casca seal" for an item, scored across 4
    dimensions (updates/usability/speed/community). This is NOT a measured
    benchmark of the actual site — it's a deterministic estimate derived only from
    the company's recognizability and the app's category, and must always be shown
    to the user labeled as a Casca-computed estimate, not an official rating."""
    verified = item.company in VERIFIED_COMPANIES
    info = kind_info(item.kind)

    community = 3 if verified else 1 if item.company == _("Independent") else 2
    updates = 3 if verified else 1 if item.kind in _SPARSE_UPDATE_KINDS else 2
    speed = info.speed_tier
    usability = min(3, info.usability_tier + (1 if verified else 0))

    scores = {
        "updates": updates,
        "usability": usability,
        "speed": speed,
        "community": community,
    }
    total = sum(scores.values())
    tier = _("Gold") if total >= 10 else _("Silver") if total >= 8 else _("Bronze")
    return BadgeInfo(tier=tier, scores=scores, total=total)


def save_icon_to_temp(item: StoreItem) -> Path | None:
    """Decode the item's embedded icon into a temporary file, if any."""
    if not item.icon_base64:
        return None
    path = Path(tempfile.gettempdir()) / f"casca-store-{slugify(item.name)}.{safe_ext(item.icon_ext)}"
    try:
        path.write_bytes(base64.b64decode(item.icon_base64, validate=True))
    except (binascii.Error, ValueError):
        return None
    return path
