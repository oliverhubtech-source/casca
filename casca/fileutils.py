"""Utilitários de nome de arquivo compartilhados entre o registro de apps e o catálogo da Loja."""

import re
import unicodedata

SAFE_ICON_EXTENSIONS = {"png", "jpg", "jpeg", "svg", "ico", "gif", "webp"}


def slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "item"


def safe_ext(ext: str | None) -> str:
    """Restringe a uma extensão de imagem conhecida. Nunca repassa um valor externo cru
    para dentro de um nome de arquivo — evita path traversal via campos como '../../x'."""
    ext = (ext or "").lower().lstrip(".")
    return ext if ext in SAFE_ICON_EXTENSIONS else "png"


_DANGEROUS_URL_SCHEMES = ("javascript:", "data:", "vbscript:", "file:")


def has_dangerous_scheme(raw_url: str) -> bool:
    """Detecta esquemas perigosos mesmo sem '://' (ex.: 'javascript:alert(1)'), que do
    contrário escapariam da normalização "sem esquema -> prefixa com https://" e só
    seriam barrados (com um motivo enganoso) na etapa seguinte."""
    return raw_url.strip().lower().startswith(_DANGEROUS_URL_SCHEMES)


def ascii_app_id_component(text: str) -> str:
    """Reduz um texto livre a um componente ASCII válido para application_id do GLib
    (que rejeita caracteres não-ASCII, ex.: 'Inteligência' vira 'Inteligncia')."""
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return "".join(c if c.isalnum() else "_" for c in normalized)
