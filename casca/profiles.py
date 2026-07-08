"""Detecção de perfis (contas) já configurados nos navegadores instalados."""

import json
from dataclasses import dataclass
from pathlib import Path

from .browsers import Browser

# subpath dentro de ~/.config (nativo) ou ~/.var/app/<flatpak-id>/config (flatpak) —
# o Flatpak espelha o mesmo subpath relativo usado pelo navegador nativo.
_CONFIG_SUBPATH = {
    "google-chrome-stable": "google-chrome",
    "google-chrome": "google-chrome",
    "com.google.Chrome": "google-chrome",
    "chromium-browser": "chromium",
    "chromium": "chromium",
    "org.chromium.Chromium": "chromium",
    "brave-browser": "BraveSoftware/Brave-Browser",
    "com.brave.Browser": "BraveSoftware/Brave-Browser",
    "microsoft-edge-stable": "microsoft-edge",
    "microsoft-edge": "microsoft-edge",
    "com.microsoft.Edge": "microsoft-edge",
    "vivaldi-stable": "vivaldi",
    "vivaldi": "vivaldi",
    "com.vivaldi.Vivaldi": "vivaldi",
    "opera": "opera",
    "com.opera.Opera": "opera",
    "helium": "net.imput.helium",
}


@dataclass(frozen=True)
class BrowserProfile:
    directory: str  # valor usado em --profile-directory (ex.: "Default", "Profile 1")
    label: str  # nome mostrado na interface


def _config_dir(browser: Browser) -> Path | None:
    if browser.app_mode != "chromium":
        return None
    _, ident = browser.key.split(":", 1)
    subpath = _CONFIG_SUBPATH.get(ident)
    if not subpath:
        return None
    if browser.kind == "native":
        return Path.home() / ".config" / subpath
    return Path.home() / ".var" / "app" / browser.target / "config" / subpath


def list_profiles(browser: Browser) -> list[BrowserProfile]:
    """Lê o Local State do navegador e retorna as contas/perfis já configurados nele."""
    config_dir = _config_dir(browser)
    if not config_dir:
        return []
    local_state_path = config_dir / "Local State"
    if not local_state_path.exists():
        return []
    try:
        data = json.loads(local_state_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    profiles = []
    for directory, info in data.get("profile", {}).get("info_cache", {}).items():
        email = info.get("user_name") or ""
        display_name = info.get("gaia_name") or info.get("name") or directory
        label = f"{display_name} ({email})" if email else display_name
        profiles.append(BrowserProfile(directory=directory, label=label))

    profiles.sort(key=lambda p: (p.directory != "Default", p.label.lower()))
    return profiles
