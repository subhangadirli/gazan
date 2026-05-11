import subprocess

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


