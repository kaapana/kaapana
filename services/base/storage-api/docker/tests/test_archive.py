import io
import tarfile
import zipfile

import pytest
from app.services.archive import stream_tar, stream_zip


def _collect(gen) -> bytes:
    return b"".join(gen)


def _member(name: str, content: bytes, chunk_size: int | None = None):
    """Build a ``(name, size, chunks)`` member; optionally split into chunks."""
    if chunk_size is None:
        chunks = iter([content])
    else:
        chunks = iter(content[i : i + chunk_size] for i in range(0, len(content), chunk_size))
    return (name, len(content), chunks)


def test_stream_tar_roundtrip() -> None:
    files = [_member("a/x.txt", b"hello"), _member("a/y.bin", b"\x00\x01\x02")]
    data = _collect(stream_tar(iter(files)))
    with tarfile.open(fileobj=io.BytesIO(data), mode="r") as tar:
        assert tar.getnames() == ["a/x.txt", "a/y.bin"]
        assert tar.extractfile("a/x.txt").read() == b"hello"
        assert tar.extractfile("a/y.bin").read() == b"\x00\x01\x02"


def test_stream_tar_multi_chunk_member_crosses_block_boundary() -> None:
    # Padding after a multi-chunk member must keep the next header block-aligned.
    big = _member("big.bin", b"a" * 1000 + b"b" * 1000, chunk_size=300)
    small = _member("small.txt", b"end")
    data = _collect(stream_tar(iter([big, small])))
    with tarfile.open(fileobj=io.BytesIO(data), mode="r") as tar:
        assert tar.getnames() == ["big.bin", "small.txt"]
        assert tar.extractfile("big.bin").read() == b"a" * 1000 + b"b" * 1000
        assert tar.extractfile("small.txt").read() == b"end"


def test_stream_tar_pulls_members_lazily() -> None:
    # Only one member's bytes may be resident: m2 must not start while m1 is in flight.
    order: list[str] = []

    def _chunks(tag: str, payload: bytes):
        order.append(f"start:{tag}")
        yield payload
        order.append(f"end:{tag}")

    files = [
        ("m1", 3, _chunks("m1", b"aaa")),
        ("m2", 3, _chunks("m2", b"bbb")),
    ]
    gen = stream_tar(iter(files))
    next(gen)  # m1 header — chunks not pulled yet
    assert order == []
    next(gen)  # m1 first chunk
    assert order == ["start:m1"]
    assert "start:m2" not in order  # m2 untouched while m1 is in flight


def test_stream_tar_long_name_round_trips_via_pax() -> None:
    name = "e1/" + "ä" * 10 + "x" * 160 + "/nested/file.bin"
    data = _collect(stream_tar(iter([_member(name, b"payload")])))
    with tarfile.open(fileobj=io.BytesIO(data), mode="r") as tar:
        assert tar.getnames() == [name]
        assert tar.extractfile(name).read() == b"payload"


def test_stream_tar_zero_members_is_valid_empty_archive() -> None:
    data = _collect(stream_tar(iter([])))
    with tarfile.open(fileobj=io.BytesIO(data), mode="r") as tar:
        assert tar.getnames() == []


def test_stream_tar_rejects_size_mismatch() -> None:
    bad = [("x", 10, iter([b"short"]))]  # declared 10, only 5 bytes streamed
    with pytest.raises(ValueError, match="declared size 10"):
        _collect(stream_tar(iter(bad)))


def test_stream_zip_roundtrip() -> None:
    files = [_member("a/x.txt", b"hello")]
    data = _collect(stream_zip(iter(files)))
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert zf.namelist() == ["a/x.txt"]
        assert zf.read("a/x.txt") == b"hello"
