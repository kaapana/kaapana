"""
Command-line interface for Kaapana workflow development tools.
"""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import container_utils, generator, packager, validators

console = Console()


@click.group()
@click.version_option(version="0.5.0")
def cli():
    """Kaapana Workflow CLI - Create, validate, and package workflows."""
    pass


@cli.command("list-containers")
@click.argument("kaapana_dir", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "simple"], case_sensitive=False),
    default="table",
    help="Output format",
)
def list_containers(kaapana_dir: Path, format: str):
    """List all processing containers in workflows."""

    containers = container_utils.find_processing_containers(kaapana_dir)

    if not containers:
        console.print("[yellow]No processing containers found[/yellow]")
        return

    if format == "table":
        table = Table(title="Available Processing Containers")
        table.add_column("Container", style="cyan")
        table.add_column("Workflow", style="green")
        table.add_column("Templates", style="yellow")
        table.add_column("Files", style="dim")

        for c in containers:
            templates_str = ", ".join(c.templates) if c.templates else "-"
            files = []
            if c.has_json:
                files.append("json")
            if c.has_dockerfile:
                files.append("Dockerfile")
            files_str = ", ".join(files) if files else "none"

            table.add_row(c.name, c.workflow, templates_str, files_str)

        console.print(table)
        console.print(f"\n[dim]Total: {len(containers)} containers[/dim]")
    else:
        for c in containers:
            console.print(f"{c.name} ({c.workflow})")


@cli.command()
@click.argument("workflow_name")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=Path("."),
    help="Output directory for workflow",
)
@click.option(
    "--engine",
    "-e",
    type=click.Choice(["airflow", "argo", "cpp"], case_sensitive=False),
    default="airflow",
    help="Workflow engine type",
)
def create(workflow_name: str, output: Path, engine: str):
    """Create new workflow template from scratch."""

    try:
        workflow_path = generator.create_workflow(
            workflow_name=workflow_name,
            output_dir=output,
            workflow_engine=engine.lower(),
        )
        console.print(f"\n[green]✓ Created workflow at:[/green] {workflow_path}")
        console.print("\n[cyan]Next steps:[/cyan]")
        console.print(f"  1. cd {workflow_path}")
        console.print("  2. Edit workflow-chart/files/workflow.json")
        console.print("  3. Edit workflow-chart/files/workflow_definition.*")
        console.print("  4. workflow-cli validate .")

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise click.Abort()


@cli.command()
@click.argument("workflow_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--strict",
    is_flag=True,
    help="Treat warnings as errors",
)
def validate(workflow_path: Path, strict: bool):
    """Validate workflow structure and metadata."""

    console.print(f"[cyan]Validating workflow:[/cyan] {workflow_path}\n")

    report = validators.validate_workflow(workflow_path)

    # Display results
    if report.info:
        for msg in report.info:
            console.print(f"[dim]ℹ {msg}[/dim]")

    if report.warnings:
        console.print()
        for msg in report.warnings:
            console.print(f"[yellow]⚠ {msg}[/yellow]")

    if report.errors:
        console.print()
        for msg in report.errors:
            console.print(f"[red]✗ {msg}[/red]")

    # Summary
    console.print()
    if report.errors:
        console.print("[red]✗ Validation failed[/red]")
        raise click.Abort()
    elif strict and report.warnings:
        console.print("[yellow]✗ Validation failed (strict mode, warnings present)[/yellow]")
        raise click.Abort()
    else:
        console.print("[green]✓ Validation passed[/green]")


@cli.command()
@click.argument("workflow_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory for .tgz (default: workflow-chart/build/)",
)
@click.option(
    "--lint",
    is_flag=True,
    help="Run helm lint before packaging",
)
def package(workflow_path: Path, output: Path, lint: bool):
    """Package workflow into Helm chart .tgz."""

    if not packager.check_helm_installed():
        console.print("[red]✗ Helm not found[/red]")
        console.print("Install from: https://helm.sh/docs/intro/install/")
        raise click.Abort()

    # Lint first if requested
    if lint:
        chart_path = workflow_path / "workflow-chart"
        console.print("[cyan]Running lint check...[/cyan]")
        lint_passed = packager.lint_chart(chart_path)
        if not lint_passed:
            console.print("[yellow]⚠ Lint failed but continuing with packaging[/yellow]\n")

    # Package
    try:
        output_file = packager.package_workflow(workflow_path, output)
        console.print(f"\n[green]✓ Package created:[/green] {output_file}")
        console.print("\n[cyan]To install:[/cyan]")
        console.print(f"  helm install my-workflow {output_file}")
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise click.Abort()


if __name__ == "__main__":
    cli()
