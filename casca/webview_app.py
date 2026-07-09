"""Runtime de janela própria do Casca: embute o site via WebKitGTK, com barra
de título colorida pela cor do ícone. Alternativa a abrir num navegador externo —
sem essa dependência, mas sites com login Google podem recusar o acesso."""

import argparse
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import Adw, Gdk, GLib, Gtk, WebKit

from .fileutils import ascii_app_id_component
from .headerbar_css import build_header_css


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Janela própria do Casca (WebKitGTK)")
    parser.add_argument("--url", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--wm-class", required=True)
    parser.add_argument("--color", default=None, help="Cor de fundo da barra, ex.: #1ed760")
    parser.add_argument("--text-color", default=None, help="Cor do texto da barra")
    parser.add_argument("--width", type=int, default=1000)
    parser.add_argument("--height", type=int, default=700)
    parser.add_argument("--user-agent", default=None)
    return parser.parse_args(argv)


def _apply_header_css(header: Adw.HeaderBar, css_class: str, color: str, text_color: str) -> Gtk.CssProvider:
    header.add_css_class(css_class)
    provider = Gtk.CssProvider()
    provider.load_from_data(build_header_css(css_class, color, text_color).encode())
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
    return provider


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    GLib.set_prgname(args.wm_class)

    app_id = "io.github.oliverhubtech-source.Casca.App" + ascii_app_id_component(args.wm_class)
    app = Adw.Application(application_id=app_id)

    def on_activate(application: Adw.Application) -> None:
        window = Adw.ApplicationWindow(
            application=application,
            title=args.title,
            default_width=args.width,
            default_height=args.height,
        )

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        if args.color:
            _apply_header_css(header, "casca-webview-header", args.color, args.text_color or "#ffffff")
        toolbar.add_top_bar(header)

        data_dir = Path(args.data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        network_session = WebKit.NetworkSession.new(str(data_dir / "storage"), str(data_dir / "cache"))

        web_view = WebKit.WebView(network_session=network_session)
        if args.user_agent:
            web_view.get_settings().set_user_agent(args.user_agent)
        web_view.load_uri(args.url)

        toolbar.set_content(web_view)
        window.set_content(toolbar)
        window.present()

    app.connect("activate", on_activate)
    return app.run([])


if __name__ == "__main__":
    sys.exit(main())
