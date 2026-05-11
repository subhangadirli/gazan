# Contributing to Gazan

Thank you for your interest in contributing. Gazan follows GNOME project standards and is working towards inclusion in [GNOME Circle](https://circle.gnome.org/).

## Where to contribute

The canonical repository is on Codeberg:

**https://codeberg.org/subhangadirli/gazan**

Mirrors on GitHub and GitLab are read-only. Please open issues and pull requests on Codeberg only.

## Reporting issues

Before opening an issue, check that it has not already been reported. When filing a bug, include:

- A clear description of the problem
- Steps to reproduce it
- What you expected to happen and what actually happened
- Your distro, GTK4 version, and rclone version (`rclone version`)
- Any relevant output from the terminal

## Submitting patches

1. Fork the repository on Codeberg.
2. Create a branch from `master` with a descriptive name (e.g. `fix-mount-error-message` or `add-pcloud-provider`).
3. Make your changes in small, focused commits.
4. Open a pull request against `master` and describe what the change does and why.

If your patch is large or changes the architecture, open an issue first to discuss the approach before writing code.

## Commit messages

Follow the standard format:

```
Short summary in imperative mood (under 72 characters)

Optional longer description explaining why the change is needed,
not what it does. Wrap at 72 characters.
```

Examples of good summaries:
- `Fix sync progress bar not resetting between transfers`
- `Add SFTP port field to edit dialog`
- `Remove unused _APP_ID constant from remotes_page`

## Code style

- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code.
- Use 4-space indentation, no tabs.
- Keep lines under 100 characters where reasonable.
- Prefer clarity over cleverness — this codebase targets GNOME/libadwaita conventions.
- UI changes should use `Adw` widgets where a suitable one exists before falling back to plain GTK4.

## Development setup

```bash
git clone https://codeberg.org/subhangadirli/gazan.git
cd gazan
python -m venv venv
source venv/bin/activate
pip install -e .
gazan
```

## Adding a new provider

Provider definitions live in [`gazan/backend/providers.py`](gazan/backend/providers.py). Each provider is a `Provider` dataclass with an `rclone_type`, display name, icon file, auth kind (`credentials` or `oauth`), and a list of `ProviderField` entries.

Place the provider logo (SVG preferred) in `gazan/assets/provider-logos/`.

## Code of Conduct

All contributors are expected to follow the [GNOME Code of Conduct](CODE_OF_CONDUCT.md). Please be respectful and considerate in all interactions.
