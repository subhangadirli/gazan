<p align="center">
  <img src="https://codeberg.org/subhangadirli/gazan/media/branch/master/gazan/assets/gazan-logos/gazan.svg" width="96" />
</p>

<h1 align="center">Gazan</h1>

Browse, upload, download and manage cloud files on Linux with a GTK4 interface. Gazan is a native [rclone](https://rclone.org/) frontend built with libadwaita — mount remotes as local folders, sync directories, and track live transfer progress, all without touching a terminal.

## Preview

<p align="center">
  <img src="https://codeberg.org/subhangadirli/gazan/media/branch/master/docs/preview-1.png" width="45%" />
  <img src="https://codeberg.org/subhangadirli/gazan/media/branch/master/docs/preview-2.png" width="45%" />
</p>
<p align="center">
  <img src="https://codeberg.org/subhangadirli/gazan/media/branch/master/docs/preview-3.png" width="45%" />
  <img src="https://codeberg.org/subhangadirli/gazan/media/branch/master/docs/preview-4.png" width="45%" />
</p>

## Features

- **Mount remotes as local folders** — access cloud files directly from your file manager
- **Sync directories** — upload or download with a live progress bar and cancel button
- **Storage usage** — see used and total space per remote at a glance
- **Add, edit and delete remotes** — guided dialogs, no terminal needed for credential-based providers
- **Desktop notifications** — get notified when a sync finishes or fails
- **Provider logos** — polished libadwaita UI that fits right in on GNOME

### Supported providers

| Provider | Auth method |
|---|---|
| Proton Drive | Email & password |
| Google Drive | OAuth (browser) |
| Dropbox | OAuth (browser) |
| Microsoft OneDrive | OAuth (browser) |
| Amazon S3 | Access key (AWS, Wasabi, or S3-compatible) |
| Backblaze B2 | Key ID & application key |
| Nextcloud | URL & credentials |
| ownCloud | URL & credentials |
| SharePoint | URL & credentials |
| WebDAV | URL, server type & credentials |
| SFTP | Host, username & password |

> **Note:** OAuth providers (Google Drive, Dropbox, OneDrive) open a browser window for sign-in. If the browser step fails, run `rclone config` once in a terminal — the remote will appear in Gazan automatically.

## Requirements

- Python 3.10+
- [rclone](https://rclone.org/install/) installed and available on `PATH`
- GTK 4 and libadwaita:

| Distro | Command |
|---|---|
| Arch / Artix | `sudo pacman -S gtk4 libadwaita` |
| Debian / Ubuntu | `sudo apt install gir1.2-gtk-4.0 gir1.2-adw-1` |
| Fedora | `sudo dnf install gtk4 libadwaita` |

## Installation

```bash
git clone https://codeberg.org/subhangadirli/gazan.git
cd gazan
python -m venv venv
source venv/bin/activate
pip install -e .
```

## Running

```bash
gazan
# or
python -m gazan
```

## Project structure

```
gazan/                         ← repo root
├── gazan/                     ← Python package
│   ├── application.py         # GApplication subclass and entry point
│   ├── ui/
│   │   ├── window.py          # Main application window
│   │   ├── remotes_page.py    # Remotes list — mount, sync, edit, delete
│   │   ├── transfer_panel.py  # Live sync progress bar (slides up from bottom)
│   │   ├── add_remote_dialog.py  # Multi-step dialog for adding a remote
│   │   ├── edit_remote_dialog.py # Edit existing remote credentials
│   │   └── icons.py           # Icon loading helpers
│   ├── backend/
│   │   ├── rclone.py          # rclone subprocess wrapper
│   │   ├── providers.py       # Provider definitions and field schemas
│   │   └── config.py          # Path standard: ~/Sync/<remote-name>
│   └── assets/
│       ├── gazan-logos/       # Application icons
│       └── provider-logos/    # Per-provider icons
└── pyproject.toml
```

## License

Gazan is free software released under the [GNU General Public License v3](LICENSE).
