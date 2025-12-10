"""
Kaapana Workflow CLI - Clean, Structured, and DRY Version
"""

import json
from pathlib import Path
from typing import Optional

import click
import yaml
from rich.console import Console
from rich.table import Table

from . import container_utils, generator, git_utils, packager, validators

console = Console()


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def load_build_config(
    kaapana_dir: Path, build_config: Optional[Path], registry_prefix: Optional[str]
):
    """
    Loads build-config.yaml and resolves registry settings and container engine overrides.
    """
    config_path = None
    docker_cmd = "docker"
    registry_user = None
    registry_pass = None
    plain_http = False
    registry_url = registry_prefix

    if build_config:
        config_path = (
            (kaapana_dir / build_config).resolve()
            if not build_config.is_absolute()
            else build_config
        )
    else:
        default_cfg = kaapana_dir / "build-scripts" / "build-config.yaml"
        if default_cfg.exists():
            config_path = default_cfg

    if config_path and config_path.exists():
        try:
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}

            if not registry_url:
                registry_url = cfg.get("default_registry")

            registry_user = cfg.get("registry_username")
            registry_pass = cfg.get("registry_password")
            plain_http = bool(cfg.get("plain_http"))

            engine = cfg.get("container_engine")
            if engine and engine.lower() == "podman":
                docker_cmd = "podman"

        except Exception as e:
            console.print(f"Warning: build-config.yaml could not be read: {e}")

    return registry_url, registry_user, registry_pass, plain_http, docker_cmd


def summarize_results(results):
    ok = [r for r in results if r.get("status") == "ok"]
    errs = [r for r in results if r.get("status") == "error"]
    skipped = [r for r in results if r.get("status") == "skipped"]

    if ok:
        console.print(f"Completed: {len(ok)} items")
    if skipped:
        console.print(f"Skipped: {len(skipped)} items (no Dockerfile)")
    if errs:
        console.print(f"Errors: {len(errs)}")
        for e in errs:
            console.print(f" - {e.get('container')}: {e.get('message')}")

    return len(errs) == 0


# ---------------------------------------------------------------------------
# Top-level CLI
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(version="0.0.0")
def cli():
    """Kaapana Workflow CLI: create, validate, build, and install workflows."""
    pass


# ---------------------------------------------------------------------------
# Workflow sub-group
# ---------------------------------------------------------------------------


@cli.group()
def workflow():
    """Workflow-related commands."""
    pass


@workflow.command("ls")
@click.argument("kaapana_dir", type=click.Path(exists=True, path_type=Path), default=".")
@click.option("--format", "-f", type=click.Choice(["table", "simple"]), default="table")
def list_workflows(kaapana_dir: Path, format: str):
    """List workflows in data-processing/workflows."""
    workflows_dir = kaapana_dir / "data-processing" / "workflows"

    if not workflows_dir.exists():
        console.print("No workflows directory found")
        return

    workflows = sorted(
        [w for w in workflows_dir.iterdir() if w.is_dir()], key=lambda x: x.name.lower()
    )

    if not workflows:
        console.print("No workflows found")
        return

    if format == "simple":
        for w in workflows:
            console.print(w.name)
        return

    table = Table(title="Workflows")
    table.add_column("Name", style="cyan")
    table.add_column("Has Chart", style="green")
    table.add_column("Path", style="dim")

    for w in workflows:
        table.add_row(w.name, "yes" if (w / "workflow-chart").exists() else "no", str(w))

    console.print(table)
    console.print(f"Total: {len(workflows)} workflows")


@workflow.command("create")
@click.argument("workflow_name")
@click.option("--output", "-o", type=click.Path(path_type=Path), default=Path("."))
@click.option("--engine", "-e", type=click.Choice(["airflow", "argo", "cpp"]), default="airflow")
def create_workflow(workflow_name: str, output: Path, engine: str):
    """Create a new workflow template."""
    try:
        path = generator.create_workflow(workflow_name, output, engine.lower())
        console.print(f"Created workflow at: {path}")
    except Exception as e:
        raise click.ClickException(str(e))


