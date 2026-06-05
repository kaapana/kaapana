import fnmatch
from pathlib import Path


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
