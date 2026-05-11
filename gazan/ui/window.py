import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk  # noqa: E402

from gazan.ui.add_remote_dialog import AddRemoteDialog  # noqa: E402
from gazan.ui.remotes_page import RemotesPage  # noqa: E402

APP_VERSION = "0.1.1"
APP_ID = "io.codeberg.subhagadirli.Gazan"


class GazanWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.set_title("Gazan")
        self.set_default_size(900, 600)

        self._setup_actions()

        self._toast_overlay = Adw.ToastOverlay()
        self.set_content(self._toast_overlay)

        toolbar_view = Adw.ToolbarView()
        self._toast_overlay.set_child(toolbar_view)

        header = Adw.HeaderBar()

        add_button = Gtk.Button(icon_name="list-add-symbolic")
        add_button.set_tooltip_text("Add cloud storage")
        add_button.connect("clicked", lambda _b: self._open_add_remote_dialog())
        header.pack_end(add_button)

        menu = Gio.Menu()
        menu.append("About Gazan", "win.about")
        menu_button = Gtk.MenuButton(
            icon_name="open-menu-symbolic",
            menu_model=menu,
            tooltip_text="Main Menu",
        )
        header.pack_end(menu_button)

        toolbar_view.add_top_bar(header)

        self._remotes_page = RemotesPage(
            on_add_remote_requested=self._open_add_remote_dialog,
            on_status_message=self._show_status,
        )
        toolbar_view.set_content(self._remotes_page)

    def _setup_actions(self) -> None:
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._show_about)
        self.add_action(about_action)

    def _show_about(self, _action, _param) -> None:
        dialog = Adw.AboutDialog(
            application_name="Gazan",
            application_icon=APP_ID,
            developer_name="Subhan Gadirli",
            version=APP_VERSION,
            website="https://codeberg.org/subhangadirli/gazan",
            issue_url="https://codeberg.org/subhangadirli/gazan/issues",
            license_type=Gtk.License.GPL_3_0,
            copyright="© 2024 Subhan Gadirli",
            comments="Browse, upload, download and manage cloud files",
            developers=["Subhan Gadirli https://codeberg.org/subhangadirli"],
        )
        dialog.present(self)

    def _open_add_remote_dialog(self) -> None:
        existing = {r["name"] for r in self._remotes_page.remotes}
        dialog = AddRemoteDialog(
            existing_remote_names=existing,
            on_remote_added=self._on_remote_added,
        )
        dialog.present(self)

    def _on_remote_added(self, name: str) -> None:
        self._toast_overlay.add_toast(Adw.Toast(title=f"Added {name}"))
        self._remotes_page.refresh()

    def _show_status(self, message: str) -> None:
        self._toast_overlay.add_toast(Adw.Toast(title=message))
