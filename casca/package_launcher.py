"""Runtime do "pacote": uma janela com grade de ícones dos apps do pacote —
clicar em um lança o comando daquele app (o mesmo tipo de comando que um app
normal do Casca usaria)."""

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gdk, Gtk

from .fileutils import ascii_app_id_component
from .headerbar_css import build_header_css


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launcher de pacote do Casca")
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def _apply_header_css(header: Adw.HeaderBar, css_class: str, color: str, text_color: str) -> None:
    header.add_css_class(css_class)
    provider = Gtk.CssProvider()
    provider.load_from_data(build_header_css(css_class, color, text_color).encode())
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def _launch(exec_cmd: str) -> None:
    try:
        subprocess.Popen(shlex.split(exec_cmd), start_new_session=True)
    except (OSError, ValueError):
        pass


def build_card(sub_app: dict) -> Gtk.Widget:
    button = Gtk.Button()
    button.add_css_class("flat")
    button.connect("clicked", lambda _b: _launch(sub_app.get("exec", "")))

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, halign=Gtk.Align.CENTER)
    box.set_margin_top(8)
    box.set_margin_bottom(8)
    icon_path = sub_app.get("icon")
    if icon_path and Path(icon_path).exists():
        image = Gtk.Image.new_from_file(icon_path)
        image.set_pixel_size(48)
        box.append(image)
    else:
        box.append(Gtk.Image.new_from_icon_name("image-missing-symbolic"))
    label = Gtk.Label(label=sub_app.get("name", ""), wrap=True, justify=Gtk.Justification.CENTER)
    box.append(label)
    button.set_child(box)
    return button


def build_window(application: Adw.Application, config: dict) -> Adw.ApplicationWindow:
    package_name = config.get("package_name", "Pacote")
    apps = config.get("apps", [])
    color = config.get("color")
    text_color = config.get("text_color", "#ffffff")

    window = Adw.ApplicationWindow(
        application=application, title=package_name, default_width=460, default_height=560
    )

    toolbar = Adw.ToolbarView()
    header = Adw.HeaderBar()
    if color:
        _apply_header_css(header, "casca-package-header", color, text_color)
    toolbar.add_top_bar(header)

    scrolled = Gtk.ScrolledWindow(vexpand=True)
    flow = Gtk.FlowBox()
    flow.set_margin_top(18)
    flow.set_margin_bottom(18)
    flow.set_margin_start(18)
    flow.set_margin_end(18)
    flow.set_selection_mode(Gtk.SelectionMode.NONE)
    flow.set_homogeneous(True)
    flow.set_row_spacing(12)
    flow.set_column_spacing(12)
    flow.set_min_children_per_line(3)
    flow.set_max_children_per_line(4)

    for sub_app in apps:
        flow.append(build_card(sub_app))

    scrolled.set_child(flow)
    toolbar.set_content(scrolled)
    window.set_content(toolbar)
    return window


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    config = json.loads(Path(args.config).read_text())

    package_name = config.get("package_name", "Pacote")
    app_id = "io.github.oliverhubtech_source.Casca.Package" + ascii_app_id_component(package_name)
    app = Adw.Application(application_id=app_id)
    app.connect("activate", lambda application: build_window(application, config).present())
    return app.run([])


if __name__ == "__main__":
    sys.exit(main())
