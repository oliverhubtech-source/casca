"""Background check for newer Casca releases on GitHub.

Safe to call from any of Casca's three entry points (main window, own-window
webview, package launcher) — the network request is throttled and runs off
the main thread, so it never delays a window from opening.
"""

import json
import os
import subprocess
import threading
import time
from pathlib import Path

import requests
from gi.repository import Gio, GLib

from . import __version__
from .i18n import _

_RELEASES_API = "https://api.github.com/repos/oliverhubtech-source/casca/releases/latest"
_CACHE_PATH = Path.home() / ".local" / "share" / "casca" / "update_check.json"
_CHECK_INTERVAL = 24 * 60 * 60  # a desktop app doesn't need to ask more often than daily
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_NOTIFICATION_ID = "update-available"  # constant id: re-triggers replace the same bubble, no stacking/spam


def _parse_version(text: str) -> tuple[int, ...]:
    parts = []
    for chunk in text.lstrip("vV").split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def is_newer(remote: str, local: str) -> bool:
    return _parse_version(remote) > _parse_version(local)


def _load_cache() -> dict:
    try:
        return json.loads(_CACHE_PATH.read_text())
    except (OSError, ValueError):
        return {}


def _save_cache(data: dict) -> None:
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(json.dumps(data))
    except OSError:
        pass


def _fetch_latest_tag() -> str | None:
    try:
        response = requests.get(_RELEASES_API, timeout=5)
        response.raise_for_status()
        return response.json()["tag_name"]
    except (requests.RequestException, ValueError, KeyError):
        return None


def _is_git_checkout() -> bool:
    return (_PROJECT_ROOT / ".git").is_dir()


def cached_latest_version() -> str | None:
    """The latest version seen by the last background check, straight from
    the on-disk cache — safe to call from the main thread (no network)."""
    return _load_cache().get("latest_tag")


def release_channel() -> str:
    """Release channel label for the About dialog, mirroring the branches
    release.yml treats as release/beta/alpha. Only a git checkout carries
    branch information; a packaged install (Flatpak/Snap/RPM/COPR) has no
    trace of which branch it was built from, so it's assumed to be a release
    build — which matches how we actually ship those today (COPR and the
    Flathub submission both only ever package the "main" channel)."""
    if _is_git_checkout():
        try:
            result = subprocess.run(
                ["git", "-C", str(_PROJECT_ROOT), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=5,
            )
            branch = result.stdout.strip() if result.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            branch = ""
        return {"main": _("Release"), "hmg": _("Beta"), "dev": _("Alpha")}.get(branch, _("Development"))
    return _("Release")


def _git_pull() -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(_PROJECT_ROOT), "pull", "--ff-only"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _report_update_result(app: Gio.Application, ok: bool) -> bool:
    notification = Gio.Notification.new(_("Casca"))
    notification.set_icon(Gio.ThemedIcon.new("io.github.oliverhubtech_source.Casca"))
    notification.set_body(
        _("Updated — restart Casca to use the new version.") if ok
        else _("Couldn't update automatically — check for updates manually.")
    )
    app.send_notification(_NOTIFICATION_ID, notification)
    return GLib.SOURCE_REMOVE


def _run_update_now(app: Gio.Application) -> None:
    def worker() -> None:
        ok = _git_pull()
        GLib.idle_add(_report_update_result, app, ok)

    threading.Thread(target=worker, daemon=True).start()


def _notify(app: Gio.Application, latest: str) -> bool:
    notification = Gio.Notification.new(_("Casca update available"))
    notification.set_icon(Gio.ThemedIcon.new("io.github.oliverhubtech_source.Casca"))
    notification.set_body(
        _("Version %(latest)s is available (you're on %(current)s).") % {"latest": latest, "current": __version__}
    )

    # Only a git checkout can update itself with no privilege escalation — Flatpak/Snap
    # already auto-update on their own, and an RPM install needs `sudo dnf upgrade`.
    if _is_git_checkout():
        if not app.lookup_action("casca-update-now"):
            action = Gio.SimpleAction.new("casca-update-now", None)
            action.connect("activate", lambda *_args: _run_update_now(app))
            app.add_action(action)
        notification.add_button(_("Update now"), "app.casca-update-now")

    app.send_notification(_NOTIFICATION_ID, notification)
    return GLib.SOURCE_REMOVE


def check_and_notify(app: Gio.Application) -> None:
    """Schedules a background check against GitHub Releases; notifies if a
    newer version exists. A no-op inside Flatpak/Snap, which already
    auto-update themselves — an in-app nag there would just be redundant."""
    if "FLATPAK_ID" in os.environ or "SNAP_NAME" in os.environ:
        return

    cache = _load_cache()
    now = time.time()

    def worker() -> None:
        latest = cache.get("latest_tag")
        if now - cache.get("checked_at", 0) > _CHECK_INTERVAL:
            fetched = _fetch_latest_tag()
            if fetched:
                latest = fetched
                _save_cache({"checked_at": now, "latest_tag": latest})
        if latest and is_newer(latest, __version__):
            GLib.idle_add(_notify, app, latest)

    threading.Thread(target=worker, daemon=True).start()
