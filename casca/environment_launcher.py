"""Runtime for an "environment" superapp: a window with the environment's banner
on top, its description/notes on the left, and a centered grid (up to 6 per row)
of the environment's apps and packages on the right — clicking one launches it.

Unlike a package (frozen config.json), this reads Casca's registries LIVE, so an
app assigned to the environment later shows up on the next launch without
recreating anything."""

import argparse
import configparser
import shlex
import subprocess
import sys
from pathlib import Path

from . import i18n

i18n.install()

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gdk, Gtk

from . import entries, icons, updater
from .fileutils import ascii_app_id_component
from .headerbar_css import build_header_css
from .i18n import _


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Casca environment launcher")
    parser.add_argument("--slug", required=True)
    return parser.parse_args(argv)


def _desktop_exec(desktop_path: Path) -> str | None:
    """Exec= line of a Casca-generated .desktop — the launch command for an app
    or package, without re-deriving browser flags here."""
    if not desktop_path.exists():
        return None
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(desktop_path)
        return parser.get("Desktop Entry", "Exec", fallback=None)
    except configparser.Error:
        return None


def _launch(exec_cmd: str) -> None:
    try:
        subprocess.Popen(shlex.split(exec_cmd), start_new_session=True)
    except (OSError, ValueError):
        pass


def _collect_items(env_slug: str) -> list[dict]:
    """Apps and packages assigned to the environment, each as
    {name, icon, exec} — blocked apps are skipped (they're suspended)."""
    items: list[dict] = []
    for app in entries.list_apps():
        if app.environment != env_slug or app.blocked:
            continue
        exec_cmd = _desktop_exec(entries.APPLICATIONS_DIR / f"{entries.DESKTOP_PREFIX}{app.slug}.desktop")
        if exec_cmd:
            items.append({"name": app.name, "icon": app.icon_path, "exec": exec_cmd})
    for package in entries.list_packages():
        if package.environment != env_slug:
            continue
        exec_cmd = _desktop_exec(
            entries.APPLICATIONS_DIR / f"{entries.PACKAGE_DESKTOP_PREFIX}{package.slug}.desktop"
        )
        if exec_cmd:
            items.append({"name": package.name, "icon": package.icon_path, "exec": exec_cmd})
    return items


def _build_card(item: dict) -> Gtk.Widget:
    button = Gtk.Button()
    button.add_css_class("flat")
    button.connect("clicked", lambda _b: _launch(item["exec"]))

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, halign=Gtk.Align.CENTER)
    box.set_margin_top(8)
    box.set_margin_bottom(8)
    icon_path = item.get("icon")
    if icon_path and Path(icon_path).exists():
        image = Gtk.Image.new_from_file(icon_path)
        image.set_pixel_size(48)
        box.append(image)
    else:
        box.append(Gtk.Image.new_from_icon_name("image-missing-symbolic"))
    label = Gtk.Label(label=item.get("name", ""), wrap=True, justify=Gtk.Justification.CENTER, lines=2)
    label.set_max_width_chars(12)
    box.append(label)
    button.set_child(box)
    return button


def build_window(application: Adw.Application, env: entries.EnvironmentInfo) -> Adw.ApplicationWindow:
    window = Adw.ApplicationWindow(
        application=application, title=env.name, default_width=860, default_height=620
    )

    toolbar = Adw.ToolbarView()
    header = Adw.HeaderBar()

    color_source = None
    for candidate in (env.icon_path, env.banner_path):
        if candidate and Path(candidate).exists():
            color_source = Path(candidate)
            break
    accent_rgb = icons.dominant_color(color_source) if color_source else (94, 92, 100)
    _apply_header_css(header, "casca-env-header", icons.to_hex(accent_rgb), icons.contrasting_text_color(accent_rgb))
    toolbar.add_top_bar(header)

    body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

    if env.banner_path and Path(env.banner_path).exists():
        banner = Gtk.Picture.new_for_filename(env.banner_path)
        banner.set_content_fit(Gtk.ContentFit.COVER)
        banner.set_size_request(-1, 200)
        body.append(banner)
    else:
        stripe = Gtk.Box()
        stripe.set_size_request(-1, 72)
        stripe.add_css_class("casca-env-header")
        body.append(stripe)

    content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24, vexpand=True)
    content.set_margin_top(18)
    content.set_margin_bottom(18)
    content.set_margin_start(18)
    content.set_margin_end(18)

    info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, valign=Gtk.Align.START)
    info_box.set_size_request(280, -1)

    name_label = Gtk.Label(label=env.name, xalign=0, wrap=True)
    name_label.add_css_class("title-1")
    info_box.append(name_label)

    if env.description:
        description_label = Gtk.Label(label=env.description, xalign=0, wrap=True)
        info_box.append(description_label)

    if env.notes:
        notes_title = Gtk.Label(label=_("Notes"), xalign=0)
        notes_title.add_css_class("heading")
        notes_title.set_margin_top(8)
        info_box.append(notes_title)
        notes_label = Gtk.Label(label=env.notes, xalign=0, wrap=True)
        notes_label.add_css_class("dim-label")
        info_box.append(notes_label)

    content.append(info_box)

    items = _collect_items(env.slug)
    if items:
        scrolled = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        flow = Gtk.FlowBox()
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_homogeneous(True)
        flow.set_row_spacing(12)
        flow.set_column_spacing(12)
        flow.set_min_children_per_line(3)
        flow.set_max_children_per_line(6)
        flow.set_halign(Gtk.Align.CENTER)
        flow.set_valign(Gtk.Align.START)
        for item in items:
            flow.append(_build_card(item))
        scrolled.set_child(flow)
        content.append(scrolled)
    else:
        status = Adw.StatusPage(
            icon_name="io.github.oliverhubtech_source.Casca",
            title=_("No apps in this environment yet"),
            description=_("Create or edit an app in Casca and pick this environment."),
        )
        status.set_hexpand(True)
        content.append(status)

    body.append(content)
    toolbar.set_content(body)
    window.set_content(toolbar)
    return window


def _apply_header_css(header: Adw.HeaderBar, css_class: str, color: str, text_color: str) -> None:
    header.add_css_class(css_class)
    provider = Gtk.CssProvider()
    provider.load_from_data(
        (
            build_header_css(css_class, color, text_color)
            + f".{css_class} {{ background: {color}; }}"
        ).encode()
    )
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def _on_activate(application: Adw.Application, env: entries.EnvironmentInfo) -> None:
    build_window(application, env).present()
    updater.check_and_notify(application)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    env = entries.get_environment(args.slug)
    if env is None:
        print(f"casca-environment: unknown environment '{args.slug}'", file=sys.stderr)
        return 1

    app_id = "io.github.oliverhubtech_source.Casca.Env" + ascii_app_id_component(env.slug)
    app = Adw.Application(application_id=app_id)
    app.connect("activate", _on_activate, env)
    return app.run([])


if __name__ == "__main__":
    sys.exit(main())
