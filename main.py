import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402

from gazan.window import GazanWindow  # noqa: E402

APP_ID = "io.codeberg.subhagadirli.Gazan"


class GazanApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self._icons_registered = False

    def do_activate(self) -> None:
        self._register_bundled_icons()
        window = self.props.active_window
        if window is None:
            window = GazanWindow(application=self)
        window.present()

    def _register_bundled_icons(self) -> None:
        if self._icons_registered:
            return
        project_root = Path(__file__).resolve().parent.parent
        icon_dir = project_root / "data" / "icons"
        if not icon_dir.is_dir():
            return
        display = Gdk.Display.get_default()
        if display is None:
            return
        Gtk.IconTheme.get_for_display(display).add_search_path(str(icon_dir))
        self._icons_registered = True


def main() -> int:
    app = GazanApplication()
    return app.run(sys.argv)
