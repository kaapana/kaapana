"""
Structural guard for the dev-code-server AI assistant.

Every Ollama model the chart configures for Continue must be baked into the ollama
image: offline platforms cannot pull a model at runtime, so a model named only in
the chart leaves chat or autocomplete silently broken.

No cluster, no network required.

Run from anywhere:
    pytest services/applications/dev-code-server/tests/test_ollama_models.py
"""

import re
from pathlib import Path


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "platforms").is_dir() and (parent / "services").is_dir():
            return parent
    raise RuntimeError("repo root not found")


ROOT = _repo_root()

DEV_CODE_SERVER = ROOT / "services/applications/dev-code-server"
VALUES = DEV_CODE_SERVER / "dev-code-server-chart/values.yaml"
OLLAMA_DOCKERFILE = ROOT / "services/base/ollama/docker/Dockerfile"


def _read(path: Path) -> str:
    assert path.is_file(), f"expected file is missing: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def test_configured_models_are_preloaded_in_ollama_image():
    configured = re.findall(
        r'^\s*ollama_(?:autocomplete_)?model:\s*"([^"]+)"', _read(VALUES), re.M
    )
    preload = re.search(
        r'ARG OLLAMA_PRELOAD_MODELS="([^"]*)"', _read(OLLAMA_DOCKERFILE)
    )
    assert len(configured) == 2, "values.yaml must name chat and autocomplete models"
    assert preload, "ollama Dockerfile must declare OLLAMA_PRELOAD_MODELS"
    missing = set(configured) - set(preload.group(1).split())
    assert not missing, f"configured but not baked into the ollama image: {missing}"
