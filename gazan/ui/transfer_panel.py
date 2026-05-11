import subprocess

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import GLib, Gtk  # noqa: E402

from gazan.backend.rclone import TransferProgress  # noqa: E402


class TransferPanel(Gtk.Revealer):
    def __init__(self) -> None:
        super().__init__(
            transition_type=Gtk.RevealerTransitionType.SLIDE_UP,
            transition_duration=200,
            reveal_child=False,
        )
        self._proc: subprocess.Popen | None = None
        self._cancelled = False

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        inner = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=10,
            margin_bottom=10,
            margin_start=16,
            margin_end=16,
        )

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._title_label = Gtk.Label(xalign=0.0)
        self._title_label.set_hexpand(True)
        self._cancel_btn = Gtk.Button(label="Cancel")
        self._cancel_btn.add_css_class("flat")
        self._cancel_btn.connect("clicked", self._on_cancel)
        top_row.append(self._title_label)
        top_row.append(self._cancel_btn)

        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_show_text(False)

        self._status_label = Gtk.Label(label="", xalign=0.0)
        self._status_label.add_css_class("caption")
        self._status_label.add_css_class("dim-label")

        inner.append(top_row)
        inner.append(self._progress_bar)
        inner.append(self._status_label)
        outer.append(inner)
        self.set_child(outer)

    def start(self, remote_name: str, direction: str, proc: subprocess.Popen) -> None:
        self._proc = proc
        self._cancelled = False
        arrow = "↑" if direction == "upload" else "↓"
        verb = "Uploading to" if direction == "upload" else "Downloading from"
        self._title_label.set_text(f'{arrow} {verb} “{remote_name}”')
        self._progress_bar.set_fraction(0.0)
        self._status_label.set_text("Starting…")
        self._cancel_btn.set_sensitive(True)
        self._cancel_btn.set_label("Cancel")
        self.set_reveal_child(True)

    def update(self, progress: TransferProgress) -> None:
        if progress.percent >= 0:
            self._progress_bar.set_fraction(progress.percent / 100)
        else:
            self._progress_bar.pulse()

        parts: list[str] = []
        if progress.files_total > 0:
            parts.append(f"{progress.files_done} / {progress.files_total} files")
        if progress.percent >= 0:
            parts.append(f"{progress.percent}%")
        if progress.speed:
            parts.append(progress.speed)
        if progress.eta:
            parts.append(f"ETA {progress.eta}")
        self._status_label.set_text("  ·  ".join(parts) if parts else "Transferring…")

    def finish(self, error: str | None) -> None:
        if self._cancelled:
            return
        self._proc = None
        self._cancel_btn.set_sensitive(False)
        if error is None:
            self._progress_bar.set_fraction(1.0)
            self._status_label.set_text("Done")
        else:
            self._status_label.set_text(f"Failed: {error}")
        GLib.timeout_add(3000, self._hide)

    def _hide(self) -> bool:
        self.set_reveal_child(False)
        return False

    def _on_cancel(self, _btn: Gtk.Button) -> None:
        self._cancelled = True
        if self._proc is not None:
            self._proc.terminate()
            self._proc = None
        self._cancel_btn.set_sensitive(False)
        self._progress_bar.set_fraction(0.0)
        self._status_label.set_text("Cancelled")
        GLib.timeout_add(2000, self._hide)
