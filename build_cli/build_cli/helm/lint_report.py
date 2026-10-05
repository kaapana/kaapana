import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

UNIT_PATTERN = re.compile(r"^==> Linting (?P<unit>.+)$")
FINDING_PATTERN = re.compile(r"^\[(?P<level>WARNING|ERROR)\] (?P<message>.*)$")
FILE_PATTERN = re.compile(r"^(?P<file>[^\s:]+): (?P<detail>.*)$")


def parse_helm_lint(stdout: str) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    unit = "."
    for line in stdout.splitlines():
        unit_match = UNIT_PATTERN.match(line)
        if unit_match:
            unit = unit_match["unit"].strip()
            continue
        finding_match = FINDING_PATTERN.match(line)
        if finding_match:
            message = finding_match["message"]
            file_match = FILE_PATTERN.match(message)
            file = file_match["file"] if file_match else "Chart.yaml"
            if file.startswith("/"):
                file = "Chart.yaml"
            findings.append(
                {
                    "unit": unit,
                    "level": finding_match["level"],
                    "file": file,
                    "message": file_match["detail"] if file_match else message,
                }
            )
        elif findings and line.startswith((" ", "\t")) and line.strip():
            findings[-1]["message"] += f" {line.strip()}"
    return findings


def write_junit_report(suite: str, cases: List[Dict[str, Optional[str]]], report_file: Path) -> None:
    failures = [case for case in cases if case["failure"]]
    root = ET.Element("testsuites", name=suite, tests=str(len(cases)), failures=str(len(failures)))
    testsuite = ET.SubElement(root, "testsuite", name=suite, tests=str(len(cases)), failures=str(len(failures)))
    for case in cases:
        testcase = ET.SubElement(testsuite, "testcase", classname=case["classname"] or "", name=case["name"] or "")
        if case["failure"]:
            ET.SubElement(testcase, "failure", message=case["failure"]).text = case["failure"]
    ET.indent(root)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(ET.tostring(root, encoding="unicode"))


def lint_cases(findings: List[Dict[str, str]], linted_charts: List[str]) -> List[Dict[str, Optional[str]]]:
    failing_charts = {finding["chart"] for finding in findings}
    failed: List[Dict[str, Optional[str]]] = [
        {
            "classname": finding["chart"],
            "name": f"{finding['unit']}/{finding['file']}",
            "failure": f"[{finding['level']}] {finding['message']}",
        }
        for finding in findings
    ]
    passed: List[Dict[str, Optional[str]]] = [
        {"classname": chart, "name": "helm lint", "failure": None}
        for chart in linted_charts
        if chart not in failing_charts
    ]
    return failed + passed


def short_message(message: str) -> str:
    message = re.split(r": metadata\.name: Invalid value| \(e\.g\.", message)[0]
    missing = re.match(r"(chart directory is missing these dependencies): (.*)", message)
    if missing:
        names = missing[2].split(",")
        listed = ", ".join(names[:3])
        return f"{missing[1]}: {listed}" + (f" (+{len(names) - 3} more)" if len(names) > 3 else "")
    return message


def finding_owner(finding: Dict[str, str]) -> str:
    return finding["chart"] if finding["unit"] == "." else Path(finding["unit"]).name


def finding_lines(findings: List[Dict[str, str]]) -> List[str]:
    counts = Counter(
        (finding_owner(finding), finding["file"], short_message(finding["message"])) for finding in findings
    )
    return [
        f"{owner}/{file}: {message}" + (f" (in {count} places)" if count > 1 else "")
        for (owner, file, message), count in counts.items()
    ]
