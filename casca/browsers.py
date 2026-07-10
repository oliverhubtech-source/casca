"""Detection of installed browsers and building the app-mode command."""

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import devices
from .i18n import _

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_WEBVIEW_RUNNER = _PROJECT_ROOT / "run_webview.py"
_FLATPAK_APP_ID = "io.github.oliverhubtech_source.Casca"


def in_flatpak() -> bool:
    return "FLATPAK_ID" in os.environ


def _host_which(binary: str) -> str | None:
    """Locate a binary on the HOST. Inside a Flatpak the sandbox doesn't see the
    system's binaries directly, and Casca deliberately doesn't request the flatpak-spawn
    permission (--talk-name=org.freedesktop.Flatpak) — that permission grants access to
    run arbitrary commands on the host and is heavily scrutinized in Flathub review.
    Sandboxed, Casca only offers its "own window" (WebKitGTK), no external browsers —
    this keeps working normally in the local install (install.sh)."""
    if in_flatpak():
        return None
    return shutil.which(binary)


def _webkit_available() -> bool:
    try:
        import gi

        gi.require_version("WebKit", "6.0")
        from gi.repository import WebKit  # noqa: F401
    except (ValueError, ImportError):
        return False
    return True

# app_mode: "chromium" (--app=URL), "epiphany" (--application-mode) or "firefox" (no real app mode)
NATIVE_CANDIDATES = [
    ("google-chrome-stable", "Google Chrome", "chromium"),
    ("google-chrome", "Google Chrome", "chromium"),
    ("chromium-browser", "Chromium", "chromium"),
    ("chromium", "Chromium", "chromium"),
    ("brave-browser", "Brave", "chromium"),
    ("microsoft-edge-stable", "Microsoft Edge", "chromium"),
    ("microsoft-edge", "Microsoft Edge", "chromium"),
    ("vivaldi-stable", "Vivaldi", "chromium"),
    ("vivaldi", "Vivaldi", "chromium"),
    ("opera", "Opera", "chromium"),
    ("helium", "Helium", "chromium"),
    ("epiphany", "GNOME Web", "epiphany"),
    ("firefox", "Firefox", "firefox"),
    ("firefox-esr", "Firefox ESR", "firefox"),
]

FLATPAK_CANDIDATES = [
    ("com.google.Chrome", "Google Chrome", "chromium"),
    ("org.chromium.Chromium", "Chromium", "chromium"),
    ("com.brave.Browser", "Brave", "chromium"),
    ("com.microsoft.Edge", "Microsoft Edge", "chromium"),
    ("com.vivaldi.Vivaldi", "Vivaldi", "chromium"),
    ("com.opera.Opera", "Opera", "chromium"),
    ("org.gnome.Epiphany", "GNOME Web", "epiphany"),
    ("org.mozilla.firefox", "Firefox", "firefox"),
]


