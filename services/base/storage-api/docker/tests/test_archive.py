import io
import tarfile
import zipfile

from app.services.archive import stream_tar, stream_zip


def _collect(gen) -> bytes:
    return b"".join(gen)


def test_stream_tar_roundtrip() -> None:
    files = [("a/x.txt", b"hello"), ("a/y.bin", b"\x00\x01\x02")]
    data = _collect(stream_tar(iter(files)))
    with tarfile.open(fileobj=io.BytesIO(data), mode="r") as tar:
        assert tar.getnames() == ["a/x.txt", "a/y.bin"]
        assert tar.extractfile("a/x.txt").read() == b"hello"
        assert tar.extractfile("a/y.bin").read() == b"\x00\x01\x02"


def test_stream_zip_roundtrip() -> None:
    files = [("a/x.txt", b"hello")]
    data = _collect(stream_zip(iter(files)))
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert zf.namelist() == ["a/x.txt"]
        assert zf.read("a/x.txt") == b"hello"
