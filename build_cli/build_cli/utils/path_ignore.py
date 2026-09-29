import fnmatch
import subprocess
from pathlib import Path

from .logger import get_logger

logger = get_logger()


def should_ignore_path(path: Path, patterns: list[str] | None) -> bool:
    if not patterns:
        return False

    path_str = path.as_posix()
    parts = path.parts
    name = path.name

    for pattern in patterns:
        normalized = pattern.strip()
        if not normalized:
            continue

        if fnmatch.fnmatch(path_str, normalized):
            return True

        if fnmatch.fnmatch(name, normalized):
            return True

        if normalized in parts:
            return True

        if fnmatch.fnmatch(path_str, f"{normalized}/*"):
            return True

        if fnmatch.fnmatch(path_str, f"*/{normalized}/*"):
            return True

        if fnmatch.fnmatch(path_str, f"*/{normalized}"):
            return True

    return False


def git_ignored(files: set[Path], repo_dir: Path) -> set[Path]:
    """The subset of files git ignores in repo_dir: build output and tool caches
    hold copies of every chart and Dockerfile and must not become build inputs."""
    if not files:
        return set()
    result = subprocess.run(
        ["git", "check-ignore", "-z", "--stdin"],
        input="\0".join(str(f) for f in files),
        capture_output=True,
        text=True,
        cwd=repo_dir,
    )
    # 0: some paths are ignored, 1: none is; anything else means the check did not run
    if result.returncode not in (0, 1):
        logger.warning(f"git check-ignore failed ({result.returncode}), ignoring nothing: {result.stderr.strip()}")
        return set()
    return {Path(path) for path in result.stdout.split("\0") if path}
