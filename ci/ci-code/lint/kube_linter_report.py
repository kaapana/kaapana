import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


def source_chart_dirs() -> dict[str, Path]:
    listed = subprocess.run(["git", "ls-files", "-z", "*Chart.yaml"], capture_output=True, text=True, check=True)
    dirs: dict[str, Path] = {}
    for chart_file in filter(None, listed.stdout.split("\0")):
        name = re.search(r"^name:\s*['\"]?([^'\"\s]+)", Path(chart_file).read_text(), re.MULTILINE)
        if name:
            dirs.setdefault(name[1], Path(chart_file).parent)
    return dirs


def source_path(rendered_file: Path, rendered_dir: Path, chart_dirs: dict[str, Path]) -> str:
    if not rendered_file.is_relative_to(rendered_dir):
        return str(rendered_file)
    parts = rendered_file.relative_to(rendered_dir).parts[1:]
    chart, index = parts[0], 1
    while len(parts) > index + 2 and parts[index] == "charts":
        chart, index = parts[index + 1], index + 2
    if chart not in chart_dirs:
        return "/".join(parts)
    return str(chart_dirs[chart] / Path(*parts[index:]))


def main() -> None:
    report_file, rendered_dir = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
    try:
        reports = json.loads(report_file.read_text()).get("Reports") or []
    except (OSError, json.JSONDecodeError):
        reports = []
    chart_dirs = source_chart_dirs()
    issues: dict[str, dict] = {}
    for report in reports:
        path = source_path(Path(report["Object"]["Metadata"]["FilePath"]).resolve(), rendered_dir, chart_dirs)
        k8s_object = report["Object"]["K8sObject"]
        resource = f"{k8s_object['GroupVersionKind']['Kind']}/{k8s_object['Name']}"
        description = f"{resource}: {report['Diagnostic']['Message']} ({report['Check']})"
        fingerprint = hashlib.sha256(f"{report['Check']}|{path}|{description}".encode()).hexdigest()
        issues.setdefault(
            fingerprint,
            {
                "description": description,
                "check_name": f"kube-linter/{report['Check']}",
                "fingerprint": fingerprint,
                "severity": "minor",
                "location": {"path": path, "lines": {"begin": 1}},
            },
        )
    print(f"kube-linter: {len(issues)} advisory findings", file=sys.stderr)
    print(json.dumps(list(issues.values()), indent=2))


if __name__ == "__main__":
    main()
