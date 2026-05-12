import json
import re
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

RCLONE_BIN = "rclone"


@dataclass
class TransferProgress:
    percent: int    # 0-100, or -1 if unknown
    speed: str      # e.g. "10.1 MiB/s"
    eta: str        # e.g. "6m10s"
    files_done: int
    files_total: int


# Matches the bytes-transferred stats line (contains "/s, ETA")
_BYTES_RE = re.compile(
    r"Transferred:\s+[\d.]+\s+\S+\s*/\s+[\d.]+\s+\S+,"
    r"\s*(-|\d+)%,"
    r"\s*([\d.]+\s+\S+/s),"
    r"\s*ETA\s+(\S+)"
)
# Matches the file-count stats line (plain integers, no unit suffix)
_FILES_RE = re.compile(r"Transferred:\s+(\d+)\s*/\s*(\d+),")


def _parse_stats_msg(msg: str) -> TransferProgress | None:
    m = _BYTES_RE.search(msg)
    if m is None:
        return None
    percent = int(m.group(1)) if m.group(1) != "-" else -1
    speed = m.group(2)
    eta = m.group(3) if m.group(3) != "-" else ""
    files_done = files_total = 0
    fm = _FILES_RE.search(msg)
    if fm:
        files_done = int(fm.group(1))
        files_total = int(fm.group(2))
    return TransferProgress(percent, speed, eta, files_done, files_total)


def start_sync_live(
    src: str,
    dst: str,
    on_progress: Callable[[TransferProgress], None],
    on_done: Callable[[str | None], None],
) -> subprocess.Popen:
    proc = subprocess.Popen(
        [
            RCLONE_BIN, "sync", src, dst,
            "--use-json-log", "--stats", "0.5s",
            "--stats-log-level", "NOTICE", "--log-level", "NOTICE",
        ],
        stderr=subprocess.PIPE,
        text=True,
    )

    def _reader() -> None:
        for raw in proc.stderr:
            raw = raw.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
                progress = _parse_stats_msg(data.get("msg", ""))
                if progress is not None:
                    on_progress(progress)
            except (json.JSONDecodeError, ValueError):
                pass
        proc.wait()
        error = None if proc.returncode == 0 else f"rclone exited with code {proc.returncode}"
        on_done(error)

    threading.Thread(target=_reader, daemon=True).start()
    return proc


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


def mount_remote(remote_name: str, mount_dir: str) -> subprocess.Popen:
    mount_path = Path(mount_dir).expanduser()
    mount_path.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [
            RCLONE_BIN,
            "mount",
            f"{remote_name}:",
            str(mount_path),
            "--vfs-cache-mode", "full",
            "--log-level", "ERROR",
        ],
        stderr=subprocess.PIPE,
        text=True,
    )
    # Give rclone a moment to fail fast if FUSE is unavailable
    import time
    time.sleep(1.5)
    if proc.poll() is not None:
        stderr = proc.stderr.read() if proc.stderr else ""
        raise RcloneError(stderr.strip() or f"rclone mount exited with code {proc.returncode}")
    return proc


def unmount_remote(mount_dir: str, proc: subprocess.Popen | None = None) -> None:
    mount_path = str(Path(mount_dir).expanduser())
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    else:
        _run_checked(["fusermount3", "-u", mount_path])


def sync_to_remote(local_dir: str, remote_name: str, remote_path: str = "") -> None:
    src = str(Path(local_dir).expanduser())
    dst = f"{remote_name}:{remote_path.lstrip('/')}"
    _run_checked([RCLONE_BIN, "sync", src, dst])


def sync_from_remote(remote_name: str, local_dir: str, remote_path: str = "") -> None:
    src = f"{remote_name}:{remote_path.lstrip('/')}"
    dst = str(Path(local_dir).expanduser())
    Path(dst).mkdir(parents=True, exist_ok=True)
    _run_checked([RCLONE_BIN, "sync", src, dst])


def authorize_remote(remote_type: str) -> str:
    """Run rclone authorize for OAuth providers. Opens the browser and blocks until done."""
    result = _run([RCLONE_BIN, "authorize", remote_type])
    if result.returncode != 0:
        raise RcloneError(result.stderr.strip() or "Authorization failed")
    combined = result.stdout + "\n" + result.stderr
    m = re.search(r"--->\n({.+?})\n<---", combined, re.DOTALL)
    if m:
        return m.group(1).strip()
    raise RcloneError("Could not read authorization token from rclone output")


def delete_remote(name: str) -> None:
    _run_checked([RCLONE_BIN, "config", "delete", name])


def get_remote_config(name: str) -> dict[str, str]:
    import json
    result = _run([RCLONE_BIN, "config", "dump"])
    if result.returncode != 0:
        return {}
    try:
        return json.loads(result.stdout).get(name, {})
    except (json.JSONDecodeError, KeyError):
        return {}


def update_remote(name: str, params: dict[str, str]) -> None:
    args = [RCLONE_BIN, "config", "update", name, "--obscure"]
    for key, value in params.items():
        if value:
            args += [key, value]
    result = _run(args)
    if result.returncode != 0:
        raise RcloneError(result.stderr.strip() or "rclone returned a non-zero exit code")


def get_remote_about(name: str) -> dict | None:
    import json
    result = _run([RCLONE_BIN, "about", f"{name}:", "--json"])
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


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


