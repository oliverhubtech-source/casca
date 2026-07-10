"""Fetching and preparing icons for the web apps created."""

import hashlib
import io
import json
import socket
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, GLib

import requests
import urllib3.util.connection as _urllib3_connection
from PIL import Image

from .i18n import _

# On networks with broken IPv6 routing (no real path out), Python tries the IPv6
# address first and hangs for several seconds before falling back to IPv4 — unlike
# curl, which already does Happy Eyeballs. Forcing IPv4 avoids that stall.
_urllib3_connection.allowed_gai_family = lambda: socket.AF_INET

ICON_SIZE = 256
ICONS_DIR = Path.home() / ".local" / "share" / "icons" / "casca"
PREVIEWS_DIR = Path(tempfile.gettempdir()) / "casca-previews"
_REQUEST_TIMEOUT = 6
_MAX_ICON_BYTES = 8 * 1024 * 1024  # generous for an icon, avoids holding a giant response in memory


def _normalize_to_png(data: bytes, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(io.BytesIO(data)) as image:
        image.convert("RGBA").resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS).save(dest, "PNG")
    return dest


def _svg_pixels(path: Path) -> list[tuple[int, int, int]]:
    """Rasterize an SVG via GdkPixbuf (librsvg) so its dominant color can be sampled —
    Pillow doesn't decode SVG directly."""
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(str(path), 48, 48)
    if not pixbuf.get_has_alpha():
        pixbuf = pixbuf.add_alpha(False, 0, 0, 0)
    data = pixbuf.get_pixels()
    n_channels = pixbuf.get_n_channels()
    rowstride = pixbuf.get_rowstride()
    pixels = []
    for y in range(pixbuf.get_height()):
        row_start = y * rowstride
        for x in range(pixbuf.get_width()):
            offset = row_start + x * n_channels
            r, g, b, a = data[offset], data[offset + 1], data[offset + 2], data[offset + 3]
            if a > 200:
                pixels.append((r, g, b))
    return pixels


def dominant_color(path: Path) -> tuple[int, int, int]:
    """Most frequent, "vivid" color of the icon (ignores transparency and near-black/white tones)."""
    try:
        if path.suffix.lower() == ".svg":
            pixels = _svg_pixels(path)
        else:
            with Image.open(path) as image:
                image = image.convert("RGBA")
                image.thumbnail((48, 48))
                pixels = [(r, g, b) for r, g, b, a in image.getdata() if a > 200]
    except (OSError, ValueError, GLib.Error):
        return (128, 128, 128)

    if not pixels:
        return (128, 128, 128)

    vivid = [p for p in pixels if not (all(c > 235 for c in p) or all(c < 20 for c in p))]
    candidates = vivid or pixels
    return Counter(candidates).most_common(1)[0][0]


def to_hex(rgb: tuple[int, int, int]) -> str:
    red, green, blue = rgb
    return f"#{red:02x}{green:02x}{blue:02x}"


def contrasting_text_color(rgb: tuple[int, int, int]) -> str:
    """White on dark colors, dark grey on light colors, to keep text legible."""
    red, green, blue = rgb
    luminance = (0.299 * red + 0.587 * green + 0.114 * blue) / 255
    return "#ffffff" if luminance < 0.55 else "#1c1c1c"


