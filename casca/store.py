"""Loja: catálogo de sites prontos para importar — local por padrão, ou de uma URL remota.

Para usar um catálogo hospedado no GitHub, defina STORE_URL com a URL "raw" do JSON
(ex.: "https://raw.githubusercontent.com/usuario/repo/main/store_catalog.json").
Enquanto STORE_URL for None, a Loja usa o catálogo local em data/store_catalog.json.
"""

import base64
import binascii
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

import requests

from .fileutils import safe_ext, slugify

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
    """Busca o catálogo da Loja (remoto, se STORE_URL estiver definida; local, senão).

    O catálogo local tem alguns MB (ícones embutidos em base64), então o resultado é
    cacheado em memória — sem isso, cada abertura da janela da Loja releria e reparsearia
    o JSON inteiro do disco."""
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
                company=entry.get("company") or "Independente",
                kind=entry.get("kind") or "Outros",
                package=entry.get("package"),
                country=entry.get("country"),
                icon_base64=entry.get("icon_base64"),
                icon_ext=entry.get("icon_ext") or "png",
            )
        )
    _catalog_cache = items
    return items


FACET_LABELS = {"company": "Empresa", "kind": "Tipo", "package": "Pacote", "country": "País"}
_FACET_FALLBACK = {"package": "Apps independentes", "country": "Global"}


def group_by(items: list[StoreItem], facet: str) -> dict[str, list[StoreItem]]:
    """Agrupa os itens por uma das facetas (company/kind/package/country)."""
    fallback = _FACET_FALLBACK.get(facet, "Outros")
    groups: dict[str, list[StoreItem]] = {}
    for item in items:
        key = getattr(item, facet) or fallback
        groups.setdefault(key, []).append(item)
    return dict(sorted(groups.items(), key=lambda pair: pair[0]))


def save_icon_to_temp(item: StoreItem) -> Path | None:
    """Decodifica o ícone embutido do item pra um arquivo temporário, se houver."""
    if not item.icon_base64:
        return None
    path = Path(tempfile.gettempdir()) / f"casca-store-{slugify(item.name)}.{safe_ext(item.icon_ext)}"
    try:
        path.write_bytes(base64.b64decode(item.icon_base64, validate=True))
    except (binascii.Error, ValueError):
        return None
    return path
