"""Store: catalog of ready-made sites to import — local by default, or from a remote URL.

To use a catalog hosted on GitHub, set STORE_URL to the JSON's "raw" URL
(e.g. "https://raw.githubusercontent.com/user/repo/main/store_catalog.json").
While STORE_URL is None, the Store uses the local catalog in data/store_catalog.json.
"""

import base64
import binascii
import json
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
