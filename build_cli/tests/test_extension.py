import json
import subprocess
from pathlib import Path
from uuid import uuid4

import pytest
from build_cli.build import BuildHelper, IssueTracker
from build_cli.container import Container
from build_cli.extension import ExtensionHelper

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


def collect(build_state) -> dict:
    ExtensionHelper.collect_extensions()
    return {extension.name: extension for extension in build_state.extensions_available}


def issue_messages() -> list[str]:
    return [issue.msg for issue in IssueTracker.issues]


def test_collects_a_valid_extension_with_its_images(kaapana_dir, build_state):
    write_extension(kaapana_dir, "registration", dag=image_line("get-input-task") + image_line("mitk-tools"))

    extensions = collect(build_state)

    assert extensions["registration-extension"].image_names == {"get-input-task", "mitk-tools"}
    assert IssueTracker.issues == []


def test_ignores_manifests_outside_the_workflows_directory(kaapana_dir, build_state):
    other = kaapana_dir / "lib" / "test-extension"
    other.mkdir(parents=True)
    (other / "extension_manifest.json").write_text("{}")

    assert collect(build_state) == {}
    assert IssueTracker.issues == []


def test_skips_git_ignored_manifests(kaapana_dir, build_state):
    subprocess.run(["git", "init", "-q", str(kaapana_dir)], check=True)
    (kaapana_dir / ".gitignore").write_text("ignored/\n")
    write_extension(kaapana_dir, "ignored")
    write_extension(kaapana_dir, "kept")

    assert set(collect(build_state)) == {"kept-extension"}


def test_skips_manifests_that_match_the_ignore_patterns(kaapana_dir, build_config, build_state):
    build_config.build_ignore_patterns = ["*/skipped/*"]
    write_extension(kaapana_dir, "skipped")
    write_extension(kaapana_dir, "kept")

    assert set(collect(build_state)) == {"kept-extension"}


@pytest.mark.parametrize(
    ("manifest_changes", "reason"),
    [
        pytest.param({"id": None}, "has no id", id="missing id"),
        pytest.param({"id": "my-extension"}, "is not a UUID", id="id is not a UUID"),
        pytest.param({"dependencies": None}, "list of dependencies", id="missing dependencies"),
        pytest.param(
            {"contents": [{"name": "broken", "contentType": "helm-chart", "files": [{"path": "workflow.json"}]}]},
            "unsupported type 'helm-chart'",
            id="unsupported content type",
        ),
        pytest.param({"version": "1.0"}, "Schema error at version", id="library schema: version is not semver"),
    ],
)
def test_rejects_invalid_manifests(kaapana_dir, build_state, manifest_changes, reason):
    manifest_path = write_extension(kaapana_dir, "broken", **manifest_changes)
    manifest_before = manifest_path.read_text()

    assert collect(build_state) == {}
    assert len(IssueTracker.issues) == 1
    assert reason in IssueTracker.issues[0].msg
    assert manifest_path.read_text() == manifest_before


def test_rejects_a_manifest_that_is_not_json(kaapana_dir, build_state):
    manifest_path = write_extension(kaapana_dir, "broken")
    manifest_path.write_text("{ not json")

    assert collect(build_state) == {}
    assert "Failed to read manifest" in issue_messages()[0]


def test_rejects_a_missing_content_file(kaapana_dir, build_state):
    manifest_path = write_extension(kaapana_dir, "broken")
    (manifest_path.parent / "broken" / "workflow.json").unlink()

    assert collect(build_state) == {}
    assert "workflow.json" in issue_messages()[0]


def test_rejects_all_extensions_with_the_same_id(kaapana_dir, build_state):
    shared_id = str(uuid4())
    write_extension(kaapana_dir, "first", id=shared_id)
    write_extension(kaapana_dir, "second", id=shared_id)
    write_extension(kaapana_dir, "other")

    assert set(collect(build_state)) == {"other-extension"}
    assert len(IssueTracker.issues) == 2
    assert all("also used by" in message for message in issue_messages())


def test_rejects_all_extensions_with_the_same_name_and_version(kaapana_dir, build_state):
    write_extension(kaapana_dir, "first", name="same-extension")
    write_extension(kaapana_dir, "second", name="same-extension")

    assert collect(build_state) == {}
    assert len(IssueTracker.issues) == 2


def test_does_not_build_images_with_a_fixed_version(kaapana_dir, build_state):
    write_extension(kaapana_dir, "pinned", dag=image_line("dummy") + image_line("external-tool", "1.2.3"))

    extension = collect(build_state)["pinned-extension"]

    assert extension.image_names == {"dummy"}
    assert extension.fixed_images == {"external-tool:1.2.3"}
    assert IssueTracker.issues == []


def test_accepts_an_extension_without_images(kaapana_dir, build_state):
    write_extension(kaapana_dir, "empty")

    extension = collect(build_state)["empty-extension"]

    assert extension.image_names == set()
    assert IssueTracker.issues == []


