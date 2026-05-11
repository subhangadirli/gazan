from pathlib import Path

# All cloud storage operations (mount and sync) use the same base directory.
SYNC_BASE = Path("~/Sync").expanduser()


def remote_dir(remote_name: str) -> str:
    """Local folder for a remote: ~/Sync/<name>"""
    return str(SYNC_BASE / remote_name.replace("/", "-"))
