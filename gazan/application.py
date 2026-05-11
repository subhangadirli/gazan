import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402

from gazan.ui.window import GazanWindow  # noqa: E402

APP_ID = "io.codeberg.subhagadirli.Gazan"
_ASSETS_DIR = Path(__file__).parent / "assets"


class GazanApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        display = Gdk.Display.get_default()
        if display is not None:
            theme = Gtk.IconTheme.get_for_display(display)
            theme.add_search_path(str(_ASSETS_DIR))

    def do_activate(self) -> None:
        window = self.props.active_window
        if window is None:
            window = GazanWindow(application=self)
        window.present()


def main() -> int:
    app = GazanApplication()
    return app.run(sys.argv)
