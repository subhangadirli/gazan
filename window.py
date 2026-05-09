import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from gazan.add_remote_dialog import AddRemoteDialog  # noqa: E402
from gazan.remotes_page import RemotesPage  # noqa: E402


class GazanWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.set_title("Gazan")
        self.set_default_size(900, 600)

        self._toast_overlay = Adw.ToastOverlay()
        self.set_content(self._toast_overlay)

        toolbar_view = Adw.ToolbarView()
        self._toast_overlay.set_child(toolbar_view)

        header = Adw.HeaderBar()
        add_button = Gtk.Button(icon_name="list-add-symbolic")
        add_button.set_tooltip_text("Add cloud storage")
        add_button.connect("clicked", lambda _b: self._open_add_remote_dialog())
        header.pack_end(add_button)
        toolbar_view.add_top_bar(header)

        self._remotes_page = RemotesPage(
            on_add_remote_requested=self._open_add_remote_dialog,
        )
        toolbar_view.set_content(self._remotes_page)

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
