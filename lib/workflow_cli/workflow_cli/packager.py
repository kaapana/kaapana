"""
Helm chart packager for workflows.

Requires Helm installed on the system.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Optional

import yaml
from rich.console import Console

console = Console()


def check_helm_installed() -> bool:
    """Check if helm is available."""
    return shutil.which("helm") is not None


def package_workflow(
    workflow_path: Path,
    output_dir: Optional[Path] = None,
) -> Path:
    """
    Package workflow into Helm chart .tgz.

    Args:
        workflow_path: Root workflow directory
        output_dir: Where to save .tgz (default: workflow-chart/build/)

    Returns:
        Path to generated .tgz file

    Raises:
        RuntimeError: If helm not found or packaging fails
    """

    if not check_helm_installed():
        raise RuntimeError(
            "Helm not found. Install from: https://helm.sh/docs/intro/install/"
        )

    chart_path = workflow_path / "workflow-chart"

    if not chart_path.exists():
        raise ValueError(f"workflow-chart/ not found in {workflow_path}")

    if output_dir is None:
        output_dir = chart_path / "build"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Build dependencies if needed
    _build_dependencies(chart_path)

    # Package with helm
    console.print(f"[cyan]Packaging {chart_path.name}[/cyan]")

    try:
        result = subprocess.run(
            [
                "helm",
                "package",
                str(chart_path),
                "--destination",
                str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(workflow_path),
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"helm package failed:\n{result.stdout}\n{result.stderr}"
            )

        # Find generated .tgz
        tgz_files = list(output_dir.glob("*.tgz"))
        if not tgz_files:
            raise RuntimeError("No .tgz file generated")

        output_file = max(tgz_files, key=lambda p: p.stat().st_mtime)

        console.print(f"[green]✓[/green] Packaged: {output_file.name}")
        return output_file

    except subprocess.TimeoutExpired:
        raise RuntimeError("helm package timed out")
    except Exception as e:
        raise RuntimeError(f"Packaging failed: {e}")


def lint_chart(chart_path: Path) -> bool:
    """
    Run helm lint on chart.

    Args:
        chart_path: Path to chart directory

    Returns:
        True if lint passed
    """

    if not check_helm_installed():
        console.print("[red]Helm not found[/red]")
        return False

    console.print("[cyan]Running helm lint[/cyan]")

    try:
        result = subprocess.run(
            ["helm", "lint", str(chart_path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode == 0:
            console.print("[green]✓[/green] Lint passed")
            return True
        else:
            console.print("[red]✗[/red] Lint failed:")
            console.print(result.stdout)
            console.print(result.stderr)
            return False

    except Exception as e:
        console.print(f"[red]✗[/red] Lint error: {e}")
        return False


def _build_dependencies(chart_path: Path) -> None:
    """Build chart dependencies from Chart.yaml."""

    chart_yaml_path = chart_path / "Chart.yaml"
    if not chart_yaml_path.exists():
        return

    try:
        with open(chart_yaml_path) as f:
            chart_data = yaml.safe_load(f)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not read Chart.yaml: {e}[/yellow]")
        return

    dependencies = chart_data.get("dependencies", [])
    if not dependencies:
        return

    has_local_deps = any(
        dep.get("repository", "").startswith("file://")
        for dep in dependencies
    )

    if not has_local_deps:
        return

    console.print(f"[cyan]Building {len(dependencies)} dependencies[/cyan]")

    charts_dir = chart_path / "charts"
    charts_dir.mkdir(exist_ok=True)

    for dep in dependencies:
        dep_name = dep.get("name")
        dep_repo = dep.get("repository", "")

        if not dep_repo.startswith("file://"):
            continue

        # Resolve local path
        dep_relative_path = dep_repo.replace("file://", "")
        dep_source = (chart_path / dep_relative_path).resolve()

        if not dep_source.exists():
            console.print(f"[yellow]Warning: Dependency {dep_name} not found[/yellow]")
            continue

        dep_target = charts_dir / dep_name

        console.print(f"[dim]  Copying: {dep_name}[/dim]")
        if dep_target.exists():
            shutil.rmtree(dep_target)
        shutil.copytree(dep_source, dep_target)

        # Recursively build nested deps
        _build_dependencies(dep_target)

    console.print("[green]✓[/green] Dependencies built")