def test_links_containers_and_reports_unknown_images(kaapana_dir, build_state):
    write_extension(kaapana_dir, "dummy", dag=image_line("dummy") + image_line("missing"))
    build_state.containers_available = {container("dummy"), container("dummy", registry="other.example.com")}
    collect(build_state)

    ExtensionHelper.resolve_extension_containers()

    extension = next(iter(build_state.extensions_available))
    assert {c.tag for c in extension.containers} == {f"{REGISTRY}/dummy:0.7.0"}
    assert extension.unresolved_images == {"missing"}
    assert issue_messages() == ["Expected one container for the image missing, found 0."]


def test_lint_only_does_not_look_up_images(kaapana_dir, build_config, build_state):
    build_config.lint_only = True
    write_extension(kaapana_dir, "dummy", dag=image_line("dummy"))
    collect(build_state)

    ExtensionHelper.resolve_extension_containers()

    assert next(iter(build_state.extensions_available)).containers == set()
    assert IssueTracker.issues == []


@pytest.fixture
def extension_graph(kaapana_dir, build_state):
    """Extensions for dummy, for classification with a chain of two local base images, and without images."""
    base_cpu = container("base-python-cpu", registry="local-only")
    base_gpu = container("base-python-gpu", base_images=[base_cpu], registry="local-only")
    images = {
        "dummy": container("dummy"),
        "classification-task": container("classification-task", base_images=[base_gpu]),
    }
    build_state.containers_available = set(images.values()) | {base_cpu, base_gpu}
    write_extension(kaapana_dir, "dummy", dag=image_line("dummy"))
    write_extension(kaapana_dir, "classification", dag=image_line("classification-task"))
    write_extension(kaapana_dir, "empty")
    collect(build_state)
    ExtensionHelper.resolve_extension_containers()

    platform_chart = ChartStub("kaapana-admin-chart")
    build_state.charts_available = {platform_chart}
    build_state.charts_available_by_name = {platform_chart.name: platform_chart}
    build_state.build_graph = BuildHelper._build_graph(platform_chart, build_state.extensions_available)
    return images, base_cpu, base_gpu


def selected_names(build_state) -> set[str]:
    return {extension.name for extension in build_state.selected_extensions}


def test_full_build_selects_all_extensions_and_their_base_images(build_state, extension_graph):
    images, base_cpu, base_gpu = extension_graph

    BuildHelper.select_containers_to_build()

    assert build_state.selected_containers == set(images.values()) | {base_cpu, base_gpu}
    assert selected_names(build_state) == {"dummy-extension", "classification-extension", "empty-extension"}


def test_selecting_the_platform_chart_selects_the_extensions(build_config, build_state, extension_graph):
    images, base_cpu, base_gpu = extension_graph
    build_config.containers_to_build_by_charts = ["kaapana-admin-chart"]

    BuildHelper.select_containers_to_build()

    assert build_state.selected_containers == set(images.values()) | {base_cpu, base_gpu}
    assert selected_names(build_state) == {"dummy-extension", "classification-extension"}


def test_selected_containers_select_only_their_extensions(build_config, build_state, extension_graph):
    build_config.containers_to_build = ["dummy"]

    BuildHelper.select_containers_to_build()

    assert selected_names(build_state) == {"dummy-extension"}


def test_extension_with_unknown_image_is_never_selected(kaapana_dir, build_state, extension_graph):
    write_extension(kaapana_dir, "unknown", dag=image_line("dummy") + image_line("missing"))
    build_state.extensions_available.clear()
    collect(build_state)
    ExtensionHelper.resolve_extension_containers()

    BuildHelper.select_containers_to_build()

    assert "unknown-extension" not in selected_names(build_state)
    assert "dummy-extension" in selected_names(build_state)


def test_graph_has_the_whole_base_chain_of_a_container_that_a_chart_also_uses(kaapana_dir, build_state):
    base_cpu = container("base-python-cpu", registry="local-only")
    base_mitk = container("base-mitk", base_images=[base_cpu], registry="local-only")
    mitk_tools = container("mitk-tools", base_images=[base_mitk])
    build_state.containers_available = {base_cpu, base_mitk, mitk_tools}
    write_extension(kaapana_dir, "classification", dag=image_line("mitk-tools"))
    collect(build_state)
    ExtensionHelper.resolve_extension_containers()

    # The chart adds only one level of base images, and it is processed before the extensions.
    platform_chart = ChartStub("kaapana-admin-chart", chart_containers=[mitk_tools])
    graph = BuildHelper._build_graph(platform_chart, build_state.extensions_available)

    assert graph.has_edge(base_mitk, base_cpu)


def test_build_tree_lists_extensions_and_their_containers(build_state, extension_graph):
    platform_chart = next(iter(build_state.charts_available))

    tree = BuildHelper._build_tree(platform_chart, include_containers=True, extensions=build_state.extensions_available)

    labels = {node.tag for node in tree.all_nodes()}
    assert {"extensions", "dummy-extension:0.1.0", f"{REGISTRY}/classification-task:0.7.0"} <= labels
