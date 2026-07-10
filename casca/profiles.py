"""Detection of profiles (accounts) already configured in the installed browsers."""

import json
from dataclasses import dataclass
from pathlib import Path

from .browsers import Browser

# subpath inside ~/.config (native) or ~/.var/app/<flatpak-id>/config (flatpak) —
# Flatpak mirrors the same relative subpath used by the native browser.
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
    directory: str  # value used in --profile-directory (e.g. "Default", "Profile 1")
    label: str  # name shown in the UI


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
    """Read the browser's Local State and return the accounts/profiles already configured in it."""
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
