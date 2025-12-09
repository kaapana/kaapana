"""
Workflow validation - single source for all validation logic.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import ValidationError
from rich.console import Console

from .schemas import WorkflowCreate

console = Console()


# Supported UI form types
SUPPORTED_UI_FORMS = {
    "bool", "int", "float", "list", "str",
    "dataset", "data_entity", "file", "terms"
}


class ValidationReport:
    """Validation results with errors, warnings, and info messages."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def is_valid(self) -> bool:
        return len(self.errors) == 0


def validate_workflow(workflow_path: Path) -> ValidationReport:
    """
    Validate complete workflow structure and metadata.

    Checks:
    - Folder structure (workflow-chart/, files/, templates/)
    - Chart.yaml exists and has required fields
    - workflow.json exists and is valid
    - Workflow parameters have supported UI forms
    - Labels structure
    - Icon file presence

    Args:
        workflow_path: Root workflow directory

    Returns:
        ValidationReport with all findings
    """

    report = ValidationReport()
    chart_path = workflow_path / "workflow-chart"

    # Check folder structure
    structure_valid = _check_structure(chart_path, report)
    if not structure_valid:
        return report

    # Check Chart.yaml
    _check_chart_yaml(chart_path, report)

    # Check values.yaml
    _check_values_yaml(chart_path, report)

    # Check workflow.json
    workflow_json_path = chart_path / "files" / "workflow.json"
    if workflow_json_path.exists():
        _check_workflow_json(workflow_json_path, report)
    else:
        report.errors.append("workflow.json not found in workflow-chart/files/")

    # Check workflow definition exists
    _check_workflow_definition(chart_path, report)

    # Cross-check: containers used in workflow vs declared in values.yaml
    _check_containers_usage(chart_path, report)

    # Check icon
    _check_icon(chart_path, report)

    return report


def validate_workflow_data(metadata: Dict, definition: str) -> tuple[Optional[WorkflowCreate], List[str]]:
    """
    Validate workflow data against pydantic schema.

    Args:
        metadata: Parsed workflow.json content
        definition: Workflow definition code

    Returns:
        Tuple of (WorkflowCreate object or None, list of error messages)
    """

    errors = []

    try:
        workflow_data = WorkflowCreate(
            title=metadata.get("title"),
            definition=definition,
            workflow_engine=metadata.get("workflow_engine", "airflow"),
            workflow_parameters=metadata.get("workflow_parameters", []),
            labels=metadata.get("labels", []),
        )
        return workflow_data, []
    except ValidationError as e:
        for error in e.errors():
            loc = " -> ".join(str(part) for part in error["loc"])
            errors.append(f"{loc}: {error['msg']}")
        return None, errors


def _check_structure(chart_path: Path, report: ValidationReport) -> bool:
    """Check required folder structure exists."""

    if not chart_path.exists():
        report.errors.append("workflow-chart/ directory not found")
        return False

    files_dir = chart_path / "files"
    templates_dir = chart_path / "templates"

    missing = []
    if not files_dir.exists():
        missing.append("workflow-chart/files/")
    if not templates_dir.exists():
        missing.append("workflow-chart/templates/")

    if missing:
        report.errors.append(f"Missing required directories: {', '.join(missing)}")
        return False

    report.info.append("Folder structure correct")
    return True


def _check_chart_yaml(chart_path: Path, report: ValidationReport) -> None:
    """Validate Chart.yaml."""

    chart_yaml_path = chart_path / "Chart.yaml"
    if not chart_yaml_path.exists():
        report.errors.append("Chart.yaml not found in workflow-chart/")
        return

    try:
        with open(chart_yaml_path) as f:
            chart_data = yaml.safe_load(f)
    except Exception as e:
        report.errors.append(f"Chart.yaml is not valid YAML: {e}")
        return

    required = ["name", "version", "apiVersion"]
    missing = [f for f in required if f not in chart_data]

    if missing:
        report.errors.append(f"Chart.yaml missing: {', '.join(missing)}")
    
    # Check for kaapanaworkflow-v2 keyword
    keywords = chart_data.get("keywords", [])
    if "kaapanaworkflow-v2" not in keywords:
        report.errors.append(
            "Chart.yaml must have 'kaapanaworkflow-v2' in keywords. "
            "Only workflow-v2 format is supported."
        )
    
    if not missing:
        report.info.append("Chart.yaml valid")


