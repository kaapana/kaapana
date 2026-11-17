"""Which docker.io account select_docker_io_credential.py picks from DOCKER_IO_CONFIG.

A local HTTP server plays Docker Hub, so the real requests run offline. The
script's stdout is read by bash like in the jobs, and no output may contain
a token.
"""

import base64
import importlib.util
import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "ci-code" / "utils" / "select_docker_io_credential.py"


@pytest.fixture(scope="module")
def selector():
    spec = importlib.util.spec_from_file_location("select_docker_io_credential", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def hub(selector, monkeypatch):
    """Accounts as {user: {"token": ..., "remaining": int | None}}, None meaning no limit."""
    accounts = {}

    class DockerHub(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            user, _, token = (
                base64.b64decode(self.headers["Authorization"].removeprefix("Basic ")).decode().partition(":")
            )
            if accounts.get(user, {}).get("token") != token:
                self.send_response(401)
                self.end_headers()
                return
            body = json.dumps({"token": f"bearer-{user}"}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_HEAD(self):
            account = accounts[self.headers["Authorization"].removeprefix("Bearer bearer-")]
            self.send_response(200)
            if account["remaining"] is not None:
                self.send_header("ratelimit-limit", "200;w=21600")
                self.send_header("ratelimit-remaining", f"{account['remaining']};w=21600")
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), DockerHub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    monkeypatch.setattr(selector, "AUTH_URL", f"{base}/token")
    monkeypatch.setattr(selector, "RATELIMIT_URL", f"{base}/v2/ratelimitpreview/test/manifests/latest")
    yield accounts
    server.shutdown()


@pytest.fixture
def select(selector, hub, monkeypatch, capsys, tmp_path):
    """Run main() with DOCKER_IO_CONFIG, read its output in bash, return (user, password, report)."""

    def run(config, environment=None):
        monkeypatch.setattr("sys.argv", ["select_docker_io_credential.py"])
        monkeypatch.setenv("DOCKER_IO_CONFIG", config if isinstance(config, str) else json.dumps(config))
        assert selector.main() == 0
        captured = capsys.readouterr()
        script = (
            'mapfile -t docker_io <<<"$OUTPUT"\n'
            'export DOCKER_IO_USER="${docker_io[0]:-}" DOCKER_IO_PASSWORD="${docker_io[1]:-}"\n'
            'printf "%s\\n%s" "$DOCKER_IO_USER" "$DOCKER_IO_PASSWORD"'
        )
        result = subprocess.run(
            ["bash", "-c", script],
            env={"PATH": "/usr/bin:/bin", "OUTPUT": captured.out.rstrip("\n"), **(environment or {})},
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=True,
        )
        tokens = [account["token"] for account in hub.values()]
        if isinstance(config, dict):
            tokens += config.values()
        for token in tokens:
            assert token not in captured.err
        user, password = result.stdout.split("\n")
        return user, password, captured.err

    return run


def test_the_account_with_the_most_pulls_left_is_used(hub, select):
    hub.update(
        first={"token": "dckr_pat_first", "remaining": 12},
        second={"token": "dckr_pat_second", "remaining": 150},
        third={"token": "dckr_pat_third", "remaining": 40},
    )
    user, password, _ = select({name: account["token"] for name, account in hub.items()})
    assert (user, password) == ("second", "dckr_pat_second")


def test_rejected_and_exhausted_accounts_are_skipped(hub, select):
    hub.update(
        revoked={"token": "dckr_pat_current", "remaining": 200},
        exhausted={"token": "dckr_pat_exhausted", "remaining": 0},
        working={"token": "dckr_pat_working", "remaining": 3},
    )
    config = {"revoked": "dckr_pat_old", "exhausted": "dckr_pat_exhausted", "working": "dckr_pat_working"}
    user, password, report = select(config)
    assert (user, password) == ("working", "dckr_pat_working")
    assert "'revoked' was rejected" in report


def test_an_unreachable_docker_hub_means_anonymous_pulls(selector, select, monkeypatch):
    monkeypatch.setattr(selector, "AUTH_URL", "http://127.0.0.1:9/token")
    user, _, report = select({"someone": "dckr_pat_someone"}, {"DOCKER_IO_USER": "legacy"})
    assert user == ""
    assert "no account in DOCKER_IO_CONFIG is usable" in report


def test_an_account_without_a_pull_limit_wins(hub, select):
    hub.update(
        free={"token": "dckr_pat_free", "remaining": 199},
        paid={"token": "dckr_pat_paid", "remaining": None},
    )
    user, _, report = select({"free": "dckr_pat_free", "paid": "dckr_pat_paid"})
    assert user == "paid"
    assert "no pull limit" in report


def test_old_project_variables_are_dropped_without_a_usable_account(hub, select):
    hub.update(exhausted={"token": "dckr_pat_exhausted", "remaining": 0})
    user, password, _ = select(
        {"exhausted": "dckr_pat_exhausted"},
        {"DOCKER_IO_USER": "legacy", "DOCKER_IO_PASSWORD": "dckr_pat_legacy"},
    )
    assert (user, password) == ("", "")


@pytest.mark.parametrize("config", ["", "not json", "{}", '["dckr_pat_secret"]', '{"someone": ""}'])
def test_an_empty_or_malformed_config_means_anonymous_pulls(select, config):
    user, _, report = select(config, {"DOCKER_IO_USER": "legacy"})
    assert user == ""
    assert "anonymously" in report
    assert "dckr_pat_secret" not in report


def test_tokens_with_shell_characters_are_read_as_data(hub, select):
    token = "dckr_pat_'$(touch pwned)\"`;\\"
    hub.update(someone={"token": token, "remaining": 5})
    user, password, _ = select({"someone": token})
    assert (user, password) == ("someone", token)
