# Gazan Agent Instructions

This repository is a Python 3.10+ desktop application for rclone, built with GTK 4 and libadwaita.

## Working Rules

- Keep changes small and focused on the current GTK, backend, or packaging surface.
- Prefer the existing 3-layer shape: `gazan/ui/`, `gazan/backend/`, and `gazan/application.py`.
- Preserve the GTK 4 and libadwaita patterns already used in the UI code.
- Treat `gazan/backend/rclone.py` as a thin subprocess wrapper around the `rclone` CLI.
- Keep provider metadata in `gazan/backend/providers.py` rather than hardcoding new provider logic in the UI.
- Maintain Python type hints and the current lightweight style.
- Assume Linux/GNOME as the target environment.
- Respect the packaging setup in `pyproject.toml` and keep asset paths consistent.

## Handy Entry Points

- App startup: `gazan/application.py`
- Main window: `gazan/ui/window.py`
- Remote creation dialog: `gazan/ui/add_remote_dialog.py`
- Remote list view: `gazan/ui/remotes_page.py`
- Provider definitions: `gazan/backend/providers.py`
- rclone wrapper: `gazan/backend/rclone.py`

## Companion Notes

See [claude.md](claude.md) for the companion project notes.