@workflow.command("validate")
@click.argument("workflow_path", type=click.Path(exists=True, path_type=Path))
@click.option("--strict", is_flag=True)
def validate_workflow(workflow_path: Path, strict: bool):
    """Validate workflow structure and metadata."""
    report = validators.validate_workflow(workflow_path)

    for msg in report.info:
        console.print(f"Info: {msg}")
    for msg in report.warnings:
        console.print(f"Warning: {msg}")
    for msg in report.errors:
        console.print(f"Error: {msg}")

    if report.errors:
        raise click.ClickException("Validation failed")
    if strict and report.warnings:
        raise click.ClickException("Validation failed (strict mode)")
    console.print("Validation passed")


@workflow.command("package")
@click.argument("workflow_path", type=str)
@click.option("--output", "-o", type=click.Path(path_type=Path))
@click.option("--lint", is_flag=True)
def package_workflow_cmd(workflow_path: str, output: Path, lint: bool):
    """Package workflow into a Helm chart."""

    # Always resolve workflow names and paths
    wf = Path(workflow_path)

    # If user provides a bare name → resolve into Kaapana workflow directory
    if not wf.exists():
        candidate = Path("data-processing/workflows") / workflow_path
        if candidate.exists():
            wf = candidate
        else:
            raise click.ClickException(f"Workflow not found: {workflow_path}")

    # Normalize path so Helm never breaks
    wf = wf.resolve()

    if not packager.check_helm_installed():
        raise click.ClickException("Helm is not installed")

    if lint:
        if not packager.lint_chart(wf / "workflow-chart"):
            console.print("Lint warnings detected")

    try:
        out_file = packager.package_workflow(wf, output)
        console.print(f"Package created: {out_file}")
    except Exception as e:
        raise click.ClickException(str(e))


# ---------------------------------------------------------------------------
# Container sub-group
# ---------------------------------------------------------------------------


@cli.group()
def container():
    """Container-related commands."""
    pass


@container.command("ls")
@click.argument("kaapana_dir", type=click.Path(exists=True, path_type=Path), default=".")
@click.option("--format", "-f", type=click.Choice(["table", "simple"]), default="table")
def list_containers(kaapana_dir: Path, format: str):
    """List processing containers."""
    containers = container_utils.find_processing_containers(kaapana_dir)

    if not containers:
        console.print("No containers found")
        return

    if format == "simple":
        for c in containers:
            console.print(f"{c.name} ({c.workflow})")
        return

    table = Table(title="Containers")
    table.add_column("Container", style="cyan")
    table.add_column("Workflow", style="green")
    table.add_column("Templates", style="yellow")
    table.add_column("Files")

    for c in containers:
        templates = ", ".join(c.templates) if c.templates else "-"
        files = []
        if c.has_json:
            files.append("json")
        if c.has_dockerfile:
            files.append("Dockerfile")
        table.add_row(c.name, c.workflow, templates, ", ".join(files) or "none")

    console.print(table)
    console.print(f"Total: {len(containers)}")


def _build_or_push(
    kaapana_dir: Path,
    build: bool,
    push: bool,
    registry_prefix: Optional[str],
    docker_cmd: str,
    build_config: Optional[Path],
    workflow: Optional[str],
):
    registry_url, registry_user, registry_pass, plain_http, docker_cmd = load_build_config(
        kaapana_dir, build_config, registry_prefix
    )

    results = container_utils.build_and_push_processing_containers(
        kaapana_dir=kaapana_dir,
        build=build,
        push=push,
        registry_url=registry_url,
        docker_cmd=docker_cmd,
        registry_username=registry_user,
        registry_password=registry_pass,
        workflow=workflow,
    )

    if not summarize_results(results):
        raise click.ClickException("Some items failed")


@container.command("build")
@click.argument("kaapana_dir", type=click.Path(exists=True, path_type=Path), default=".")
@click.option("--push", is_flag=True)
@click.option("--registry-prefix", type=str)
@click.option("--docker-cmd", type=str, default="docker")
@click.option("--build-config", type=click.Path(path_type=Path))
@click.option("--workflow", type=str)
def build_containers(kaapana_dir, push, registry_prefix, docker_cmd, build_config, workflow):
    """Build (and optionally push) processing containers."""
    _build_or_push(
        kaapana_dir,
        build=True,
        push=push,
        registry_prefix=registry_prefix,
        docker_cmd=docker_cmd,
        build_config=build_config,
        workflow=workflow,
    )


