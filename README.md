# Gazan

A graphical frontend for [rclone](https://rclone.org/) built with GTK 4 and libadwaita. Gazan lets you manage your cloud storage connections through a clean, native GNOME-style interface — no terminal required for supported providers.

## Features

- View all configured rclone remotes at a glance
- Add new cloud storage connections through a guided dialog
- Provider logos and a polished libadwaita UI that fits right in on GNOME

### Supported providers

| Provider | Auth method |
|---|---|
| Google Drive | OAuth (via `rclone config`) |
| Dropbox | OAuth (via `rclone config`) |
| Microsoft OneDrive | OAuth (via `rclone config`) |
| Proton Drive | Email & password |
| Amazon S3 | Access key (AWS, Wasabi, or S3-compatible) |
| Backblaze B2 | Key ID & application key |
| SFTP | Host, username & password |
| WebDAV | URL, server type & credentials |

> **Note:** OAuth providers (Google Drive, Dropbox, OneDrive) require browser sign-in, which isn't yet handled inside Gazan. Run `rclone config` once in a terminal to set those up — they'll appear in Gazan automatically after that.

## Requirements

- Python 3.10+
- GTK 4 and libadwaita (`python3-gi`, `gir1.2-gtk-4.0`, `gir1.2-adw-1`)
- [rclone](https://rclone.org/install/) installed and available on `PATH`

## Installation

```bash
# Clone the repository
git clone https://codeberg.org/subhagadirli/gazan
cd gazan

# Create a virtual environment and install
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Running

```bash
python -m gazan
```

## Project structure

```
gazan/
├── main.py              # Application entry point (GApplication)
├── window.py            # Main application window
├── remotes_page.py      # Remotes list view
├── add_remote_dialog.py # Multi-step dialog for adding a remote
├── providers.py         # Provider definitions and field schemas
├── rclone.py            # rclone subprocess wrapper
├── icons.py             # Icon loading helpers
└── assets/
    ├── gazan-logos/     # Application icons
    └── provider-logos/  # Per-provider icons
```

## License

Gazan is free software released under the [GNU General Public License v3](gazan/LICENSE).
