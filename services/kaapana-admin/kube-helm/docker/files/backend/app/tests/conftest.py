"""Shared setup for the unit tests that run without a cluster.

The fake helm, kubectl and ctr executables record their arguments, so the tests can check
that every untrusted value reaches the tool as exactly one argument.
"""

import json
import logging
import os
import sys
import time
import types
from pathlib import Path

import pytest

# app.config reads these variables at import time.
_TEST_ENVIRONMENT = {
    "SECRET_KEY": "test",
    "APPLICATION_ROOT": "/kube-helm-api",
    "HELM_PATH": "helm",
    "HELM_NAMESPACE": "default",
    "HELM_EXTENSIONS_CACHE": "/nonexistent/extensions",
    "HELM_PLATFORMS_CACHE": "/nonexistent/platforms",
    "KAAPANA_COLLECTIONS": "",
    "REGISTRY_URL": "registry.example.com/kaapana",
    "KUBECTL_PATH": "kubectl",
    "CONTAINERD_SOCK": "/nonexistent/containerd.sock",
    "RELEASE_NAME": "kaapana-admin-chart",
}
for _name, _value in _TEST_ENVIRONMENT.items():
    os.environ.setdefault(_name, _value)

try:
    import kaapanapy.logger  # noqa: F401
except ImportError:
    # kaapanapy is only installed in the platform images.
    _logger_module = types.ModuleType("kaapanapy.logger")
    _logger_module.get_logger = lambda name, *args, **kwargs: logging.getLogger(name)
    _package = types.ModuleType("kaapanapy")
    _package.logger = _logger_module
    sys.modules["kaapanapy"] = _package
    sys.modules["kaapanapy.logger"] = _logger_module


FAKE_CLI_SOURCE = """#!@PYTHON@
import json
import os
import sys

arguments = sys.argv[1:]
with open(os.environ["FAKE_CLI_LOG"], "a") as log:
    log.write(json.dumps([os.path.basename(sys.argv[0])] + arguments) + "\\n")
with open(os.environ["FAKE_CLI_RULES"]) as rules_file:
    for rule in json.load(rules_file):
        if all(token in arguments for token in rule["when"]):
            sys.stdout.write(rule["stdout"])
            sys.exit(rule["code"])
"""

DEFAULT_CHART_YAML = "name: demo-chart\nversion: 0.1.0\nkeywords:\n- kaapanaapplication\n"

DEFAULT_RULES = [
    {"when": ["status"], "stdout": "", "code": 1},
    {"when": ["get", "values"], "stdout": "{}", "code": 0},
    {"when": ["ls"], "stdout": "[]", "code": 0},
    {"when": ["show", "chart"], "stdout": DEFAULT_CHART_YAML, "code": 0},
    {"when": ["show", "values"], "stdout": "{}", "code": 0},
    {"when": ["install"], "stdout": '{"manifest": ""}', "code": 0},
]


class FakeCli:
    def __init__(self, directory: Path):
        self.bin_dir = directory / "bin"
        self.log = directory / "calls.jsonl"
        self.rules_file = directory / "rules.json"
        self.rules = [dict(rule) for rule in DEFAULT_RULES]
        self._write_rules()

    def respond(self, when, stdout="", code=0):
        """Adds a canned answer that takes precedence over the defaults."""
        self.rules.insert(0, {"when": list(when), "stdout": stdout, "code": code})
        self._write_rules()

    def calls(self, tool="helm"):
        if not self.log.exists():
            return []
        entries = [json.loads(line) for line in self.log.read_text().splitlines()]
        return [entry[1:] for entry in entries if entry[0] == tool]

    def calls_with(self, *tokens, tool="helm"):
        return [call for call in self.calls(tool) if all(token in call for token in tokens)]

    def wait_for_calls(self, *tokens, count=1, tool="helm", timeout=10.0):
        """Waits for commands that were started in the background."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            calls = self.calls_with(*tokens, tool=tool)
            if len(calls) >= count:
                return calls
            time.sleep(0.05)
        return self.calls_with(*tokens, tool=tool)

    def _write_rules(self):
        self.rules_file.write_text(json.dumps(self.rules))


@pytest.fixture
def fake_cli(tmp_path, monkeypatch):
    from app.config import settings

    fake = FakeCli(tmp_path)
    fake.bin_dir.mkdir()
    source = FAKE_CLI_SOURCE.replace("@PYTHON@", sys.executable)
    for tool in ("helm", "kubectl", "ctr"):
        executable = fake.bin_dir / tool
        executable.write_text(source)
        executable.chmod(0o755)

    for cache in ("extensions", "platforms", "helpers", "collections"):
        (tmp_path / cache).mkdir()

    monkeypatch.setenv("FAKE_CLI_LOG", str(fake.log))
    monkeypatch.setenv("FAKE_CLI_RULES", str(fake.rules_file))
    monkeypatch.setenv("PATH", f"{fake.bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setattr(settings, "helm_path", str(fake.bin_dir / "helm"))
    monkeypatch.setattr(settings, "kubectl_path", str(fake.bin_dir / "kubectl"))
    monkeypatch.setattr(settings, "helm_extensions_cache", str(tmp_path / "extensions"))
    monkeypatch.setattr(settings, "helm_platforms_cache", str(tmp_path / "platforms"))
    monkeypatch.setattr(settings, "helm_helpers_cache", str(tmp_path / "helpers"))
    monkeypatch.setattr(settings, "helm_collections_cache", str(tmp_path / "collections"))
    return fake


@pytest.fixture
def marker(tmp_path):
    """A file that only exists if an injected command was executed."""
    return tmp_path / "injected-command-ran"


@pytest.fixture
def client(fake_cli):
    """A test client with the same middleware and router as app.main."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.middlewares import SanitizeBodyInputs, SanitizeQueryParams
    from app.routes import router

    app = FastAPI()
    app.add_middleware(SanitizeBodyInputs)
    app.add_middleware(SanitizeQueryParams)
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)
