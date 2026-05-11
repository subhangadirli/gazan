# Gazan Claude Notes

This file mirrors the project guidance used for agent work in this repository.

## Project Snapshot

- Gazan is a GTK 4 + libadwaita desktop frontend for `rclone`.
- The codebase is Python-only and targets Linux desktop environments.
- The project is still early-stage, so prefer practical, low-risk changes over broad refactors.

## Codebase Shape

- `gazan/application.py` contains the `Adw.Application` entry point.
- `gazan/ui/` holds the GTK UI, including the main window, remotes page, and add-remote dialog.
- `gazan/backend/` contains rclone execution and provider definitions.
- `pyproject.toml` is the source of truth for packaging, metadata, and installed assets.

## Working Preferences

- Preserve the current architecture instead of introducing extra layers.
- Keep provider-specific logic in `gazan/backend/providers.py`.
- Keep subprocess handling narrow in `gazan/backend/rclone.py`.
- Match the existing libadwaita UI style and naming.
- Keep edits small enough to validate quickly.

## Relation To AGENTS

`AGENTS.md` is the primary instruction file for this repo. This file is the readable companion copy referenced from there.