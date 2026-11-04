import re

VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse a MAJOR.MINOR.PATCH version, the only form the extension schema allows."""
    match = VERSION_PATTERN.match(version)
    if not match:
        raise ValueError(f"Invalid extension version {version!r}, expected MAJOR.MINOR.PATCH")
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def compare_versions(a: str, b: str) -> int:
    """Return -1 if a is older than b, 0 if both are equal and 1 if a is newer."""
    parsed_a, parsed_b = parse_version(a), parse_version(b)
    return (parsed_a > parsed_b) - (parsed_a < parsed_b)