def _domain_of(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return parsed.netloc


def _get(url: str, **params) -> bytes | None:
    try:
        with requests.get(url, params=params or None, timeout=_REQUEST_TIMEOUT, stream=True) as response:
            response.raise_for_status()
            chunks = []
            total = 0
            for chunk in response.iter_content(chunk_size=65536):
                total += len(chunk)
                if total > _MAX_ICON_BYTES:
                    return None
                chunks.append(chunk)
            return b"".join(chunks)
    except requests.RequestException:
        return None


def _is_valid_image(data: bytes) -> bool:
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        return True
    except (OSError, ValueError, SyntaxError):
        return False


def fetch_favicon(url: str) -> bytes | None:
    """Fetch the site's favicon via Google's public service. Returns image bytes or None."""
    domain = _domain_of(url)
    if not domain:
        return None
    return _get("https://www.google.com/s2/favicons", domain=domain, sz=ICON_SIZE)


def _fetch_from_manifest(domain: str) -> bytes | None:
    """Read the site's manifest.json/webmanifest and fetch the largest PWA icon declared in it."""
    for manifest_path in ("/manifest.json", "/manifest.webmanifest", "/site.webmanifest"):
        raw = _get(f"https://{domain}{manifest_path}")
        if not raw:
            continue
        try:
            manifest = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        icon_entries = manifest.get("icons") or []
        if not icon_entries:
            continue

        def _icon_area(icon: dict) -> int:
            sizes = icon.get("sizes", "")
            try:
                w, h = sizes.lower().split("x")
                return int(w) * int(h)
            except (ValueError, AttributeError):
                return 0

        best = max(icon_entries, key=_icon_area)
        src = best.get("src")
        if not src:
            continue

        icon_url = src if src.startswith("http") else f"https://{domain}/{src.lstrip('/')}"
        icon_data = _get(icon_url)
        if icon_data:
            return icon_data
    return None


_SEARCH_SOURCES = (
    ("Google", lambda domain: _get("https://www.google.com/s2/favicons", domain=domain, sz=ICON_SIZE)),
    (_("Site icon (.ico)"), lambda domain: _get(f"https://{domain}/favicon.ico")),
    (_("Site icon (32px)"), lambda domain: _get(f"https://{domain}/favicon-32x32.png")),
    (_("Apple touch icon"), lambda domain: _get(f"https://{domain}/apple-touch-icon.png")),
    ("DuckDuckGo", lambda domain: _get(f"https://icons.duckduckgo.com/ip3/{domain}.ico")),
    ("Clearbit", lambda domain: _get(f"https://logo.clearbit.com/{domain}")),
    ("Yandex", lambda domain: _get(f"https://favicon.yandex.net/favicon/v2/{domain}", size=ICON_SIZE)),
    ("Icon Horse", lambda domain: _get(f"https://icon.horse/icon/{domain}")),
    ("FaviconKit", lambda domain: _get(f"https://api.faviconkit.com/{domain}/{ICON_SIZE}")),
    (_("PWA Manifest"), _fetch_from_manifest),
)


def search_icons(url: str) -> list[tuple[str, bytes]]:
    """Look for icon candidates across several internet sources, in parallel. Returns (source, bytes), deduplicated."""
    domain = _domain_of(url)
    if not domain:
        return []

    results: list[tuple[str, bytes]] = []
    seen_hashes: set[str] = set()

    with ThreadPoolExecutor(max_workers=len(_SEARCH_SOURCES)) as executor:
        future_to_label = {executor.submit(fetch, domain): label for label, fetch in _SEARCH_SOURCES}
        for future in as_completed(future_to_label, timeout=_REQUEST_TIMEOUT + 2):
            data = future.result()
            if not data or not _is_valid_image(data):
                continue
            digest = hashlib.md5(data).hexdigest()
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)
            results.append((future_to_label[future], data))

    return results


def save_icon_from_bytes(data: bytes, slug: str) -> Path:
    """Normaliza a imagem para PNG 256x256 e salva em ICONS_DIR/<slug>.png."""
    return _normalize_to_png(data, ICONS_DIR / f"{slug}.png")


def save_preview(data: bytes, key: str) -> Path:
    """Save an icon candidate (not yet confirmed) to a temporary PNG for preview."""
    return _normalize_to_png(data, PREVIEWS_DIR / f"{key}.png")


def save_icon_from_file(source: Path, slug: str) -> Path:
    """Copy/normalize an image file chosen by the user to ICONS_DIR/<slug>.<ext>."""
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".svg":
        dest = ICONS_DIR / f"{slug}.svg"
        dest.write_bytes(source.read_bytes())
        return dest
    dest = ICONS_DIR / f"{slug}.png"
    with Image.open(source) as image:
        image = image.convert("RGBA")
        image = image.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
        image.save(dest, "PNG")
    return dest


def delete_icon(slug: str) -> None:
    for ext in (".png", ".svg"):
        path = ICONS_DIR / f"{slug}{ext}"
        if path.exists():
            path.unlink()
