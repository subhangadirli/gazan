from pathlib import Path

import gi

gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gtk", "4.0")

from gi.repository import Gdk, GdkPixbuf, Gtk  # noqa: E402

_LOGOS_DIR = Path(__file__).parent.parent / "assets" / "provider-logos"


def provider_image(icon_file: str | None, size: int = 48) -> Gtk.Widget:
    if icon_file is not None:
        path = _LOGOS_DIR / icon_file
        if path.exists():
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    str(path), size, size
                )
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                return Gtk.Image.new_from_paintable(texture)
            except Exception:
                pass

    img = Gtk.Image.new_from_icon_name("network-server-symbolic")
    img.set_pixel_size(min(size, 48))
    return img


def provider_picture(icon_file: str | None) -> Gtk.Widget:
    if icon_file is not None:
        path = _LOGOS_DIR / icon_file
        if path.exists():
            picture = Gtk.Picture.new_for_filename(str(path))
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)
            picture.set_vexpand(True)
            picture.set_hexpand(True)
            return picture

    img = Gtk.Image.new_from_icon_name("network-server-symbolic")
    img.set_pixel_size(48)
    img.set_vexpand(True)
    img.set_hexpand(True)
    return img
