"""Creation, listing and removal of web apps (registry + .desktop files)."""

import base64
import binascii
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import urlparse

import gi
import requests

gi.require_version("GLib", "2.0")
from gi.repository import GLib

from . import icons
from .browsers import Browser, detect_browsers, find_by_key
from .fileutils import has_dangerous_scheme, safe_ext, slugify
from .i18n import _

DATA_DIR = Path.home() / ".local" / "share" / "casca"
PROFILES_DIR = DATA_DIR / "profiles"
REGISTRY_PATH = DATA_DIR / "apps.json"
APPLICATIONS_DIR = Path.home() / ".local" / "share" / "applications"
DESKTOP_PREFIX = "casca-"

PACKAGES_DIR = DATA_DIR / "packages"
PACKAGES_REGISTRY_PATH = DATA_DIR / "packages.json"
PACKAGE_DESKTOP_PREFIX = "casca-pkg-"
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PACKAGE_RUNNER = _PROJECT_ROOT / "run_package.py"


def _package_runner_command() -> str:
    """Command for the package's .desktop Exec= — same as webkit in browsers.py,
    re-enters the packaging's own entrypoint when Casca itself is sandboxed,
    since this Exec= is run by the host, outside Casca's sandbox."""
    if "FLATPAK_ID" in os.environ:
        return "flatpak run --command=casca-package io.github.oliverhubtech_source.Casca"
    if "SNAP_NAME" in os.environ:
        return f"{os.environ['SNAP_NAME']}.casca-package"
    return f"python3 {_PACKAGE_RUNNER}"


def _desktop_dir() -> Path:
    path = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DESKTOP)
    return Path(path) if path else Path.home() / "Desktop"


