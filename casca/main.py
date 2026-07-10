"""Casca entry point."""

import sys

from . import i18n

i18n.install()

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio

from .window import CascaWindow

APP_ID = "io.github.oliverhubtech_source.Casca"


class CascaApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self) -> None:
        window = self.props.active_window
        if not window:
            window = CascaWindow(self)
        window.present()


def main() -> int:
    app = CascaApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
