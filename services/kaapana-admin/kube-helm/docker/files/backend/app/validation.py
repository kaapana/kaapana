"""Checks for values that become arguments of helm and ctr commands.

Each check returns the value unchanged or raises InvalidValueError. The rules follow the names that
helm and Kubernetes accept, so the values of legitimate requests pass.
"""

import re
from pathlib import Path
from typing import List

# Helm's own rule for release names.
RELEASE_NAME_PATTERN = re.compile(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*")
RELEASE_NAME_MAX_LENGTH = 53

# Namespaces are DNS-1123 labels.
NAMESPACE_PATTERN = re.compile(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?")
NAMESPACE_MAX_LENGTH = 63

# Kaapana charts also use upper case letters and underscores in their names.
CHART_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")

# Helm reads chart versions with this pattern, so every chart that helm can install matches it.
CHART_VERSION_PATTERN = re.compile(
    r"v?[0-9]+(\.[0-9]+)?(\.[0-9]+)?(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?"
)

# Helm splits --set arguments at commas and equal signs, so keys must not contain them.
SET_KEY_PATTERN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.\-/\[\]\\]*")

# Keywords become the names of Kubernetes labels.
LABEL_NAME_PATTERN = re.compile(r"([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9]")
LABEL_NAME_MAX_LENGTH = 63

DELETE_COMMAND_ADDONS = {"": [], "--no-hooks": ["--no-hooks"]}


class InvalidValueError(ValueError):
    """A value that must not reach helm or ctr."""


def _check(value, pattern: re.Pattern, max_length: int, message: str) -> str:
    if not isinstance(value, str) or len(value) > max_length or pattern.fullmatch(value) is None:
        raise InvalidValueError(message)
    return value


def is_release_name(value) -> bool:
    try:
        check_release_name(value)
    except InvalidValueError:
        return False
    return True


def check_release_name(value) -> str:
    return _check(
        value,
        RELEASE_NAME_PATTERN,
        RELEASE_NAME_MAX_LENGTH,
        "Invalid release name. Use lower case letters, digits, '-' and '.', at most 53 characters.",
    )


def check_namespace(value) -> str:
    return _check(
        value,
        NAMESPACE_PATTERN,
        NAMESPACE_MAX_LENGTH,
        "Invalid namespace. Use lower case letters, digits and '-', at most 63 characters.",
    )


def check_chart_name(value) -> str:
    message = "Invalid chart name. Use letters, digits, '_', '-' and '.'."
    _check(value, CHART_NAME_PATTERN, 253, message)
    if ".." in value:
        raise InvalidValueError(message)
    return value


def check_chart_version(value) -> str:
    return _check(value, CHART_VERSION_PATTERN, 253, "Invalid chart version. Use a semantic version.")


def check_set_key(value) -> str:
    return _check(
        value,
        SET_KEY_PATTERN,
        253,
        "Invalid value key. Use letters, digits and '_', '-', '.', '/', '[', ']', '\\'.",
    )


def check_keyword(value) -> str:
    return _check(
        value,
        LABEL_NAME_PATTERN,
        LABEL_NAME_MAX_LENGTH,
        "Invalid chart keyword. Use letters, digits, '-', '_' and '.', at most 63 characters.",
    )


def check_file_name(value) -> str:
    if not isinstance(value, str) or value in ("", ".", "..") or "/" in value or "\0" in value:
        raise InvalidValueError("Invalid file name. Use a file name without a directory.")
    return value


def check_path_inside(path, directory) -> str:
    if not Path(path).resolve().is_relative_to(Path(directory).resolve()):
        raise InvalidValueError("Invalid path. The file must be inside its cache directory.")
    return str(path)


def check_delete_addons(value) -> List[str]:
    """Returns the extra uninstall arguments for one of the values that the clients send."""
    if not isinstance(value, str) or value not in DELETE_COMMAND_ADDONS:
        raise InvalidValueError("Invalid helm_command_addons. Use '' or '--no-hooks'.")
    return list(DELETE_COMMAND_ADDONS[value])
