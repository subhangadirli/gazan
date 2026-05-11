import threading
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from gazan.ui import icons  # noqa: E402
from gazan.backend import rclone  # noqa: E402
from gazan.backend.providers import find_provider  # noqa: E402


class RemotesPage(Gtk.Box):
    def __init__(
        self,
        on_add_remote_requested: Callable[[], None],
        on_status_message: Callable[[str], None],
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self._on_add_remote_requested = on_add_remote_requested
        self._on_status_message = on_status_message
        self._remotes: list[dict] = []
        self._rows: list[Adw.ActionRow] = []
        self._mount_dirs: dict[str, str] = {}

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

        self._mount_dirs = rclone.list_active_mounts()
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
            self._add_row_actions(row, remote)
            self._list_group.add(row)
            self._rows.append(row)

        self._stack.set_visible_child_name("list")
        return False

    def _clear_rows(self) -> None:
        for row in self._rows:
            self._list_group.remove(row)
        self._rows.clear()

    def _add_row_actions(self, row: Adw.ActionRow, remote: dict) -> None:
        open_button = Gtk.Button(icon_name="folder-open-symbolic")
        open_button.set_tooltip_text("Open mounted folder")
        open_button.add_css_class("flat")
        open_button.connect("clicked", lambda _b: self._open_mounted_folder(remote["name"]))

        mount_button = Gtk.Button(icon_name="drive-harddisk-symbolic")
        mount_button.set_tooltip_text("Mount")
        mount_button.add_css_class("flat")
        mount_button.connect("clicked", lambda _b: self._open_mount_dialog(remote))

        unmount_button = Gtk.Button(icon_name="media-eject-symbolic")
        unmount_button.set_tooltip_text("Unmount")
        unmount_button.add_css_class("flat")
        unmount_button.connect("clicked", lambda _b: self._open_unmount_dialog(remote))

        sync_button = Gtk.Button(icon_name="emblem-synchronizing-symbolic")
        sync_button.set_tooltip_text("Sync")
        sync_button.add_css_class("flat")
        sync_button.connect("clicked", lambda _b: self._open_sync_dialog(remote))

        row.add_suffix(sync_button)
        row.add_suffix(unmount_button)
        row.add_suffix(mount_button)
        row.add_suffix(open_button)

    def _open_mounted_folder(self, remote_name: str) -> None:
        mount_dir = self._mount_dirs.get(remote_name)
        if mount_dir is None:
            mount_dir = rclone.list_active_mounts().get(
                remote_name,
                self._default_mount_dir(remote_name),
            )
        path = Path(mount_dir).expanduser()
        if not path.exists():
            self._on_status_message(f"Mount folder not found: {path}")
            return

        try:
            Gio.AppInfo.launch_default_for_uri(path.resolve().as_uri(), None)
        except GLib.Error as e:
            self._on_status_message(f"Couldn't open folder: {e.message}")

    def _default_mount_dir(self, remote_name: str) -> str:
        safe_name = remote_name.replace("/", "-")
        return str(Path("~/Cloud").expanduser() / safe_name)

    def _open_mount_dialog(self, remote: dict) -> None:
        dialog = Adw.Dialog()
        dialog.set_title(f"Mount {remote['name']}")
        dialog.set_content_width(520)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        mount_button = Gtk.Button(label="Mount")
        mount_button.add_css_class("suggested-action")
        header.pack_end(mount_button)
        toolbar.add_top_bar(header)

        group = Adw.PreferencesGroup(
            title="Mount Options",
            description="Mounted folders can be opened from Nautilus, Thunar, and other file managers.",
        )
        mount_dir = Adw.EntryRow(title="Mount folder")
        mount_dir.set_text(self._default_mount_dir(remote["name"]))
        group.add(mount_dir)

        clamp = Adw.Clamp(maximum_size=560, margin_top=12, margin_bottom=12)
        clamp.set_child(group)
        toolbar.set_content(clamp)
        dialog.set_child(toolbar)

        mount_button.connect(
            "clicked",
            lambda _b: self._run_mount(remote["name"], mount_dir.get_text().strip(), dialog),
        )
        dialog.present(self.get_root())

    def _open_unmount_dialog(self, remote: dict) -> None:
        dialog = Adw.Dialog()
        dialog.set_title(f"Unmount {remote['name']}")
        dialog.set_content_width(520)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        unmount_button = Gtk.Button(label="Unmount")
        unmount_button.add_css_class("destructive-action")
        header.pack_end(unmount_button)
        toolbar.add_top_bar(header)

        group = Adw.PreferencesGroup(
            title="Unmount Options",
            description="Provide the mount folder used when mounting this remote.",
        )
        mount_dir = Adw.EntryRow(title="Mount folder")
        mount_dir.set_text(
            self._mount_dirs.get(
                remote["name"],
                rclone.list_active_mounts().get(
                    remote["name"],
                    self._default_mount_dir(remote["name"]),
                ),
            )
        )
        group.add(mount_dir)

        clamp = Adw.Clamp(maximum_size=560, margin_top=12, margin_bottom=12)
        clamp.set_child(group)
        toolbar.set_content(clamp)
        dialog.set_child(toolbar)

        unmount_button.connect(
            "clicked",
            lambda _b: self._run_unmount(remote["name"], mount_dir.get_text().strip(), dialog),
        )
        dialog.present(self.get_root())

    def _open_sync_dialog(self, remote: dict) -> None:
        dialog = Adw.Dialog()
        dialog.set_title(f"Sync {remote['name']}")
        dialog.set_content_width(520)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        run_button = Gtk.Button(label="Run")
        run_button.add_css_class("suggested-action")
        header.pack_end(run_button)
        toolbar.add_top_bar(header)

        group = Adw.PreferencesGroup(
            title="Sync Options",
            description="Choose direction and paths for this sync job.",
        )
        direction = Adw.ComboRow(title="Direction")
        directions = Gtk.StringList.new(["Upload local -> cloud", "Download cloud -> local"])
        direction.set_model(directions)
        direction.set_selected(0)

        local_dir = Adw.EntryRow(title="Local folder")
        local_dir.set_text(str(Path("~").expanduser()))

        remote_path = Adw.EntryRow(title="Remote path (optional)")
        remote_path.set_text("")

        group.add(direction)
        group.add(local_dir)
        group.add(remote_path)

        clamp = Adw.Clamp(maximum_size=560, margin_top=12, margin_bottom=12)
        clamp.set_child(group)
        toolbar.set_content(clamp)
        dialog.set_child(toolbar)

        run_button.connect(
            "clicked",
            lambda _b: self._run_sync(
                remote_name=remote["name"],
                local_dir=local_dir.get_text().strip(),
                remote_path=remote_path.get_text().strip(),
                upload=direction.get_selected() == 0,
                dialog=dialog,
            ),
        )
        dialog.present(self.get_root())

    def _run_mount(self, remote_name: str, mount_dir: str, dialog: Adw.Dialog) -> None:
        if not mount_dir:
            self._on_status_message("Mount folder is required")
            return
        dialog.close()
        self._on_status_message(f"Mounting {remote_name}...")

        def worker() -> None:
            try:
                rclone.mount_remote(remote_name, mount_dir)
                error: str | None = None
            except (rclone.RcloneError, rclone.RcloneNotFoundError) as e:
                error = str(e)
            GLib.idle_add(self._on_mount_done, remote_name, mount_dir, error)

        threading.Thread(target=worker, daemon=True).start()

    def _on_mount_done(self, remote_name: str, mount_dir: str, error: str | None) -> bool:
        if error is not None:
            self._on_status_message(f"Mount failed: {error}")
            return False

        self._mount_dirs[remote_name] = mount_dir
        self._on_status_message(f"Mounted {remote_name} at {mount_dir}")
        return False

    def _run_unmount(self, remote_name: str, mount_dir: str, dialog: Adw.Dialog) -> None:
        if not mount_dir:
            self._on_status_message("Mount folder is required")
            return
        dialog.close()
        self._on_status_message("Unmounting...")

        def worker() -> None:
            try:
                rclone.unmount_remote(mount_dir)
                error: str | None = None
            except (rclone.RcloneError, rclone.RcloneNotFoundError) as e:
                error = str(e)
            GLib.idle_add(self._on_unmount_done, remote_name, mount_dir, error)

        threading.Thread(target=worker, daemon=True).start()

    def _on_unmount_done(self, remote_name: str, mount_dir: str, error: str | None) -> bool:
        if error is not None:
            self._on_status_message(f"Unmount failed: {error}")
            return False

        self._mount_dirs.pop(remote_name, None)
        self._on_status_message(f"Unmounted {mount_dir}")
        return False

    def _run_sync(
        self,
        remote_name: str,
        local_dir: str,
        remote_path: str,
        upload: bool,
        dialog: Adw.Dialog,
    ) -> None:
        if not local_dir:
            self._on_status_message("Local folder is required")
            return
        dialog.close()
        self._on_status_message("Starting sync...")

        def worker() -> None:
            try:
                if upload:
                    rclone.sync_to_remote(local_dir, remote_name, remote_path)
                    message = f"Uploaded {local_dir} to {remote_name}:{remote_path or '/'}"
                else:
                    rclone.sync_from_remote(remote_name, local_dir, remote_path)
                    message = f"Downloaded {remote_name}:{remote_path or '/'} to {local_dir}"
            except (rclone.RcloneError, rclone.RcloneNotFoundError) as e:
                message = f"Sync failed: {e}"
            GLib.idle_add(self._on_status_message, message)

        threading.Thread(target=worker, daemon=True).start()
