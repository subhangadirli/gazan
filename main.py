import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio  # noqa: E402

from gazan.window import GazanWindow  # noqa: E402

APP_ID = "io.codeberg.subhagadirli.Gazan"


class GazanApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

    def do_activate(self) -> None:
        window = self.props.active_window
        if window is None:
            window = GazanWindow(application=self)
        window.present()


def main() -> int:
    app = GazanApplication()
    return app.run(sys.argv)
