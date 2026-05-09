import threading
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from gazan import icons, rclone  # noqa: E402
from gazan.providers import find_provider  # noqa: E402


class RemotesPage(Gtk.Box):
    def __init__(self, on_add_remote_requested: Callable[[], None]) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self._on_add_remote_requested = on_add_remote_requested
        self._remotes: list[dict] = []
        self._rows: list[Adw.ActionRow] = []

        self._stack = Gtk.Stack()
        self._stack.set_vexpand(True)
        self._stack.set_hexpand(True)
        self.append(self._stack)

        self._stack.add_named(self._build_loading_page(), "loading")
        self._stack.add_named(self._build_empty_page(), "empty")
        self._stack.add_named(self._build_error_page(), "error")

        self._list_page = Adw.PreferencesPage()
        self._list_group = Adw.PreferencesGroup(title="Cloud storage")
        self._list_page.add(self._list_group)
        self._stack.add_named(self._list_page, "list")

        self._stack.set_visible_child_name("loading")
        self._load_remotes()

    @property
    def remotes(self) -> list[dict]:
        return list(self._remotes)

    def refresh(self) -> None:
        self._stack.set_visible_child_name("loading")
        self._load_remotes()

    def _build_loading_page(self) -> Gtk.Widget:
        spinner = Gtk.Spinner(spinning=True)
        spinner.set_size_request(48, 48)
        spinner.set_halign(Gtk.Align.CENTER)
        spinner.set_valign(Gtk.Align.CENTER)
        return spinner

    def _build_empty_page(self) -> Adw.StatusPage:
        page = Adw.StatusPage(
            icon_name="folder-cloud-symbolic",
            title="No cloud storage",
            description="Add a cloud storage provider to get started",
        )
        button = Gtk.Button(label="Add cloud storage")
        button.add_css_class("pill")
        button.add_css_class("suggested-action")
        button.set_halign(Gtk.Align.CENTER)
        button.connect("clicked", lambda _b: self._on_add_remote_requested())
        page.set_child(button)
        return page

    def _build_error_page(self) -> Adw.StatusPage:
        return Adw.StatusPage(
            icon_name="dialog-error-symbolic",
            title="rclone not found",
            description=(
                "Gazan needs the rclone command-line tool. "
                "Install it from your distribution’s package manager."
            ),
        )

    def _load_remotes(self) -> None:
        def worker() -> None:
            try:
                remotes = rclone.list_remotes()
                error: BaseException | None = None
            except rclone.RcloneNotFoundError as e:
                remotes = []
                error = e
            GLib.idle_add(self._on_remotes_loaded, remotes, error)

        threading.Thread(target=worker, daemon=True).start()

    def _on_remotes_loaded(
        self,
        remotes: list[dict],
        error: BaseException | None,
    ) -> bool:
        if error is not None:
            self._stack.set_visible_child_name("error")
            return False

        self._remotes = remotes
        self._clear_rows()

        if not remotes:
            self._stack.set_visible_child_name("empty")
            return False

        for remote in remotes:
            row = Adw.ActionRow(title=remote["name"], subtitle=remote["type"])
            p = find_provider(remote["type"])
            icon = icons.provider_image(p.icon_file if p else None, size=32)
            row.add_prefix(icon)
            self._list_group.add(row)
            self._rows.append(row)

        self._stack.set_visible_child_name("list")
        return False

    def _clear_rows(self) -> None:
        for row in self._rows:
            self._list_group.remove(row)
        self._rows.clear()
