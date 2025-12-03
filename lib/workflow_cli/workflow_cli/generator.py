"""
Template generator for creating new workflow scaffolding.
"""

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from rich.console import Console

console = Console()


SUPPORTED_ENGINES = ["airflow", "argo", "cpp"]


def create_workflow(
    workflow_name: str,
    output_dir: Path,
    workflow_engine: str = "airflow"
) -> Path:
    """
    Create new workflow template from scratch.

    Args:
        workflow_name: Name for workflow (e.g., "my-workflow")
        output_dir: Where to create workflow directory
        workflow_engine: Engine type (airflow, argo, cpp)

    Returns:
        Path to created workflow directory
    """

    if workflow_engine not in SUPPORTED_ENGINES:
        supported = ", ".join(SUPPORTED_ENGINES)
        raise ValueError(
            f"Unsupported workflow engine: {workflow_engine}. "
            f"Supported: {supported}"
        )

    # Clean directory name
    safe_name = workflow_name.lower().replace(" ", "-").replace("_", "-")
    workflow_path = output_dir / safe_name

    if workflow_path.exists():
        raise ValueError(f"Workflow directory already exists: {workflow_path}")

    # Create structure
    console.print(f"Creating workflow: {safe_name}")
    workflow_path.mkdir(parents=True, exist_ok=True)

    chart_path = workflow_path / "workflow-chart"
    chart_path.mkdir(exist_ok=True)
    (chart_path / "files").mkdir(exist_ok=True)
    (chart_path / "templates").mkdir(exist_ok=True)

    # Load templates
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))

    # Template context
    context = {
        "workflow_name": safe_name,
        "workflow_display_name": workflow_name.title(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "version": "0.1.0",
        "workflow_engine": workflow_engine,
    }

    # Generate files
    _generate_chart_files(env, context, chart_path)
    _generate_readme(env, context, workflow_path)

    console.print(f"[green]✓[/green] Workflow created at: {workflow_path}")
    return workflow_path


def _generate_chart_files(env: Environment, context: dict, chart_path: Path) -> None:
    """Generate Helm chart files."""

    files_to_create = [
        ("Chart.yaml.j2", chart_path / "Chart.yaml"),
        ("values.yaml.j2", chart_path / "values.yaml"),
        ("workflow.json.j2", chart_path / "files" / "workflow.json"),
        ("configmap.yaml.j2", chart_path / "templates" / "configmap.yaml"),
        ("job.yaml.j2", chart_path / "templates" / "job.yaml"),
    ]

    # Add workflow definition based on engine
    engine = context["workflow_engine"]
    definition_templates = {
        "airflow": ("files/demo_workflow_airflow.py", ".py"),
        "argo": ("files/demo_workflow_argo.yaml", ".yaml"),
        "cpp": ("files/demo_workflow_cpp.cpp", ".cpp"),
    }

    if engine in definition_templates:
        template_file, ext = definition_templates[engine]
        files_to_create.append(
            (template_file, chart_path / "files" / f"workflow_definition{ext}")
        )

    for template_name, output_path in files_to_create:
        try:
            template = env.get_template(template_name)
            content = template.render(**context)
            output_path.write_text(content)
            console.print(f"[dim]  Created: {output_path.name}[/dim]")
        except Exception as e:
            console.print(f"[yellow]  Warning: Could not generate {template_name}: {e}[/yellow]")


def _generate_readme(env: Environment, context: dict, workflow_path: Path) -> None:
    """Generate README.md."""

    try:
        template = env.get_template("README.md.j2")
        content = template.render(**context)
        readme_path = workflow_path / "README.md"
        readme_path.write_text(content)
        console.print("[dim]  Created: README.md[/dim]")
    except Exception as e:
        console.print(f"[yellow]  Warning: Could not generate README: {e}[/yellow]")