def _check_values_yaml(chart_path: Path, report: ValidationReport) -> None:
    """Validate values.yaml structure and processingContainers."""

    values_yaml_path = chart_path / "values.yaml"
    if not values_yaml_path.exists():
        report.errors.append("values.yaml not found")
        return

    try:
        with open(values_yaml_path) as f:
            values_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        report.errors.append(f"values.yaml is not valid YAML: {e}")
        return

    # Check processingContainers exists
    if "processingContainers" not in values_data:
        report.errors.append(
            "values.yaml must have 'processingContainers' field. "
            "Can be empty list [] but must be present."
        )
        return

    processing_containers = values_data.get("processingContainers", [])
    
    if not isinstance(processing_containers, list):
        report.errors.append("processingContainers must be a list")
        return

    # Check for duplicates
    if processing_containers:
        seen = set()
        duplicates = set()
        for container in processing_containers:
            if container in seen:
                duplicates.add(container)
            seen.add(container)
        
        if duplicates:
            for dup in sorted(duplicates):
                report.errors.append(
                    f"Duplicate container '{dup}' in processingContainers. "
                    "Each container should be listed only once."
                )

    if processing_containers:
        report.info.append(f"values.yaml: {len(processing_containers)} processing containers declared")
    else:
        report.info.append("values.yaml: no processing containers (empty list)")


def _check_workflow_json(workflow_json_path: Path, report: ValidationReport) -> None:
    """Validate workflow.json structure."""

    try:
        with open(workflow_json_path) as f:
            metadata = json.load(f)
    except Exception as e:
        report.errors.append(f"workflow.json is not valid JSON: {e}")
        return

    # Check required fields
    if not metadata.get("title"):
        report.errors.append("workflow.json must have 'title'")

    if not metadata.get("workflow_engine"):
        report.warnings.append("workflow.json should specify 'workflow_engine'")

    # Validate parameters
    params = metadata.get("workflow_parameters", [])
    _validate_parameters(params, report)

    # Validate labels
    labels = metadata.get("labels", [])
    _validate_labels(labels, report)

    report.info.append(f"workflow.json: {len(params)} parameters, {len(labels)} labels")


def _validate_parameters(params: List[Dict], report: ValidationReport) -> None:
    """Validate workflow parameters."""

    for idx, param in enumerate(params):
        param_name = param.get("env_variable_name", f"param_{idx}")

        if "task_title" not in param:
            report.errors.append(f"Parameter '{param_name}' missing 'task_title'")

        if "env_variable_name" not in param:
            report.errors.append(f"Parameter {idx} missing 'env_variable_name'")

        if "ui_form" not in param:
            report.errors.append(f"Parameter '{param_name}' missing 'ui_form'")
            continue

        ui_form = param["ui_form"]
        form_type = ui_form.get("type")

        if not form_type:
            report.errors.append(f"Parameter '{param_name}' ui_form missing 'type'")
        elif form_type not in SUPPORTED_UI_FORMS:
            supported_list = ", ".join(sorted(SUPPORTED_UI_FORMS))
            report.errors.append(
                f"Parameter '{param_name}' has unsupported ui_form type: '{form_type}'. "
                f"Supported: {supported_list}"
            )

        required_ui_fields = ["title", "description"]
        missing = [f for f in required_ui_fields if f not in ui_form]
        if missing:
            report.warnings.append(
                f"Parameter '{param_name}' ui_form should have: {', '.join(missing)}"
            )


def _validate_labels(labels: List[Dict], report: ValidationReport) -> None:
    """Validate labels structure."""

    required_keys = {"provider", "category"}
    label_keys = {label.get("key") for label in labels if "key" in label}

    missing = required_keys - label_keys
    if missing:
        report.warnings.append(f"Missing recommended labels: {', '.join(missing)}")

    for idx, label in enumerate(labels):
        if "key" not in label or "value" not in label:
            report.errors.append(f"Label {idx} must have 'key' and 'value'")


def _check_workflow_definition(chart_path: Path, report: ValidationReport) -> None:
    """Check workflow definition files exist."""

    files_dir = chart_path / "files"
    definition_files = [
        f for f in files_dir.iterdir()
        if f.is_file() and f.name != "workflow.json"
    ]

    if not definition_files:
        report.errors.append(
            "No workflow definition files found in workflow-chart/files/. "
            "Expected .py, .yaml, or other workflow file."
        )
    else:
        report.info.append(f"Found {len(definition_files)} definition file(s)")