@dataclass(frozen=True)
class Browser:
    key: str  # stable identifier saved in the created app
    label: str  # name shown in the UI
    kind: str  # "native" or "flatpak"
    target: str  # binary or flatpak app-id
    app_mode: str  # "chromium", "epiphany" or "firefox"

    def build_exec(
        self,
        url: str,
        profile_dir: str,
        wm_class: str,
        mobile: bool = False,
        device_key: str | None = None,
        browser_profile: str | None = None,
        width: int | None = None,
        height: int | None = None,
        title: str = "",
        header_color: str | None = None,
        text_color: str | None = None,
    ) -> str:
        if self.app_mode == "webkit":
            # This command goes into the Exec= of a .desktop that the HOST (GNOME Shell)
            # runs directly — if Casca itself is running as a Flatpak, "python3 <path>"
            # doesn't exist outside the sandbox, so it needs to re-enter via `flatpak run`.
            if in_flatpak():
                runner = f"flatpak run --command=casca-webview {_FLATPAK_APP_ID}"
            else:
                runner = f"python3 {shlex.quote(str(_WEBVIEW_RUNNER))}"
            command = (
                f'{runner} '
                f'--url={shlex.quote(url)} --title={shlex.quote(title)} '
                f'--data-dir={shlex.quote(profile_dir)} --wm-class={wm_class}'
            )
            if header_color:
                command += f' --color={shlex.quote(header_color)} --text-color={shlex.quote(text_color or "#ffffff")}'
            if width and height:
                command += f' --width={width} --height={height}'
            if mobile:
                device = devices.find_device(device_key)
                command += f' --user-agent={shlex.quote(device.user_agent)}'
            return command

        if self.kind == "native":
            launcher = shlex.quote(self.target)
        else:
            launcher = f"flatpak run {shlex.quote(self.target)}"

        if self.app_mode == "chromium":
            command = f'{launcher} --app={shlex.quote(url)} --class={wm_class} --name={wm_class}'
            if browser_profile:
                command += f' --profile-directory={shlex.quote(browser_profile)}'
            else:
                command += f' --user-data-dir={shlex.quote(profile_dir)}'
            if mobile:
                device = devices.find_device(device_key)
                command += f' --user-agent={shlex.quote(device.user_agent)}'
            if width and height:
                command += f' --window-size={width},{height}'
            return command
        if self.app_mode == "epiphany":
            # WebKitGTK/Epiphany doesn't expose a user-agent, window size, or profile/account flag via CLI.
            return f'{launcher} --application-mode --profile={shlex.quote(profile_dir)} {shlex.quote(url)}'
        # firefox: no native app mode exists, opens in a regular new window
        command = f'{launcher} --new-window {shlex.quote(url)}'
        if width and height:
            command += f' --width {width} --height {height}'
        return command

    @property
    def supports_isolated_profile(self) -> bool:
        return self.app_mode in ("chromium", "epiphany", "webkit")

    @property
    def supports_mobile_mode(self) -> bool:
        return self.app_mode in ("chromium", "firefox", "webkit")

    @property
    def supports_account_profile(self) -> bool:
        return self.app_mode == "chromium"

    @property
    def supports_header_color(self) -> bool:
        return self.app_mode == "webkit"


def _installed_flatpaks() -> set[str]:
    # Sandboxed, "flatpak list" would only see Casca itself — without flatpak-spawn (see
    # _host_which), there's no way to ask the host. In that case there are never any
    # external Flatpak candidates.
    if in_flatpak():
        return set()
    if not shutil.which("flatpak"):
        return set()
    try:
        result = subprocess.run(
            ["flatpak", "list", "--app", "--columns=application"],
            capture_output=True, text=True, timeout=5, check=True,
        )
    except (subprocess.SubprocessError, OSError):
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


_detected_cache: list[Browser] | None = None


def detect_browsers(force_refresh: bool = False) -> list[Browser]:
    """Returns the available browsers: Casca's own window (if WebKitGTK is present)
    first, as the default, followed by the installed browsers (native and Flatpak).

    The result is cached in memory — the scan involves `shutil.which` for ~14
    candidates and a `flatpak list` via subprocess, so repeating this on every app
    creation/edit has a real cost. Pass `force_refresh=True` only if the user
    installs/removes something during the session."""
    global _detected_cache
    if _detected_cache is not None and not force_refresh:
        return _detected_cache

    found: list[Browser] = []
    seen: set[tuple[str, str]] = set()

    if _webkit_available():
        found.append(
            Browser(key="webkit:casca", label=_("Casca's own window"), kind="native", target="", app_mode="webkit")
        )

    for binary, label, app_mode in NATIVE_CANDIDATES:
        path = _host_which(binary)
        if not path or (label, "native") in seen:
            continue
        seen.add((label, "native"))
        found.append(Browser(key=f"native:{binary}", label=label, kind="native", target=path, app_mode=app_mode))

    flatpaks = _installed_flatpaks()
    for app_id, label, app_mode in FLATPAK_CANDIDATES:
        if app_id not in flatpaks or (label, "flatpak") in seen:
            continue
        seen.add((label, "flatpak"))
        display = f"{label} (Flatpak)" if (label, "native") in seen else label
        found.append(Browser(key=f"flatpak:{app_id}", label=display, kind="flatpak", target=app_id, app_mode=app_mode))

    _detected_cache = found
    return found


def find_by_key(key: str, available: list[Browser] | None = None) -> Browser | None:
    for browser in available if available is not None else detect_browsers():
        if browser.key == key:
            return browser
    return None
