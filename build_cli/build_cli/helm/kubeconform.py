import json
import os
import re
import shutil
from pathlib import Path
from subprocess import CompletedProcess, run

from build_cli.helm.lint_report import rendered_location

SCHEMA_LOCATIONS = (
    "default",
    "https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json",
)
FAILED_STATUSES = ("statusInvalid", "statusError")


def is_installed() -> bool:
    return shutil.which("kubeconform") is not None


def validate_directory(directory: Path) -> CompletedProcess:
    command = ["kubeconform", "-strict", "-verbose", "-output", "json"]
    for location in SCHEMA_LOCATIONS:
        command += ["-schema-location", location]

    skip_kinds = os.environ.get("KUBECONFORM_SKIP_KINDS", "")
    if skip_kinds:
        command += ["-skip", skip_kinds]

    return run(
        [*command, str(directory)],
        capture_output=True,
        text=True,
        timeout=300,
    )


def clean_message(message: str) -> str:
    details = re.split(r"jsonschema validation failed with '[^']*' - ", message, maxsplit=1)
    if len(details) == 2:
        return "; ".join(part.strip() for part in details[1].split(" - "))
    return message


def parse_resources(stdout: str, render_dir: Path, chart: str) -> list[dict[str, str]] | None:
    try:
        resources = json.loads(stdout).get("resources") or []
    except (json.JSONDecodeError, AttributeError):
        return None
    results = []
    for resource in resources:
        if resource.get("status") == "statusEmpty":
            continue
        unit, file = rendered_location(render_dir, Path(resource["filename"]))
        errors = resource.get("validationErrors") or []
        message = "; ".join(f"{error['path']}: {error['msg']}" for error in errors) or clean_message(
            resource.get("msg", "")
        )
        results.append(
            {
                "chart": chart,
                "unit": unit,
                "file": file,
                "resource": f"{resource.get('kind') or '?'}/{resource.get('name') or '?'}",
                "status": resource["status"],
                "message": message,
            }
        )
    return results
