import pytest
from v1.services.versioning import compare_versions, parse_version


def test_parse_version():
    assert parse_version("1.10.3") == (1, 10, 3)


@pytest.mark.parametrize("version", ["1.0", "1.0.0-rc1", "v1.0.0", "latest", ""])
def test_parse_version_rejects_other_forms(version: str):
    with pytest.raises(ValueError):
        parse_version(version)


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("1.0.0", "1.0.0", 0),
        ("1.0.1", "1.0.0", 1),
        ("1.9.0", "1.10.0", -1),
        ("2.0.0", "1.99.99", 1),
    ],
)
def test_compare_versions(a: str, b: str, expected: int):
    assert compare_versions(a, b) == expected