def _as_positive_int(value) -> int | None:
    """Convert a width/height value coming from an imported JSON, discarding
    anything that isn't a plausible positive integer (avoids passing arbitrary
    strings through to the browser command)."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if 0 < number <= 10000 else None


@dataclass
class WebApp:
    slug: str
    name: str
    url: str
    browser_key: str
    icon_path: str
    desktop_shortcut: bool
    mobile: bool = False
    device_key: str | None = None
    browser_profile: str | None = None
    width: int | None = None
    height: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _load_json_registry(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_json_registry(path: Path, registry: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2, ensure_ascii=False))


def list_apps() -> list[WebApp]:
    registry = _load_json_registry(REGISTRY_PATH)
    return [WebApp(**data) for data in registry.values()]


def _unique_slug(name: str, registry: dict, existing_slug: str | None = None) -> str:
    base = slugify(name)
    if existing_slug and existing_slug in registry:
        return existing_slug
    slug = base
    counter = 2
    while slug in registry:
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def _desktop_file_content(app: WebApp, browser: Browser, exec_cmd: str) -> str:
    return (
        "[Desktop Entry]\n"
        "Version=1.0\n"
        "Type=Application\n"
        f"Name={app.name}\n"
        f"Comment={app.url}\n"
        f"Exec={exec_cmd}\n"
        f"Icon={app.icon_path}\n"
        "Terminal=false\n"
        "Categories=Network;WebBrowser;\n"
        f"StartupWMClass={app.slug.replace('-', '_')}\n"
        "X-Casca=true\n"
    )


def _write_desktop_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    path.chmod(0o755)


def _mark_trusted(path: Path) -> None:
    subprocess.run(
        ["gio", "set", str(path), "metadata::trusted", "true"],
        capture_output=True,
        check=False,
    )


def _refresh_desktop_database() -> None:
    subprocess.run(
        ["update-desktop-database", str(APPLICATIONS_DIR)],
        capture_output=True,
        check=False,
    )


def _write_all(app: WebApp, browser: Browser) -> None:
    profile_dir = PROFILES_DIR / app.slug
    if browser.supports_isolated_profile:
        profile_dir.mkdir(parents=True, exist_ok=True)

    header_color = text_color = None
    if browser.supports_header_color and app.icon_path and Path(app.icon_path).exists():
        rgb = icons.dominant_color(Path(app.icon_path))
        header_color = icons.to_hex(rgb)
        text_color = icons.contrasting_text_color(rgb)

    exec_cmd = browser.build_exec(
        app.url,
        str(profile_dir),
        app.slug.replace("-", "_"),
        mobile=app.mobile,
        device_key=app.device_key,
        browser_profile=app.browser_profile,
        width=app.width,
        height=app.height,
        title=app.name,
        header_color=header_color,
        text_color=text_color,
    )
    content = _desktop_file_content(app, browser, exec_cmd)

    menu_path = APPLICATIONS_DIR / f"{DESKTOP_PREFIX}{app.slug}.desktop"
    _write_desktop_file(menu_path, content)

    desktop_copy = _desktop_dir() / f"{DESKTOP_PREFIX}{app.slug}.desktop"
    if app.desktop_shortcut:
        _write_desktop_file(desktop_copy, content)
        _mark_trusted(desktop_copy)
    elif desktop_copy.exists():
        desktop_copy.unlink()

    _refresh_desktop_database()


def create_app(
    name: str,
    url: str,
    browser_key: str,
    icon_path: Path,
    desktop_shortcut: bool,
    mobile: bool = False,
    device_key: str | None = None,
    browser_profile: str | None = None,
    width: int | None = None,
    height: int | None = None,
) -> str:
    browser = find_by_key(browser_key)
    if browser is None:
        raise ValueError(_("Browser not found: %(key)s") % {"key": browser_key})

    registry = _load_json_registry(REGISTRY_PATH)
    slug = _unique_slug(name, registry)

    saved_icon = icons.save_icon_from_file(icon_path, slug) if icon_path.parent != icons.ICONS_DIR else icon_path

    app = WebApp(
        slug=slug,
        name=name,
        url=url,
        browser_key=browser_key,
        icon_path=str(saved_icon),
        desktop_shortcut=desktop_shortcut,
        mobile=mobile,
        device_key=device_key,
        browser_profile=browser_profile,
        width=width,
        height=height,
    )
    _write_all(app, browser)

    registry[slug] = app.to_dict()
    _save_json_registry(REGISTRY_PATH, registry)
    return slug


def update_app(
    slug: str,
    name: str,
    url: str,
    browser_key: str,
    icon_path: Path | None,
    desktop_shortcut: bool,
    mobile: bool = False,
    device_key: str | None = None,
    browser_profile: str | None = None,
    width: int | None = None,
    height: int | None = None,
) -> None:
    browser = find_by_key(browser_key)
    if browser is None:
        raise ValueError(_("Browser not found: %(key)s") % {"key": browser_key})

    registry = _load_json_registry(REGISTRY_PATH)
    if slug not in registry:
        raise KeyError(_("App not found: %(slug)s") % {"slug": slug})

    current = WebApp(**registry[slug])
    icon = str(icons.save_icon_from_file(icon_path, slug)) if icon_path else current.icon_path

    app = WebApp(
        slug=slug,
        name=name,
        url=url,
        browser_key=browser_key,
        icon_path=icon,
        desktop_shortcut=desktop_shortcut,
        mobile=mobile,
        device_key=device_key,
        browser_profile=browser_profile,
        width=width,
        height=height,
    )
    _write_all(app, browser)

    registry[slug] = app.to_dict()
    _save_json_registry(REGISTRY_PATH, registry)


def delete_app(slug: str) -> None:
    registry = _load_json_registry(REGISTRY_PATH)
    if slug not in registry:
        return

    menu_path = APPLICATIONS_DIR / f"{DESKTOP_PREFIX}{slug}.desktop"
    if menu_path.exists():
        menu_path.unlink()

    desktop_copy = _desktop_dir() / f"{DESKTOP_PREFIX}{slug}.desktop"
    if desktop_copy.exists():
        desktop_copy.unlink()

    profile_dir = PROFILES_DIR / slug
    if profile_dir.exists():
        shutil.rmtree(profile_dir, ignore_errors=True)

    icons.delete_icon(slug)

    del registry[slug]
    _save_json_registry(REGISTRY_PATH, registry)


def export_apps(dest: Path, slugs: list[str] | None = None) -> int:
    """Export apps (all, or just the given slugs) to a JSON with the icon embedded.
    Returns how many apps were exported."""
    registry = _load_json_registry(REGISTRY_PATH)
    selected = [data for slug, data in registry.items() if slugs is None or slug in slugs]

    exported = []
    for data in selected:
        app = WebApp(**data)
        entry = app.to_dict()
        del entry["slug"]
        del entry["icon_path"]

        icon_path = Path(app.icon_path) if app.icon_path else None
        if icon_path and icon_path.exists():
            entry["icon_base64"] = base64.b64encode(icon_path.read_bytes()).decode("ascii")
            entry["icon_ext"] = icon_path.suffix.lstrip(".") or "png"
        else:
            entry["icon_base64"] = None
            entry["icon_ext"] = None
        exported.append(entry)

    payload = {"casca_export_version": 1, "apps": exported}
    dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return len(exported)


_IMPORT_URL_TIMEOUT = 10
_MAX_IMPORT_BYTES = 20 * 1024 * 1024  # an export with several base64 icons can add up to a few MB


def fetch_import_payload(url: str) -> bytes:
    """Download an export JSON from a URL (e.g. a GitHub "raw" link)."""
    try:
        with requests.get(url, timeout=_IMPORT_URL_TIMEOUT, stream=True) as response:
            response.raise_for_status()
            chunks = []
            total = 0
            for chunk in response.iter_content(chunk_size=65536):
                total += len(chunk)
                if total > _MAX_IMPORT_BYTES:
                    raise ValueError(_("remote file too large"))
                chunks.append(chunk)
            return b"".join(chunks)
    except requests.RequestException as error:
        raise ValueError(_("could not download the file (%(error)s)") % {"error": error}) from error


def parse_import_candidates(data: bytes) -> list[dict]:
    """Read the bytes of an export JSON and return the raw list of 'apps' entries,
    to show on a selection screen before actually importing."""
    try:
        payload = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(_("could not read the file (%(error)s)") % {"error": error}) from error

    app_entries = payload.get("apps")
    if not isinstance(app_entries, list):
        raise ValueError(_("unexpected format: no 'apps' list found"))
    return app_entries


@dataclass
class ImportFailure:
    name: str
    reason: str


@dataclass
class ImportResult:
    created: list[str]
    failures: list[ImportFailure]


def import_selected(app_entries: list[dict], selected_indices: set[int]) -> ImportResult:
    """Import only the entries in `app_entries` whose index is in `selected_indices`.
    An entry with a problem (invalid URL, no browser available, icon impossible to
    fetch, error creating the app) becomes an `ImportFailure` instead of aborting the
    rest — those cases can be reviewed and fixed by hand afterward."""
    browsers_available = detect_browsers()
    fallback_browser = next((b for b in browsers_available if b.key == "webkit:casca"), None) or (
        browsers_available[0] if browsers_available else None
    )

    created_slugs: list[str] = []
    failures: list[ImportFailure] = []
    for index, entry in enumerate(app_entries):
        if index not in selected_indices:
            continue

        name = (entry.get("name") or "").strip()
        raw_url = (entry.get("url") or "").strip()
        display_name = name or _("item %(n)d") % {"n": index + 1}
        if not name or not raw_url:
            failures.append(ImportFailure(display_name, _("missing name or URL")))
            continue
        if has_dangerous_scheme(raw_url):
            failures.append(ImportFailure(name, _("unsupported URL scheme")))
            continue

        url = raw_url if "://" in raw_url else f"https://{raw_url}"
        if urlparse(url).scheme not in ("http", "https"):
            failures.append(ImportFailure(name, _("unsupported URL scheme")))
            continue

        browser_key = entry.get("browser_key")
        if not browser_key or find_by_key(browser_key, browsers_available) is None:
            if fallback_browser is None:
                failures.append(ImportFailure(name, _("no browser available")))
                continue
            browser_key = fallback_browser.key

        icon_b64 = entry.get("icon_base64")
        icon_source: Path | None = None
        if icon_b64:
            icon_ext = safe_ext(entry.get("icon_ext"))
            candidate = Path(tempfile.gettempdir()) / f"casca-import-{slugify(name)}.{icon_ext}"
            try:
                candidate.write_bytes(base64.b64decode(icon_b64, validate=True))
                icon_source = candidate
            except (binascii.Error, ValueError):
                icon_source = None
        if icon_source is None:
            data = icons.fetch_favicon(url)
            if data:
                icon_source = icons.save_preview(data, f"casca-import-{slugify(name)}")
        if icon_source is None:
            failures.append(ImportFailure(name, _("could not get an icon")))
            continue

        try:
            slug = create_app(
                name,
                url,
                browser_key,
                icon_source,
                desktop_shortcut=bool(entry.get("desktop_shortcut", False)),
                mobile=bool(entry.get("mobile", False)),
                device_key=entry.get("device_key"),
                browser_profile=entry.get("browser_profile"),
                width=_as_positive_int(entry.get("width")),
                height=_as_positive_int(entry.get("height")),
            )
        except (ValueError, KeyError, OSError) as error:
            failures.append(ImportFailure(name, str(error)))
            continue
        created_slugs.append(slug)

    return ImportResult(created=created_slugs, failures=failures)


@dataclass
class PackageInfo:
    slug: str
    name: str
    icon_path: str
    app_names: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def list_packages() -> list[PackageInfo]:
    registry = _load_json_registry(PACKAGES_REGISTRY_PATH)
    return [PackageInfo(**data) for data in registry.values()]


def create_package(name: str, sub_apps: list[dict], icon_path: Path) -> str:
    """Create a package: its own window listing the apps in `sub_apps`
    (each with a name/url) that opens the corresponding app on click.

    Each sub-app opens in Casca's own window (webkit), with an isolated
    session and its title bar colored from that specific app's icon.
    """
    registry = _load_json_registry(PACKAGES_REGISTRY_PATH)
    slug = _unique_slug(name, registry)
    package_dir = PACKAGES_DIR / slug
    icons_dir = package_dir / "icons"
    profiles_dir = package_dir / "profiles"
    icons_dir.mkdir(parents=True, exist_ok=True)
    profiles_dir.mkdir(parents=True, exist_ok=True)

    available = detect_browsers()
    browser = find_by_key("webkit:casca", available) or (available[0] if available else None)
    if browser is None:
        raise ValueError(_("No browser available to assemble the package."))

    sub_app_configs = []
    app_names = []
    for sub_app in sub_apps:
        sub_name = sub_app["name"]
        sub_url = sub_app["url"]
        sub_slug = slugify(sub_name)
        app_names.append(sub_name)

        icon_source = sub_app.get("icon_source")
        if icon_source and Path(icon_source).exists():
            sub_icon = icons.save_icon_from_file(Path(icon_source), f"{slug}-{sub_slug}")
            shutil.copy(sub_icon, icons_dir / f"{sub_slug}.png")
            icons.delete_icon(f"{slug}-{sub_slug}")
        else:
            data = icons.fetch_favicon(sub_url)
            if data:
                icons._normalize_to_png(data, icons_dir / f"{sub_slug}.png")

        sub_icon_path = icons_dir / f"{sub_slug}.png"
        header_color = text_color = None
        if browser.supports_header_color and sub_icon_path.exists():
            rgb = icons.dominant_color(sub_icon_path)
            header_color = icons.to_hex(rgb)
            text_color = icons.contrasting_text_color(rgb)

        sub_profile_dir = profiles_dir / sub_slug
        sub_profile_dir.mkdir(parents=True, exist_ok=True)
        exec_cmd = browser.build_exec(
            sub_url,
            str(sub_profile_dir),
            f"{slug}_{sub_slug}".replace("-", "_"),
            title=sub_name,
            header_color=header_color,
            text_color=text_color,
        )
        sub_app_configs.append(
            {
                "name": sub_name,
                "icon": str(sub_icon_path) if sub_icon_path.exists() else None,
                "exec": exec_cmd,
            }
        )

    package_color = package_text_color = None
    if icon_path.exists():
        rgb = icons.dominant_color(icon_path)
        package_color = icons.to_hex(rgb)
        package_text_color = icons.contrasting_text_color(rgb)

    config = {
        "package_name": name,
        "color": package_color,
        "text_color": package_text_color,
        "apps": sub_app_configs,
    }
    config_path = package_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False))

    package_icon_path = icons_dir / "package.png"
    if icon_path.suffix.lower() == ".svg":
        package_icon_path = icons_dir / "package.svg"
        package_icon_path.write_bytes(icon_path.read_bytes())
    else:
        shutil.copy(icon_path, package_icon_path)

    desktop_content = (
        "[Desktop Entry]\n"
        "Version=1.0\n"
        "Type=Application\n"
        f"Name={name}\n"
        "Comment=" + _("Package of web apps created by Casca") + "\n"
        f"Exec={_package_runner_command()} --config {config_path}\n"
        f"Icon={package_icon_path}\n"
        "Terminal=false\n"
        "Categories=Network;WebBrowser;\n"
        f"StartupWMClass={slug.replace('-', '_')}\n"
        "X-Casca=true\n"
        "X-CascaPackage=true\n"
    )
    menu_path = APPLICATIONS_DIR / f"{PACKAGE_DESKTOP_PREFIX}{slug}.desktop"
    _write_desktop_file(menu_path, desktop_content)
    _refresh_desktop_database()

    registry[slug] = PackageInfo(
        slug=slug, name=name, icon_path=str(package_icon_path), app_names=app_names
    ).to_dict()
    _save_json_registry(PACKAGES_REGISTRY_PATH, registry)
    return slug


def delete_package(slug: str) -> None:
    registry = _load_json_registry(PACKAGES_REGISTRY_PATH)
    if slug not in registry:
        return

    menu_path = APPLICATIONS_DIR / f"{PACKAGE_DESKTOP_PREFIX}{slug}.desktop"
    if menu_path.exists():
        menu_path.unlink()

    package_dir = PACKAGES_DIR / slug
    if package_dir.exists():
        shutil.rmtree(package_dir, ignore_errors=True)

    del registry[slug]
    _save_json_registry(PACKAGES_REGISTRY_PATH, registry)
    _refresh_desktop_database()
