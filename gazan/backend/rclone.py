import subprocess
from pathlib import Path

RCLONE_BIN = "rclone"


class RcloneNotFoundError(Exception):
    """Raised when the rclone binary is not available on PATH."""


class RcloneError(Exception):
    """Raised when rclone returns a non-zero exit code."""


def _run(args: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise RcloneNotFoundError(
            f"rclone binary not found (looked for '{RCLONE_BIN}')"
        ) from e


def list_remotes() -> list[dict]:
    result = _run([RCLONE_BIN, "listremotes", "--long"])
    if result.returncode != 0:
        return []

    remotes: list[dict] = []
    for line in result.stdout.strip().splitlines():
        if ":" in line:
            name, rtype = line.split(":", 1)
            remotes.append({"name": name.strip(), "type": rtype.strip()})
    return remotes


def create_remote(name: str, remote_type: str, params: dict[str, str]) -> None:
    args = [RCLONE_BIN, "config", "create", name, remote_type, "--obscure"]
    for key, value in params.items():
        if value:
            args += [key, value]
    result = _run(args)
    if result.returncode != 0:
        raise RcloneError(
            result.stderr.strip() or "rclone returned a non-zero exit code"
        )


def _run_checked(args: list[str]) -> None:
    result = _run(args)
    if result.returncode != 0:
        raise RcloneError(result.stderr.strip() or "rclone returned a non-zero exit code")


def mount_remote(remote_name: str, mount_dir: str) -> None:
    mount_path = Path(mount_dir).expanduser()
    mount_path.mkdir(parents=True, exist_ok=True)
    _run_checked(
        [
            RCLONE_BIN,
            "mount",
            f"{remote_name}:",
            str(mount_path),
            "--daemon",
            "--vfs-cache-mode",
            "full",
        ]
    )


def unmount_remote(mount_dir: str) -> None:
    mount_path = str(Path(mount_dir).expanduser())
    _run_checked(["fusermount", "-u", mount_path])


def sync_to_remote(local_dir: str, remote_name: str, remote_path: str = "") -> None:
    src = str(Path(local_dir).expanduser())
    dst = f"{remote_name}:{remote_path.lstrip('/')}"
    _run_checked([RCLONE_BIN, "sync", src, dst])


def sync_from_remote(remote_name: str, local_dir: str, remote_path: str = "") -> None:
    src = f"{remote_name}:{remote_path.lstrip('/')}"
    dst = str(Path(local_dir).expanduser())
    Path(dst).mkdir(parents=True, exist_ok=True)
    _run_checked([RCLONE_BIN, "sync", src, dst])


def list_active_mounts() -> dict[str, str]:
    mounts: dict[str, str] = {}
    try:
        with open("/proc/mounts", encoding="utf-8") as handle:
            for line in handle:
                parts = line.split()
                if len(parts) < 3:
                    continue
                source, target, fstype = parts[0], parts[1], parts[2]
                if fstype != "fuse.rclone":
                    continue
                if not source.endswith(":"):
                    continue
                remote_name = source[:-1]
                mount_point = target.replace("\\040", " ")
                mounts[remote_name] = mount_point
    except OSError:
        return {}
    return mounts


