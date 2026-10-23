import io
import logging
import socket
import tarfile
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from kaapana_containers.kubernetes.utils import KubernetsUtils
from kubernetes import client
from kubernetes.stream.ws_client import STDERR_CHANNEL, STDOUT_CHANNEL
from websocket import ABNF

FILE_PATH = "/processing-container.json"
# The tar header of the single member takes the first 512 bytes of the stream.
TAR_HEADER_SIZE = 512


class _FakeWebsocket:
    """Replays exec frames to the real WSClient of the kubernetes client."""

    def __init__(self, frames: list[tuple[int, bytes]]):
        self._frames = list(frames)
        # WSClient polls the socket before it reads a frame, so the socket must stay readable.
        self._reader, self._writer = socket.socketpair()
        self._writer.send(b"x")
        self.sock = self._reader
        self.connected = True
        self.subprotocol = "v4.channel.k8s.io"

    def recv_data_frame(self, control_frame: bool):
        if not self._frames:
            self.connected = False
            return ABNF.OPCODE_CLOSE, SimpleNamespace(data=b"")
        channel, data = self._frames.pop(0)
        return ABNF.OPCODE_BINARY, SimpleNamespace(data=bytes([channel]) + data)

    def close(self, **kwargs):
        self.connected = False
        self._reader.close()
        self._writer.close()


def _tar_of(content: bytes) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:", format=tarfile.GNU_FORMAT) as tar:
        info = tarfile.TarInfo(FILE_PATH.lstrip("/"))
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


def _stdout_frames(data: bytes, frame_size: int) -> list[tuple[int, bytes]]:
    return [(STDOUT_CHANNEL, data[i : i + frame_size]) for i in range(0, len(data), frame_size)]


@pytest.fixture
def exec_frames():
    """Serve the frames that a test adds to the yielded list as the exec output of the helper pod."""
    frames = []
    running_pod = SimpleNamespace(status=SimpleNamespace(phase="Running"))
    with (
        patch("kaapana_containers.kubernetes.utils.config.load_config"),
        patch.object(client.CoreV1Api, "create_namespaced_pod"),
        patch.object(client.CoreV1Api, "read_namespaced_pod", return_value=running_pod),
        patch.object(client.CoreV1Api, "delete_namespaced_pod"),
        patch(
            "kubernetes.stream.ws_client.create_websocket",
            side_effect=lambda *args, **kwargs: _FakeWebsocket(frames),
        ),
    ):
        yield frames


def _extract() -> bytes:
    with KubernetsUtils.extract_file_from_image("registry.example.com/image:tag", FILE_PATH) as f:
        return f.read()


class TestExtractFileFromImage:
    def test_keeps_multibyte_character_across_frames(self, exec_frames):
        content = '{"description": "Größe"}\n'.encode()
        boundary = TAR_HEADER_SIZE + content.index("ö".encode()) + 1
        exec_frames.extend(_stdout_frames(_tar_of(content), boundary))

        assert _extract() == content

    def test_keeps_bytes_that_are_not_utf8(self, exec_frames):
        content = bytes(range(256))
        exec_frames.extend(_stdout_frames(_tar_of(content), 10240))

        assert _extract() == content

    def test_logs_stderr_as_text(self, exec_frames, caplog):
        content = b"{}\n"
        exec_frames.append((STDERR_CHANNEL, b"tar: warning\n"))
        exec_frames.extend(_stdout_frames(_tar_of(content), 10240))

        with caplog.at_level(logging.INFO, logger="kaapana_containers.kubernetes.utils"):
            assert _extract() == content

        assert "[stderr]: tar: warning" in caplog.text
