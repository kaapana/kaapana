from uuid import UUID

import pytest

from app.services.entity_query import (
    QueryTranslationError,
    _coerce_bool,
    _coerce_uuid,
    _normalize_storage_type,
    _parse_metadata_field,
    _sequence_from_value,
)


def test_parse_metadata_field_requires_key() -> None:
    with pytest.raises(QueryTranslationError):
        _parse_metadata_field("metadata.")


def test_parse_metadata_field_parses_path_segments() -> None:
    parsed = _parse_metadata_field("metadata.acquisition.details.series")
    assert parsed.key == "acquisition"
    assert parsed.path == ("details", "series")


def test_coerce_uuid_accepts_string_values() -> None:
    raw = "12345678-1234-5678-1234-567812345678"
    value = _coerce_uuid(raw)
    assert isinstance(value, UUID)
    assert str(value) == raw


def test_coerce_uuid_rejects_invalid_strings() -> None:
    with pytest.raises(QueryTranslationError):
        _coerce_uuid("not-a-uuid")


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("true", True),
        ("FALSE", False),
        ("1", True),
        ("0", False),
    ],
)
def test_coerce_bool_normalizes_common_strings(raw: str, expected: bool) -> None:
    assert _coerce_bool(raw) is expected


def test_normalize_storage_type_lowercases_and_trims() -> None:
    assert _normalize_storage_type("  S3  ") == "s3"


def test_sequence_from_value_handles_scalars_and_lists() -> None:
    assert _sequence_from_value("abc") == ["abc"]
    assert _sequence_from_value([1, 2]) == [1, 2]
    assert _sequence_from_value(None) == []
