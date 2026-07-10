"""Filename utilities shared between the app registry and the Store catalog."""

import re
import unicodedata

SAFE_ICON_EXTENSIONS = {"png", "jpg", "jpeg", "svg", "ico", "gif", "webp"}


def slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "item"


def safe_ext(ext: str | None) -> str:
    """Restrict to a known image extension. Never passes an external raw value
    straight into a filename — avoids path traversal via fields like '../../x'."""
    ext = (ext or "").lower().lstrip(".")
    return ext if ext in SAFE_ICON_EXTENSIONS else "png"


_DANGEROUS_URL_SCHEMES = ("javascript:", "data:", "vbscript:", "file:")


def has_dangerous_scheme(raw_url: str) -> bool:
    """Detect dangerous schemes even without '://' (e.g. 'javascript:alert(1)'), which
    would otherwise slip past the "no scheme -> prefix with https://" normalization and
    only get blocked (with a misleading reason) at the next step."""
    return raw_url.strip().lower().startswith(_DANGEROUS_URL_SCHEMES)


def ascii_app_id_component(text: str) -> str:
    """Reduce free text to a component valid for GLib's application_id
    (which rejects non-ASCII characters, e.g. 'Inteligência' becomes 'Inteligncia')."""
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return "".join(c if c.isalnum() else "_" for c in normalized)
