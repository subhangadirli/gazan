import threading
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from gazan.backend import rclone  # noqa: E402
from gazan.backend.providers import Provider, find_provider  # noqa: E402


class EditRemoteDialog(Adw.Dialog):
    def __init__(
        self,
        remote: dict,
        on_remote_updated: Callable[[str], None],
    ) -> None:
        super().__init__()
        self.set_title(f"Edit {remote['name']}")
        self.set_content_width(540)

        self._remote = remote
        self._on_remote_updated = on_remote_updated
        self._provider = find_provider(remote["type"])
        self._field_widgets: dict[str, Gtk.Widget] = {}
        self._save_button: Gtk.Button | None = None
        self._closed = False

        self.connect("closed", lambda _: setattr(self, "_closed", True))

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        save_button = Gtk.Button(label="Save")
        save_button.add_css_class("suggested-action")
        save_button.connect("clicked", self._on_save)
        header.pack_end(save_button)
        self._save_button = save_button
        toolbar.add_top_bar(header)
        self.set_child(toolbar)

        provider = self._provider
        if provider is None or provider.auth_kind in ("oauth", "terminal"):
            toolbar.set_content(self._build_unsupported_page(provider))
            save_button.set_sensitive(False)
            return

        # Load current config to pre-fill fields
        spinner = Gtk.Spinner(spinning=True)
        spinner.set_size_request(48, 48)
        spinner.set_halign(Gtk.Align.CENTER)
        spinner.set_valign(Gtk.Align.CENTER)
        toolbar.set_content(spinner)
        self._toolbar = toolbar

        threading.Thread(target=self._load_and_build, daemon=True).start()

    def _build_unsupported_page(self, provider: Provider | None) -> Gtk.Widget:
        if provider is None:
            title = "Unknown provider"
            description = (
                "Gazan doesn't recognise this remote type. "
                "Edit it using rclone config in a terminal."
            )
        else:
            title = f"{provider.display_name} uses browser sign-in"
            description = (
                "To re-authenticate, open a terminal and run:\n\n"
                f"    rclone config reconnect {self._remote['name']}:\n\n"
                "Then return to Gazan."
            )
        return Adw.StatusPage(
            icon_name="dialog-information-symbolic",
            title=title,
            description=description,
        )

    def _load_and_build(self) -> None:
        config = rclone.get_remote_config(self._remote["name"])
        GLib.idle_add(self._build_form, config)

    def _build_form(self, config: dict[str, str]) -> bool:
        if self._closed:
            return False
        provider = self._provider
        assert provider is not None

        group = Adw.PreferencesGroup(
            title=provider.display_name,
            description="Leave a password field empty to keep the current value",
        )

        self._field_widgets = {}
        for f in provider.fields:
            widget = self._make_field_widget(f, config.get(f.key, ""))
            group.add(widget)
            self._field_widgets[f.key] = widget

        clamp = Adw.Clamp(
            maximum_size=520,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )
        clamp.set_child(group)

        scrolled = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        scrolled.set_child(clamp)
        self._toolbar.set_content(scrolled)
        return False

    def _make_field_widget(self, f, current_value: str) -> Gtk.Widget:
        if f.kind == "text":
            row = Adw.EntryRow(title=f.label)
            row.set_text(current_value)
            return row
        if f.kind == "password":
            row = Adw.PasswordEntryRow(title=f.label)
            # Don't pre-fill passwords; placeholder explains why
            row.set_show_apply_button(False)
            return row
        if f.kind == "choice":
            store = Gtk.StringList.new([label for _, label in f.choices])
            combo = Adw.ComboRow(title=f.label, model=store)
            keys = [k for k, _ in f.choices]
            if current_value in keys:
                combo.set_selected(keys.index(current_value))
            return combo
        raise ValueError(f"unknown field kind: {f.kind}")

    def _on_save(self, button: Gtk.Button) -> None:
        provider = self._provider
        assert provider is not None

        params: dict[str, str] = {}
        for f in provider.fields:
            widget = self._field_widgets.get(f.key)
            if widget is None:
                continue
            if f.kind == "choice":
                idx = widget.get_selected()
                params[f.key] = f.choices[idx][0]
            else:
                text = widget.get_text().strip()
                if f.kind == "password" and not text:
                    continue  # keep existing password
                if f.required and not text:
                    self._show_error("Missing information", f"{f.label} is required")
                    return
                params[f.key] = text

        button.set_sensitive(False)
        spinner = Gtk.Spinner(spinning=True)
        button.set_child(spinner)

        name = self._remote["name"]
        rtype = self._remote["type"]

        def worker() -> None:
            try:
                rclone.update_remote(name, params)
                err: str | None = None
            except (rclone.RcloneError, rclone.RcloneNotFoundError) as e:
                err = str(e)
            GLib.idle_add(self._on_save_done, err)

        threading.Thread(target=worker, daemon=True).start()

    def _on_save_done(self, error: str | None) -> bool:
        if self._closed:
            return False
        if error is None:
            self._on_remote_updated(self._remote["name"])
            self.close()
            return False

        assert self._save_button is not None
        self._save_button.set_sensitive(True)
        self._save_button.set_child(None)
        self._save_button.set_label("Save")
        self._show_error("Couldn't save changes", error)
        return False

    def _show_error(self, heading: str, body: str) -> None:
        alert = Adw.AlertDialog(heading=heading, body=body)
        alert.add_response("ok", "OK")
        alert.present(self)
