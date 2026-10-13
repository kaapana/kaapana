"""Builders for extension directories and containers in the build_cli tests."""

import json
from pathlib import Path
from uuid import uuid4

from build_cli.container import Container

REGISTRY = "registry.example.com/kaapana"


def image_line(image: str, version: str = "{KAAPANA_BUILD_VERSION}") -> str:
    return f'        image=f"{{DEFAULT_REGISTRY}}/{image}:{version}",\n'


def write_extension(kaapana_dir: Path, workflow: str, dag: str = "", **manifest_changes) -> Path:
    extension_dir = kaapana_dir / "data-processing" / "workflows" / workflow / f"{workflow}-extension"
    content_dir = extension_dir / workflow
    content_dir.mkdir(parents=True)
    (content_dir / "workflow_definition.py").write_text(dag)
    (content_dir / "workflow.json").write_text("{}")
    manifest = {
        "name": f"{workflow}-extension",
        "version": "0.1.0",
        "id": str(uuid4()),
        "contents": [
            {
                "name": workflow,
                "contentType": "workflow-v1",
                "files": [{"path": "workflow_definition.py"}, {"path": "workflow.json"}],
            }
        ],
        "dependencies": [],
    }
    for key, value in manifest_changes.items():
        if value is None:
            manifest.pop(key)
        else:
            manifest[key] = value
    manifest_path = extension_dir / "extension_manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return manifest_path


def container(name: str, base_images=(), registry: str = REGISTRY) -> Container:
    local = registry == "local-only"
    version = "latest" if local else "0.7.0"
    return Container(
        dockerfile=Path(name) / "Dockerfile",
        registry=registry,
        image_name=name,
        version=version,
        tag=f"{registry}/{name}:{version}",
        base_images=set(base_images),
        local_image=local,
    )


class ChartStub:
    def __init__(self, name: str, chart_containers=()):
        self.name = name
        self.chart_dependencies = []
        self.kaapana_collections = []
        self.chart_containers = set(chart_containers)
