import threading
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from gazan.ui import icons  # noqa: E402
from gazan.backend import rclone  # noqa: E402
from gazan.backend.providers import PROVIDERS, Provider, ProviderField  # noqa: E402


class AddRemoteDialog(Adw.Dialog):
    def __init__(
        self,
        existing_remote_names: set[str],
        on_remote_added: Callable[[str], None],
    ) -> None:
        super().__init__()
        self.set_title("Add cloud storage")
        self.set_content_width(540)
        self.set_content_height(580)

        self._existing_names = existing_remote_names
        self._on_remote_added = on_remote_added
        self._selected_provider: Provider | None = None
        self._field_widgets: dict[str, Gtk.Widget] = {}
        self._field_values: dict[str, str] = {}
        self._oauth_token: str | None = None
        self._closed = False
        self._oauth_status_label: Gtk.Label | None = None
        self._oauth_button: Gtk.Button | None = None

        self._nav = Adw.NavigationView()
        self.set_child(self._nav)
        self._nav.add(self._build_provider_page())

        self.connect("closed", self._on_dialog_closed)

    def _on_dialog_closed(self, _dialog: Adw.Dialog) -> None:
        self._closed = True

    def _build_provider_page(self) -> Adw.NavigationPage:
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        flow = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.NONE,
            homogeneous=True,
            row_spacing=12,
            column_spacing=12,
            min_children_per_line=2,
            max_children_per_line=3,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )
        for provider in PROVIDERS:
            flow.append(self._make_provider_card(provider))

        clamp = Adw.Clamp(maximum_size=520)
        clamp.set_child(flow)

        scrolled = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        scrolled.set_child(clamp)
        toolbar.set_content(scrolled)

        return Adw.NavigationPage(child=toolbar, title="Choose provider")

    def _make_provider_card(self, provider: Provider) -> Gtk.Widget:
        button = Gtk.Button()
        button.add_css_class("card")
        button.connect("clicked", self._on_provider_selected, provider)

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
            margin_top=18,
            margin_bottom=18,
            margin_start=12,
            margin_end=12,
        )
        icon = icons.provider_picture(provider.icon_file)
        label = Gtk.Label(
            label=provider.display_name,
            wrap=True,
            justify=Gtk.Justification.CENTER,
        )

        box.append(icon)
        box.append(label)
        button.set_child(box)
        return button

    def _on_provider_selected(self, _button: Gtk.Button, provider: Provider) -> None:
        self._selected_provider = provider
        if provider.auth_kind == "oauth":
            self._nav.push(self._build_oauth_page(provider))
            self._start_oauth_setup(provider)
        else:
            self._nav.push(self._build_credentials_page(provider))

    def _build_oauth_page(self, provider: Provider) -> Adw.NavigationPage:
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())

        title = f"Connect {provider.display_name}"
        description = (
            "Gazan will open your browser for sign-in and finish the setup automatically."
        )

        status = Adw.StatusPage(
            icon_name="network-server-symbolic",
            title=title,
            description=description,
        )

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.append(status)

        self._oauth_status_label = Gtk.Label(
            label="Waiting for the browser sign-in to finish…",
            wrap=True,
            justify=Gtk.Justification.CENTER,
        )
        self._oauth_status_label.add_css_class("dim-label")
        self._oauth_status_label.set_margin_top(12)
        self._oauth_status_label.set_margin_start(24)
        self._oauth_status_label.set_margin_end(24)
        box.append(self._oauth_status_label)

        retry_button = Gtk.Button(label="Try again")
        retry_button.add_css_class("pill")
        retry_button.connect("clicked", lambda _b: self._start_oauth_setup(provider))
        retry_button.set_halign(Gtk.Align.CENTER)
        self._oauth_button = retry_button
        box.append(retry_button)

        spinner = Gtk.Spinner(spinning=True)
        spinner.set_size_request(32, 32)
        spinner.set_halign(Gtk.Align.CENTER)
        box.append(spinner)

        clamp = Adw.Clamp(maximum_size=520)
        clamp.set_child(box)
        toolbar.set_content(clamp)
        return Adw.NavigationPage(child=toolbar, title=provider.display_name)

    def _start_oauth_setup(self, provider: Provider) -> None:
        assert provider.auth_kind == "oauth"
        self._oauth_token = None
        if self._oauth_status_label is not None:
            self._oauth_status_label.set_text(
                f"Opening the browser for {provider.display_name}…"
            )
        if self._oauth_button is not None:
            self._oauth_button.set_sensitive(False)

        def worker() -> None:
            try:
                token = rclone.authorize_remote(provider.rclone_type)
                error: str | None = None
            except (rclone.RcloneError, rclone.RcloneNotFoundError) as e:
                token = ""
                error = str(e)
            GLib.idle_add(self._on_oauth_ready, provider, token, error)

        threading.Thread(target=worker, daemon=True).start()

        def worker() -> None:
            try:
                token = rclone.exchange_google_drive_code(code)
                error: str | None = None
            except (rclone.RcloneError, rclone.RcloneNotFoundError) as e:
                token = ""
                error = str(e)
            GLib.idle_add(self._on_oauth_ready, self._selected_provider, token, error)

        threading.Thread(target=worker, daemon=True).start()

    def _on_oauth_ready(
        self,
        provider: Provider | None,
        token: str,
        error: str | None,
    ) -> bool:
        if self._closed:
            return False
        if error is not None:
            if self._oauth_status_label is not None:
                self._oauth_status_label.set_text(error)
            if self._oauth_button is not None:
                self._oauth_button.set_sensitive(True)
            self._show_error("Couldn’t connect cloud storage", error)
            return False

        self._oauth_token = token
        if self._oauth_status_label is not None and provider is not None:
            self._oauth_status_label.set_text(
                f"{provider.display_name} is connected. Choose a name next."
            )
        if self._oauth_button is not None:
            self._oauth_button.set_sensitive(True)
        self._nav.push(self._build_name_page())
        return False

    def _build_credentials_page(self, provider: Provider) -> Adw.NavigationPage:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        next_button = Gtk.Button(label="Next")
        next_button.add_css_class("suggested-action")
        next_button.connect("clicked", self._on_credentials_next)
        header.pack_end(next_button)
        toolbar.add_top_bar(header)

        group = Adw.PreferencesGroup(
            title=provider.display_name,
            description="Enter your account details",
        )

        self._field_widgets = {}
        for f in provider.fields:
            widget = self._make_field_widget(f)
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
        toolbar.set_content(scrolled)

        return Adw.NavigationPage(child=toolbar, title="Account details")

    def _make_field_widget(self, f: ProviderField) -> Gtk.Widget:
        if f.kind == "text":
            row = Adw.EntryRow(title=f.label)
            return row
        if f.kind == "password":
            return Adw.PasswordEntryRow(title=f.label)
        if f.kind == "choice":
            store = Gtk.StringList.new([label for _, label in f.choices])
            return Adw.ComboRow(title=f.label, model=store)
        raise ValueError(f"unknown field kind: {f.kind}")

    def _read_field_values(self) -> tuple[dict[str, str] | None, str | None]:
        assert self._selected_provider is not None
        values: dict[str, str] = {}
        for f in self._selected_provider.fields:
            widget = self._field_widgets[f.key]
            if f.kind == "choice":
                idx = widget.get_selected()
                values[f.key] = f.choices[idx][0]
            else:
                text = widget.get_text().strip()
                if f.required and not text:
                    return None, f"{f.label} is required"
                values[f.key] = text
        return values, None

    def _on_credentials_next(self, _button: Gtk.Button) -> None:
        values, error = self._read_field_values()
        if error is not None:
            self._show_error("Missing information", error)
            return
        self._field_values = values  # type: ignore[assignment]
        self._nav.push(self._build_name_page())

    def _build_name_page(self) -> Adw.NavigationPage:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        save_button = Gtk.Button(label="Add")
        save_button.add_css_class("suggested-action")
        save_button.connect("clicked", self._on_save)
        header.pack_end(save_button)
        toolbar.add_top_bar(header)

        group = Adw.PreferencesGroup(
            title="Name this connection",
            description="Choose a short name to identify this storage",
        )
        name_row = Adw.EntryRow(title="Name")
        assert self._selected_provider is not None
        name_row.set_text(self._suggest_name(self._selected_provider))
        group.add(name_row)

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
        toolbar.set_content(scrolled)

        self._name_row = name_row
        self._save_button = save_button
        return Adw.NavigationPage(child=toolbar, title="Name")

    def _suggest_name(self, provider: Provider) -> str:
        base = provider.rclone_type
        if base not in self._existing_names:
            return base
        i = 2
        while f"{base}{i}" in self._existing_names:
            i += 1
        return f"{base}{i}"

    def _validate_name(self, name: str) -> str | None:
        if not name:
            return "Name cannot be empty"
        if any(c in name for c in ":/ \t"):
            return "Name can’t contain spaces, slashes, or colons"
        if name in self._existing_names:
            return f"A connection named “{name}” already exists"
        return None

    def _on_save(self, button: Gtk.Button) -> None:
        name = self._name_row.get_text().strip()
        error = self._validate_name(name)
        if error is not None:
            self._show_error("Invalid name", error)
            return

        button.set_sensitive(False)
        spinner = Gtk.Spinner(spinning=True)
        button.set_child(spinner)

        provider = self._selected_provider
        params = dict(self._field_values)
        assert provider is not None
        if provider.auth_kind == "oauth":
            assert self._oauth_token is not None
            params["token"] = self._oauth_token

        def worker() -> None:
            try:
                rclone.create_remote(name, provider.rclone_type, params)
                err: str | None = None
            except (rclone.RcloneError, rclone.RcloneNotFoundError) as e:
                err = str(e)
            GLib.idle_add(self._on_save_done, name, err)

        threading.Thread(target=worker, daemon=True).start()

    def _on_save_done(self, name: str, error: str | None) -> bool:
        if self._closed:
            return False
        if error is None:
            self._on_remote_added(name)
            self.close()
            return False

        self._save_button.set_sensitive(True)
        self._save_button.set_child(None)
        self._save_button.set_label("Add")
        self._show_error("Couldn’t add cloud storage", error)
        return False

    def _show_error(self, heading: str, body: str) -> None:
        alert = Adw.AlertDialog(heading=heading, body=body)
        alert.add_response("ok", "OK")
        alert.present(self)
