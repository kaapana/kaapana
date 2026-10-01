import json
import shutil
from pathlib import Path
from subprocess import CompletedProcess, run

from build_cli.helm.lint_report import rendered_location

ENFORCED_CONFIG = ".kube-linter.yaml"
ADVISORY_CONFIG = "ci/ci-code/lint/kube-linter-quality.yaml"


def is_installed() -> bool:
    return shutil.which("kube-linter") is not None


def lint_directory(directory: Path, config: Path) -> CompletedProcess:
    return run(
        ["kube-linter", "lint", "--config", str(config), "--format", "json", str(directory)],
        capture_output=True,
        text=True,
        timeout=300,
    )


def parse_reports(stdout: str, render_dir: Path, chart: str) -> list[dict[str, str]] | None:
    try:
        reports = json.loads(stdout).get("Reports") or []
    except (json.JSONDecodeError, AttributeError):
        return None
    findings = []
    for report in reports:
        unit, file = rendered_location(render_dir, Path(report["Object"]["Metadata"]["FilePath"]))
        k8s_object = report["Object"]["K8sObject"]
        findings.append(
            {
                "chart": chart,
                "unit": unit,
                "file": file,
                "resource": f"{k8s_object['GroupVersionKind']['Kind']}/{k8s_object['Name']}",
                "check": report["Check"],
                "message": f"{report['Diagnostic']['Message']} ({report['Check']})",
                "remediation": report.get("Remediation", ""),
            }
        )
    return findings
