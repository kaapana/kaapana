"""
Validation rules for workflow metadata.

Configurable rules to enforce workflow standards and best practices.
"""

from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ValidationRule(BaseModel):
    """Base class for validation rules."""

    enabled: bool = True
    severity: str = Field(
        default="error", description="error, warning, or info"
    )  # error, warning, info


class RequiredLabelsRule(ValidationRule):
    """Validate that specific labels are present."""

    required_labels: List[str] = Field(
        default_factory=list, description="List of required label keys"
    )


class IconFileRule(ValidationRule):
    """Validate that an icon file exists in the workflow directory."""

    icon_filename: str = Field(default="icon.png", description="Expected icon filename")
    allowed_extensions: List[str] = Field(
        default_factory=lambda: [".png", ".svg", ".jpg", ".jpeg"],
        description="Allowed icon file extensions",
    )


class WorkflowEngineRule(ValidationRule):
    """Validate that workflow_engine is one of the allowed values."""

    allowed_engines: Optional[List[str]] = Field(
        default=None,
        description="List of allowed workflow engines. If None, auto-discover from adapters.",
    )
    adapters_path: Optional[Path] = Field(
        default=None,
        description="Path to adapters directory for auto-discovery",
    )


class ValidationConfig(BaseModel):
    """Configuration for all validation rules."""

    required_labels: RequiredLabelsRule = Field(
        default_factory=lambda: RequiredLabelsRule(
            enabled=True, required_labels=["provider", "category"], severity="error"
        )
    )
    icon_file: IconFileRule = Field(
        default_factory=lambda: IconFileRule(enabled=True, severity="warning")
    )
    workflow_engine: WorkflowEngineRule = Field(
        default_factory=lambda: WorkflowEngineRule(enabled=True, severity="error")
    )


class ValidationResult(BaseModel):
    """Result of a validation check."""

    rule_name: str
    severity: str
    passed: bool
    message: str


class WorkflowValidator:
    """Validator for workflow metadata and files."""

    def __init__(self, config: Optional[ValidationConfig] = None):
        self.config = config or ValidationConfig()
        self.results: List[ValidationResult] = []

    def validate_required_labels(
        self, labels: List[Dict[str, str]]
    ) -> ValidationResult:
        """Check if required labels are present."""
        rule = self.config.required_labels
        if not rule.enabled:
            return ValidationResult(
                rule_name="required_labels",
                severity=rule.severity,
                passed=True,
                message="Rule disabled",
            )

        label_keys = {label["key"] for label in labels}
        missing_labels = [key for key in rule.required_labels if key not in label_keys]

        if missing_labels:
            return ValidationResult(
                rule_name="required_labels",
                severity=rule.severity,
                passed=False,
                message=f"Missing required labels: {', '.join(missing_labels)}",
            )

        return ValidationResult(
            rule_name="required_labels",
            severity=rule.severity,
            passed=True,
            message=f"All required labels present: {', '.join(rule.required_labels)}",
        )

    def validate_icon_file(self, workflow_dir: Path) -> ValidationResult:
        """Check if icon file exists."""
        rule = self.config.icon_file
        if not rule.enabled:
            return ValidationResult(
                rule_name="icon_file",
                severity=rule.severity,
                passed=True,
                message="Rule disabled",
            )

        # Check for exact filename first
        icon_path = workflow_dir / rule.icon_filename
        if icon_path.exists():
            return ValidationResult(
                rule_name="icon_file",
                severity=rule.severity,
                passed=True,
                message=f"Icon file found: {rule.icon_filename}",
            )

        # Check for any file with allowed extensions
        for file in workflow_dir.iterdir():
            if (
                file.suffix.lower() in rule.allowed_extensions
                and "icon" in file.name.lower()
            ):
                return ValidationResult(
                    rule_name="icon_file",
                    severity=rule.severity,
                    passed=True,
                    message=f"Icon file found: {file.name}",
                )

        return ValidationResult(
            rule_name="icon_file",
            severity=rule.severity,
            passed=False,
            message=f"No icon file found. Expected '{rule.icon_filename}' or file with extensions: {', '.join(rule.allowed_extensions)}",
        )

    def _discover_available_engines(self, adapters_path: Optional[Path]) -> List[str]:
        """Discover available workflow engines from adapter files."""
        if not adapters_path or not adapters_path.exists():
            return ["airflow", "dummy"]  # Default fallback

        engines = []
        adapters_dir = adapters_path / "adapters"
        if adapters_dir.exists():
            for file in adapters_dir.glob("*_adapter.py"):
                # Extract engine name from filename (e.g., dummy_adapter.py -> dummy)
                engine_name = file.stem.replace("_adapter", "")
                engines.append(engine_name)

        return engines if engines else ["airflow", "dummy"]

    def validate_workflow_engine(self, workflow_engine: str) -> ValidationResult:
        """Check if workflow_engine is valid."""
        rule = self.config.workflow_engine
        if not rule.enabled:
            return ValidationResult(
                rule_name="workflow_engine",
                severity=rule.severity,
                passed=True,
                message="Rule disabled",
            )

        # Determine allowed engines
        if rule.allowed_engines is None:
            allowed_engines = self._discover_available_engines(rule.adapters_path)
            discovery_note = " (auto-discovered)"
        else:
            allowed_engines = rule.allowed_engines
            discovery_note = ""

        if workflow_engine in allowed_engines:
            return ValidationResult(
                rule_name="workflow_engine",
                severity=rule.severity,
                passed=True,
                message=f"Workflow engine '{workflow_engine}' is valid{discovery_note}",
            )

        return ValidationResult(
            rule_name="workflow_engine",
            severity=rule.severity,
            passed=False,
            message=f"Invalid workflow engine '{workflow_engine}'. Allowed values{discovery_note}: {', '.join(allowed_engines)}",
        )

    def validate_all(
        self, workflow_dir: Path, metadata: Dict, workflow_engine: str
    ) -> List[ValidationResult]:
        """Run all validation rules."""
        self.results = []

        # Validate required labels
        labels = metadata.get("labels", [])
        self.results.append(self.validate_required_labels(labels))

        # Validate icon file
        self.results.append(self.validate_icon_file(workflow_dir))

        # Validate workflow engine
        self.results.append(self.validate_workflow_engine(workflow_engine))

        return self.results

    def has_errors(self) -> bool:
        """Check if any validation resulted in errors."""
        return any(
            not result.passed and result.severity == "error" for result in self.results
        )

    def has_warnings(self) -> bool:
        """Check if any validation resulted in warnings."""
        return any(
            not result.passed and result.severity == "warning"
            for result in self.results
        )

    def get_summary(self) -> str:
        """Get a summary of validation results."""
        errors = [r for r in self.results if not r.passed and r.severity == "error"]
        warnings = [r for r in self.results if not r.passed and r.severity == "warning"]
        passed = [r for r in self.results if r.passed]

        summary_parts = []
        if errors:
            summary_parts.append(f"{len(errors)} error(s)")
        if warnings:
            summary_parts.append(f"{len(warnings)} warning(s)")
        if passed:
            summary_parts.append(f"{len(passed)} check(s) passed")

        return ", ".join(summary_parts) if summary_parts else "No checks performed"
