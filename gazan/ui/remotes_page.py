import threading
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

_APP_ID = "io.codeberg.subhagadirli.Gazan"

from gazan.ui import icons  # noqa: E402
from gazan.ui.edit_remote_dialog import EditRemoteDialog  # noqa: E402
from gazan.ui.transfer_panel import TransferPanel  # noqa: E402
from gazan.backend import rclone  # noqa: E402
from gazan.backend import config as gazan_config  # noqa: E402
from gazan.backend.providers import find_provider  # noqa: E402


def _format_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.1f} {unit}"
        n /= 1024
    return str(n)


def _format_usage(info: dict) -> str:
    used = info.get("used")
    total = info.get("total")
    if used is None:
        return ""
    if total:
        return f"{_format_bytes(used)} / {_format_bytes(total)}"
    return f"{_format_bytes(used)} used"


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
        self._mount_procs: dict[str, object] = {}
        # per-row widget refs for live state updates
        self._row_widgets: dict[str, dict] = {}

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

        self._transfer_panel = TransferPanel()
        self.append(self._transfer_panel)

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
                "Install it from your distribution's package manager."
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
        self._row_widgets.clear()
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
        for remote in remotes:
            self._fetch_usage(remote["name"])
        return False

    def _clear_rows(self) -> None:
        for row in self._rows:
            self._list_group.remove(row)
        self._rows.clear()

    def _add_row_actions(self, row: Adw.ActionRow, remote: dict) -> None:
        name = remote["name"]
        is_mounted = name in self._mount_dirs

        # Mount status icon (shown when mounted)
        badge = Gtk.Image(icon_name="emblem-ok-symbolic")
        badge.add_css_class("success")
        badge.set_tooltip_text("Mounted")
        badge.set_pixel_size(16)
        badge.set_margin_end(4)
        badge.set_visible(is_mounted)

        open_button = Gtk.Button(icon_name="folder-open-symbolic")
        open_button.set_tooltip_text("Open mounted folder")
        open_button.add_css_class("flat")
        open_button.set_visible(is_mounted)
        open_button.connect("clicked", lambda _b: self._open_mounted_folder(name))

        mount_button = Gtk.Button(icon_name="drive-harddisk-symbolic")
        mount_button.set_tooltip_text("Mount")
        mount_button.add_css_class("flat")
        mount_button.set_visible(not is_mounted)
        mount_button.connect("clicked", lambda _b: self._open_mount_dialog(remote))

        unmount_button = Gtk.Button(icon_name="media-eject-symbolic")
        unmount_button.set_tooltip_text("Unmount")
        unmount_button.add_css_class("flat")
        unmount_button.set_visible(is_mounted)
        unmount_button.connect("clicked", lambda _b: self._open_unmount_dialog(remote))

        # ⋮ menu with Sync, Edit and Delete
        popover = Gtk.Popover()
        popover.set_has_arrow(False)
        menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        menu_box.set_margin_top(4)
        menu_box.set_margin_bottom(4)
        menu_box.set_margin_start(4)
        menu_box.set_margin_end(4)

        sync_btn = Gtk.Button(label="Sync")
        sync_btn.add_css_class("flat")
        sync_btn.connect("clicked", lambda _b: (popover.popdown(), self._open_sync_dialog(remote)))

        edit_btn = Gtk.Button(label="Edit")
        edit_btn.add_css_class("flat")
        edit_btn.connect("clicked", lambda _b: (popover.popdown(), self._open_edit_dialog(remote)))

        delete_btn = Gtk.Button(label="Delete")
        delete_btn.add_css_class("destructive-action")
        delete_btn.connect("clicked", lambda _b: (popover.popdown(), self._confirm_delete(remote)))

        menu_box.append(sync_btn)
        menu_box.append(edit_btn)
        menu_box.append(delete_btn)
        popover.set_child(menu_box)

        more_button = Gtk.MenuButton(
            icon_name="view-more-symbolic",
            tooltip_text="More actions",
            popover=popover,
        )
        more_button.add_css_class("flat")

        self._row_widgets[name] = {
            "row": row,
            "badge": badge,
            "mount_btn": mount_button,
            "unmount_btn": unmount_button,
            "open_btn": open_button,
            "rtype": remote["type"],
        }

        row.add_suffix(badge)
        row.add_suffix(unmount_button)
        row.add_suffix(mount_button)
        row.add_suffix(open_button)
        row.add_suffix(more_button)

    def _fetch_usage(self, name: str) -> None:
        def worker() -> None:
            info = rclone.get_remote_about(name)
            GLib.idle_add(self._on_usage_ready, name, info)

        threading.Thread(target=worker, daemon=True).start()

    def _on_usage_ready(self, name: str, info: dict | None) -> bool:
        widgets = self._row_widgets.get(name)
        if widgets is None or info is None:
            return False
        usage = _format_usage(info)
        rtype = widgets["rtype"]
        subtitle = f"{rtype} · {usage}" if usage else rtype
        widgets["row"].set_subtitle(subtitle)
        return False

    def _update_row_state(self, name: str, is_mounted: bool) -> None:
        widgets = self._row_widgets.get(name)
        if widgets is None:
            return
        widgets["badge"].set_visible(is_mounted)
        widgets["mount_btn"].set_visible(not is_mounted)
        widgets["unmount_btn"].set_visible(is_mounted)
        widgets["open_btn"].set_visible(is_mounted)

    # ── open mounted folder ──────────────────────────────────────────────────

    def _open_mounted_folder(self, remote_name: str) -> None:
        mount_dir = self._mount_dirs.get(remote_name)
        if mount_dir is None:
            mount_dir = rclone.list_active_mounts().get(
                remote_name,
                self._default_dir(remote_name),
            )
        path = Path(mount_dir).expanduser()
        if not path.exists():
            self._on_status_message(f"Mount folder not found: {path}")
            return
        try:
            Gio.AppInfo.launch_default_for_uri(path.resolve().as_uri(), None)
        except GLib.Error as e:
            self._on_status_message(f"Couldn't open folder: {e.message}")

    def _default_dir(self, remote_name: str) -> str:
        return gazan_config.remote_dir(remote_name)

    # ── mount ────────────────────────────────────────────────────────────────

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
        mount_dir.set_text(self._default_dir(remote["name"]))
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

    def _run_mount(self, remote_name: str, mount_dir: str, dialog: Adw.Dialog) -> None:
        if not mount_dir:
            self._on_status_message("Mount folder is required")
            return
        dialog.close()
        self._on_status_message(f"Mounting {remote_name}…")

        def worker() -> None:
            try:
                proc = rclone.mount_remote(remote_name, mount_dir)
                error: str | None = None
            except (rclone.RcloneError, rclone.RcloneNotFoundError) as e:
                proc = None
                error = str(e)
            GLib.idle_add(self._on_mount_done, remote_name, mount_dir, proc, error)

        threading.Thread(target=worker, daemon=True).start()

    def _on_mount_done(
        self, remote_name: str, mount_dir: str, proc: object, error: str | None
    ) -> bool:
        if error is not None:
            self._on_status_message(f"Mount failed: {error}")
            self._send_notification("Mount failed", f'"{remote_name}": {error}', error=True)
            return False
        self._mount_dirs[remote_name] = mount_dir
        self._mount_procs[remote_name] = proc
        self._update_row_state(remote_name, is_mounted=True)
        self._on_status_message(f"Mounted {remote_name} at {mount_dir}")
        return False

    # ── unmount ──────────────────────────────────────────────────────────────

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
                    self._default_dir(remote["name"]),
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

    def _run_unmount(self, remote_name: str, mount_dir: str, dialog: Adw.Dialog) -> None:
        if not mount_dir:
            self._on_status_message("Mount folder is required")
            return
        dialog.close()
        self._on_status_message("Unmounting…")
        proc = self._mount_procs.get(remote_name)

        def worker() -> None:
            try:
                rclone.unmount_remote(mount_dir, proc)
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
        self._mount_procs.pop(remote_name, None)
        self._update_row_state(remote_name, is_mounted=False)
        self._on_status_message(f"Unmounted {mount_dir}")
        return False

    # ── sync ─────────────────────────────────────────────────────────────────

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
        directions = Gtk.StringList.new(["Upload local → cloud", "Download cloud → local"])
        direction.set_model(directions)
        direction.set_selected(0)

        local_dir = Adw.EntryRow(title="Local folder")
        local_dir.set_text(self._default_dir(remote["name"]))

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

        local_path = Path(local_dir).expanduser()
        remote_spec = f"{remote_name}:{remote_path.lstrip('/')}"

        local_path.mkdir(parents=True, exist_ok=True)
        if upload:
            src, dst = str(local_path), remote_spec
        else:
            src, dst = remote_spec, str(local_path)

        direction = "upload" if upload else "download"
        proc = rclone.start_sync_live(
            src=src,
            dst=dst,
            on_progress=lambda p: GLib.idle_add(self._transfer_panel.update, p),
            on_done=lambda err: GLib.idle_add(self._on_sync_done, remote_name, err),
        )
        self._transfer_panel.start(remote_name, direction, proc)

    def _send_notification(self, title: str, body: str, error: bool = False) -> None:
        app = Gio.Application.get_default()
        if app is None:
            return
        notif = Gio.Notification.new(title)
        notif.set_body(body)
        notif.set_priority(
            Gio.NotificationPriority.URGENT if error else Gio.NotificationPriority.NORMAL
        )
        app.send_notification(None, notif)

    def _on_sync_done(self, remote_name: str, error: str | None) -> bool:
        self._transfer_panel.finish(error)
        if error is None:
            self._on_status_message(f"Sync complete: {remote_name}")
            self._send_notification(
                "Sync complete", f'"{remote_name}" synced successfully'
            )
        else:
            self._on_status_message(f"Sync failed: {error}")
            self._send_notification("Sync failed", f'"{remote_name}": {error}', error=True)
        return False

    # ── edit ─────────────────────────────────────────────────────────────────

    def _open_edit_dialog(self, remote: dict) -> None:
        dialog = EditRemoteDialog(
            remote=remote,
            on_remote_updated=self._on_remote_updated,
        )
        dialog.present(self.get_root())

    def _on_remote_updated(self, name: str) -> None:
        self._on_status_message(f"Updated {name}")

    # ── delete ────────────────────────────────────────────────────────────────

    def _confirm_delete(self, remote: dict) -> None:
        name = remote["name"]
        alert = Adw.AlertDialog(
            heading=f"Delete “{name}”?",
            body="This removes the connection from Gazan and rclone. It does not delete any files.",
        )
        alert.add_response("cancel", "Cancel")
        alert.add_response("delete", "Delete")
        alert.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        alert.set_default_response("cancel")
        alert.set_close_response("cancel")
        alert.connect("response", self._on_delete_response, remote)
        alert.present(self.get_root())

    def _on_delete_response(self, _alert: Adw.AlertDialog, response: str, remote: dict) -> None:
        if response != "delete":
            return
        self._on_status_message(f"Deleting {remote['name']}…")

        def worker() -> None:
            try:
                rclone.delete_remote(remote["name"])
                error: str | None = None
            except (rclone.RcloneError, rclone.RcloneNotFoundError) as e:
                error = str(e)
            GLib.idle_add(self._on_delete_done, remote["name"], error)

        threading.Thread(target=worker, daemon=True).start()

    def _on_delete_done(self, name: str, error: str | None) -> bool:
        if error is not None:
            self._on_status_message(f"Delete failed: {error}")
            return False
        self._on_status_message(f"Deleted {name}")
        self.refresh()
        return False