@container.command("push")
@click.argument("kaapana_dir", type=click.Path(exists=True, path_type=Path), default=".")
@click.option("--registry-prefix", type=str)
@click.option("--docker-cmd", type=str, default="docker")
@click.option("--build-config", type=click.Path(path_type=Path))
@click.option("--workflow", type=str)
def push_containers(kaapana_dir, registry_prefix, docker_cmd, build_config, workflow):
    """Push already built containers."""
    _build_or_push(
        kaapana_dir,
        build=False,
        push=True,
        registry_prefix=registry_prefix,
        docker_cmd=docker_cmd,
        build_config=build_config,
        workflow=workflow,
    )


# ---------------------------------------------------------------------------
# Extension sub-group
# ---------------------------------------------------------------------------


@cli.group()
def extension():
    """Extension-building commands."""
    pass


@extension.command("build")
@click.argument("kaapana_dir", type=click.Path(exists=True, path_type=Path))
@click.option("--workflow", required=True)
@click.option("--build-config", type=click.Path(path_type=Path))
@click.option("--helm-namespace", type=str)
def build_extension(kaapana_dir, workflow, build_config, helm_namespace):
    """Build an extension workflow: build containers, package chart, and install via Helm."""
    kaapana_dir = Path(kaapana_dir)

    # ------------------------------------------------------------
    # 1) Resolve workflow name → full workflow path
    # ------------------------------------------------------------
    workflow_path = Path(workflow)

    # If the user passed only a workflow name (e.g., "registration-workflow")
    if not workflow_path.exists():
        candidate = kaapana_dir / "data-processing" / "workflows" / workflow
        if candidate.exists():
            workflow_path = candidate
        else:
            raise click.ClickException(f"Workflow path not found: {workflow}")

    workflow_path = workflow_path.resolve()
    workflow_name = workflow_path.name  # actual folder name

    # ------------------------------------------------------------
    # 2) Build + push processing containers (using resolved name)
    # ------------------------------------------------------------
    registry_url, registry_user, registry_pass, plain_http, docker_cmd = load_build_config(
        kaapana_dir, build_config, registry_prefix=None
    )

    results = container_utils.build_and_push_processing_containers(
        kaapana_dir=kaapana_dir,
        build=True,
        push=True,
        registry_url=registry_url,
        docker_cmd=docker_cmd,
        registry_username=registry_user,
        registry_password=registry_pass,
        workflow=workflow_name,  # ← FIXED (now always correct)
    )

    if not summarize_results(results):
        raise click.ClickException("Container build or push failed")

    # ------------------------------------------------------------
    # 3) Package Helm chart
    # ------------------------------------------------------------
    if not packager.check_helm_installed():
        raise click.ClickException("Helm is not installed")

    tgz = packager.package_workflow(workflow_path)

    # ------------------------------------------------------------
    # 4) Determine Helm release name
    # ------------------------------------------------------------
    release_name = workflow_name
    wf_json = workflow_path / "workflow-chart" / "files" / "workflow.json"

    if wf_json.exists():
        try:
            with open(wf_json) as f:
                release_name = json.load(f).get("title", workflow_name)
        except Exception:
            pass

    # ------------------------------------------------------------
    # 5) Build Helm command
    # ------------------------------------------------------------
    version, _, _, _ = git_utils.GitUtils.get_repo_info(kaapana_dir)

    helm_cmd = [
        "helm",
        "upgrade",
        "--install",
        release_name,
        str(tgz),
        "--set",
        "global.services_namespace=services",
        "--set",
        f"global.registry_url={registry_url}",
        "--set",
        f"global.kaapana_build_version={version}",
    ]

    if helm_namespace:
        helm_cmd.extend(["--namespace", helm_namespace])

    import subprocess

    subprocess.run(helm_cmd, check=True)

    console.print(f"Installed or updated Helm release '{release_name}'")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
