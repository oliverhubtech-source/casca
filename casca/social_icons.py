"""Gallery of well-known brand icons, bundled with the project (see LICENSE.txt)."""

from pathlib import Path

SOCIAL_ICONS_DIR = Path(__file__).parent / "data" / "social_icons"


def list_icons() -> list[tuple[str, Path]]:
    if not SOCIAL_ICONS_DIR.exists():
        return []
    paths = list(SOCIAL_ICONS_DIR.glob("*.svg")) + list(SOCIAL_ICONS_DIR.glob("*.png"))
    return sorted(((path.stem, path) for path in paths), key=lambda item: item[0])


def get_icon_path(key: str | None) -> Path | None:
    if not key:
        return None
    for ext in (".svg", ".png"):
        path = SOCIAL_ICONS_DIR / f"{key}{ext}"
        if path.exists():
            return path
    return None