def _check_icon(chart_path: Path, report: ValidationReport) -> None:
    """Check for icon file."""

    icon_extensions = {".png", ".svg", ".jpg", ".jpeg"}
    chart_files = list(chart_path.glob("*"))

    icon_files = [
        f for f in chart_files
        if f.is_file() and f.suffix.lower() in icon_extensions
    ]

    if not icon_files:
        extensions_str = ", ".join(icon_extensions)
        report.warnings.append(f"No icon file found. Consider adding: {extensions_str}")
    else:
        report.info.append(f"Icon file: {icon_files[0].name}")


def _extract_containers_from_workflow_definition(files_dir: Path) -> set:
    """
    Extract container image names from workflow definition files.
    
    Looks for patterns like:
    - image=f"{DEFAULT_REGISTRY}/container-name:..."
    - image="registry/container-name:tag"
    """
    import re
    
    containers = set()
    
    # Pattern to match image definitions in workflow files
    # Matches: image=f"{DEFAULT_REGISTRY}/container-name:..." or image="registry/container-name:..."
    pattern = re.compile(r'image\s*=\s*f?["\'].*?/([^:/\'"]+)[:"\']', re.MULTILINE)
    
    for definition_file in files_dir.iterdir():
        if definition_file.name == "workflow.json" or not definition_file.is_file():
            continue
            
        try:
            with open(definition_file, 'r') as f:
                content = f.read()
                matches = pattern.findall(content)
                containers.update(matches)
        except (OSError, UnicodeDecodeError):
            continue
    
    return containers


def _check_containers_usage(chart_path: Path, report: ValidationReport) -> None:
    """
    Check that containers used in workflow definition are declared in values.yaml
    and that declared containers (Dockerfile) actually exist in processing-containers/ directory.
    """
    workflow_path = chart_path.parent
    files_dir = chart_path / "files"
    values_yaml_path = chart_path / "values.yaml"
    processing_containers_dir = workflow_path / "processing-containers"
    
    if not values_yaml_path.exists():
        return
    
    try:
        with open(values_yaml_path) as f:
            values_data = yaml.safe_load(f)
    except yaml.YAMLError:
        return
    
    declared_containers = set(values_data.get("processingContainers", []))
    used_containers = _extract_containers_from_workflow_definition(files_dir)
    
    # Get containers that actually exist in processing-containers/
    existing_containers = set()
    if processing_containers_dir.exists():
        for container_dir in processing_containers_dir.iterdir():
            if not container_dir.is_dir():
                continue
            
            # Check for Dockerfile to get actual image name
            dockerfile = container_dir / "Dockerfile"
            if dockerfile.exists():
                try:
                    with open(dockerfile) as f:
                        for line in f:
                            if line.strip().startswith("LABEL IMAGE="):
                                image_name = line.split("=", 1)[1].strip().strip('"')
                                existing_containers.add(image_name)
                                break
                except OSError:
                    pass
    
    if not used_containers:
        if declared_containers:
            report.warnings.append(
                f"processingContainers declares {len(declared_containers)} container(s) "
                "but workflow definition doesn't seem to use any"
            )
        return
    
    # Check each used container is declared
    undeclared = used_containers - declared_containers
    if undeclared:
        for container in sorted(undeclared):
            report.errors.append(
                f"Container '{container}' used in workflow but not declared in "
                f"processingContainers in values.yaml"
            )
    
    # Check declared containers actually exist
    for container in sorted(declared_containers):
        if container not in existing_containers:
            report.errors.append(
                f"Container '{container}' declared in processingContainers but not found in "
                f"processing-containers/ directory. Add Dockerfile with LABEL IMAGE=\"{container}\""
            )
    
    # Check declared containers are used
    unused = declared_containers - used_containers
    if unused:
        for container in sorted(unused):
            report.warnings.append(
                f"Container '{container}' declared in processingContainers "
                f"but not used in workflow definition"
            )
    
    # Info about matches
    used_and_declared = used_containers & declared_containers & existing_containers
    if used_and_declared:
        report.info.append(
            f"Container usage validated: {len(used_and_declared)} container(s) properly declared and implemented"
        )
